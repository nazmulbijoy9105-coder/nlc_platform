from datetime import date, datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import app.api.companies as companies_api
from app.api.companies import (
    _company_to_response,
    _flag_to_response,
    _score_history_to_response,
)


def _company(score, band):
    return SimpleNamespace(
        id=uuid4(),
        company_name="NLC Test Company",
        registration_number="TEST-001",
        incorporation_date=date(2020, 1, 1),
        current_compliance_score=score,
        current_risk_band=band,
        last_evaluated_at=None,
        directors=[],
        compliance_flags=[],
        financial_year_end=None,
    )


def test_legacy_stored_company_score_is_visible_after_product_release():
    response = _company_to_response(_company(88, "GREEN"))

    assert response.band == "GREEN"
    assert response.compliance_score == 88
    assert response.violation_count == 0
    assert response.active_flags == 0


def test_not_evaluated_company_does_not_expose_placeholder_score():
    response = _company_to_response(_company(100, "NOT_EVALUATED"))

    assert response.band == "NOT_EVALUATED"
    assert response.compliance_score is None


def test_released_company_score_is_visible_only_when_release_switch_is_enabled(monkeypatch):
    monkeypatch.setattr(companies_api, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(companies_api, "PRODUCT_SCORING_RULE_IDS", {"AGM-001"})

    response = _company_to_response(_company(88, "GREEN"))

    assert response.band == "GREEN"
    assert response.compliance_score == 88


def test_historical_score_history_is_visible_without_mutating_the_database_record():
    item = {
        "month": "2026-10-01",
        "score": 72,
        "risk_band": "GREEN",
        "active_flags": 3,
        "black_flags": 1,
        "red_flags": 1,
        "yellow_flags": 1,
        "calculated_at": datetime(2026, 10, 1, tzinfo=timezone.utc).isoformat(),
    }

    response = _score_history_to_response(item)

    assert response.score == 72
    assert response.risk_band == "GREEN"
    assert response.black_flags == 1
    assert response.red_flags == 1
    assert response.yellow_flags == 1
    assert response.active_flags == 3
    assert item["score"] == 72  # Preserve immutable historical evidence.


def test_product_scoring_flag_is_visible_without_claiming_legal_verification():
    flag = SimpleNamespace(
        id=uuid4(),
        rule_id="AGM-001",
        description="Provisional AGM evidence flag",
        flag_code="AGM-001",
        severity="BLACK",
        score_impact=20,
        flag_status="ACTIVE",
        triggered_date=date(2026, 10, 1),
        resolved_date=None,
        is_black_override=True,
        resolution_notes=None,
    )

    response = _flag_to_response(flag)

    assert response.severity == "BLACK"
    assert response.score_impact == 20
    assert response.is_black_override is False
    assert response.legal_review_status == "NOT_LEGALLY_VERIFIED"
    assert response.rule_name == "Provisional AGM evidence flag"


def test_product_scoring_flag_remains_legally_pending_after_product_release(monkeypatch):
    monkeypatch.setattr(companies_api, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(companies_api, "PRODUCT_SCORING_RULE_IDS", {"AGM-001"})
    flag = SimpleNamespace(
        id=uuid4(),
        rule_id="AGM-001",
        description="Approved AGM finding",
        flag_code="AGM-001",
        severity="RED",
        score_impact=15,
        flag_status="ACTIVE",
        triggered_date=date(2026, 10, 1),
        resolved_date=None,
        is_black_override=False,
        resolution_notes=None,
    )

    response = _flag_to_response(flag)

    assert response.severity == "RED"
    assert response.score_impact == 15
    assert response.legal_review_status == "NOT_LEGALLY_VERIFIED"


def test_flag_summary_separates_pending_review_from_released_findings(monkeypatch):
    import asyncio
    from unittest.mock import AsyncMock, MagicMock
    import app.rule_engine.engine as engine_module
    from app.services.compliance_service import ComplianceService

    monkeypatch.setattr(engine_module, "LEGAL_SCORE_RELEASED", False)
    monkeypatch.setattr(engine_module, "PRODUCT_SCORING_RULE_IDS", {"AGM-001"})
    summary_result = MagicMock()
    summary_result.mappings.return_value.one_or_none.return_value = {"total_active": 2}
    flags_result = MagicMock()
    flags_result.all.return_value = [("AGM-001", "RED"), ("TAX-001", "YELLOW")]
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[summary_result, flags_result])

    result = asyncio.run(ComplianceService(db).get_flag_summary(uuid4()))

    assert result["total_active"] == 0
    assert result["black"] == result["red"] == result["yellow"] == 0
    assert result["pending_review"] == 2
    assert result["pending_review_flags"] == 2


def test_release_switch_without_product_scoring_rules_hides_company_score(monkeypatch):
    monkeypatch.setattr(companies_api, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(companies_api, "PRODUCT_SCORING_RULE_IDS", set())

    response = _company_to_response(_company(88, "GREEN"))

    assert response.band == "NOT_EVALUATED"
    assert response.compliance_score is None
    assert response.violation_count == 0
