#!/usr/bin/env python3
"""Rehearse the exact production 0112 schema through 0122 on a disposable Neon child.

The script is pinned to the NLC production project and the preserved backup
branch. It captures immutable fingerprints for historical finding/score tables
and the exact legacy INC-001/INC-002 payloads before running Alembic.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import asyncpg
from sqlalchemy.engine import make_url

from app.db_url import prepare_asyncpg_connection

PROJECT_ID = "rapid-bonus-26545234"
PARENT_BRANCH_ID = "br-divine-glade-aovapmi5"
DATABASE = "neondb"
START_REVISION = "0112_runtime_acl_and_alembic_rls"
HEAD_REVISION = "0122_rls_staff_scope_and_score_history"
HISTORICAL_TABLES = (
    "compliance_flags",
    "compliance_score_history",
    "compliance_evaluation_runs",
    "rescue_audit_log",
)
LEGACY_FINGERPRINTS = {
    "INC-001": {
        ("Certificate of Incorporation Not Obtained",
         "Section 9, Companies Act 1994 (Bangladesh)",
         "certificate_obtained == False"),
        ("Memorandum and Articles Not Filed",
         "Section 23, Companies Act 1994 (Bangladesh)",
         "moa_aoa_filed == False"),
    },
    "INC-002": {
        ("Memorandum and Articles Not Filed",
         "Section 11, Companies Act 1994 (Bangladesh)",
         "moa_filed == False OR aoa_filed == False"),
        ("Form III Not Filed",
         "Section 23, Companies Act 1994 (Bangladesh)",
         "paid_up_capital_bdt > 0 AND form_iii_filed == False AND days_since_incorporation > 28"),
    },
}
REPORT = Path("artifacts/neon-production-0112-to-0122.json")


def _url() -> str:
    raw = os.environ.get("MIGRATION_DATABASE_URL", "").strip()
    if not raw or "-pooler." in raw.lower():
        raise RuntimeError("A direct MIGRATION_DATABASE_URL is required.")
    return raw


async def _connect() -> asyncpg.Connection:
    url, args = prepare_asyncpg_connection(_url(), require_tls=True)
    dsn = make_url(url).set(drivername="postgresql").render_as_string(hide_password=False)
    conn = await asyncpg.connect(dsn, **args)
    identity = await conn.fetchrow(
        "SELECT session_user, current_user, current_database(), "
        "current_setting('neon.project_id', true) AS project_id, "
        "current_setting('neon.branch_id', true) AS branch_id"
    )
    if identity["session_user"] != "nlc_migration_user" or identity["current_user"] != "nlc_migration_user":
        await conn.close()
        raise RuntimeError("Expected nlc_migration_user login before SET ROLE.")
    if identity["current_database"] != DATABASE or identity["project_id"] != PROJECT_ID:
        await conn.close()
        raise RuntimeError(f"Wrong Neon target: {dict(identity)!r}")
    if identity["branch_id"] != os.environ.get("NLC_REHEARSAL_BRANCH_ID"):
        await conn.close()
        raise RuntimeError("Connection does not point to the disposable rehearsal branch.")
    await conn.execute("SET ROLE nlc_migration_owner")
    role = await conn.fetchrow("SELECT session_user, current_user")
    if role["session_user"] != "nlc_migration_user" or role["current_user"] != "nlc_migration_owner":
        await conn.close()
        raise RuntimeError("Could not assume nlc_migration_owner.")
    return conn


def _canonical(value: Any) -> str:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            pass
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


async def _rows_digest(conn: asyncpg.Connection, table: str) -> dict[str, Any]:
    exists = await conn.fetchval(
        "SELECT to_regclass($1) IS NOT NULL", f"public.{table}"
    )
    if not exists:
        raise RuntimeError(f"Required historical table public.{table} is missing.")
    rows = await conn.fetch(f'SELECT to_jsonb(t) AS payload FROM public."{table}" t ORDER BY to_jsonb(t)::text')
    digest = hashlib.sha256()
    for row in rows:
        digest.update(_canonical(row["payload"]).encode("utf-8"))
        digest.update(b"\n")
    return {"rows": len(rows), "sha256": digest.hexdigest()}


async def _legacy_payloads(conn: asyncpg.Connection) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for rule_id, allowed in LEGACY_FINGERPRINTS.items():
        row = await conn.fetchrow(
            "SELECT to_jsonb(r) AS payload, rule_name, statutory_basis, "
            "rule_condition ->> 'trigger' AS trigger "
            "FROM public.legal_rules r WHERE rule_id=$1",
            rule_id,
        )
        if row is None:
            if rule_id == "INC-002":
                continue
            raise RuntimeError("INC-001 is missing before quarantine.")
        fingerprint = (row["rule_name"], row["statutory_basis"], row["trigger"])
        if fingerprint not in allowed:
            raise RuntimeError(f"{rule_id} does not match a known legacy fingerprint: {fingerprint!r}")
        output[rule_id] = row["payload"]
    return output


async def _alembic_revision(conn: asyncpg.Connection) -> list[str]:
    rows = await conn.fetch("SELECT version_num FROM public.alembic_version ORDER BY version_num")
    return [row["version_num"] for row in rows]


async def _postflight(conn: asyncpg.Connection, before_tables: dict[str, Any], before_rules: dict[str, Any]) -> dict[str, Any]:
    after_tables = {table: await _rows_digest(conn, table) for table in HISTORICAL_TABLES}
    if before_tables != after_tables:
        raise RuntimeError(f"Historical finding/score data changed: before={before_tables!r}, after={after_tables!r}")

    archive = await conn.fetch(
        "SELECT legacy_rule_id, original_payload, payload_sha256 "
        "FROM public.legal_rule_identity_archive ORDER BY legacy_rule_id"
    )
    archived = {row["legacy_rule_id"]: row for row in archive}
    for rule_id, original in before_rules.items():
        row = archived.get(rule_id)
        if row is None:
            raise RuntimeError(f"0115 did not archive {rule_id}.")
        original_json = _canonical(original)
        archived_json = _canonical(row["original_payload"])
        if original_json != archived_json:
            raise RuntimeError(f"0115 archive payload differs from original {rule_id}.")
        expected_hash = hashlib.sha256(original_json.encode("utf-8")).hexdigest()
        if row["payload_sha256"] != expected_hash:
            raise RuntimeError(f"0115 archive SHA-256 mismatch for {rule_id}.")

    quarantined = await conn.fetch(
        "SELECT rule_id, is_active, default_severity, score_impact, "
        "is_black_override, verification_status FROM public.legal_rules "
        "WHERE rule_id = ANY($1::text[]) ORDER BY rule_id",
        list(before_rules),
    )
    for row in quarantined:
        if row["is_active"] or row["default_severity"] != "NOT_EVALUATED" or row["score_impact"] != 0 or row["is_black_override"] or row["verification_status"] != "PENDING":
            raise RuntimeError(f"Legacy rule was not safely quarantined: {dict(row)!r}")

    required_tables = (
        "legal_rule_identity_archive", "legal_rule_identities", "legal_rule_aliases",
        "legal_rule_revisions", "compliance_finding_bindings",
        "compliance_finding_evidence", "legal_rule_finding_contexts",
        "legal_rule_finding_context_reviews",
    )
    missing = [name for name in required_tables if not await conn.fetchval("SELECT to_regclass($1) IS NOT NULL", f"public.{name}")]
    if missing:
        raise RuntimeError(f"Canonical identity/evidence migration tables missing: {missing!r}")

    score_history = await conn.fetchrow(
        "SELECT c.relrowsecurity AS rls, c.relforcerowsecurity AS force_rls, "
        "EXISTS (SELECT 1 FROM pg_trigger t WHERE t.tgrelid=c.oid "
        "AND t.tgname='trg_compliance_score_history_append_only' AND NOT t.tgisinternal) AS append_only "
        "FROM pg_class c WHERE c.oid='public.compliance_score_history'::regclass"
    )
    if not score_history["rls"] or not score_history["force_rls"] or not score_history["append_only"]:
        raise RuntimeError(f"Score history append-only/RLS invariant missing: {dict(score_history)!r}")

    role_boundary = await conn.fetchrow(
        "SELECT pg_has_role('nlc_migration_user', 'nlc_migration_owner', 'SET') AS migration_set, "
        "pg_has_role('nlc_app_role', 'nlc_migration_owner', 'SET') AS app_set"
    )
    if not role_boundary["migration_set"] or role_boundary["app_set"]:
        raise RuntimeError(f"Migration role boundary is not least-privilege: {dict(role_boundary)!r}")

    legal_rule_guard = await conn.fetchval(
        "SELECT pg_get_functiondef('public.nlc_require_legal_rule_version_snapshot()'::regprocedure)"
    )
    if (
        "session_user = 'nlc_migration_user'" not in legal_rule_guard
        or "current_setting('role', true) = 'nlc_migration_owner'" not in legal_rule_guard
    ):
        raise RuntimeError("Legal-rule guard does not recognize only the scoped migration login/owner pair.")

    return {
        "historical_table_fingerprints_before": before_tables,
        "historical_table_fingerprints_after": after_tables,
        "legacy_archive_verified": sorted(before_rules),
        "quarantined_legacy_rules": [dict(row) for row in quarantined],
        "required_identity_evidence_tables": list(required_tables),
        "score_history_invariants": dict(score_history),
        "scoped_migration_guard_exception_verified": True,
        "migration_role_boundary": dict(role_boundary),
    }


async def main() -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    conn = await _connect()
    started = datetime.now(timezone.utc).isoformat()
    try:
        identity = dict(await conn.fetchrow(
            "SELECT session_user, current_user, current_database(), "
            "current_setting('neon.project_id', true) AS project_id, "
            "current_setting('neon.branch_id', true) AS branch_id"
        ))
        revisions = await _alembic_revision(conn)
        if revisions != [START_REVISION]:
            raise RuntimeError(f"Expected exact production starting revision {START_REVISION}; got {revisions!r}")
        before_tables = {table: await _rows_digest(conn, table) for table in HISTORICAL_TABLES}
        before_rules = await _legacy_payloads(conn)
        await conn.close()

        env = os.environ.copy()
        env["ENVIRONMENT"] = "production"
        subprocess.run(["python", "-m", "alembic", "upgrade", "head"], check=True, env=env)
        current = subprocess.run(
            ["python", "-m", "alembic", "current"], check=True, capture_output=True,
            text=True, env=env,
        ).stdout.strip()
        if HEAD_REVISION not in current:
            raise RuntimeError(f"Alembic did not reach {HEAD_REVISION}: {current!r}")

        conn = await _connect()
        final_revisions = await _alembic_revision(conn)
        if final_revisions != [HEAD_REVISION]:
            raise RuntimeError(f"Unexpected final Alembic revisions: {final_revisions!r}")
        postflight = await _postflight(conn, before_tables, before_rules)
        report = {
            "status": "PASS",
            "started_at": started,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "target": identity,
            "starting_revision": START_REVISION,
            "final_revision": final_revisions,
            "alembic_current": current,
            **postflight,
        }
        REPORT.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2, default=str))
    finally:
        if not conn.is_closed():
            await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
