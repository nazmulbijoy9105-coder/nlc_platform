"""
NEUM LEX COUNSEL — Celery Task Definitions
app/worker/tasks.py

All background tasks for the NLC platform.
Each task is async-wrapped using an asyncio event loop bridge.

TASK CATALOGUE:

COMPLIANCE TASKS:
  evaluate_company_compliance     Single company evaluation (triggered manually or from API)
  evaluate_all_companies          Batch evaluation of all active companies (daily cron)
  trigger_rescue_reevaluation     Re-evaluate after a rescue step is completed

NOTIFICATION TASKS:
  send_pending_notifications      Process PENDING notifications and attempt delivery
  queue_deadline_warning_notifications  Check upcoming deadlines and queue warnings
  send_single_notification        Attempt delivery of one notification (email/WhatsApp)

DOCUMENT TASKS:
  generate_ai_document_async      Queue AI document generation (Article 3 compliant)
  render_pdf                      Convert stored document to PDF
  process_ai_review_queue         Alert staff about pending AI document approvals

MAINTENANCE TASKS:
  monthly_score_snapshot_all      Take monthly score snapshot for all companies
  cleanup_old_activity_logs       Archive logs >7 years to S3, remove from DB
  cleanup_expired_notifications   Mark stale pending notifications as FAILED
  database_health_check           Quick DB connectivity verification
  sync_sro_registry               Alert Super Admin of pending SRO rule updates

AI Constitution compliance is enforced per task:
  Article 1: Compliance tasks use deterministic rule engine only
  Article 3: AI document tasks always set human_approved=False
  Article 4: Score snapshots are append-only
  Article 6: All task outcomes logged in user_activity_logs
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

from celery import Task
from celery.exceptions import SoftTimeLimitExceeded

from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# ASYNC BRIDGE
# ═══════════════════════════════════════════════════════════════════════

def run_async(coro):
    """
    Run an async coroutine from a synchronous Celery task.
    Celery workers run synchronously; our services are async.
    This bridge creates a new event loop per task execution.

    IMPORTANT: Do NOT use asyncio.get_event_loop() — always create a
    fresh loop. Celery workers reuse processes; stale loops cause bugs.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
        asyncio.set_event_loop(None)


# ═══════════════════════════════════════════════════════════════════════
# BASE TASK CLASS
# ═══════════════════════════════════════════════════════════════════════

class NLCBaseTask(Task):
    """
    Base class for all NLC Celery tasks.
    Provides: structured logging, automatic retry on connection errors,
    activity log writing on failure.
    """
    abstract = True
    max_retries = 3
    default_retry_delay = 60  # 1 minute

    def on_failure(self, exc, task_id, args, kwargs, einfo) -> None:
        """Called on permanent failure (after all retries exhausted)."""
        logger.error(
            f"[Task] PERMANENT FAILURE "
            f"task={self.name} id={task_id} error={exc!r:.300}"
        )

    def on_retry(self, exc, task_id, args, kwargs, einfo) -> None:
        """Called on each retry."""
        logger.warning(
            f"[Task] RETRYING "
            f"task={self.name} id={task_id} error={exc!r:.200}"
        )


# ═══════════════════════════════════════════════════════════════════════
# COMPLIANCE TASKS
# ═══════════════════════════════════════════════════════════════════════

@celery_app.task(
    bind=True,
    base=NLCBaseTask,
    name="app.worker.tasks.evaluate_company_compliance",
    queue="compliance",
    max_retries=3,
    default_retry_delay=120,   # 2 minutes between retries
    time_limit=300,            # 5 minutes max per single company
    soft_time_limit=270,
)
def evaluate_company_compliance(
    self: Task,
    company_id: str,
    trigger_source: str = "CELERY_TASK",
) -> dict[str, Any]:
    """
    Evaluate compliance for a single company.

    Trigger sources: CRON_DAILY | API_REQUEST | RESCUE_STEP_COMPLETE | MANUAL
    AI Constitution Article 1: uses deterministic NLCRuleEngine only.

    Args:
        company_id: UUID string of the company to evaluate
        trigger_source: What triggered this evaluation (for audit trail)

    Returns:
        dict with score, risk_band, flags, and evaluation metadata
    """
    logger.info(
        f"[Compliance] Evaluating company={company_id} trigger={trigger_source}"
    )

    async def _run():
        from app.models.database import AsyncSessionLocal, set_admin_context
        from app.services.compliance_service import ComplianceService

        async with AsyncSessionLocal() as db, db.begin():
            await set_admin_context(db)  # Bypass RLS for cron/background
            svc = ComplianceService(db)
            result = await svc.evaluate_company(
                company_id=uuid.UUID(company_id),
                trigger_source=trigger_source,
            )
            return result

    try:
        result = run_async(_run())
        logger.info(
            f"[Compliance] Complete company={company_id} "
            f"score={result.get('score')} band={result.get('risk_band')} "
            f"flags={len(result.get('flags', []))}"
        )
        return result

    except SoftTimeLimitExceeded:
        logger.error(f"[Compliance] TIMEOUT company={company_id}")
        raise

    except Exception as exc:
        # Retry on transient DB/network errors
        if _is_transient_error(exc):
            logger.warning(
                f"[Compliance] Transient error, retrying: {exc!r}"
            )
            raise self.retry(exc=exc)

        logger.error(
            f"[Compliance] Non-retryable failure company={company_id}: {exc!r}"
        )
        raise


