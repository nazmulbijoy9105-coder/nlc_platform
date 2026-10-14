import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.compliance_calendar import ComplianceCalendarEvent, CalendarEventType, CalendarEventStatus

pytestmark = pytest.mark.asyncio

async def test_overdue_logic(db_session: AsyncSession):
    """Test that the database correctly stores and retrieves overdue events"""
    past_date = datetime.utcnow() - timedelta(days=5)
    
    event = ComplianceCalendarEvent(
        title="Overdue Tax Payment",
        event_type=CalendarEventType.TAX_DEADLINE,
        due_date=past_date,
        status=CalendarEventStatus.PENDING
    )
    db_session.add(event)
    await db_session.commit()
    
    saved_event = await db_session.get(ComplianceCalendarEvent, event.id)
    assert saved_event is not None
    assert saved_event.due_date < datetime.utcnow()
