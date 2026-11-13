"""API surface must not expose stored scores while legal release is paused."""
from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from uuid import uuid4

from app.api import companies as companies_api
from app.api.companies import _company_to_response, _flag_to_response


def _company(score, band):
    return SimpleNamespace(
        id=uuid4(),
        company_name="Visibility Test Co",
        registration_number="VIS-001",
        company_type="PRIVATE_LIMITED",
        incorporation_date=date(2020, 1, 1),
        is_active=True,
        current_compliance_score=score,
        current_risk_band=band,
        last_evaluated_at=None,
        directors=[],
        compliance_flags=[],
        financial_year_end=None,
    )


def test_legacy_stored_company_score_stays_hidden_while_release_is_paused():
    response = _company_to_response(_company(88, "GREEN"))

    assert response.band == "NOT_EVALUATED"
    assert response.compliance_score is None
    assert response.violation_count == 0
    assert response.active_flags == 0


def test_not_evaluated_company_does_not_expose_placeholder_score():
    response = _company_to_response(_company(100, "NOT_EVALUATED"))

    assert response.band == "NOT_EVALUATED"
    assert response.compliance_score is None


def test_released_company_score_is_visible_only_with_complete_verified_catalogue(monkeypatch):
    monkeypatch.setattr(companies_api, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(companies_api, "PRODUCT_SCORING_RULE_IDS", {"AGM-001"})
    monkeypatch.setattr(companies_api, "VERIFIED_RULE_IDS", {"AGM-001"})

    response = _company_to_response(_company(88, "GREEN"))

    # Still hidden unless the engine release gate itself is open; API mirrors that.
    assert response.band in ("NOT_EVALUATED", "GREEN")


def test_dashboard_summary_hides_score_aggregates_while_paused():
    summary = companies_api._build_flag_summary(
        [
            SimpleNamespace(severity="RED", flag_status="ACTIVE", rule_id="AGM-001"),
            SimpleNamespace(severity="YELLOW", flag_status="ACTIVE", rule_id="AR-001"),
        ]
    )
    assert summary["black"] == 0
    assert summary["red"] == 0
    assert summary["yellow"] == 0
    assert summary["total_active"] == 0


def test_pending_review_counts_are_exposed_while_scores_are_paused():
    result = companies_api._flag_summary_payload(
        [
            SimpleNamespace(severity="RED", flag_status="ACTIVE", rule_id="AGM-001"),
            SimpleNamespace(severity="YELLOW", flag_status="ACTIVE", rule_id="AR-001"),
        ]
    )
    assert result["pending_review"] == 2
    assert result["pending_review_flags"] == 2


def test_release_switch_without_product_scoring_rules_hides_company_score(monkeypatch):
    monkeypatch.setattr(companies_api, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(companies_api, "PRODUCT_SCORING_RULE_IDS", set())
    monkeypatch.setattr(companies_api, "VERIFIED_RULE_IDS", set())

    response = _company_to_response(_company(88, "GREEN"))

    assert response.band == "NOT_EVALUATED"
    assert response.compliance_score is None
    assert response.violation_count == 0


def test_product_switch_alone_cannot_publish_stored_company_score(monkeypatch):
    monkeypatch.setattr(companies_api, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(companies_api, "PRODUCT_SCORING_RULE_IDS", {"AGM-001"})
    monkeypatch.setattr(companies_api, "VERIFIED_RULE_IDS", set())

    response = _company_to_response(_company(88, "GREEN"))

    assert response.band == "NOT_EVALUATED"
    assert response.compliance_score is None
    assert response.active_flags == 0
    assert response.violation_count == 0


def test_released_flag_reports_rule_specific_counsel_verification(monkeypatch):
    monkeypatch.setattr(companies_api, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(companies_api, "PRODUCT_SCORING_RULE_IDS", {"AGM-001"})
    monkeypatch.setattr(companies_api, "VERIFIED_RULE_IDS", {"AGM-001"})
    flag = SimpleNamespace(
        id=uuid4(),
        rule_id="AGM-001",
        description="Counsel-verified AGM finding",
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
    assert response.legal_review_status == "LEGALLY_VERIFIED"


def test_partial_counsel_verification_cannot_release_company_api_score(monkeypatch):
    monkeypatch.setattr(companies_api, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(
        companies_api, "PRODUCT_SCORING_RULE_IDS", {"AGM-001", "TAX-001"}
    )
    monkeypatch.setattr(companies_api, "VERIFIED_RULE_IDS", {"AGM-001"})

    assert companies_api._legal_score_is_released() is False
    response = _company_to_response(_company(88, "GREEN"))
    assert response.band == "NOT_EVALUATED"
    assert response.compliance_score is None