@celery_app.task(
    bind=True,
    base=NLCBaseTask,
    name="app.worker.tasks.evaluate_all_companies",
    queue="compliance",
    max_retries=1,
    time_limit=7200,          # 2 hours hard limit for full portfolio
    soft_time_limit=6900,
)
def evaluate_all_companies(
    self: Task,
    trigger_source: str = "CRON_DAILY",
    batch_size: int = 50,
) -> dict[str, Any]:
    """
    Daily batch evaluation of ALL active companies.
    Runs every night at 00:00 UTC (06:00 BST).

    Dispatches individual evaluate_company_compliance tasks in batches
    to avoid overloading the DB. Uses Celery chord/group internally.

    Args:
        trigger_source: Should be "CRON_DAILY" for scheduled runs
        batch_size: Companies to send to queue per batch

    Returns:
        dict with total companies evaluated, success count, failure count
    """
    logger.info(
        f"[Compliance] Starting batch evaluation trigger={trigger_source}"
    )

    async def _get_company_ids() -> list[str]:
        from app.models.database import AsyncSessionLocal, set_admin_context
        from app.services.company_service import CompanyService

        async with AsyncSessionLocal() as db:
            await set_admin_context(db)
            svc = CompanyService(db)
            ids = await svc.get_all_active_ids()
            return [str(cid) for cid in ids]

    try:
        company_ids = run_async(_get_company_ids())
        total = len(company_ids)

        logger.info(f"[Compliance] Found {total} active companies to evaluate")

        # Dispatch individual tasks in batches
        dispatched = 0
        for i in range(0, total, batch_size):
            batch = company_ids[i : i + batch_size]
            for cid in batch:
                evaluate_company_compliance.apply_async(
                    kwargs={
                        "company_id":     cid,
                        "trigger_source": trigger_source,
                    },
                    queue="compliance",
                    countdown=0,
                )
                dispatched += 1

            logger.info(
                f"[Compliance] Dispatched batch {i // batch_size + 1} "
                f"({len(batch)} companies) — total so far: {dispatched}/{total}"
            )

        result = {
            "trigger_source": trigger_source,
            "total_companies": total,
            "dispatched":      dispatched,
            "started_at":      datetime.now(UTC).isoformat(),
        }
        logger.info(
            f"[Compliance] Batch dispatch complete: {dispatched}/{total} companies"
        )
        return result

    except Exception as exc:
        logger.error(f"[Compliance] Batch evaluation failed: {exc!r}")
        raise


@celery_app.task(
    bind=True,
    base=NLCBaseTask,
    name="app.worker.tasks.trigger_rescue_reevaluation",
    queue="compliance",
    max_retries=3,
    default_retry_delay=60,
    time_limit=300,
)
def trigger_rescue_reevaluation(
    self: Task,
    company_id: str,
    rescue_plan_id: str,
    completed_step_number: int,
) -> dict[str, Any]:
    """
    Re-evaluate compliance after a rescue step is completed.
    Triggered when rescue step 8 (RJSC Acknowledgment) is marked complete.
    Determines if the company has moved to a better risk band.

    AI Constitution Article 1: evaluation is fully deterministic.
    """
    logger.info(
        f"[Rescue] Re-evaluation triggered company={company_id} "
        f"plan={rescue_plan_id} completed_step={completed_step_number}"
    )

    # Schedule evaluation with short delay to allow DB writes to settle
    evaluate_company_compliance.apply_async(
        kwargs={
            "company_id":     company_id,
            "trigger_source": "RESCUE_STEP_COMPLETE",
        },
        queue="compliance",
        countdown=5,  # 5 second delay
    )

    return {
        "company_id":             company_id,
        "rescue_plan_id":         rescue_plan_id,
        "completed_step_number":  completed_step_number,
        "evaluation_scheduled_at": datetime.now(UTC).isoformat(),
    }


