"""Public legal-rule catalogue must not publish unapproved legal assertions."""

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


def test_product_scoring_catalogue_shows_rules_but_keeps_legal_verification_pending(monkeypatch):
    monkeypatch.setattr(rules_api, "LEGAL_SCORE_RELEASED", False)
    monkeypatch.setattr(rules_api, "VERIFIED_RULE_IDS", frozenset())
    monkeypatch.setattr(rules_api, "PRODUCT_SCORING_RULE_IDS", frozenset({"AGM-001"}))
    response = rules_api._rule_to_response(_rule())

    assert response.default_severity == "RED"
    assert response.score_impact == 20
    assert response.is_black_override is False
    assert response.is_active is True
    assert response.verification_status == "PENDING"
    assert response.verified_at is None
    assert response.statutory_effective_date is None
    assert response.statutory_basis == "Section 81, Companies Act 1994"
    assert response.description == "Unverified statutory proposition."


def test_rule_catalogue_does_not_conflate_product_eligibility_with_legal_verification(monkeypatch):
    monkeypatch.setattr(rules_api, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(rules_api, "VERIFIED_RULE_IDS", frozenset())
    monkeypatch.setattr(rules_api, "PRODUCT_SCORING_RULE_IDS", frozenset({"AGM-001"}))
    response = rules_api._rule_to_response(_rule())

    assert response.default_severity == "RED"
    assert response.score_impact == 20
    assert response.is_black_override is False
    assert response.is_active is True
    assert response.verification_status == "ENGINE_ALIGNED_NOT_COUNSEL_VALIDATED"
