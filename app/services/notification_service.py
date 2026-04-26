"""
NEUM LEX COUNSEL — Notification Service
app/services/notification_service.py

Implements _queue_notification, _get_user_notifications,
_acknowledge_notification, _send_upcoming_deadline_warnings stubs.

Channels: Dashboard, Email (AWS SES), WhatsApp (optional).
AI Constitution Article 6: All notifications logged with flag reference.
"""
from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import select

from app.models.enums import NotificationChannel, NotificationStatus
from app.models.infrastructure import Notification
from app.services.base import BaseService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("nlc.notification")


class NotificationService(BaseService[Notification]):
    model = Notification

    async def queue_notification(
        self,
        *,
        company_id: uuid.UUID | None,
        user_id: uuid.UUID | None = None,
        title: str,
        body: str,
        notification_type: str,
        channel: NotificationChannel = NotificationChannel.DASHBOARD,
        days_until_deadline: int | None = None,
        related_flag_id: uuid.UUID | None = None,
        scheduled_for: datetime | None = None,
    ) -> Notification:
        """
        Queue a notification for delivery.
        _queue_notification stub implementation.
        Dashboard notifications are immediately PENDING.
        Email/WhatsApp are sent by Celery worker.
        """
        return await self.create(
            company_id=company_id,
            user_id=user_id,
            title=title,
            body=body,
            notification_type=notification_type,
            channel=channel,
            notification_status=NotificationStatus.PENDING,
            scheduled_for=scheduled_for or datetime.now(UTC),
            days_until_deadline=days_until_deadline,
            related_flag_id=related_flag_id,
        )

    async def queue_for_new_flags(
        self,
        company_id: uuid.UUID,
        flags: list[Any],  # ComplianceFlag objects from rule engine output
    ) -> None:
        """
        Generate notifications for new RED/BLACK compliance flags.
        _process_flag_notifications stub implementation.
        """
        for flag in flags:
            severity = getattr(flag, "severity", "")
            if severity not in ("RED", "BLACK"):
                continue

            title = f"{'🔴' if severity == 'RED' else '⚫'} Compliance Alert: {getattr(flag, 'rule_id', '')}"
            body = (
                f"{getattr(flag, 'description', '')}\n\n"
                f"Statutory Basis: {getattr(flag, 'statutory_basis', '')}\n"
                f"Score Impact: -{getattr(flag, 'score_impact', 0)} points\n"
                f"Action Required: {getattr(flag, 'revenue_tier', '').replace('_', ' ')}"
            )
            await self.queue_notification(
                company_id=company_id,
                title=title,
                body=body,
                notification_type=getattr(flag, "rule_id", "COMPLIANCE_FLAG"),
                channel=NotificationChannel.DASHBOARD,
            )

            # Also queue email for critical flags
            if severity == "BLACK":
                await self.queue_notification(
                    company_id=company_id,
                    title=title,
                    body=body,
                    notification_type=getattr(flag, "rule_id", "COMPLIANCE_FLAG"),
                    channel=NotificationChannel.EMAIL,
                )

    async def queue_deadline_warnings(
        self,
        company_id: uuid.UUID,
        deadline_type: str,
        days_remaining: int,
        deadline_date: str,
        company_name: str,
    ) -> None:
        """
        Queue deadline warning notifications.
        _send_upcoming_deadline_warnings stub implementation.
        """
        urgency = "URGENT: " if days_remaining <= 7 else ""
        title = f"{urgency}{deadline_type} Deadline in {days_remaining} days"
        body = (
            f"{company_name}: {deadline_type} is due on {deadline_date}.\n"
            f"You have {days_remaining} day{'s' if days_remaining != 1 else ''} remaining.\n"
            f"Immediate action required to avoid compliance default."
        )
        await self.queue_notification(
            company_id=company_id,
            title=title,
            body=body,
            notification_type=f"{deadline_type}_DEADLINE_WARNING",
            channel=NotificationChannel.DASHBOARD,
            days_until_deadline=days_remaining,
        )

    async def get_for_user(
        self,
        user_id: uuid.UUID,
        *,
        company_id: uuid.UUID | None = None,
        unread_only: bool = False,
        limit: int = 50,
    ) -> list[Notification]:
        """
        Get notifications for a user.
        _get_user_notifications stub implementation.
        """
        filters = [Notification.user_id == user_id]
        if company_id:
            filters.append(Notification.company_id == company_id)
        if unread_only:
            filters.append(Notification.notification_status == NotificationStatus.PENDING)

        result = await self.db.execute(
            select(Notification)
            .where(*filters)
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_for_company(
        self,
        company_id: uuid.UUID,
        *,
        limit: int = 50,
    ) -> list[Notification]:
        """Get all notifications for a company (admin view)."""
        result = await self.db.execute(
            select(Notification)
            .where(Notification.company_id == company_id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def acknowledge(
        self,
        notification_id: uuid.UUID,
        acknowledged_by: uuid.UUID,
    ) -> Notification | None:
        """
        Mark a notification as acknowledged.
        _acknowledge_notification stub implementation.
        """
        notif = await self.get_by_id(notification_id)
        if not notif:
            return None
        return await self.update_instance(
            notif,
            notification_status=NotificationStatus.ACKNOWLEDGED,
            acknowledged_at=datetime.now(UTC),
        )

    async def mark_sent(
        self,
        notification_id: uuid.UUID,
    ) -> Notification | None:
        """Mark as sent (called by Celery email/WhatsApp worker)."""
        notif = await self.get_by_id(notification_id)
        if not notif:
            return None
        return await self.update_instance(
            notif,
            notification_status=NotificationStatus.SENT,
            sent_at=datetime.now(UTC),
        )

    async def mark_failed(
        self,
        notification_id: uuid.UUID,
        reason: str,
    ) -> Notification | None:
        """Mark as failed with reason (delivery failure)."""
        notif = await self.get_by_id(notification_id)
        if not notif:
            return None
        return await self.update_instance(
            notif,
            notification_status=NotificationStatus.FAILED,
            failure_reason=reason,
            retry_count=notif.retry_count + 1,
        )

    async def get_pending(
        self,
        channel: NotificationChannel | None = None,
        limit: int = 100,
    ) -> list[Notification]:
        """Get pending notifications for the Celery delivery worker."""
        filters = [Notification.notification_status == NotificationStatus.PENDING]
        if channel:
            filters.append(Notification.channel == channel)
        result = await self.db.execute(
            select(Notification)
            .where(*filters)
            .order_by(Notification.created_at)
            .limit(limit)
        )
        return list(result.scalars().all())


# ═══════════════════════════════════════════════════════════════════════
# ACTIVITY LOG SERVICE
# ═══════════════════════════════════════════════════════════════════════

class ActivityService:
    """
    Append-only audit trail service.
    AI Constitution Article 6: Every write operation must produce an audit log entry.
    user_activity_logs table: INSERT only, no UPDATE, no DELETE.
    7-year retention minimum.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def log(
        self,
        *,
        user_id: uuid.UUID | None,
        company_id: uuid.UUID | None,
        action: str,
        resource_type: str | None = None,
        resource_id: uuid.UUID | None = None,
        description: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
        detail: dict | None = None,
    ) -> None:
        """
        Append a single activity log entry.
        _log_activity stub implementation.
        Always called in background — never blocks the response.
        """
        from app.models.infrastructure import UserActivityLog
        log = UserActivityLog(
            id=uuid.uuid4(),
            user_id=user_id,
            company_id=company_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            request_id=request_id,
            detail=detail,
            logged_at=datetime.now(UTC),
        )
        self.db.add(log)
        try:
            await self.db.flush()
        except Exception as exc:
            # Never let audit logging fail a request
            logger.error(f"[ActivityService] Failed to log {action}: {exc}")

    async def get_logs(
        self,
        *,
        user_id: uuid.UUID | None = None,
        company_id: uuid.UUID | None = None,
        action: str | None = None,
        days: int = 90,
        limit: int = 200,
        offset: int = 0,
    ) -> list[dict]:
        """
        Query audit logs with filters.
        _get_activity_logs stub implementation.
        """
        from datetime import timedelta

        from app.models.infrastructure import UserActivityLog

        filters = [
            UserActivityLog.logged_at >= datetime.now(UTC) - timedelta(days=days)
        ]
        if user_id:
            filters.append(UserActivityLog.user_id == user_id)
        if company_id:
            filters.append(UserActivityLog.company_id == company_id)
        if action:
            filters.append(UserActivityLog.action.ilike(f"%{action}%"))

        result = await self.db.execute(
            select(UserActivityLog)
            .where(*filters)
            .order_by(UserActivityLog.logged_at.desc())
            .limit(limit)
            .offset(offset)
        )
        logs = result.scalars().all()
        return [
            {
                "id":            str(log.id),
                "user_id":       str(log.user_id) if log.user_id else None,
                "company_id":    str(log.company_id) if log.company_id else None,
                "action":        log.action,
                "resource_type": log.resource_type,
                "resource_id":   str(log.resource_id) if log.resource_id else None,
                "description":   log.description,
                "ip_address":    log.ip_address,
                "request_id":    log.request_id,
                "logged_at":     log.logged_at.isoformat(),
            }
            for log in logs
        ]
