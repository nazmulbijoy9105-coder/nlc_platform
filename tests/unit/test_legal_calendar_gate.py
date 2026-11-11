"""Statutory calendar creation stays gated by registered product-owner releases."""

import pytest\n\nfrom fastapi import HTTPException

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
    from app.services import compliance_calendar as calendar_service

    monkeypatch.setattr(calendar_service, "LEGAL_CALENDAR_RELEASED", False)
    monkeypatch.setattr(calendar_service, "VERIFIED_CALENDAR_EVENT_TYPES", frozenset())
    monkeypatch.setattr(calendar_service, "VERIFIED_CALENDAR_RULE_IDS", frozenset())
    monkeypatch.setattr(calendar_service, "APPROVED_CALENDAR_EVENT_DEFINITIONS", ())
    try:
        calendar_api._require_calendar_release()
    except HTTPException as exc:
        assert exc.status_code == 503
        assert "No registered product-owner approved deadline manifest" in exc.detail
    else:
        raise AssertionError("calendar endpoint must fail closed before a product-owner deadline manifest")


def test_customer_facing_dashboard_reads_only_persisted_deadline_events():
    import app.api.companies as companies_api

    # New events can only be written through the source/mapping/owner-release
    # endpoint after a verified tenant fact is supplied. An empty result is
    # reported separately; it is not interpreted as no statutory obligations.
    companies_api._require_legal_dashboard_release(deadlines=True)


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
        assert "product-owner deadline registry" in str(exc)
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
    monkeypatch.setattr(calendar_service, "APPROVED_PENALTY_RULES", (("FIRST_AGM", rule),))
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

    # The wrapper derives an omitted due date from the overdue interval.
    assert calendar_service.calculate_rule_penalty(
        rule,
        event_type="FIRST_AGM",
        days_overdue=20,
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

    monkeypatch.setattr(
        calendar_service,
        "VERIFIED_PENALTY_EVENT_TYPES",
        frozenset({"FIRST_AGM", "ANNUAL_RETURN"}),
    )
    assert calendar_service.calculate_rule_penalty(
        rule,
        event_type="ANNUAL_RETURN",
        days_overdue=20,
        due_date=date(2026, 1, 1),
        trigger_date=date(2026, 1, 1),
        as_of=date(2026, 1, 21),
        applicable=True,
        trigger_evidence_verified=True,
    ) is None
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
    from app.services import compliance_calendar as calendar_service

    monkeypatch.setattr(calendar_service, "LEGAL_CALENDAR_RELEASED", True)
    monkeypatch.setattr(calendar_service, "VERIFIED_CALENDAR_EVENT_TYPES", frozenset({"FIRST_AGM"}))
    monkeypatch.setattr(calendar_service, "VERIFIED_CALENDAR_RULE_IDS", frozenset({"AGM-001"}))
    monkeypatch.setattr(calendar_service, "APPROVED_CALENDAR_EVENT_DEFINITIONS", ())

    try:
        calendar_api._require_calendar_release()
    except HTTPException as exc:
        assert exc.status_code == 503
    else:
        raise AssertionError("event-type/rule allowlists without a definition manifest must remain closed")


@pytest.mark.asyncio
async def test_customer_calendar_generation_uses_source_backed_definitions_and_tenant_facts(monkeypatch):
    from types import SimpleNamespace
    from uuid import uuid4

    from app.api import calendar as calendar_module

    company_id = uuid4()
    definition_with_fact = SimpleNamespace(
        id=uuid4(), rule_id="AGM-001", trigger_fact_key="incorporation_date"
    )
    definition_without_fact = SimpleNamespace(
        id=uuid4(), rule_id="AUD-001", trigger_fact_key="auditor_appointment_date"
    )
    fact = SimpleNamespace(id=uuid4())

    class Result:
        def __init__(self, rows=None, scalar=None):
            self.rows = rows or []
            self.scalar = scalar

        def scalars(self):
            return self

        def all(self):
            return self.rows

        def scalar_one_or_none(self):
            return self.scalar

    class FakeDb:
        def __init__(self):
            self.call_count = 0

        async def execute(self, statement):
            self.call_count += 1
            if self.call_count == 1:
                return Result(rows=[definition_with_fact, definition_without_fact])
            if self.call_count == 2:
                return Result(scalar=fact)
            if self.call_count == 3:
                return Result(scalar=None)
            raise AssertionError("unexpected database query")

    class FakeCalendarService:
        def __init__(self, db):
            self.db = db

        async def get_calendar(self, company_id, include_past_days, include_future_days):
            assert company_id == company_id
            assert include_past_days == 0
            assert include_future_days == 3 * 366
            return [{"event_id": "already-persisted"}]

    seen = []

    async def fake_preview_or_release_deadline(**kwargs):
        seen.append(kwargs["definition_id"])
        return {
            "status": "PRODUCT_OWNER_RELEASED",
            "customer_calendar_write": True,
            "calendar_event_id": "fixture-event",
        }

    monkeypatch.setattr(
        calendar_module,
        "preview_or_release_deadline",
        fake_preview_or_release_deadline,
    )
    monkeypatch.setattr(calendar_module, "ComplianceCalendarService", FakeCalendarService)

    result = await calendar_module.generate_calendar(
        company_id=company_id,
        years_ahead=3,
        db=FakeDb(),
        current_user=SimpleNamespace(role="CLIENT_DIRECTOR"),
    )

    assert result["processed"] == 2
    assert result["count"] == 1
    assert result["without_trigger_fact"] == 1
    assert result["results"][0]["status"] == "PRODUCT_OWNER_RELEASED"
    assert result["results"][1]["status"] == "NO_TRIGGER_FACT"
    assert seen == [definition_with_fact.id]
    assert result["events"] == [{"event_id": "already-persisted"}]
    assert result["no_obligation_inference"] is True
