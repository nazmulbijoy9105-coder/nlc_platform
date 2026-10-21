from contextlib import asynccontextmanager
from datetime import date, timedelta

import pytest

from app.models.compliance_calendar import (
    ComplianceCalendarEvent,
    CalendarEventType,
    CalendarEventStatus,
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
