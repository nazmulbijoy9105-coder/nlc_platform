"""
NEUM LEX COUNSEL — Notification Service
app/services/notification_service.py

Implements _queue_notification, _get_user_notifications,
_acknowledge_notification, _send_upcoming_deadline_warnings stubs.

Channels: Dashboard, Email (AWS SES), WhatsApp (optional).
AI Constitution Article 6: All notifications logged with flag reference.
"""
from __future__ import annotations

import uuid
import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import and_, or_, select

from app.models.enums import NotificationChannel, NotificationStatus
from app.rule_engine.engine import LEGAL_SCORE_RELEASED, VERIFIED_RULE_IDS
from app.models.infrastructure import Notification
from app.services.base import BaseService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


_RULE_NOTIFICATION_TYPE = re.compile(r"^[A-Z]{2,5}-[0-9]{3}$")


def is_rule_notification_type(notification_type: str | None) -> bool:
    return bool(notification_type and _RULE_NOTIFICATION_TYPE.fullmatch(notification_type))


GENERIC_LEGAL_ALERT_TYPES = frozenset({
    "COMPLIANCE_ALERT", "LEGAL_ALERT", "RISK_ALERT", "RULE_ALERT",
})
NON_LEGAL_OPERATIONAL_NOTIFICATION_TYPES = frozenset({
    "SYSTEM",
    "AI_REVIEW_QUEUE_ALERT",
    "SRO_RULE_UPDATE_REQUIRED",
})
NON_LEGAL_OPERATIONAL_PREFIXES = (
    "BILLING_", "PAYMENT_", "SUBSCRIPTION_", "ACCOUNT_SECURITY_",
)


def is_notification_eligible(
    notification_type: str | None,
    *,
    related_flag_id: uuid.UUID | None = None,
) -> bool:
    """Allow only known operational notifications; legal and unknown types fail closed."""
    normalized_type = str(notification_type or "").strip().upper()
    if not normalized_type or related_flag_id is not None:
        return False
    if is_rule_notification_type(normalized_type):
        return LEGAL_SCORE_RELEASED and normalized_type in VERIFIED_RULE_IDS
    if normalized_type in GENERIC_LEGAL_ALERT_TYPES:
        return False
    legal_tokens = (
        "COMPLIANCE", "LEGAL", "RISK", "RULE_ALERT", "TAX_", "VAT_",
        "AGM_", "BSEC_", "LABOUR_", "LABOR_", "TRADE_LICENCE_", "TRADE_LICENSE_",
    )
    if any(token in normalized_type for token in legal_tokens):
        return False
    if normalized_type in NON_LEGAL_OPERATIONAL_NOTIFICATION_TYPES:
        return True
    if normalized_type.startswith(NON_LEGAL_OPERATIONAL_PREFIXES):
        return True
    if normalized_type.endswith("_DEADLINE_WARNING") or normalized_type.startswith("DEADLINE_"):
        return False
    return False