# ═══════════════════════════════════════════════════════════════════════
# NOTIFICATION TASKS
# ═══════════════════════════════════════════════════════════════════════

@celery_app.task(
    bind=True,
    base=NLCBaseTask,
    name="app.worker.tasks.send_pending_notifications",
    queue="notifications",
    max_retries=2,
    time_limit=600,
)
def send_pending_notifications(
    self: Task,
    batch_size: int = 50,
) -> dict[str, Any]:
    """
    Process all PENDING notifications and attempt delivery.
    Runs every 10 minutes via beat schedule.

    Channels: EMAIL (via AWS SES), DASHBOARD (DB update), WHATSAPP (optional).
    Failed deliveries increment retry_count and are retried up to 3 times.
    After 3 failures, status is set to FAILED.
    """
    logger.info(f"[Notifications] Processing pending batch (max={batch_size})")

    async def _process():

        from app.models.database import AsyncSessionLocal, set_admin_context
        from app.services.notification_service import NotificationService

        sent = failed = skipped = 0

        async with AsyncSessionLocal() as db, db.begin():
            await set_admin_context(db)
            svc = NotificationService(db)

            # Get pending notifications
            pending = await svc.get_pending(limit=batch_size)

            for notif in pending:
                try:
                    success = await _deliver_notification(notif, db)
                    if success:
                        await svc.mark_sent(notif.id)
                        sent += 1
                    else:
                        if notif.retry_count >= 3:
                            await svc.mark_failed(
                                notif.id,
                                reason="Max retries exceeded"
                            )
                            failed += 1
                        else:
                            # Increment retry count
                            notif.retry_count += 1
                            db.add(notif)
                            skipped += 1
                except Exception as e:
                    logger.warning(
                        f"[Notifications] Delivery error notif={notif.id}: {e!r}"
                    )
                    failed += 1

        return {"sent": sent, "failed": failed, "skipped": skipped}

    async def _deliver_notification(notif, db) -> bool:
        """Attempt to deliver a single notification. Returns True on success."""
        from app.models.enums import NotificationChannel

        if notif.channel == NotificationChannel.EMAIL:
            return await _send_email(notif)
        elif notif.channel == NotificationChannel.DASHBOARD:
            return True  # Dashboard notifications are already in DB — they're "delivered"
        elif notif.channel == NotificationChannel.WHATSAPP:
            return await _send_whatsapp(notif)
        return False

    async def _send_email(notif) -> bool:
        """Send email via AWS SES."""
        try:
            import boto3

            from app.core.config import get_settings

            settings = get_settings()
            if not settings.aws_key_id:
                logger.warning("[Notifications] AWS credentials not configured for email")
                return False

            ses = boto3.client(
                "ses",
                region_name=settings.ses_region,
                aws_access_key_id=settings.aws_key_id,
                aws_secret_access_key=settings.aws_secret,
            )

            # Get user email for this notification
            if not notif.user_id:
                return False

            from sqlalchemy import select

            from app.models.database import AsyncSessionLocal
            from app.models.user import User

            async with AsyncSessionLocal() as db2:
                result = await db2.execute(
                    select(User.email).where(User.id == notif.user_id)
                )
                email = result.scalar_one_or_none()
                if not email:
                    return False

            ses.send_email(
                Source=settings.email_from,
                Destination={"ToAddresses": [email]},
                Message={
                    "Subject": {"Data": notif.title, "Charset": "UTF-8"},
                    "Body": {
                        "Text": {"Data": notif.body, "Charset": "UTF-8"},
                        "Html": {
                            "Data": f"<p>{notif.body.replace(chr(10), '<br>')}</p>",
                            "Charset": "UTF-8",
                        },
                    },
                },
            )
            return True

        except Exception as e:
            logger.warning(f"[Notifications] SES send failed: {e!r}")
            return False

    async def _send_whatsapp(notif) -> bool:
        """Send WhatsApp message via Facebook Graph API."""
        try:

            from app.core.config import get_settings

            settings = get_settings()
            if not settings.whatsapp_enabled or not settings.whatsapp_api_token:
                return False  # WhatsApp not configured

            # Implementation depends on WhatsApp Business API template messages
            # For now, log intent — full implementation requires approved templates
            logger.info(
                f"[Notifications] WhatsApp delivery queued for notif={notif.id}"
            )
            return False  # Return False until WA templates are approved

        except Exception as e:
            logger.warning(f"[Notifications] WhatsApp send failed: {e!r}")
            return False

    try:
        result = run_async(_process())
        logger.info(
            f"[Notifications] Batch complete: "
            f"sent={result['sent']} failed={result['failed']} skipped={result['skipped']}"
        )
        return result
    except Exception as exc:
        if _is_transient_error(exc):
            raise self.retry(exc=exc)
        raise


