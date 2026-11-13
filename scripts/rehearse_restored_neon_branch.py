#!/usr/bin/env python3
"""Migrate the exact isolated Neon restore branch and produce a preservation report.

This script is deliberately pinned to the known restored branch. It refuses to
run against production, a different Neon project/branch, a pooler, or a database
not at the expected starting revision. It never prints the connection URL.
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import asyncpg

from app.db_url import prepare_asyncpg_connection

EXPECTED_PROJECT_ID = "rapid-bonus-26545234"
EXPECTED_BRANCH_ID = "br-little-cake-aovrrz0y"
EXPECTED_DATABASE = "neondb"
EXPECTED_START_REVISION = "0042_dedup_key"
EXPECTED_HEAD_REVISION = "0111_rule_outcome_ledger"
EVIDENCE_TABLES = (
    "rescue_audit_log",
    "webhook_endpoints",
    "webhook_deliveries",
)
EXPECTED_PROVIDER_MEMBERSHIPS = {
    ("neondb_owner", "nlc_app_role", "cloud_admin", True, False, False),
    ("neondb_owner", "nlc_ci_audit_role", "cloud_admin", True, False, False),
}
REPORT_PATH = Path("artifacts/neon-restored-branch-rehearsal.json")


def _database_url(secret_name: str) -> str:
    value = os.environ.get(secret_name, "").strip()
    if not value:
        raise RuntimeError(
            f"{secret_name} is required; use the direct connection URL "
            "for the pinned restored branch."
        )
    if "-pooler." in value.lower():
        raise RuntimeError("Refusing a pooled Neon URL for a migration rehearsal.")
    return value


def _connect_args(raw_url: str) -> tuple[str, dict[str, Any]]:
    url, args = prepare_asyncpg_connection(raw_url, require_tls=True)
    if url.startswith("postgresql+asyncpg://"):
        url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return url, args


async def _connect(raw_url: str) -> asyncpg.Connection:
    url, args = _connect_args(raw_url)
    return await asyncpg.connect(url, **args)


async def _identity(conn: asyncpg.Connection) -> dict[str, Any]:
    row = await conn.fetchrow(
        """
        SELECT current_setting('neon.project_id', true) AS project_id,
               current_setting('neon.branch_id', true) AS branch_id,
               current_database() AS database_name,
               current_user AS current_user,
               session_user AS session_user
        """
    )
    versions = await conn.fetch(
        "SELECT version_num FROM public.alembic_version ORDER BY version_num"
    )
    return {
        **dict(row),
        "alembic_versions": [item["version_num"] for item in versions],
    }


async def _table_row_counts(conn: asyncpg.Connection) -> dict[str, int]:
    rows = await conn.fetch(
        """
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
          AND tablename <> 'alembic_version'
        ORDER BY tablename
        """
    )
    counts: dict[str, int] = {}
    for row in rows:
        table_name = row["tablename"]
        quoted = '"' + table_name.replace('"', '""') + '"'
        counts[table_name] = int(
            await conn.fetchval(f"SELECT count(*) FROM public.{quoted}")
        )
    return counts


async def _security_audit(conn: asyncpg.Connection) -> dict[str, Any]:
    role_rows = await conn.fetch(
        """
        SELECT rolname, rolcanlogin, rolsuper, rolcreatedb, rolcreaterole,
               rolinherit, rolreplication, rolbypassrls
        FROM pg_roles
        WHERE rolname IN ('nlc_app_role', 'nlc_ci_audit_role')
        ORDER BY rolname
        """
    )
    roles = [dict(row) for row in role_rows]
    if {row["rolname"] for row in roles} != {
        "nlc_app_role",
        "nlc_ci_audit_role",
    }:
        raise RuntimeError("One or more restricted NLC runtime roles are missing.")
    for role in roles:
        if (
            not role["rolcanlogin"]
            or role["rolsuper"]
            or role["rolcreatedb"]
            or role["rolcreaterole"]
            or role["rolinherit"]
            or role["rolreplication"]
            or role["rolbypassrls"]
        ):
            raise RuntimeError(
                f"Restricted role {role['rolname']} has unsafe role attributes."
            )

    membership_rows = await conn.fetch(
        """
        SELECT member_role.rolname AS member_role,
               granted_role.rolname AS granted_role,
               grantor_role.rolname AS grantor_role,
               membership.admin_option,
               membership.inherit_option,
               membership.set_option
        FROM pg_auth_members membership
        JOIN pg_roles granted_role ON granted_role.oid = membership.roleid
        JOIN pg_roles member_role ON member_role.oid = membership.member
        JOIN pg_roles grantor_role ON grantor_role.oid = membership.grantor
        WHERE member_role.rolname IN ('nlc_app_role', 'nlc_ci_audit_role', 'neondb_owner')
           OR granted_role.rolname IN ('nlc_app_role', 'nlc_ci_audit_role', 'neondb_owner')
        ORDER BY 1, 2, 3
        """
    )
    memberships = {
        (
            row["member_role"],
            row["granted_role"],
            row["grantor_role"],
            row["admin_option"],
            row["inherit_option"],
            row["set_option"],
        )
        for row in membership_rows
        if row["member_role"] in {"nlc_app_role", "nlc_ci_audit_role"}
        or row["granted_role"] in {"nlc_app_role", "nlc_ci_audit_role"}
    }
    if memberships != EXPECTED_PROVIDER_MEMBERSHIPS:
        raise RuntimeError(
            "Restricted NLC role membership topology differs from the approved "
            f"Neon provider exception: {sorted(memberships)!r}"
        )

    rls_gaps = await conn.fetch(
        """
        SELECT c.relname
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND c.relkind = 'r'
          AND c.relname <> 'alembic_version'
          AND (NOT c.relrowsecurity OR NOT c.relforcerowsecurity)
        ORDER BY c.relname
        """
    )
    if rls_gaps:
        raise RuntimeError(
            "Public tenant tables without ENABLE + FORCE RLS: "
            + ", ".join(row["relname"] for row in rls_gaps)
        )

    dangerous_privileges = await conn.fetch(
        """
        SELECT c.relname
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND c.relkind = 'r'
          AND (
              has_table_privilege('nlc_app_role', c.oid, 'TRUNCATE')
              OR has_table_privilege('nlc_app_role', c.oid, 'REFERENCES')
              OR has_table_privilege('nlc_app_role', c.oid, 'TRIGGER')
          )
        ORDER BY c.relname
        """
    )
    app_schema_create = await conn.fetchval(
        "SELECT has_schema_privilege('nlc_app_role', 'public', 'CREATE')"
    )
    audit_role_schema_create = await conn.fetchval(
        "SELECT has_schema_privilege('nlc_ci_audit_role', 'public', 'CREATE')"
    )
    audit_role_public_access = await conn.fetch(
        """
        SELECT c.relname
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND c.relkind IN ('r', 'v', 'm')
          AND (
              has_table_privilege('nlc_ci_audit_role', c.oid, 'SELECT')
              OR has_table_privilege('nlc_ci_audit_role', c.oid, 'INSERT')
              OR has_table_privilege('nlc_ci_audit_role', c.oid, 'UPDATE')
              OR has_table_privilege('nlc_ci_audit_role', c.oid, 'DELETE')
          )
        ORDER BY c.relname
        """
    )
    audit_schema_usage = await conn.fetchval(
        "SELECT has_schema_privilege('nlc_ci_audit_role', 'audit', 'USAGE')"
    )
    audit_view_select = await conn.fetchval(
        "SELECT has_table_privilege('nlc_ci_audit_role', 'audit.active_legal_rule_ids', 'SELECT')"
    )
    key_table_exists = await conn.fetchval(
        "SELECT to_regclass('nlc_private.rls_signing_key') IS NOT NULL"
    )
    app_can_use_private_schema = await conn.fetchval(
        "SELECT has_schema_privilege('nlc_app_role', 'nlc_private', 'USAGE')"
    )
    app_can_read_signing_key = (
        await conn.fetchval(
            "SELECT has_table_privilege('nlc_app_role', 'nlc_private.rls_signing_key', 'SELECT')"
        )
        if key_table_exists
        else True
    )
    signing_key_state = (
        await conn.fetchrow(
            """
            SELECT count(*)::int AS rows, min(length(secret))::int AS minimum_length
            FROM nlc_private.rls_signing_key
            WHERE singleton = true
            """
        )
        if key_table_exists
        else None
    )
    if (
        app_schema_create
        or audit_role_schema_create
        or dangerous_privileges
        or audit_role_public_access
        or not audit_schema_usage
        or not audit_view_select
        or not key_table_exists
        or app_can_use_private_schema
        or app_can_read_signing_key
        or signing_key_state is None
        or signing_key_state["rows"] != 1
        or signing_key_state["minimum_length"] is None
        or signing_key_state["minimum_length"] < 32
    ):
        raise RuntimeError(
            "Runtime/audit role grants do not match the restricted production contract."
        )

    views = await conn.fetch(
        """
        SELECT c.relname, c.reloptions
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public'
          AND c.relkind = 'v'
          AND c.relname IN (
              'vw_admin_dashboard_kpis',
              'vw_company_flag_summary',
              'vw_risk_distribution',
              'vw_upcoming_deadlines',
              'vw_revenue_pipeline'
          )
        ORDER BY c.relname
        """
    )
    view_security = {
        row["relname"]: row["reloptions"] or [] for row in views
    }
    expected_views = {
        "vw_admin_dashboard_kpis",
        "vw_company_flag_summary",
        "vw_risk_distribution",
        "vw_upcoming_deadlines",
        "vw_revenue_pipeline",
    }
    if set(view_security) != expected_views:
        raise RuntimeError(
            "Expected all five dashboard security-invoker views; observed "
            f"{sorted(view_security)!r}."
        )
    for name, options in view_security.items():
        if "security_invoker=true" not in options:
            raise RuntimeError(f"Dashboard view {name} is not security_invoker.")

    evidence = []
    for table in EVIDENCE_TABLES:
        row = await conn.fetchrow(
            """
            SELECT c.relrowsecurity, c.relforcerowsecurity,
                   obj_description(c.oid, 'pg_class') AS table_comment
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public' AND c.relname = $1 AND c.relkind = 'r'
            """,
            table,
        )
        if row is None:
            raise RuntimeError(f"Required evidence table public.{table} is missing.")
        count = int(await conn.fetchval(f'SELECT count(*) FROM public."{table}"'))
        comment = row["table_comment"] or ""
        if not row["relrowsecurity"] or not row["relforcerowsecurity"]:
            raise RuntimeError(f"Evidence table {table} is not ENABLE + FORCE RLS.")
        if "SCHEMA-ONLY RECONSTRUCTION" not in comment:
            raise RuntimeError(
                f"Evidence table {table} lacks its schema-only reconstruction comment."
            )
        if count != 0:
            raise RuntimeError(
                f"Expected schema-only evidence table {table} to be empty; found {count} rows."
            )
        evidence.append(
            {
                "table": table,
                "rows": count,
                "rls_enabled": row["relrowsecurity"],
                "rls_forced": row["relforcerowsecurity"],
                "comment": comment,
            }
        )

    return {
        "restricted_roles": roles,
        "provider_role_memberships": [
            {
                "member": item[0],
                "granted_role": item[1],
                "grantor": item[2],
                "admin_option": item[3],
                "inherit_option": item[4],
                "set_option": item[5],
            }
            for item in sorted(memberships)
        ],
        "rls_gap_tables": [],
        "app_schema_create": app_schema_create,
        "app_dangerous_privilege_tables": [],
        "audit_role_schema_create": audit_role_schema_create,
        "audit_role_public_access_tables": [],
        "audit_schema_usage": audit_schema_usage,
        "audit_view_select": audit_view_select,
        "private_signing_key_table_exists": key_table_exists,
        "app_can_use_private_schema": app_can_use_private_schema,
        "app_can_read_signing_key": app_can_read_signing_key,
        "private_signing_key_rows": signing_key_state["rows"] if signing_key_state else 0,
        "private_signing_key_minimum_length": signing_key_state["minimum_length"] if signing_key_state else None,
        "security_invoker_views": view_security,
        "schema_only_evidence_tables": evidence,
    }


async def _app_role_spoof_audit(raw_url: str) -> dict[str, Any]:
    conn = await _connect(raw_url)
    try:
        identity_row = await conn.fetchrow(
            """
            SELECT current_setting('neon.project_id', true) AS project_id,
                   current_setting('neon.branch_id', true) AS branch_id,
                   current_database() AS database_name,
                   current_user AS current_user,
                   session_user AS session_user
            """
        )
        identity = dict(identity_row)
        if identity["project_id"] != EXPECTED_PROJECT_ID:
            raise RuntimeError("App-role connection points to a different Neon project.")
        if identity["branch_id"] != EXPECTED_BRANCH_ID:
            raise RuntimeError("App-role connection points to a different Neon branch.")
        if identity["database_name"] != EXPECTED_DATABASE:
            raise RuntimeError("App-role connection points to a different database.")
        if (
            identity["current_user"] != "nlc_app_role"
            or identity["session_user"] != "nlc_app_role"
        ):
            raise RuntimeError("RLS spoof test must connect directly as nlc_app_role.")

        async with conn.transaction():
            await conn.execute(
                """
                SELECT set_config('app.current_user_id', 'ADMIN', true),
                       set_config('app.current_user_signature', repeat('0', 64), true)
                """
            )
            principal = await conn.fetchval(
                "SELECT public.nlc_current_user_principal()"
            )
            visible = await conn.fetchrow(
                """
                SELECT
                    (SELECT count(*) FROM public.companies) AS companies,
                    (SELECT count(*) FROM public.users) AS users,
                    (SELECT count(*) FROM public.compliance_evaluation_runs) AS evaluations
                """
            )
        if principal is not None or any(int(value) != 0 for value in visible.values()):
            raise RuntimeError(
                "Unsigned ADMIN spoof was not rejected by the signed RLS boundary."
            )
        return {
            "identity": identity,
            "unsigned_admin_principal": principal,
            "visible_rows_with_unsigned_admin": dict(visible),
            "result": "PASS",
        }
    finally:
        await conn.close()


def _run_command(command: list[str], env: dict[str, str]) -> str:
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    output = (result.stdout or "") + (result.stderr or "")
    for secret_name in (
        "NLC_RESTORED_REHEARSAL_DATABASE_URL",
        "NLC_RESTORED_REHEARSAL_APP_DATABASE_URL",
    ):
        secret = env.get(secret_name, "")
        if secret:
            output = output.replace(secret, "[REDACTED_DATABASE_URL]")
    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed ({result.returncode}): {' '.join(command)}\n"
            + output[-12000:]
        )
    return output[-12000:]


async def main() -> int:
    report: dict[str, Any] = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "expected_project_id": EXPECTED_PROJECT_ID,
        "expected_branch_id": EXPECTED_BRANCH_ID,
        "expected_start_revision": EXPECTED_START_REVISION,
        "expected_head_revision": EXPECTED_HEAD_REVISION,
        "migration_applied": False,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    try:
        raw_url = _database_url("NLC_RESTORED_REHEARSAL_DATABASE_URL")
        app_raw_url = _database_url("NLC_RESTORED_REHEARSAL_APP_DATABASE_URL")
        conn = await _connect(raw_url)
        try:
            before_identity = await _identity(conn)
            report["before_identity"] = before_identity
            if before_identity["project_id"] != EXPECTED_PROJECT_ID:
                raise RuntimeError("Refusing: Neon project ID does not match the pinned project.")
            if before_identity["branch_id"] != EXPECTED_BRANCH_ID:
                raise RuntimeError("Refusing: Neon branch ID is not the isolated restored branch.")
            if before_identity["database_name"] != EXPECTED_DATABASE:
                raise RuntimeError("Refusing: connected database name is not neondb.")
            if (
                before_identity["current_user"] != "neondb_owner"
                or before_identity["session_user"] != "neondb_owner"
            ):
                raise RuntimeError(
                    "Refusing: migration connection must log in directly as the Neon branch owner."
                )
            if before_identity["alembic_versions"] != [EXPECTED_START_REVISION]:
                raise RuntimeError(
                    "Refusing: restored branch must be exactly at "
                    f"{EXPECTED_START_REVISION}; observed "
                    f"{before_identity['alembic_versions']!r}."
                )
            before_counts = await _table_row_counts(conn)
            report["before_table_row_counts"] = before_counts
        finally:
            await conn.close()

        env = os.environ.copy()
        env["MIGRATION_DATABASE_URL"] = raw_url
        env["DATABASE_URL"] = raw_url
        report["alembic_upgrade_output"] = _run_command(
            ["alembic", "upgrade", "head"], env
        )
        report["migration_applied"] = True
        report["alembic_graph_audit_output"] = _run_command(
            ["python", "scripts/audit_alembic_graph.py"], env
        )
        report["alembic_heads_output"] = _run_command(["alembic", "heads"], env)

        conn = await _connect(raw_url)
        try:
            after_identity = await _identity(conn)
            report["after_identity"] = after_identity
            if after_identity["project_id"] != EXPECTED_PROJECT_ID:
                raise RuntimeError("Neon project identity changed during rehearsal.")
            if after_identity["branch_id"] != EXPECTED_BRANCH_ID:
                raise RuntimeError("Neon branch identity changed during rehearsal.")
            if after_identity["alembic_versions"] != [EXPECTED_HEAD_REVISION]:
                raise RuntimeError(
                    f"Expected one head {EXPECTED_HEAD_REVISION}; observed "
                    f"{after_identity['alembic_versions']!r}."
                )
            after_counts = await _table_row_counts(conn)
            report["after_table_row_counts"] = after_counts
            report["security_audit"] = await _security_audit(conn)
        finally:
            await conn.close()
        report["app_role_spoof_audit"] = await _app_role_spoof_audit(app_raw_url)

        decreases = {
            table: {"before": count, "after": after_counts.get(table)}
            for table, count in before_counts.items()
            if after_counts.get(table) is None or after_counts[table] < count
        }
        report["row_count_decreases"] = decreases
        if decreases:
            raise RuntimeError(
                "Migration reduced or removed pre-existing table row counts; "
                f"manual data-preservation review required: {decreases!r}"
            )

        report["status"] = "PASS"
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        REPORT_PATH.write_text(json.dumps(report, indent=2, default=str) + "\n")
        print(
            "PASS: isolated restored Neon branch migrated from "
            f"{EXPECTED_START_REVISION} to {EXPECTED_HEAD_REVISION}; "
            "branch identity, row counts, RLS, role privileges, views and "
            "schema-only evidence tables verified."
        )
        return 0
    except Exception as exc:  # noqa: BLE001 - preserve the failure report for the operator
        report["status"] = "FAIL"
        report["error"] = str(exc)
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        REPORT_PATH.write_text(json.dumps(report, indent=2, default=str) + "\n")
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