class NotificationService(BaseService[Notification]):
    model = Notification

    async def queue_notification(
        self,
        *,
        company_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        title: str | None = None,
        body: str | None = None,
        notification_type: str | None = None,
        channel: NotificationChannel = NotificationChannel.DASHBOARD,
        days_until_deadline: int | None = None,
        related_flag_id: uuid.UUID | None = None,
        scheduled_for: datetime | None = None,
        subject=None,
        message=None
    ) -> Notification:
        title = title or subject
        body = body or message
        notification_type = notification_type or 'SYSTEM'
        # Unapproved legal alerts remain auditable but never enter delivery queues.
        legal_alert_eligible = is_notification_eligible(
            notification_type,
            related_flag_id=related_flag_id,
        )
        return await self.create(
            company_id=company_id,
            user_id=user_id,
            title=title,
            body=body,
            notification_type=notification_type,
            channel=channel,
            notification_status=(
                NotificationStatus.PENDING
                if legal_alert_eligible
                else NotificationStatus.SUPPRESSED
            ),
            failure_reason=(
                None
                if legal_alert_eligible
                else "Suppressed at creation: legal rule is not counsel-approved for release."
            ),
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
        # A provisional RED/BLACK engine label is not an authorised legal
        # alert. Do not notify customers until the statutory score release
        # gate is open and the rule is in the internally source-checked set.
        from app.rule_engine.engine import LEGAL_SCORE_RELEASED, VERIFIED_RULE_IDS, RuleState

        if not LEGAL_SCORE_RELEASED:
            return

        for flag in flags:
            severity = getattr(getattr(flag, "severity", None), "value", getattr(flag, "severity", ""))
            rule_id = getattr(flag, "rule_id", "")
            if severity not in ("RED", "BLACK") or rule_id not in VERIFIED_RULE_IDS:
                continue
            if (
                getattr(flag, "state", None) != RuleState.NON_COMPLIANT
                or getattr(flag, "eval_state", "VIOLATION") == "UNKNOWN"
            ):
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
            f"{company_name}: an unverified internal reminder for {deadline_type} "
            f"contains a provisional date of {deadline_date}.\n"
            f"This is not a verified statutory deadline or a finding of default. "
            f"Confirm the applicable law, company classification, event date, "
            f"extensions and filing evidence with qualified counsel before relying on it."
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
        offset=0
    ) -> list[Notification]:
        """
        Get notifications for a user.
        _get_user_notifications stub implementation.
        """
        filters = [
            or_(
                Notification.user_id == user_id,
                and_(Notification.user_id.is_(None), Notification.company_id.is_not(None)),
            )
        ]
        if company_id:
            filters.append(Notification.company_id == company_id)
        if unread_only:
            filters.append(Notification.notification_status == NotificationStatus.PENDING)

        result = await self.db.execute(
            select(Notification)
            .where(*filters)
            .order_by(Notification.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return [
            n for n in result.scalars().all()
            if n.notification_status != NotificationStatus.SUPPRESSED
            and is_notification_eligible(n.notification_type)
        ]

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
        return [
            n for n in result.scalars().all()
            if n.notification_status != NotificationStatus.SUPPRESSED
            and is_notification_eligible(n.notification_type)
        ]

    async def acknowledge(
        self,
        notification_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Notification | None:
        """
        Mark a notification as acknowledged.
        _acknowledge_notification stub implementation.
        """
        notif = await self.get_by_id(notification_id)
        if not notif or notif.notification_status == NotificationStatus.SUPPRESSED or (notif.user_id is not None and notif.user_id != user_id):
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

    async def mark_suppressed(
        self,
        notification_id: uuid.UUID,
        reason: str,
    ) -> Notification | None:
        """Stop an unapproved legal-rule alert from entering delivery queues."""
        notif = await self.get_by_id(notification_id)
        if not notif:
            return None
        return await self.update_instance(
            notif,
            notification_status=NotificationStatus.SUPPRESSED,
            failure_reason=reason,
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
        # Apply the same closed operational allowlist in SQL before LIMIT.
        # Otherwise legacy deadline/unknown legal notices can consume the batch
        # and starve unrelated payment, subscription or operational notices.
        rule_id_type = Notification.notification_type.op("~")(r"^[A-Z]{2,5}-[0-9]{3}$")
        operational_prefix = Notification.notification_type.op("~")(
            r"^(BILLING_|PAYMENT_|SUBSCRIPTION_|ACCOUNT_SECURITY_)"
        )
        legal_type_pattern = Notification.notification_type.op("~")(
            r"(COMPLIANCE|LEGAL|RISK|RULE_ALERT|TAX_|VAT_|AGM_|BSEC_|LABOUR_|LABOR_|TRADE_LICENCE_|TRADE_LICENSE_)"
        )
        eligible_operational = and_(
            Notification.related_flag_id.is_(None),
            ~legal_type_pattern,
            or_(
                Notification.notification_type.in_(NON_LEGAL_OPERATIONAL_NOTIFICATION_TYPES),
                operational_prefix,
            ),
        )
        if LEGAL_SCORE_RELEASED:
            eligible_rule = and_(
                rule_id_type,
                Notification.notification_type.in_(VERIFIED_RULE_IDS),
            )
            filters.append(or_(eligible_rule, eligible_operational))
        else:
            filters.append(eligible_operational)
        result = await self.db.execute(
            select(Notification)
            .where(*filters)
            .order_by(Notification.created_at)
            .limit(limit)
        )
        # Re-check the release gate at dispatch time. Rows queued before the
        # gate was closed (or before this guard existed) must not be delivered.
        return [
            n for n in result.scalars().all()
            if is_notification_eligible(
                n.notification_type,
                related_flag_id=n.related_flag_id,
            )
        ]


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
        user_id: uuid.UUID | None = None,
        actor_user_id: uuid.UUID | None = None,
        company_id: uuid.UUID | None = None,
        action: str,
        resource_type: str | None = None,
        resource_id: uuid.UUID | str | None = None,
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
        if user_id is None:
            user_id = actor_user_id
        if isinstance(resource_id, str):
            try:
                resource_id = uuid.UUID(resource_id)
            except ValueError:
                resource_id = None
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
        # Audit records are mandatory. Propagate insert/RLS failures so the
        # caller's transaction is rolled back instead of silently losing the
        # audit record and leaving the AsyncSession in a failed state.
        await self.db.flush()

    async def get_logs(
        self,
        *,
        user_id: uuid.UUID | None = None,
        company_id: uuid.UUID | None = None,
        action: str | None = None,
        days: int = 90,
        limit: int = 200,
        offset: int = 0,
        resource_type=None,
        resource_id=None
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
        return result.scalars().all()
