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


def test_legacy_stored_company_score_is_hidden_while_release_is_disabled():
    response = _company_to_response(_company(88, "GREEN"))

    assert response.band == "NOT_EVALUATED"
    assert response.compliance_score is None
    assert response.violation_count == 0
    assert response.active_flags == 0
    assert response.black_flags == response.red_flags == response.yellow_flags == 0


def test_not_evaluated_company_does_not_expose_placeholder_score():
    response = _company_to_response(_company(100, "NOT_EVALUATED"))

    assert response.band == "NOT_EVALUATED"
    assert response.compliance_score is None


def test_released_company_score_is_visible_only_when_release_switch_is_enabled(monkeypatch):
    monkeypatch.setattr(companies_api, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(companies_api, "VERIFIED_RULE_IDS", {"AGM-001"})

    response = _company_to_response(_company(88, "GREEN"))

    assert response.band == "GREEN"
    assert response.compliance_score == 88


def test_legacy_score_history_is_hidden_without_mutating_the_database_record():
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

    assert response.score is None
    assert response.risk_band == "NOT_EVALUATED"
    assert response.black_flags == response.red_flags == response.yellow_flags == 0
    assert response.active_flags == 0
    assert item["score"] == 72  # Preserve immutable historical evidence.


def test_unapproved_flag_severity_and_score_impact_are_not_presented_as_legal_findings():
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

    assert response.severity == "NOT_EVALUATED"
    assert response.score_impact == 0
    assert response.is_black_override is False
    assert response.rule_name.startswith("Pending counsel review:")


def test_counsel_approved_flag_is_visible_after_release_switch(monkeypatch):
    monkeypatch.setattr(companies_api, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(companies_api, "VERIFIED_RULE_IDS", {"AGM-001"})
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
