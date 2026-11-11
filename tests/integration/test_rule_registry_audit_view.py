"""Least-privilege audit view for the full legal-rule catalogue."""

import os

import pytest
from sqlalchemy import text

from tools.audit_rule_parity import (
    compare_database_metadata,
    get_seed_rule_definitions,
    get_seed_rules,
)


pytestmark = [pytest.mark.integration]


@pytest.mark.asyncio
async def test_ci_audit_role_can_read_full_catalogue_without_legal_verification_claims(db):
    role_exists = await db.execute(
        text("SELECT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nlc_ci_audit_role')")
    )
    if not role_exists.scalar():
        if os.getenv("CI", "").lower() == "true":
            pytest.fail("CI must provision nlc_ci_audit_role before migration/integration tests")
        pytest.skip("nlc_ci_audit_role is provisioned by the CI integration database setup")

    await db.execute(text("SET LOCAL ROLE nlc_ci_audit_role"))
    rows = (
        await db.execute(
            text(
                """
                SELECT
                    rule_id, rule_name, rule_type, statutory_basis, description,
                    rule_condition, default_severity, score_impact, revenue_tier,
                    is_black_override, rule_version, is_active, verification_status
                FROM audit.legal_rule_registry_inventory
                ORDER BY rule_id
                """
            )
        )
    ).mappings().all()
    verified_ids = (
        await db.execute(text("SELECT rule_id FROM audit.active_legal_rule_ids"))
    ).scalars().all()
    await db.execute(text("RESET ROLE"))

    inventory = {row["rule_id"]: dict(row) for row in rows}
    active_ids = {row["rule_id"] for row in rows if row["is_active"] is True}
    inactive_ids = {row["rule_id"] for row in rows if row["is_active"] is not True}
    metadata = compare_database_metadata(get_seed_rule_definitions(), inventory)

    assert metadata["mismatches"] == []
    assert (
        metadata["seed_manifest_sha256"]
        == metadata["database_active_manifest_sha256"]
    )
    assert len(rows) == 86
    assert active_ids == get_seed_rules()
    assert inactive_ids == {"INC-002"}
    assert all(row["default_severity"] == "NOT_EVALUATED" for row in rows)
    assert all(row["score_impact"] == 0 for row in rows)
    assert all(row["is_black_override"] is False for row in rows)
    assert all(row["verification_status"] == "PENDING" for row in rows)
    assert verified_ids == []

    direct_select = await db.execute(
        text(
            "SELECT has_table_privilege("
            "'nlc_ci_audit_role', 'public.legal_rules', 'SELECT')"
        )
    )
    assert direct_select.scalar() is False

    columns = (
        await db.execute(
            text(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'audit'
                  AND table_name = 'legal_rule_registry_inventory'
                """
            )
        )
    ).scalars().all()
    assert not {
        "verified_at",
        "verified_by",
        "verification_notes",
        "statutory_effective_date",
    }.intersection(columns)
