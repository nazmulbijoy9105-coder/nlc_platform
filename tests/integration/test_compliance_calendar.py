from contextlib import asynccontextmanager
from datetime import date, timedelta

import pytest

from app.models.compliance_calendar import (
    CalendarEventStatus,
    CalendarEventType,
    ComplianceCalendarEvent,
)
from app.tasks.compliance_tasks import check_overdue_events

pytestmark = pytest.mark.asyncio


async def test_overdue_logic(db, db_company, monkeypatch):
    """Mark a past-due event OVERDUE without escaping the test transaction."""
    past_date = date.today() - timedelta(days=5)

    event = ComplianceCalendarEvent(
        company_id=db_company.id,
        title="Overdue Tax Payment",
        event_type=CalendarEventType.TAX_RETURN,
        due_date=past_date,
        period_label=f"TEST-{date.today().isoformat()}",
        status=CalendarEventStatus.UPCOMING,
    )
    db.add(event)
    await db.flush()

    # Keep the task inside the fixture's rollback-protected test session.
    # The real task otherwise opens an independent session that cannot see
    # uncommitted rows in this test's transaction.
    @asynccontextmanager
    async def test_session():
        yield db

    monkeypatch.setattr(
        "app.tasks.compliance_tasks.AsyncSessionLocal",
        test_session,
    )

    overdue_count = await check_overdue_events()

    assert overdue_count >= 1

    saved_event = await db.get(ComplianceCalendarEvent, event.id)
    assert saved_event is not None
    assert saved_event.status == CalendarEventStatus.OVERDUE



async def test_approved_calendar_definition_persists_legal_provenance(
    db, db_company, monkeypatch
):
    from app.models.enums import CalendarEventType
    from app.services import compliance_calendar as calendar_service
    from app.services.legal_deadline_engine import DeadlineRule

    monkeypatch.setattr(calendar_service, "LEGAL_CALENDAR_RELEASED", True)
    monkeypatch.setattr(
        calendar_service,
        "VERIFIED_CALENDAR_EVENT_TYPES",
        frozenset({CalendarEventType.FIRST_AGM.value}),
    )
    definition = calendar_service.CalendarEventDefinition(
        event_type=CalendarEventType.FIRST_AGM,
        title="Fixture statutory deadline",
        period_label="FIXTURE-2026",
        rule=DeadlineRule(
            rule_id="TEST-CAL-001",
            source_citation="Fixture-only source, section 1",
            source_version="fixture-v1",
            effective_from=date(2020, 1, 1),
            effective_to=None,
            offset=10,
            unit="DAYS",
            approved=True,
        ),
        trigger_date=date(2026, 1, 1),
        applicable=True,
        trigger_evidence_verified=True,
        trigger_evidence_ref="fixture:evidence:agm-date",
    )
    monkeypatch.setattr(calendar_service, "VERIFIED_CALENDAR_RULE_IDS", frozenset({"TEST-CAL-001"}))
    monkeypatch.setattr(calendar_service, "APPROVED_CALENDAR_EVENT_DEFINITIONS", (definition,))

    service = calendar_service.ComplianceCalendarService(db)
    events = await service.generate_approved_events(db_company.id, [definition])
    assert len(events) == 1
    event = events[0]
    assert event.due_date == date(2026, 1, 11)
    assert event.legal_rule_id == "TEST-CAL-001"
    assert event.legal_source_version == "fixture-v1"
    assert event.legal_effective_from == date(2020, 1, 1)
    assert event.legal_trigger_date == date(2026, 1, 1)
    assert event.trigger_evidence_ref == "fixture:evidence:agm-date"
    assert len(event.legal_manifest_sha256) == 64

    # Repeated generation updates the same unique company/type/period row.
    again = await service.generate_approved_events(db_company.id, [definition])
    assert len(again) == 1
    assert again[0].id == event.id


async def test_calendar_does_not_persist_unverified_or_inapplicable_trigger(
    db, db_company, monkeypatch
):
    from app.models.enums import CalendarEventType
    from app.services import compliance_calendar as calendar_service
    from app.services.legal_deadline_engine import DeadlineRule

    monkeypatch.setattr(calendar_service, "LEGAL_CALENDAR_RELEASED", True)
    monkeypatch.setattr(
        calendar_service,
        "VERIFIED_CALENDAR_EVENT_TYPES",
        frozenset({CalendarEventType.FIRST_AGM.value}),
    )
    definition = calendar_service.CalendarEventDefinition(
        event_type=CalendarEventType.FIRST_AGM,
        title="Must not emit",
        period_label="FIXTURE-UNKNOWN",
        rule=DeadlineRule(
            rule_id="TEST-CAL-UNKNOWN",
            source_citation="Fixture-only source, section 1",
            source_version="fixture-v1",
            effective_from=date(2020, 1, 1),
            effective_to=None,
            offset=10,
            unit="DAYS",
            approved=True,
        ),
        trigger_date=date(2026, 1, 1),
        applicable=True,
        trigger_evidence_verified=False,
        trigger_evidence_ref="fixture:evidence:unverified",
    )
    monkeypatch.setattr(calendar_service, "VERIFIED_CALENDAR_RULE_IDS", frozenset({"TEST-CAL-UNKNOWN"}))
    monkeypatch.setattr(calendar_service, "APPROVED_CALENDAR_EVENT_DEFINITIONS", (definition,))

    service = calendar_service.ComplianceCalendarService(db)
    assert await service.generate_approved_events(db_company.id, [definition]) == []



async def test_calendar_rejects_caller_forged_definition_even_for_approved_event_type(
    db, db_company, monkeypatch
):
    from dataclasses import replace

    from app.models.enums import CalendarEventType
    from app.services import compliance_calendar as calendar_service
    from app.services.legal_deadline_engine import DeadlineRule

    approved = calendar_service.CalendarEventDefinition(
        event_type=CalendarEventType.FIRST_AGM,
        title="Approved fixture event",
        period_label="APPROVED-2026",
        rule=DeadlineRule(
            rule_id="TEST-CAL-APPROVED",
            source_citation="Fixture-only source, section 1",
            source_version="fixture-v1",
            effective_from=date(2020, 1, 1),
            effective_to=None,
            offset=10,
            unit="DAYS",
            approved=True,
        ),
        trigger_date=date(2026, 1, 1),
        applicable=True,
        trigger_evidence_verified=True,
        trigger_evidence_ref="fixture:evidence:approved",
    )
    forged = replace(
        approved,
        title="Caller-invented statutory event",
        period_label="FORGED-2026",
    )
    monkeypatch.setattr(calendar_service, "LEGAL_CALENDAR_RELEASED", True)
    monkeypatch.setattr(
        calendar_service,
        "VERIFIED_CALENDAR_EVENT_TYPES",
        frozenset({CalendarEventType.FIRST_AGM.value}),
    )
    monkeypatch.setattr(
        calendar_service, "VERIFIED_CALENDAR_RULE_IDS", frozenset({"TEST-CAL-APPROVED"})
    )
    monkeypatch.setattr(
        calendar_service, "APPROVED_CALENDAR_EVENT_DEFINITIONS", (approved,)
    )

    service = calendar_service.ComplianceCalendarService(db)
    with pytest.raises(PermissionError, match="exact counsel-approved"):
        await service.generate_approved_events(db_company.id, [forged])
    assert not any(isinstance(item, ComplianceCalendarEvent) for item in db.new)