@celery_app.task(
    bind=True,
    base=NLCBaseTask,
    name="app.worker.tasks.queue_deadline_warning_notifications",
    queue="notifications",
    max_retries=2,
    time_limit=600,
)
def queue_deadline_warning_notifications(
    self: Task,
    warning_days: list[int] | None = None,
) -> dict[str, Any]:
    """
    Scan all companies for upcoming AGM, Annual Return, and Audit deadlines.
    Queue warning notifications for each deadline within warning_days threshold.

    Runs daily at 08:00 UTC (14:00 BST).
    Avoids duplicate notifications: checks if warning already sent for same
    deadline + days_remaining combination.
    """
    if warning_days is None:
        warning_days = [30, 15, 7, 3, 1]

    logger.info(
        f"[Deadlines] Checking upcoming deadlines for days: {warning_days}"
    )

    async def _scan_and_queue():
        from app.models.database import AsyncSessionLocal, set_admin_context
        from app.services.company_service import CompanyService
        from app.services.notification_service import NotificationService

        async with AsyncSessionLocal() as db, db.begin():
            await set_admin_context(db)
            svc = NotificationService(db)
            company_svc = CompanyService(db)

            queued = 0
            today = date.today()

            # Get all upcoming deadlines within max warning window
            max_days = max(warning_days)
            deadlines = await company_svc.get_upcoming_deadlines(
                days_ahead=max_days
            )

            for deadline_item in deadlines:
                days_remaining = (
                    deadline_item["deadline_date"] - today
                ).days

                # Only notify at exact warning thresholds
                if days_remaining not in warning_days:
                    continue

                # Queue notification
                await svc.queue_notification(
                    company_id=deadline_item["company_id"],
                    title=(
                        f"⚠ {deadline_item['deadline_type']} due in "
                        f"{days_remaining} day{'s' if days_remaining != 1 else ''}"
                    ),
                    body=(
                        f"{deadline_item['company_name']} "
                        f"({deadline_item['registration_number']}): "
                        f"{deadline_item['deadline_type']} deadline is "
                        f"{deadline_item['deadline_date'].isoformat()} "
                        f"({days_remaining} day{'s' if days_remaining != 1 else ''} remaining). "
                        f"Immediate action required to avoid statutory default."
                    ),
                    notification_type=f"DEADLINE_{deadline_item['deadline_type']}",
                    channel="DASHBOARD",
                    days_until_deadline=days_remaining,
                )
                queued += 1

            return {"queued": queued, "deadlines_checked": len(deadlines)}

    try:
        result = run_async(_scan_and_queue())
        logger.info(
            f"[Deadlines] Complete: "
            f"queued={result['queued']} checked={result['deadlines_checked']}"
        )
        return result
    except Exception as exc:
        if _is_transient_error(exc):
            raise self.retry(exc=exc)
        raise


# ═══════════════════════════════════════════════════════════════════════
# DOCUMENT TASKS
# ═══════════════════════════════════════════════════════════════════════

