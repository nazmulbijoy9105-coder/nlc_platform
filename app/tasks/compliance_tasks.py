import logging
from datetime import date

from sqlalchemy import select

from app.models.compliance_calendar import ComplianceCalendarEvent
from app.models.database import AsyncSessionLocal
from app.models.enums import CalendarEventStatus

logger = logging.getLogger(__name__)


async def check_overdue_events() -> int:
    """Mark UPCOMING/DUE_SOON events past their due_date as OVERDUE."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ComplianceCalendarEvent).where(
                ComplianceCalendarEvent.status.in_(
                    [CalendarEventStatus.UPCOMING, CalendarEventStatus.DUE_SOON]
                ),
                ComplianceCalendarEvent.due_date < date.today(),
            )
        )
        events = result.scalars().all()
        for event in events:
            event.status = CalendarEventStatus.OVERDUE
            logger.info("Event %s (%s) marked OVERDUE", event.id, event.title)
        await db.commit()
        return len(events)
