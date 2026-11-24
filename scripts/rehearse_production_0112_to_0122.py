#!/usr/bin/env python3
"""Rehearse the documented production 0112 schema through the current Alembic head on a disposable Neon child.

The script is pinned to the NLC production project and the preserved backup
branch. It captures immutable fingerprints for historical finding/score tables
and the exact legacy INC-001/INC-002/AGM-001 payloads before running Alembic.
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
HEAD_REVISION = "0127_one_active_rescue_plan_per_company"
AGM_MIGRATION_REVISION = "0125_reconcile_agm001_statutory_basis"
AGM_PRE_0125_REVISION = "0124_restore_85_rule_catalogue_parity"
PREVIOUS_REVISION = "0122_rls_staff_scope_and_score_history"
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
    "AGM-001": {
        ("First AGM Default",
         "Section 81, Companies Act 1994 (Bangladesh)",
         "first_agm_held == False AND days_since_incorporation > 548"),
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
REPORT = Path("artifacts/neon-production-0112-to-0127.json")


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


_LIVE_RULE_SQL = (
    "SELECT to_jsonb(r) AS payload, rule_name, statutory_basis, "
    "rule_condition ->> 'trigger' AS trigger "
    "FROM public.legal_rules r WHERE rule_id=$1"
)
_ARCHIVED_RULE_SQL = (
    "SELECT original_payload AS payload, "
    "original_payload ->> 'rule_name' AS rule_name, "
    "original_payload ->> 'statutory_basis' AS statutory_basis, "
    "original_payload -> 'rule_condition' ->> 'trigger' AS trigger "
    "FROM public.legal_rule_identity_archive "
    "WHERE legacy_rule_id=$1 ORDER BY captured_at, legacy_identity_key LIMIT 1"
)


async def _legacy_payloads(
    conn: asyncpg.Connection, *, from_archive: bool = False
) -> dict[str, Any]:
    """Capture the legacy before-images the postflight compares against.

    When resuming at 0124, 0115 has already quarantined INC-001/INC-002, so
    their original payloads come from the append-only identity archive instead
    of the live rows. AGM-001 is still the untouched legacy row until 0125.
    """
    output: dict[str, Any] = {}
    for rule_id, allowed in LEGACY_FINGERPRINTS.items():
        archived = from_archive and rule_id != "AGM-001"
        row = await conn.fetchrow(
            _ARCHIVED_RULE_SQL if archived else _LIVE_RULE_SQL, rule_id
        )
        if row is None:
            if rule_id == "INC-002":
                continue
            raise RuntimeError(f"{rule_id} is missing before migration reconciliation.")
        fingerprint = (row["rule_name"], row["statutory_basis"], row["trigger"])
        if fingerprint not in allowed:
            raise RuntimeError(f"{rule_id} does not match a known legacy fingerprint: {fingerprint!r}")
        payload = row["payload"]
        if isinstance(payload, str):
            payload = json.loads(payload)
        if not isinstance(payload, dict):
            raise RuntimeError(
                f"{rule_id} before-image is not a JSON object: {type(payload).__name__}"
            )
        output[rule_id] = payload
    return output


async def _rule_payload(conn: asyncpg.Connection, rule_id: str) -> dict[str, Any]:
    row = await conn.fetchrow(
        "SELECT to_jsonb(r) AS payload FROM public.legal_rules r WHERE rule_id=$1",
        rule_id,
    )
    if row is None:
        raise RuntimeError(f"{rule_id} is missing at the 0125 migration boundary.")
    payload = row["payload"]
    if isinstance(payload, str):
        payload = json.loads(payload)
    if not isinstance(payload, dict):
        raise RuntimeError(f"{rule_id} migration-boundary payload is not a JSON object.")
    return payload


async def _alembic_revision(conn: asyncpg.Connection) -> list[str]:
    rows = await conn.fetch("SELECT version_num FROM public.alembic_version ORDER BY version_num")
    return [row["version_num"] for row in rows]


async def _postflight(
    conn: asyncpg.Connection,
    before_tables: dict[str, Any],
    before_rules: dict[str, Any],
    agm001_before_0125: dict[str, Any],
) -> dict[str, Any]:
    after_tables = {table: await _rows_digest(conn, table) for table in HISTORICAL_TABLES}
    if before_tables != after_tables:
        raise RuntimeError(f"Historical finding/score data changed: before={before_tables!r}, after={after_tables!r}")

    archive = await conn.fetch(
        "SELECT legacy_rule_id, original_payload, payload_sha256 "
        "FROM public.legal_rule_identity_archive ORDER BY legacy_rule_id"
    )
    archived = {row["legacy_rule_id"]: row for row in archive}
    migration_history_verified = []
    for rule_id, original in before_rules.items():
        if rule_id == "AGM-001":
            original = agm001_before_0125
            history = await conn.fetch(
                "SELECT version, change_reason, changed_by, actor_type, "
                "migration_revision, previous_definition "
                "FROM public.legal_rule_versions "
                "WHERE rule_id=$1 AND migration_revision=$2",
                rule_id,
                AGM_MIGRATION_REVISION,
            )
            if len(history) != 1:
                raise RuntimeError(
                    f"0125 did not create exactly one AGM-001 migration history row: {len(history)}"
                )
            history_row = history[0]
            if (
                history_row["actor_type"] != "MIGRATION"
                or history_row["changed_by"] is not None
                or history_row["migration_revision"] != AGM_MIGRATION_REVISION
                or history_row["version"] != original.get("rule_version")
                or not history_row["change_reason"]
                or _canonical(history_row["previous_definition"]) != _canonical(original)
            ):
                raise RuntimeError(
                    "0125 AGM-001 migration history does not preserve the exact before-image: "
                    f"{dict(history_row)!r}"
                )
            migration_history_verified.append(rule_id)
            continue
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
        "is_black_override, verification_status, statutory_basis, rule_version, "
        "to_jsonb(r) AS payload FROM public.legal_rules r "
        "WHERE rule_id = ANY($1::text[]) ORDER BY rule_id",
        list(before_rules),
    )
    by_rule = {row["rule_id"]: dict(row) for row in legacy_rows}
    inc001 = by_rule.get("INC-001")
    if (
        inc001 is None
        or not inc001["is_active"]
        or inc001["default_severity"] != "NOT_EVALUATED"
        or inc001["score_impact"] != 0
        or inc001["is_black_override"]
        or inc001["verification_status"] != "PENDING"
    ):
        raise RuntimeError(
            f"INC-001 85-ID catalogue activation parity failed: {inc001!r}"
        )
    agm001 = by_rule.get("AGM-001")
    if (
        agm001 is None
        or not agm001["is_active"]
        or agm001["statutory_basis"] != "Section 81(1), Companies Act 1994 (Bangladesh)"
    ):
        raise RuntimeError(
            f"AGM-001 canonical catalogue identity was not reconciled: {agm001!r}"
        )
    original_agm001 = before_rules["AGM-001"]
    original_agm001 = agm001_before_0125
    previous_version = str(original_agm001["rule_version"])
    version_parts = previous_version.split(".")
    if any(not part.isdigit() for part in version_parts):
        raise RuntimeError(f"AGM-001 has a non-numeric prior version: {previous_version!r}")
    version_parts[-1] = str(int(version_parts[-1]) + 1)
    expected_agm001_version = ".".join(version_parts)
    if agm001["rule_version"] != expected_agm001_version:
        raise RuntimeError(
            "AGM-001 version history was not advanced exactly once: "
            f"expected={expected_agm001_version!r}, actual={agm001['rule_version']!r}"
        )
    current_agm001 = agm001["payload"]
    if isinstance(current_agm001, str):
        current_agm001 = json.loads(current_agm001)
    if not isinstance(current_agm001, dict):
        raise RuntimeError("AGM-001 current row payload is not a JSON object")
    before_compare = dict(original_agm001)
    current_compare = dict(current_agm001)
    for mutable_key in ("statutory_basis", "rule_version", "last_modified_at", "updated_at"):
        before_compare.pop(mutable_key, None)
        current_compare.pop(mutable_key, None)
    mutable_fields = ("statutory_basis", "rule_version", "last_modified_at", "updated_at")
    for field in mutable_fields:
        before_compare.pop(field, None)
        current_compare.pop(field, None)
    if current_compare != before_compare:
        raise RuntimeError(
            "0125 changed AGM-001 fields beyond citation/version/timestamps"
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
        "legacy_archive_verified": sorted(
            rule_id for rule_id in before_rules if rule_id != "AGM-001"
        ),
        "migration_version_history_verified": migration_history_verified,
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
        if actual_revision not in {HEAD_REVISION, AGM_PRE_0125_REVISION, PREVIOUS_REVISION} or failed:
            raise RuntimeError(
                f"Restricted audit view parity failed: revision={actual_revision!r}; "
                f"failed={failed!r}"
            )
        if result.get("identity_archive_rows") != 2:
            raise RuntimeError("Expected exactly the two preserved legacy identity collision records.")
        expected_identity_counts = (
            {
                "canonical_identity_rows": 85,
                "canonical_alias_rows": 85,
                "unresolved_alias_rows": 85,
                "resolved_alias_rows": 0,
                "canonical_revision_rows": 0,
            }
            if actual_revision == PREVIOUS_REVISION
            else {
                "canonical_identity_rows": 170,
                "canonical_alias_rows": 169,
                "unresolved_alias_rows": 169,
                "resolved_alias_rows": 0,
                "canonical_revision_rows": 0,
            }
        )
        actual_identity_counts = {
            key: result.get(key) for key in expected_identity_counts
        }
        if actual_identity_counts != expected_identity_counts:
            raise RuntimeError(
                f"Restricted audit view canonical identity counts mismatch: {actual_identity_counts!r}"
            )
        if actual_revision in {HEAD_REVISION, AGM_PRE_0125_REVISION}:
            if result.get("active_legal_rule_rows") != 85:
                raise RuntimeError(
                    "0125 requires exactly 85 active catalogue rows "
                    f"(observed {result.get('active_legal_rule_rows')!r})."
                )
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
        if revisions in ([HEAD_REVISION], [PREVIOUS_REVISION]):
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
        # A branch left at the previous rehearsal head resumes at 0125 only.
        resume_from_0124 = revisions == [AGM_PRE_0125_REVISION]
        if not resume_from_0124 and revisions != [START_REVISION]:
            raise RuntimeError(
                f"Expected starting revision {START_REVISION}, resumable revision "
                f"{AGM_PRE_0125_REVISION}, or already-rehearsed {HEAD_REVISION}; got {revisions!r}"
            )
        before_tables = {table: await _rows_digest(conn, table) for table in HISTORICAL_TABLES}
        before_rules = await _legacy_payloads(conn, from_archive=resume_from_0124)
        await conn.close()

        env = os.environ.copy()
        env["ENVIRONMENT"] = "production"
        if not resume_from_0124:
            subprocess.run(
                ["python", "-m", "alembic", "upgrade", AGM_PRE_0125_REVISION],
                check=True,
                env=env,
            )
            pre_0125_current = subprocess.run(
                ["python", "-m", "alembic", "current"],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            ).stdout.strip()
            if AGM_PRE_0125_REVISION not in pre_0125_current:
                raise RuntimeError(
                    f"Alembic did not stop at {AGM_PRE_0125_REVISION}: {pre_0125_current!r}"
                )

        conn = await _connect()
        agm001_before_0125 = await _rule_payload(conn, "AGM-001")
        if agm001_before_0125.get("statutory_basis") != (
            "Section 81, Companies Act 1994 (Bangladesh)"
        ):
            raise RuntimeError(
                "AGM-001 does not carry the exact legacy citation at the 0125 boundary: "
                f"{agm001_before_0125.get('statutory_basis')!r}"
            )
        await conn.close()

        subprocess.run(
            ["python", "-m", "alembic", "upgrade", HEAD_REVISION],
            check=True,
            env=env,
        )
        current = subprocess.run(
            ["python", "-m", "alembic", "current"],
            check=True,
            capture_output=True,
            text=True,
            env=env,
        ).stdout.strip()
        if HEAD_REVISION not in current:
            raise RuntimeError(f"Alembic did not reach {HEAD_REVISION}: {current!r}")

        conn = await _connect()
        final_revisions = await _alembic_revision(conn)
        if final_revisions != [HEAD_REVISION]:
            raise RuntimeError(f"Unexpected final Alembic revisions: {final_revisions!r}")
        postflight = await _postflight(
            conn, before_tables, before_rules, agm001_before_0125
        )
        audit_view = await _audit_view_parity()
        report = {
            "status": "PASS",
            "started_at": started,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "target": identity,
            "starting_revision": AGM_PRE_0125_REVISION if resume_from_0124 else START_REVISION,
            "final_revision": final_revisions,
            "alembic_current": current,
            **(
                {
                    "mode": "resumed_from_0124",
                    "legacy_before_image_source": "legal_rule_identity_archive",
                }
                if resume_from_0124
                else {}
            ),
            **postflight,
            "agm001_pre_0125_before_image_sha256": hashlib.sha256(
                _canonical(agm001_before_0125).encode("utf-8")
            ).hexdigest(),
            "restricted_audit_view_parity": audit_view,
        }
        REPORT.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2, default=str))
    finally:
        if not conn.is_closed():
            await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
