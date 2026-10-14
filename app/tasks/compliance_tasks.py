import logging
from datetime import datetime
from sqlalchemy import select
from app.core.database import async_session_maker
from app.models.compliance_calendar import ComplianceCalendarEvent, CalendarEventStatus

logger = logging.getLogger(__name__)

async def check_overdue_events():
    """Background task to mark pending events as overdue if past their due_date."""
    async with async_session_maker() as db:
        result = await db.execute(
            select(ComplianceCalendarEvent).where(
                ComplianceCalendarEvent.status == CalendarEventStatus.PENDING,
                ComplianceCalendarEvent.due_date < datetime.utcnow()
            )
        )
        overdue_events = result.scalars().all()
        
        for event in overdue_events:
            event.status = CalendarEventStatus.OVERDUE
            logger.info(f"Event {event.id} ({event.title}) marked as OVERDUE")
            
        await db.commit()
        return len(overdue_events)
