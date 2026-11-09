"""PostgreSQL proof for the 0090 legal-rule registry reconciliation."""
from __future__ import annotations

import pytest
from sqlalchemy import select, text

from app.models.rules import LegalRule
from app.services.rules_service import RulesService
from canonical_architecture.statutory_rules import STATUTORY_RULE_REGISTRY
from scripts.seed_rules import ILRMF_RULES

pytestmark = [pytest.mark.integration]


def _enum_value(value):
    return value.value if hasattr(value, "value") else str(value)


@pytest.mark.asyncio
async def test_postgres_registry_ids_match_engine_and_seed_catalogue(db):
    """The active PostgreSQL rule IDs must match both maintained catalogues."""
    seed_by_id = {item["rule_id"]: item for item in ILRMF_RULES}
    seed_ids = set(seed_by_id)
    engine_ids = set(STATUTORY_RULE_REGISTRY)

    rows = (
        await db.execute(
            select(LegalRule).where(LegalRule.is_active.is_(True))
        )
    ).scalars().all()
    database_by_id = {row.rule_id: row for row in rows}

    assert len(seed_by_id) == 85
    assert len(database_by_id) == 85
    assert set(database_by_id) == seed_ids == engine_ids

    # Every database row, including the retained inactive legacy row, must be
    # quarantined until independent legal approval is recorded.
    all_rows = (await db.execute(select(LegalRule))).scalars().all()
    assert all_rows
    unsafe = [
        {
            "rule_id": row.rule_id,
            "severity": _enum_value(row.default_severity),
            "score_impact": row.score_impact,
            "black_override": row.is_black_override,
            "verification_status": row.verification_status,
        }
        for row in all_rows
        if (
            _enum_value(row.default_severity) != "NOT_EVALUATED"
            or row.score_impact != 0
            or row.is_black_override is not False
            or row.verification_status != "PENDING"
        )
    ]
    assert not unsafe, unsafe

    # Confirm the two known live-database metadata corrections exactly match
    # the maintained seed catalogue. This is catalogue parity, not legal sign-off.
    for rule_id in ("SH-001", "SH-002"):
        row = database_by_id[rule_id]
        seed = seed_by_id[rule_id]
        assert row.rule_name == seed["rule_name"]
        assert row.statutory_basis == seed["statutory_basis"]
        assert row.description == seed["description"]
        assert row.rule_condition == seed["rule_condition"]


@pytest.mark.asyncio
async def test_rule_registry_reconciliation_audit_has_before_and_after_snapshots(db):
    """Every rule row changed by 0090 has a complete immutable audit snapshot."""
    rule_count = (
        await db.execute(select(text("count(*)")).select_from(LegalRule))
    ).scalar_one()
    audit_rows = (
        await db.execute(
            text("""
                SELECT rule_id, migration_revision, actor_type,
                       before_definition, after_definition
                FROM legal_rule_reconciliation_audit
                WHERE migration_revision = '0090_rule_registry_drift_quarantine'
                ORDER BY rule_id
            """)
        )
    ).mappings().all()

    assert len(audit_rows) == rule_count
    assert all(item["actor_type"] == "ALEMBIC_MIGRATION" for item in audit_rows)
    for item in audit_rows:
        before = item["before_definition"]
        after = item["after_definition"]
        assert before["rule_id"] == item["rule_id"]
        assert after["rule_id"] == item["rule_id"]
        assert after["default_severity"] == "NOT_EVALUATED"
        assert after["score_impact"] == 0
        assert after["is_black_override"] is False
        assert after["verification_status"] == "PENDING"


@pytest.mark.asyncio
async def test_rules_service_returns_same_rule_identity_as_database(db):
    """RulesService must not remap a rule ID to another rule's metadata."""
    service = RulesService(db)
    for rule_id in ("SH-001", "SH-002"):
        rule = await service.get_by_rule_id(rule_id)
        assert rule is not None
        assert rule.rule_id == rule_id
        assert rule.default_severity is not None
        assert rule.score_impact == 0
        assert rule.is_black_override is False