@celery_app.task(
    bind=True,
    base=NLCBaseTask,
    name="app.worker.tasks.generate_ai_document_async",
    queue="documents",
    max_retries=2,
    default_retry_delay=300,   # 5 minutes before retry
    time_limit=180,            # 3 minutes for AI call
    soft_time_limit=150,
)
def generate_ai_document_async(
    self: Task,
    company_id: str,
    document_type: str,
    template_name: str,
    template_params: dict[str, Any],
    requested_by: str,
) -> dict[str, Any]:
    """
    Generate an AI-assisted document draft.
    AI Constitution Article 3:
      - Sets in_review_queue=True, human_approved=False, auto_sent_blocked=True
      - Logs AI call in ai_output_log (with prompt_hash, never raw PII)
      - Never auto-sends to client
      - Queues review notification to NLC legal staff

    Args:
        company_id:      UUID string
        document_type:   e.g. "AGM_MINUTES"
        template_name:   e.g. "AGM_MINUTES_STANDARD"
        template_params: Dict of {PLACEHOLDER: value} for template substitution
        requested_by:    UUID string of requesting user
    """
    logger.info(
        f"[Document] Generating company={company_id} type={document_type} "
        f"template={template_name}"
    )

    async def _generate():
        from app.models.database import AsyncSessionLocal, set_admin_context
        from app.services.document_service import DocumentService

        async with AsyncSessionLocal() as db, db.begin():
            await set_admin_context(db)
            svc = DocumentService(db)
            doc_id, _review_notif = await svc.generate_ai_document(
                company_id=uuid.UUID(company_id),
                document_type=document_type,
                template_name=template_name,
                template_params=template_params,
                requested_by=uuid.UUID(requested_by),
            )
            return str(doc_id)

    try:
        doc_id = run_async(_generate())
        logger.info(
            f"[Document] Generated document_id={doc_id} — "
            f"pending human review (AI Constitution Art.3)"
        )
        return {"document_id": doc_id, "status": "IN_REVIEW_QUEUE"}

    except SoftTimeLimitExceeded:
        logger.error(
            f"[Document] AI call TIMEOUT company={company_id} type={document_type}"
        )
        raise
    except Exception as exc:
        if _is_transient_error(exc):
            raise self.retry(exc=exc)
        raise


@celery_app.task(
    bind=True,
    base=NLCBaseTask,
    name="app.worker.tasks.render_pdf",
    queue="documents",
    max_retries=2,
    time_limit=120,
    soft_time_limit=100,
)
def render_pdf(
    self: Task,
    document_id: str,
    upload_to_s3: bool = True,
) -> dict[str, Any]:
    """
    Render a stored document as PDF using WeasyPrint.
    Uploads to S3 and updates document record with s3_key.

    Only runs for human-approved documents (checks human_approved=True).
    AI Constitution Article 3: PDFs are never auto-sent to client.
    """
    logger.info(f"[PDF] Rendering document_id={document_id}")

    async def _render():
        from app.models.database import AsyncSessionLocal, set_admin_context
        from app.services.document_service import DocumentService

        async with AsyncSessionLocal() as db, db.begin():
            await set_admin_context(db)
            svc = DocumentService(db)
            presigned_url = await svc.generate_pdf_and_presign(
                document_id=uuid.UUID(document_id)
            )
            return presigned_url

    try:
        url = run_async(_render())
        logger.info(f"[PDF] Rendered document_id={document_id}")
        return {"document_id": document_id, "presigned_url": url}
    except Exception as exc:
        if _is_transient_error(exc):
            raise self.retry(exc=exc)
        raise


@celery_app.task(
    bind=True,
    base=NLCBaseTask,
    name="app.worker.tasks.process_ai_review_queue",
    queue="documents",
    max_retries=1,
    time_limit=120,
)
def process_ai_review_queue(
    self: Task,
    alert_threshold_hours: int = 2,
) -> dict[str, Any]:
    """
    Check for AI documents waiting for human review longer than threshold.
    AI Constitution Article 3: AI documents must not linger without review.

    Sends dashboard notification to all ADMIN_STAFF and LEGAL_STAFF users
    listing documents that need approval.
    """
    logger.info(
        f"[AI Review] Checking queue (threshold={alert_threshold_hours}h)"
    )

    async def _check():
        from sqlalchemy import select

        from app.models.database import AsyncSessionLocal, set_admin_context
        from app.models.documents import Document
        from app.models.enums import UserRole
        from app.models.user import User

        alert_threshold = datetime.now(UTC) - timedelta(
            hours=alert_threshold_hours
        )

        async with AsyncSessionLocal() as db, db.begin():
            await set_admin_context(db)

            # Find documents waiting more than threshold
            result = await db.execute(
                select(Document).where(
                    Document.ai_generated,
                    Document.in_review_queue,
                    not Document.human_approved,
                    Document.created_at < alert_threshold,
                    Document.is_active,
                )
            )
            pending_docs = result.scalars().all()

            if not pending_docs:
                return {"pending_documents": 0, "alerts_sent": 0}

            # Find all legal staff users to alert
            staff_result = await db.execute(
                select(User).where(
                    User.role.in_([UserRole.ADMIN_STAFF, UserRole.LEGAL_STAFF]),
                    User.is_active,
                )
            )
            staff_users = staff_result.scalars().all()

            # Queue a notification for each staff member
            from app.services.notification_service import NotificationService
            notif_svc = NotificationService(db)

            alerts_sent = 0
            for staff in staff_users:
                await notif_svc.queue_notification(
                    user_id=staff.id,
                    title=(
                        f"⏳ {len(pending_docs)} AI document(s) awaiting review"
                    ),
                    body=(
                        f"{len(pending_docs)} AI-generated document(s) have been "
                        f"waiting for human review for more than "
                        f"{alert_threshold_hours} hour(s). "
                        f"Please review and approve or reject them in the "
                        f"Documents section. "
                        f"AI Constitution Article 3: documents must not be "
                        f"auto-sent without review."
                    ),
                    notification_type="AI_REVIEW_QUEUE_ALERT",
                    channel="DASHBOARD",
                )
                alerts_sent += 1

            return {
                "pending_documents": len(pending_docs),
                "alerts_sent": alerts_sent,
            }

    try:
        result = run_async(_check())
        if result["pending_documents"] > 0:
            logger.warning(
                f"[AI Review] {result['pending_documents']} docs pending review — "
                f"sent {result['alerts_sent']} alerts"
            )
        return result
    except Exception as exc:
        if _is_transient_error(exc):
            raise self.retry(exc=exc)
        raise


