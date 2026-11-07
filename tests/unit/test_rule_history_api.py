"""Regression tests for legal-rule history response serialization."""

from datetime import UTC, date, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.api import rules as rules_api


class StubRulesService:
    def __init__(self, _db):
        pass

    async def get_by_rule_id(self, rule_id):
        return SimpleNamespace(
            rule_id=rule_id,
            default_severity="RED",
            score_impact=15,
        )

    async def get_version_history(self, _rule_id):
        return self.versions


@pytest.mark.asyncio
async def test_rule_history_maps_snapshots_to_previous_and_new_values(monkeypatch):
    changed_at = datetime(2026, 11, 1, 12, 0, tzinfo=UTC)
    latest = SimpleNamespace(
        id=uuid4(),
        rule_id="AGM-001",
        version="1.1",
        previous_definition={
            "default_severity": "YELLOW",
            "score_impact": 10,
        },
        change_reason="Severity increased after legal review",
        changed_by=uuid4(),
        changed_at=changed_at,
    )
    earlier = SimpleNamespace(
        id=uuid4(),
        rule_id="AGM-001",
        version="1.0",
        previous_definition={
            "default_severity": "GREEN",
            "score_impact": 5,
        },
        change_reason="Initial rule adjustment recorded",
        changed_by=uuid4(),
        changed_at=changed_at,
    )

    class ServiceWithHistory(StubRulesService):
        async def get_version_history(self, _rule_id):
            return [latest, earlier]

    monkeypatch.setattr(rules_api, "RulesService", ServiceWithHistory)

    result = await rules_api.get_rule_history(
        rule_id="AGM-001",
        current_user=SimpleNamespace(id=uuid4()),
        db=object(),
    )

    assert len(result) == 2
    assert result[0].previous_severity == "YELLOW"
    assert result[0].new_severity == "RED"
    assert result[0].previous_score_impact == 10
    assert result[0].new_score_impact == 15
    assert result[0].changed_by_id == str(latest.changed_by)

    assert result[1].previous_severity == "GREEN"
    assert result[1].new_severity == "YELLOW"
    assert result[1].previous_score_impact == 5
    assert result[1].new_score_impact == 10


@pytest.mark.asyncio
async def test_rule_history_returns_empty_list_when_no_versions(monkeypatch):
    class ServiceWithoutHistory(StubRulesService):
        async def get_version_history(self, _rule_id):
            return []

    monkeypatch.setattr(rules_api, "RulesService", ServiceWithoutHistory)

    result = await rules_api.get_rule_history(
        rule_id="AGM-001",
        current_user=SimpleNamespace(id=uuid4()),
        db=object(),
    )

    assert result == []


def test_public_rule_response_discloses_pending_legal_verification():
    created_at = datetime(2026, 11, 6, 12, 0, tzinfo=UTC)
    rule = SimpleNamespace(
        rule_id="AGM-001",
        rule_name="AGM held within statutory period",
        rule_type="DEADLINE",
        statutory_basis="Section 81, Companies Act 1994",
        statutory_effective_date=date(1994, 2, 12),
        description="Illustrative rule description",
        default_severity="YELLOW",
        score_impact=5,
        revenue_tier="COMPLIANCE_PACKAGE",
        is_black_override=False,
        is_active=True,
        verification_status="PENDING",
        verified_at=None,
        rule_version="1.0",
        created_at=created_at,
        updated_at=None,
    )

    response = rules_api._rule_to_response(rule)

    assert response.verification_status == "PENDING"
    assert response.verified_at is None
    assert response.statutory_effective_date is None
