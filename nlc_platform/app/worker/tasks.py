from datetime import datetime, timezone, timedelta

from sqlalchemy import select

from app.core.database import async_session_maker
from app.models import Filing, FilingStatus, Notification, NotificationType, NotificationStatus, EmailQueue, EmailQueueStatus


async def check_filing_deadlines():
    async with async_session_maker() as session:
        upcoming_cutoff = datetime.now(timezone.utc) + timedelta(days=7)

        result = await session.execute(
            select(Filing)
            .where(Filing.due_date <= upcoming_cutoff)
            .where(Filing.status == FilingStatus.PENDING)
        )
        filings = result.scalars().all()

        for filing in filings:
            notification = Notification(
                id=generate_uuid(),
                user_id=filing.created_by_id or "",
                notification_type=NotificationType.FILING_DEADLINE,
                title="Filing Deadline Approaching",
                message=f"Filing due date is approaching: {filing.filing_type.value}",
                link=f"/filings/{filing.id}",
            )
            session.add(notification)

            email = EmailQueue(
                id=generate_uuid(),
                recipient_email="admin@nlc.platform",
                subject="Filing Deadline Warning",
                body=f"Filing {filing.id} is due on {filing.due_date}",
            )
            session.add(email)

        await session.commit()
        return {"processed": len(filings)}


async def check_overdue_filings():
    async with async_session_maker() as session:
        result = await session.execute(
            select(Filing)
            .where(Filing.due_date < datetime.now(timezone.utc))
            .where(Filing.status == FilingStatus.PENDING)
        )
        filings = result.scalars().all()

        for filing in filings:
            filing.status = FilingStatus.OVERDUE

            notification = Notification(
                id=generate_uuid(),
                user_id=filing.created_by_id or "",
                notification_type=NotificationType.FILING_DEADLINE,
                title="Filing Overdue",
                message=f"Filing is now overdue: {filing.filing_type.value}",
                link=f"/filings/{filing.id}",
            )
            session.add(notification)

        await session.commit()
        return {"overdue": len(filings)}


async def send_daily_summary():
    async with async_session_maker() as session:
        result = await session.execute(
            select(Filing).where(Filing.status == FilingStatus.OVERDUE)
        )
        overdue = result.scalars().all()

        pending_result = await session.execute(
            select(Filing).where(Filing.status == FilingStatus.PENDING)
        )
        pending = pending_result.scalars().all()

        summary = f"""
Daily Compliance Summary
========================
Overdue Filings: {len(overdue)}
Pending Filings: {len(pending)}

Please review and take necessary actions.
"""

        email = EmailQueue(
            id=generate_uuid(),
            recipient_email="admin@nlc.platform",
            subject="Daily Compliance Summary",
            body=summary,
            status=EmailQueueStatus.PENDING,
        )
        session.add(email)

        await session.commit()
        return {"summary_sent": True}


def generate_uuid() -> str:
    import uuid

    return str(uuid.uuid4())


if __name__ == "__main__":
    import asyncio

    asyncio.run(check_filing_deadlines())
