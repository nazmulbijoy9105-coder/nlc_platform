"""Statutory calendar must remain unavailable until legal approval is real."""

from fastapi import HTTPException

import app.api.calendar as calendar_api

from app.services.compliance_calendar import (
    LEGAL_CALENDAR_RELEASED,
    VERIFIED_CALENDAR_EVENT_TYPES,
    VERIFIED_PENALTY_EVENT_TYPES,
    _generate_calendar,
    calculate_penalty,
)


def test_statutory_calendar_is_fail_closed():
    assert LEGAL_CALENDAR_RELEASED is False
    assert VERIFIED_CALENDAR_EVENT_TYPES == frozenset()
    assert _generate_calendar(None) == []


def test_unapproved_statutory_penalties_are_never_estimated():
    assert VERIFIED_PENALTY_EVENT_TYPES == frozenset()
    assert calculate_penalty("agm", 30) is None
    assert calculate_penalty("corporate_tax_return", 30) is None
    assert calculate_penalty("vat_return", 30) is None
    assert calculate_penalty("bsec_q1_report", 30) is None



def test_calendar_api_returns_unavailable_not_an_empty_no_deadline_claim(monkeypatch):
    monkeypatch.setattr(calendar_api, "LEGAL_CALENDAR_RELEASED", False)
    monkeypatch.setattr(calendar_api, "VERIFIED_CALENDAR_EVENT_TYPES", frozenset())
    try:
        calendar_api._require_calendar_release()
    except HTTPException as exc:
        assert exc.status_code == 503
        assert "pending rule-level legal validation" in exc.detail
    else:
        raise AssertionError("calendar endpoint must fail closed before legal approval")


def test_customer_facing_dashboard_deadlines_fail_closed(monkeypatch):
    import app.api.companies as companies_api

    monkeypatch.setattr(companies_api, "LEGAL_CALENDAR_RELEASED", False)
    try:
        companies_api._require_legal_dashboard_release(deadlines=True)
    except HTTPException as exc:
        assert exc.status_code == 503
        assert "Statutory deadlines are unavailable" in exc.detail
    else:
        raise AssertionError("dashboard must not expose unapproved statutory deadlines")


def test_dashboard_risk_aggregates_fail_closed_until_score_release(monkeypatch):
    import app.api.companies as companies_api

    monkeypatch.setattr(companies_api, "LEGAL_SCORE_RELEASED", False)
    try:
        companies_api._require_legal_dashboard_release()
    except HTTPException as exc:
        assert exc.status_code == 503
        assert "Compliance risk aggregates are unavailable" in exc.detail
    else:
        raise AssertionError("dashboard must not expose unreleased legal risk aggregates")