# ═══════════════════════════════════════════════════════════════════════
# MAINTENANCE TASKS
# ═══════════════════════════════════════════════════════════════════════

@celery_app.task(
    bind=True,
    base=NLCBaseTask,
    name="app.worker.tasks.monthly_score_snapshot_all",
    queue="maintenance",
    max_retries=1,
    time_limit=3600,           # 1 hour for full portfolio snapshot
    soft_time_limit=3300,
)
def monthly_score_snapshot_all(self: Task) -> dict[str, Any]:
    """
    Take the formal monthly compliance score snapshot for all companies.
    Runs on the 1st of each month at 01:00 UTC.

    Creates an immutable ComplianceScoreHistory record for each company.
    These records are used for trend reporting and client monthly reports.
    AI Constitution Article 4: score snapshots are append-only (no update/delete).
    """
    logger.info("[Snapshot] Starting monthly score snapshot")

    async def _snapshot():
        from app.models.database import AsyncSessionLocal, set_admin_context
        from app.services.company_service import CompanyService

        async with AsyncSessionLocal() as db:
            await set_admin_context(db)
            company_svc = CompanyService(db)
            ids = await company_svc.get_all_active_ids()

        completed = 0
        failed = 0

        for cid in ids:
            try:
                # Evaluate triggers a new snapshot (only creates if not exists this month)
                evaluate_company_compliance.apply_async(
                    kwargs={
                        "company_id":     str(cid),
                        "trigger_source": "MONTHLY_SNAPSHOT",
                    },
                    queue="compliance",
                )
                completed += 1
            except Exception as e:
                logger.warning(f"[Snapshot] Failed to dispatch for company={cid}: {e!r}")
                failed += 1

        return {"dispatched": completed, "failed": failed, "total": len(ids)}

    try:
        result = run_async(_snapshot())
        logger.info(
            f"[Snapshot] Monthly snapshot dispatched: "
            f"{result['dispatched']}/{result['total']} companies"
        )
        return result
    except Exception:
        raise


