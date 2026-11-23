#!/usr/bin/env python3
"""Rehearse the documented production 0112 schema through 0124 on a disposable Neon child.

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
from canonical_architecture.statutory_rules import STATUTORY_RULE_REGISTRY

PROJECT_ID = "rapid-bonus-26545234"
PARENT_BRANCH_ID = "br-divine-glade-aovapmi5"
DATABASE = "neondb"
START_REVISION = "0112_runtime_acl_and_alembic_rls"
HEAD_REVISION = "0125_requarantine_legacy_inc001_catalogue_row"
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
REPORT = Path(os.environ.get("REPORT_PATH", "artifacts/neon-production-0112-to-0125.json"))


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
    target_branch_id = (
        os.environ.get("NLC_TARGET_BRANCH_ID")
        or os.environ.get("NLC_REHEARSAL_BRANCH_ID")
    )
    if identity["branch_id"] != target_branch_id:
        await conn.close()
        raise RuntimeError("Connection does not point to the explicitly pinned Neon target branch.")
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

    legacy_rows = await conn.fetch(
        "SELECT rule_id, is_active, default_severity, score_impact, "
        "is_black_override, verification_status FROM public.legal_rules "
        "WHERE rule_id = ANY($1::text[]) ORDER BY rule_id",
        list(before_rules),
    )
    by_rule = {row["rule_id"]: dict(row) for row in legacy_rows}
    inc001 = by_rule.get("INC-001")
    if (
        inc001 is None
        or inc001["is_active"]
        or inc001["default_severity"] != "NOT_EVALUATED"
        or inc001["score_impact"] != 0
        or inc001["is_black_override"]
        or inc001["verification_status"] != "PENDING"
    ):
        raise RuntimeError(
            f"INC-001 legacy identity quarantine verification failed: {inc001!r}"
        )
    inc002 = by_rule.get("INC-002")
    if inc002 is not None and (
        inc002["is_active"]
        or inc002["default_severity"] != "NOT_EVALUATED"
        or inc002["score_impact"] != 0
        or inc002["is_black_override"]
        or inc002["verification_status"] != "PENDING"
    ):
        raise RuntimeError(
            f"Legacy INC-002 row was not safely retired: {inc002!r}"
        )

    required_tables = (
        "legal_rule_identity_archive", "legal_rule_identities", "legal_rule_aliases",
        "legal_rule_revisions", "compliance_finding_bindings",
        "compliance_finding_evidence", "legal_rule_finding_contexts",
        "legal_rule_finding_context_reviews",
    )
    missing = [name for name in required_tables if not await conn.fetchval("SELECT to_regclass($1) IS NOT NULL", f"public.{name}")]
    if missing:
        raise RuntimeError(f"Canonical identity/evidence migration tables missing: {missing!r}")

    identity_counts = await conn.fetchrow("""
        SELECT
            (SELECT count(*) FROM public.legal_rule_identities) AS identities,
            (SELECT count(*) FROM public.legal_rule_identities
              WHERE identity_status = 'ACTIVE') AS active_identities,
            (SELECT count(*) FROM public.legal_rule_aliases) AS aliases,
            (SELECT count(*) FROM public.legal_rule_aliases
              WHERE resolution_status = 'UNRESOLVED') AS unresolved_aliases,
            (SELECT count(*) FROM public.legal_rule_aliases
              WHERE resolution_status = 'RESOLVED') AS resolved_aliases,
            (SELECT count(*) FROM public.legal_rule_aliases
              WHERE source_namespace = 'NLC_ENGINE_REGISTRY_V2') AS engine_aliases,
            (SELECT count(*) FROM public.legal_rule_aliases
              WHERE source_namespace <> 'NLC_ENGINE_REGISTRY_V2') AS other_source_aliases,
            (SELECT count(*) FROM public.legal_rule_aliases
              WHERE historical_rule_id = '') AS empty_alias_ids,
            (SELECT count(*) FROM public.legal_rule_aliases
              WHERE source_namespace = 'NLC_ENGINE_REGISTRY_V2'
                AND historical_rule_id = 'INC-001') AS inc001_engine_aliases,
            (SELECT count(*) FROM public.legal_rule_aliases
              WHERE source_namespace = 'NLC_ENGINE_REGISTRY_V2'
                AND historical_rule_id = 'INC-002') AS inc002_engine_aliases,
            (SELECT count(*) FROM public.legal_rule_revisions) AS revisions
    """)
    expected_identity_counts = {
        "identities": 170,
        "active_identities": 85,
        "aliases": 169,
        "unresolved_aliases": 169,
        "resolved_aliases": 0,
        "engine_aliases": 85,
        "other_source_aliases": 84,
        "empty_alias_ids": 0,
        "inc001_engine_aliases": 1,
        "inc002_engine_aliases": 0,
        "revisions": 0,
    }
    if dict(identity_counts) != expected_identity_counts:
        raise RuntimeError(
            "Canonical engine identities/aliases are incomplete or incorrectly resolved: "
            f"actual={dict(identity_counts)!r} expected={expected_identity_counts!r}"
        )
    alias_rows = await conn.fetch("""
        SELECT historical_rule_id
          FROM public.legal_rule_aliases
         WHERE source_namespace = 'NLC_ENGINE_REGISTRY_V2'
    """)
    actual_alias_ids = {row["historical_rule_id"] for row in alias_rows}
    expected_alias_ids = set(STATUTORY_RULE_REGISTRY)
    if actual_alias_ids != expected_alias_ids:
        raise RuntimeError(
            "Canonical engine alias IDs do not exactly match the static registry: "
            f"missing={sorted(expected_alias_ids - actual_alias_ids)!r}, "
            f"unexpected={sorted(actual_alias_ids - expected_alias_ids)!r}"
        )

    binding_counts = {
        table: await conn.fetchval(f'SELECT count(*) FROM public."{table}"')
        for table in ("compliance_finding_bindings", "compliance_finding_evidence")
    }
    if any(binding_counts.values()):
        raise RuntimeError(
            "Identity/evidence migrations unexpectedly backfilled historical findings: "
            f"{binding_counts!r}"
        )

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
        or "pg_has_role(session_user, 'nlc_migration_owner', 'SET')" not in legal_rule_guard
    ):
        raise RuntimeError("Legal-rule guard does not recognize only the scoped migration login/owner pair.")

    return {
        "historical_table_fingerprints_before": before_tables,
        "historical_table_fingerprints_after": after_tables,
        "legacy_archive_verified": sorted(before_rules),
        "legacy_rule_catalogue_states": [dict(row) for row in legacy_rows],
        "required_identity_evidence_tables": list(required_tables),
        "canonical_identity_seed_counts": dict(identity_counts),
        "historical_finding_binding_rows_after_migration": binding_counts,
        "score_history_invariants": dict(score_history),
        "scoped_migration_guard_exception_verified": True,
        "migration_role_boundary": dict(role_boundary),
    }


async def _audit_view_parity() -> dict[str, Any]:
    raw = os.environ.get("NLC_AUDIT_DATABASE_URL", "").strip()
    if not raw:
        raise RuntimeError("NLC_AUDIT_DATABASE_URL is required for restricted-view verification.")
    if make_url(raw).username != "nlc_ci_audit_role":
        raise RuntimeError("Audit-view verification must use nlc_ci_audit_role.")
    url, args = prepare_asyncpg_connection(raw, require_tls=True)
    dsn = make_url(url).set(drivername="postgresql").render_as_string(hide_password=False)
    audit_conn = await asyncpg.connect(dsn, **args)
    try:
        expected_branch_id = (
            os.environ.get("NLC_TARGET_BRANCH_ID")
            or os.environ.get("NLC_REHEARSAL_BRANCH_ID")
        )
        actual_branch_id = await audit_conn.fetchval(
            "SELECT current_setting('neon.branch_id', true)"
        )
        if not expected_branch_id or actual_branch_id != expected_branch_id:
            raise RuntimeError(
                "Restricted audit connection is not pinned to the same Neon branch "
                f"as the migration target: expected={expected_branch_id!r}, "
                f"actual={actual_branch_id!r}"
            )
        row = await audit_conn.fetchrow("SELECT * FROM audit.production_release_parity")
        if row is None:
            raise RuntimeError("Restricted audit role cannot read audit.production_release_parity.")
        result = dict(row)
        required_true = (
            "identity_archive_present", "identities_present", "aliases_present",
            "revisions_present", "finding_bindings_present", "finding_evidence_present",
            "finding_contexts_present", "finding_context_reviews_present",
            "score_history_rls_forced", "score_history_append_only_trigger",
            "score_history_app_mutation_revoked", "score_history_mutation_policies_absent",
            "users_write_scope_restricted", "users_credential_reads_scoped",
            "membership_write_scope_restricted", "membership_reads_scoped",
            "app_role_cannot_bypass_rls", "migration_role_isolated",
            "legal_rule_migration_guard_scoped", "core_tenant_rls_forced",
        )
        failed = [key for key in required_true if result.get(key) is not True]
        actual_revision = result.get("alembic_revision")
        if actual_revision != HEAD_REVISION or failed:
            raise RuntimeError(
                f"Restricted audit view parity failed: revision={actual_revision!r}; "
                f"failed={failed!r}"
            )
        if result.get("identity_archive_rows") != 2:
            raise RuntimeError("Expected exactly the two preserved legacy identity collision records.")
        expected_identity_counts = {
            "canonical_identity_rows": 170,
            "canonical_alias_rows": 169,
            "unresolved_alias_rows": 169,
            "resolved_alias_rows": 0,
            "canonical_revision_rows": 0,
        }
        actual_identity_counts = {
            key: result.get(key) for key in expected_identity_counts
        }
        if actual_identity_counts != expected_identity_counts:
            raise RuntimeError(
                f"Restricted audit view canonical identity counts mismatch: {actual_identity_counts!r}"
            )
        if result.get("active_legal_rule_rows") != 84:
            raise RuntimeError(
                "0125 requires 84 active non-colliding catalogue rows after "
                "legacy INC-001 quarantine "
                f"(observed {result.get('active_legal_rule_rows')!r})."
            )
        if result.get("inc001_quarantined") is not True or result.get("inc002_quarantined") is not True:
            raise RuntimeError("Restricted audit view did not confirm both legacy INC-001/INC-002 quarantine states.")
        if result.get("historical_finding_binding_rows") != 0 or result.get("historical_finding_evidence_rows") != 0:
            raise RuntimeError("Restricted audit view reports historical finding backfill.")
        return result
    finally:
        await audit_conn.close()


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
        if revisions == [HEAD_REVISION]:
            # A previous one-shot rehearsal may already have migrated this
            # disposable branch. Revalidate branch-pinned restricted parity
            # instead of trying to replay the 0112-only migration.
            await conn.close()
            audit_view = await _audit_view_parity()
            report = {
                "status": "PASS",
                "mode": "verified_existing_rehearsal",
                "started_at": started,
                "finished_at": datetime.now(timezone.utc).isoformat(),
                "target": identity,
                "starting_revision": START_REVISION,
                "final_revision": revisions,
                "prior_rehearsal_run_id": os.environ.get("NLC_PRIOR_REHEARSAL_RUN_ID"),
                "restricted_audit_view_parity": audit_view,
                "notes": f"The isolated branch was already at {revisions[0]}; no migration was replayed.",
            }
            REPORT.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
            print(json.dumps(report, indent=2, default=str))
            return
        if revisions != [START_REVISION]:
            raise RuntimeError(f"Expected exact starting revision {START_REVISION} or already-rehearsed {HEAD_REVISION}; got {revisions!r}")
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
        audit_view = await _audit_view_parity()
        report = {
            "status": "PASS",
            "started_at": started,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "target": identity,
            "starting_revision": START_REVISION,
            "final_revision": final_revisions,
            "alembic_current": current,
            **postflight,
            "restricted_audit_view_parity": audit_view,
        }
        REPORT.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2, default=str))
    finally:
        if not conn.is_closed():
            await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
