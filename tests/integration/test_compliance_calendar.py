import uuid
import pytest
from datetime import date, timedelta
from app.models.compliance_calendar import ComplianceCalendarEvent, CalendarEventType, CalendarEventStatus
from app.tasks.compliance_tasks import check_overdue_events

pytestmark = pytest.mark.asyncio

async def test_overdue_logic(db):
    """Test that the background task correctly marks UPCOMING events as OVERDUE"""
    past_date = date.today() - timedelta(days=5)
    
    event = ComplianceCalendarEvent(
        company_id=uuid.uuid4(),
        title="Overdue Tax Payment",
        event_type=CalendarEventType.TAX_RETURN,
        due_date=past_date,
        period_label="2026-Q1",
        status=CalendarEventStatus.UPCOMING
    )
    db.add(event)
    await db.commit()

    # Run the actual background task
    overdue_count = await check_overdue_events()
    assert overdue_count > 0

    # Verify the event was updated in the DB
    saved_event = await db.get(ComplianceCalendarEvent, event.id)
    assert saved_event.status == CalendarEventStatus.OVERDUE