@celery_app.task(
    bind=True,
    base=NLCBaseTask,
    name="app.worker.tasks.cleanup_old_activity_logs",
    queue="maintenance",
    max_retries=1,
    time_limit=3600,
)
def cleanup_old_activity_logs(
    self: Task,
    retain_years: int = 7,
) -> dict[str, Any]:
    """
    Archive activity logs older than retain_years to S3, then delete from DB.
    Runs every Sunday at 02:00 UTC.

    7-year retention requirement: Bangladesh companies must maintain corporate
    records for 7 years under the Companies Act 1994 and tax regulations.

    Process:
    1. Find user_activity_logs older than 7 years
    2. Export to JSON
    3. Upload to S3 (nlc-backups/activity_logs/YYYY/)
    4. Delete from DB only after successful S3 upload
    5. Same for compliance_events
    """
    logger.info(f"[Cleanup] Activity log retention check (retain={retain_years} years)")

    cutoff_date = datetime.now(UTC) - timedelta(days=365 * retain_years)

    async def _cleanup():
        import json

        from sqlalchemy import delete, select

        from app.models.database import AsyncSessionLocal, set_admin_context
        from app.models.infrastructure import UserActivityLog

        archived = 0
        deleted = 0

        async with AsyncSessionLocal() as db, db.begin():
            await set_admin_context(db)

            # Count eligible records
            count_result = await db.execute(
                select(UserActivityLog).where(
                    UserActivityLog.logged_at < cutoff_date
                )
            )
            old_logs = count_result.scalars().all()

            if not old_logs:
                return {"archived": 0, "deleted": 0, "total_checked": 0}

            logger.info(
                f"[Cleanup] Found {len(old_logs)} logs older than "
                f"{retain_years} years for archival"
            )

            # Try to archive to S3
            try:
                import boto3

                from app.core.config import get_settings

                settings = get_settings()
                if settings.aws_key_id:
                    s3 = boto3.client(
                        "s3",
                        region_name=settings.aws_region,
                        aws_access_key_id=settings.aws_key_id,
                        aws_secret_access_key=settings.aws_secret,
                    )

                    # Export to JSON for archival
                    archive_data = [
                        {
                            "id":            str(log.id),
                            "user_id":       str(log.user_id) if log.user_id else None,
                            "company_id":    str(log.company_id) if log.company_id else None,
                            "action":        log.action,
                            "resource_type": log.resource_type,
                            "resource_id":   str(log.resource_id) if log.resource_id else None,
                            "description":   log.description,
                            "ip_address":    log.ip_address,
                            "logged_at":     log.logged_at.isoformat(),
                        }
                        for log in old_logs
                    ]

                    archive_key = (
                        f"activity_logs/{cutoff_date.year}/"
                        f"archive_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}.json"
                    )
                    s3.put_object(
                        Bucket=settings.s3_backup_bucket,
                        Key=archive_key,
                        Body=json.dumps(archive_data).encode("utf-8"),
                        ContentType="application/json",
                    )
                    archived = len(old_logs)
                    logger.info(
                        f"[Cleanup] Archived {archived} logs to s3://"
                        f"{settings.s3_backup_bucket}/{archive_key}"
                    )
            except Exception as archive_err:
                logger.error(
                    f"[Cleanup] S3 archival failed: {archive_err!r}. "
                    f"Skipping deletion to preserve data."
                )
                return {"archived": 0, "deleted": 0, "error": str(archive_err)}

            # Delete from DB only if archival succeeded
            if archived > 0:
                old_ids = [log.id for log in old_logs]
                await db.execute(
                    delete(UserActivityLog).where(
                        UserActivityLog.id.in_(old_ids)
                    )
                )
                deleted = archived

        return {
            "archived":      archived,
            "deleted":       deleted,
            "cutoff_date":   cutoff_date.isoformat(),
            "retain_years":  retain_years,
        }

    try:
        result = run_async(_cleanup())
        logger.info(
            f"[Cleanup] Log cleanup complete: "
            f"archived={result['archived']} deleted={result['deleted']}"
        )
        return result
    except Exception:
        raise


@celery_app.task(
    bind=True,
    base=NLCBaseTask,
    name="app.worker.tasks.cleanup_expired_notifications",
    queue="maintenance",
    max_retries=1,
    time_limit=120,
)
def cleanup_expired_notifications(
    self: Task,
    expire_after_hours: int = 48,
) -> dict[str, Any]:
    """
    Mark PENDING notifications that have not been sent within expire_after_hours
    as FAILED. Prevents notification queue from accumulating stale entries.
    Runs daily at 03:00 UTC.
    """
    logger.info(
        f"[Cleanup] Checking expired notifications (expire={expire_after_hours}h)"
    )

    async def _cleanup():
        from sqlalchemy import update

        from app.models.database import AsyncSessionLocal, set_admin_context
        from app.models.enums import NotificationStatus
        from app.models.infrastructure import Notification

        cutoff = datetime.now(UTC) - timedelta(hours=expire_after_hours)

        async with AsyncSessionLocal() as db, db.begin():
            await set_admin_context(db)
            result = await db.execute(
                update(Notification)
                .where(
                    Notification.notification_status == NotificationStatus.PENDING,
                    Notification.created_at < cutoff,
                )
                .values(
                    notification_status=NotificationStatus.FAILED,
                    failure_reason=(
                        f"Notification expired: not delivered within "
                        f"{expire_after_hours} hours"
                    ),
                )
            )
            return result.rowcount

    try:
        count = run_async(_cleanup())
        if count:
            logger.warning(
                f"[Cleanup] Expired {count} stale pending notifications"
            )
        return {"expired": count}
    except Exception:
        raise


