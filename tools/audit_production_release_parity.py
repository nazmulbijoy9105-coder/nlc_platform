#!/usr/bin/env python3
"""Read-only production database/API parity certification for the 85-ID catalogue."""
from __future__ import annotations

import asyncio
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import asyncpg
from sqlalchemy.engine import make_url

from app.db_url import prepare_asyncpg_connection
from scripts.seed_rules import ILRMF_RULES

EXPECTED_REVISION = "0124_restore_85_rule_catalogue_parity"
REQUIRED_TRUE = (
    "identity_archive_present",
    "identities_present",
    "aliases_present",
    "revisions_present",
    "finding_bindings_present",
    "finding_evidence_present",
    "finding_contexts_present",
    "finding_context_reviews_present",
    "score_history_rls_forced",
    "score_history_append_only_trigger",
    "score_history_app_mutation_revoked",
    "score_history_mutation_policies_absent",
    "users_write_scope_restricted",
    "users_credential_reads_scoped",
    "membership_write_scope_restricted",
    "membership_reads_scoped",
    "app_role_cannot_bypass_rls",
    "migration_role_isolated",
    "legal_rule_migration_guard_scoped",
    "core_tenant_rls_forced",
)


async def _database_parity() -> dict:
    raw = os.environ.get("NLC_PRODUCTION_DATABASE_URL", "").strip()
    if not raw:
        raise RuntimeError("NLC_PRODUCTION_DATABASE_URL is required.")
    parsed = make_url(raw)
    if parsed.username != "nlc_ci_audit_role":
        raise RuntimeError(
            "Production parity must use the restricted nlc_ci_audit_role, "
            f"not {parsed.username!r}."
        )
    url, args = prepare_asyncpg_connection(raw, require_tls=True)
    dsn = make_url(url).set(drivername="postgresql").render_as_string(hide_password=False)
    conn = await asyncpg.connect(dsn, **args)
    try:
        row = await conn.fetchrow("SELECT * FROM audit.production_release_parity")
        if row is None:
            raise RuntimeError("audit.production_release_parity returned no row.")
        result = dict(row)
        if result.get("alembic_revision") != EXPECTED_REVISION:
            raise RuntimeError(
                f"Production DB revision mismatch: {result.get('alembic_revision')!r}"
            )
        failures = [name for name in REQUIRED_TRUE if result.get(name) is not True]
        if failures:
            raise RuntimeError(
                "Production DB parity invariants failed: "
                + ", ".join(f"{name}={result.get(name)!r}" for name in failures)
            )
        if result.get("identity_archive_rows", 0) < 1:
            raise RuntimeError("No legacy identity archive rows were preserved.")
        if result.get("identity_archive_rows") != 2:
            raise RuntimeError("Expected exactly two preserved legacy identity collision records.")
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
                f"Production canonical identity counts mismatch: {actual_identity_counts!r}"
            )
        if result.get("active_legal_rule_rows") != 85:
            raise RuntimeError(
                "Production database must expose exactly 85 active catalogue rows "
                f"(observed {result.get('active_legal_rule_rows')!r})."
            )
        if result.get("historical_finding_binding_rows") != 0:
            raise RuntimeError("Historical findings were unexpectedly rebound.")
        if result.get("historical_finding_evidence_rows") != 0:
            raise RuntimeError("Historical findings were unexpectedly backfilled with evidence.")
        return result
    finally:
        await conn.close()


def _api_parity() -> dict:
    api_url = os.environ.get("API_URL", "").strip().rstrip("/")
    expected_sha = os.environ.get("EXPECTED_DEPLOYED_SHA", "").strip()
    if not api_url or not expected_sha:
        raise RuntimeError("API_URL and EXPECTED_DEPLOYED_SHA are required.")
    url = f"{api_url}/api/v1/health/ready"
    request = Request(url, headers={"Accept": "application/json"}, method="GET")
    try:
        with urlopen(request, timeout=30) as response:
            status = response.status
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"Readiness endpoint request failed: {exc}") from exc

    if status != 200 or payload.get("ready") is not True:
        raise RuntimeError(f"Production API is not ready: HTTP {status}, {payload!r}")
    if payload.get("database") != "ok":
        raise RuntimeError(f"Production API database check is not ok: {payload!r}")
    if payload.get("redis") not in {"ok", "degraded"}:
        raise RuntimeError(f"Production API Redis check is not ready: {payload!r}")
    if payload.get("revision") != expected_sha:
        raise RuntimeError(
            f"Deployed SHA mismatch: expected {expected_sha}, "
            f"health endpoint reports {payload.get('revision')!r}"
        )
    rules_url = f"{api_url}/api/v1/rules"
    rules_request = Request(rules_url, headers={"Accept": "application/json"}, method="GET")
    try:
        with urlopen(rules_request, timeout=30) as response:
            rules_status = response.status
            rules_payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"Rules catalogue endpoint request failed: {exc}") from exc
    if rules_status != 200 or not isinstance(rules_payload, list):
        raise RuntimeError(
            f"Production rules catalogue is invalid: HTTP {rules_status}, {rules_payload!r}"
        )
    actual_ids = {
        item.get("rule_id") for item in rules_payload
        if isinstance(item, dict) and item.get("rule_id")
    }
    expected_ids = {item["rule_id"] for item in ILRMF_RULES}
    if len(actual_ids) != 85 or actual_ids != expected_ids:
        raise RuntimeError(
            "Production /api/v1/rules must return exactly the 85 seed IDs "
            f"(missing={sorted(expected_ids - actual_ids)!r}, "
            f"unexpected={sorted(actual_ids - expected_ids)!r})."
        )
    if any(item.get("is_active") is not True for item in rules_payload):
        raise RuntimeError("Production rules endpoint contains inactive catalogue rows.")
    return {
        "http_status": status,
        **payload,
        "expected_sha": expected_sha,
        "rules_http_status": rules_status,
        "rules_id_count": len(actual_ids),
    }


async def main() -> None:
    database = await _database_parity()
    api = _api_parity()
    output = {
        "status": "PASS",
        "database": database,
        "api": api,
        "notes": {
            "canonical_identity_rows": database.get("canonical_identity_rows"),
            "canonical_alias_rows": database.get("canonical_alias_rows"),
            "canonical_revision_rows": database.get("canonical_revision_rows"),
            "active_legal_rule_rows": database.get("active_legal_rule_rows"),
            "verified_legal_rule_rows": database.get("verified_legal_rule_rows"),
        },
    }
    print(json.dumps(output, indent=2, default=str))


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print(f"PRODUCTION PARITY FAILED: {exc}", file=sys.stderr)
        raise
