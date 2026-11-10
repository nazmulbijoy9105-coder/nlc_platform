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
    assert not LEGAL_CALENDAR_RELEASED
    assert not VERIFIED_CALENDAR_EVENT_TYPES
    assert _generate_calendar(None) == []


def test_unapproved_statutory_penalties_are_never_estimated():
    assert not VERIFIED_PENALTY_EVENT_TYPES
    assert calculate_penalty("agm", 30) is None
    assert calculate_penalty("corporate_tax_return", 30) is None
    assert calculate_penalty("vat_return", 30) is None
    assert calculate_penalty("bsec_q1_report", 30) is None



def test_calendar_api_returns_unavailable_not_an_empty_no_deadline_claim(monkeypatch):
    monkeypatch.setattr(calendar_api, "LEGAL_CALENDAR_RELEASED", False)
    monkeypatch.setattr(calendar_api, "VERIFIED_CALENDAR_EVENT_TYPES", frozenset())
    monkeypatch.setattr(calendar_api, "VERIFIED_CALENDAR_RULE_IDS", frozenset())
    monkeypatch.setattr(calendar_api, "APPROVED_CALENDAR_EVENT_DEFINITIONS", ())
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

def test_legacy_calendar_generator_cannot_emit_unverified_deadlines():
    import asyncio

    from app.services.bd_calendar_generator import BDCalendarGenerator

    generator = BDCalendarGenerator(db=None)
    try:
        asyncio.run(
            generator.generate_for_company(
                company_id="00000000-0000-0000-0000-000000000001",
                incorporation_date=__import__("datetime").date(2020, 1, 1),
                fye=__import__("datetime").date(2025, 12, 31),
            )
        )
    except RuntimeError as exc:
        assert "independently approved" in str(exc)
    else:
        raise AssertionError("legacy calendar generator must remain disabled")


def test_source_specific_penalty_service_requires_event_type_allowlist(monkeypatch):
    from datetime import date
    from decimal import Decimal

    from app.services import compliance_calendar as calendar_service
    from app.services.legal_deadline_engine import PenaltyRule

    rule = PenaltyRule(
        rule_id="PEN-TEST-03",
        source_citation="Fixture-only source",
        source_version="fixture-v1",
        effective_from=date(2025, 1, 1),
        effective_to=None,
        liable_person="company",
        fixed_amount=Decimal("100"),
        approved=True,
    )
    monkeypatch.setattr(
        calendar_service, "VERIFIED_PENALTY_EVENT_TYPES", frozenset()
    )
    assert calendar_service.calculate_rule_penalty(
        rule,
        event_type="FIRST_AGM",
        days_overdue=20,
        due_date=date(2026, 1, 1),
        trigger_date=date(2026, 1, 1),
        as_of=date(2026, 1, 21),
        applicable=True,
        trigger_evidence_verified=True,
    ) is None
    monkeypatch.setattr(
        calendar_service,
        "VERIFIED_PENALTY_EVENT_TYPES",
        frozenset({"FIRST_AGM"}),
    )
    # Event-type approval alone is not approval of this caller-supplied rule.
    assert calendar_service.calculate_rule_penalty(
        rule,
        event_type="FIRST_AGM",
        days_overdue=20,
        due_date=date(2026, 1, 1),
        trigger_date=date(2026, 1, 1),
        as_of=date(2026, 1, 21),
        applicable=True,
        trigger_evidence_verified=True,
    ) is None
    monkeypatch.setattr(
        calendar_service, "VERIFIED_PENALTY_RULE_IDS", frozenset({"PEN-TEST-03"})
    )
    monkeypatch.setattr(calendar_service, "APPROVED_PENALTY_RULES", (rule,))
    assert calendar_service.calculate_rule_penalty(
        rule,
        event_type="FIRST_AGM",
        days_overdue=20,
        due_date=date(2026, 1, 1),
        trigger_date=date(2026, 1, 1),
        as_of=date(2026, 1, 21),
        applicable=True,
        trigger_evidence_verified=True,
    ) == Decimal("100.00")

    # A registered rule is still rejected when the event is not applicable
    # or the caller mutates any source/formula field.
    assert calendar_service.calculate_rule_penalty(
        rule,
        event_type="FIRST_AGM",
        days_overdue=20,
        due_date=date(2026, 1, 1),
        trigger_date=date(2026, 1, 1),
        as_of=date(2026, 1, 21),
        applicable=False,
        trigger_evidence_verified=True,
    ) is None
    from dataclasses import replace
    forged = replace(rule, fixed_amount=Decimal("999"))
    assert calendar_service.calculate_rule_penalty(
        forged,
        event_type="FIRST_AGM",
        days_overdue=20,
        due_date=date(2026, 1, 1),
        trigger_date=date(2026, 1, 1),
        as_of=date(2026, 1, 21),
        applicable=True,
        trigger_evidence_verified=True,
    ) is None



def test_calendar_release_requires_exact_nonempty_approved_manifest(monkeypatch):
    monkeypatch.setattr(calendar_api, "LEGAL_CALENDAR_RELEASED", True)
    monkeypatch.setattr(calendar_api, "VERIFIED_CALENDAR_EVENT_TYPES", frozenset({"FIRST_AGM"}))
    monkeypatch.setattr(calendar_api, "VERIFIED_CALENDAR_RULE_IDS", frozenset({"AGM-001"}))
    monkeypatch.setattr(calendar_api, "APPROVED_CALENDAR_EVENT_DEFINITIONS", ())
    try:
        calendar_api._require_calendar_release()
    except HTTPException as exc:
        assert exc.status_code == 503
    else:
        raise AssertionError("event-type/rule allowlists without a definition manifest must remain closed")
