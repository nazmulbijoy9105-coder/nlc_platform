"""Product scoring eligibility and legal-verification metadata stay independent."""

import asyncio
from datetime import datetime
from types import SimpleNamespace

import app.api.rules as rules_api


def _rule(**overrides):
    values = {
        "rule_id": "AGM-001",
        "rule_name": "First AGM Default",
        "rule_type": "DEADLINE",
        "statutory_basis": "Section 81, Companies Act 1994",
        "description": "Unverified statutory proposition.",
        "default_severity": "RED",
        "score_impact": 20,
        "revenue_tier": "CORPORATE_RESCUE",
        "is_black_override": True,
        "is_active": True,
        "verification_status": "ENGINE_ALIGNED_NOT_COUNSEL_VALIDATED",
        "verified_at": datetime(2026, 1, 1),
        "statutory_effective_date": datetime(2026, 1, 1).date(),
        "rule_version": "2.2",
        "created_at": datetime(2026, 1, 1),
        "updated_at": datetime(2026, 1, 2),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_product_authorized_black_override_does_not_require_legal_verification(monkeypatch):
    monkeypatch.setattr(rules_api, "legal_score_is_released", lambda: False)
    monkeypatch.setattr(rules_api, "VERIFIED_RULE_IDS", frozenset())
    monkeypatch.setattr(rules_api, "AUTHORIZED_BLACK_OVERRIDE_RULE_IDS", frozenset({"INC-003"}))
    monkeypatch.setattr(rules_api, "PRODUCT_SCORING_RULE_IDS", frozenset({"INC-003"}))
    response = rules_api._rule_to_response(_rule(rule_id="INC-003"))

    assert response.default_severity == "RED"
    assert response.score_impact == 20
    assert response.is_black_override is True
    assert response.is_active is True
    assert response.verification_status == "PENDING"
    assert response.verified_at is None
    assert response.statutory_effective_date is None
    assert response.statutory_basis == "Section 81, Companies Act 1994"
    assert response.description == "Unverified statutory proposition."


def test_super_admin_black_override_catalogue_remains_visible_when_scoring_is_disabled(monkeypatch):
    monkeypatch.setattr(rules_api, "legal_score_is_released", lambda: False)
    monkeypatch.setattr(rules_api, "VERIFIED_RULE_IDS", frozenset())
    monkeypatch.setattr(rules_api, "PRODUCT_SCORING_RULE_IDS", frozenset({"INC-003"}))
    monkeypatch.setattr(rules_api, "AUTHORIZED_BLACK_OVERRIDE_RULE_IDS", frozenset({"INC-003"}))

    class FakeRulesService:
        def __init__(self, db):
            self.db = db

        async def get_all(self):
            # The legacy database row still has is_black_override=False; the
            # product-owned allowlist is the authoritative override setting.
            return [_rule(rule_id="INC-003", is_black_override=False)]

    monkeypatch.setattr(rules_api, "RulesService", FakeRulesService)
    result = asyncio.run(rules_api.get_black_overrides(current_user=None, db=object()))

    assert len(result) == 1
    assert result[0].product_scoring_enabled is False
    assert result[0].default_severity == "RED"
    assert result[0].score_impact == 20
    assert result[0].is_active is True
    assert result[0].is_black_override is True
    assert result[0].verification_status == "PENDING"


def test_unlisted_black_override_is_not_authorized_by_product_release_alone(monkeypatch):
    monkeypatch.setattr(rules_api, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(rules_api, "VERIFIED_RULE_IDS", frozenset())
    monkeypatch.setattr(rules_api, "AUTHORIZED_BLACK_OVERRIDE_RULE_IDS", frozenset())
    monkeypatch.setattr(rules_api, "PRODUCT_SCORING_RULE_IDS", frozenset({"AGM-001"}))
    response = rules_api._rule_to_response(_rule())

    assert response.default_severity == "RED"
    assert response.score_impact == 20
    assert response.is_black_override is False
    assert response.is_active is True
    assert response.verification_status == "PENDING"
