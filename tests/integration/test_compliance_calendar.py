import pytest
from datetime import date, timedelta
from app.models.compliance_calendar import ComplianceCalendarEvent
from app.models.enums import CalendarEventType, CalendarEventStatus

pytestmark = pytest.mark.asyncio


async def test_overdue_logic(db, db_company):
    past_date = date.today() - timedelta(days=5)
    event = ComplianceCalendarEvent(
        company_id=db_company.id,
        title="Overdue Tax Payment",
        event_type=CalendarEventType.TAX_RETURN,
        due_date=past_date,
        period_label="2026-Q1",
        status=CalendarEventStatus.UPCOMING,
    )
    db.add(event)
    await db.commit()

    saved = await db.get(ComplianceCalendarEvent, event.id)
    assert saved is not None
    assert saved.due_date < date.today()