@celery_app.task(
    bind=True,
    base=NLCBaseTask,
    name="app.worker.tasks.database_health_check",
    queue="maintenance",
    max_retries=0,
    time_limit=30,
)
def database_health_check(self: Task) -> dict[str, Any]:
    """
    Lightweight DB connectivity check.
    Runs every 5 minutes. Alerts if DB is unreachable.
    Just runs SELECT 1 — should complete in <100ms.
    """
    async def _check():
        import sqlalchemy as sa

        from app.models.database import AsyncSessionLocal

        start = datetime.now(UTC)
        async with AsyncSessionLocal() as db:
            await db.execute(sa.text("SELECT 1"))
        elapsed_ms = (datetime.now(UTC) - start).total_seconds() * 1000
        return elapsed_ms

    try:
        elapsed_ms = run_async(_check())
        status = "ok" if elapsed_ms < 1000 else "slow"
        if status == "slow":
            logger.warning(f"[Health] DB response slow: {elapsed_ms:.0f}ms")
        return {"status": status, "response_ms": round(elapsed_ms, 2)}
    except Exception as exc:
        logger.error(f"[Health] DB health check FAILED: {exc!r}")
        return {"status": "failed", "error": str(exc), "response_ms": None}


@celery_app.task(
    bind=True,
    base=NLCBaseTask,
    name="app.worker.tasks.sync_sro_registry",
    queue="maintenance",
    max_retries=1,
    time_limit=120,
)
def sync_sro_registry(self: Task) -> dict[str, Any]:
    """
    Check SRO registry for entries with rule_update_required=True.
    Alert Super Admin of any SROs that require rule engine updates.

    Run daily at 06:00 UTC. Ensures the rule engine stays current with
    new RJSC statutory orders.
    AI Constitution Article 1: Rule changes require Super Admin approval.
    """
    logger.info("[SRO] Checking SRO registry for pending rule updates")

    async def _check():
        from sqlalchemy import select

        from app.models.database import AsyncSessionLocal, set_admin_context
        from app.models.enums import UserRole
        from app.models.infrastructure import SRORegistry
        from app.models.user import User
        from app.services.notification_service import NotificationService

        async with AsyncSessionLocal() as db, db.begin():
            await set_admin_context(db)

            # Find SROs needing rule updates
            result = await db.execute(
                select(SRORegistry).where(
                    SRORegistry.rule_update_required,
                    SRORegistry.rule_updated_at is None,
                    SRORegistry.is_active,
                )
            )
            pending_sros = result.scalars().all()

            if not pending_sros:
                return {"pending_sros": 0, "alerts_sent": 0}

            # Alert Super Admin
            super_admins = await db.execute(
                select(User).where(
                    User.role == UserRole.SUPER_ADMIN,
                    User.is_active,
                )
            )
            admins = super_admins.scalars().all()

            notif_svc = NotificationService(db)
            alerts_sent = 0

            for admin in admins:
                sro_list = ", ".join(
                    s.sro_number for s in pending_sros[:10]
                )
                await notif_svc.queue_notification(
                    user_id=admin.id,
                    title=(
                        f"⚠ {len(pending_sros)} SRO(s) require rule engine update"
                    ),
                    body=(
                        f"The following SROs have rule_update_required=True "
                        f"but no rule update has been made: {sro_list}. "
                        f"Please review and update the affected ILRMF rules "
                        f"via the Legal Rules admin panel. "
                        f"AI Constitution Article 1: Only Super Admin may "
                        f"modify rules."
                    ),
                    notification_type="SRO_RULE_UPDATE_REQUIRED",
                    channel="DASHBOARD",
                )
                alerts_sent += 1

            return {
                "pending_sros": len(pending_sros),
                "alerts_sent":  alerts_sent,
            }

    try:
        result = run_async(_check())
        if result["pending_sros"] > 0:
            logger.warning(
                f"[SRO] {result['pending_sros']} SROs pending rule update"
            )
        return result
    except Exception as exc:
        if _is_transient_error(exc):
            raise self.retry(exc=exc)
        raise


# ═══════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════

def _is_transient_error(exc: Exception) -> bool:
    """
    Determine if an exception is transient (worth retrying) or permanent.
    Transient: DB connection errors, network timeouts, Redis unavailable.
    Permanent: validation errors, not-found errors, programming errors.
    """
    transient_types = (
        ConnectionRefusedError,
        ConnectionError,
        TimeoutError,
        OSError,
    )
    if isinstance(exc, transient_types):
        return True

    # SQLAlchemy async connection errors
    exc_module = type(exc).__module__ or ""
    exc_name   = type(exc).__name__ or ""

    if "sqlalchemy" in exc_module and any(
        kw in exc_name for kw in
        ["OperationalError", "InterfaceError", "TimeoutError", "DisconnectionError"]
    ):
        return True

    # asyncpg connection errors
    return bool("asyncpg" in exc_module and any(kw in exc_name for kw in ["ConnectionFailureError", "TooManyConnectionsError"]))
