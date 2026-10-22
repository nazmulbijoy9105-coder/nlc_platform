"""APScheduler for free-tier deployment — no Celery workers needed."""
from __future__ import annotations

import logging
import os
from datetime import date, UTC

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)
scheduler: AsyncIOScheduler | None = None


def _is_eager() -> bool:
    return os.environ.get("CELERY_TASK_ALWAYS_EAGER", "true").lower() == "true"


async def _run_daily_compliance_evaluation() -> None:
    try:
        from app.worker.tasks import evaluate_all_companies
        evaluate_all_companies.delay()
        logger.info("scheduled_task_completed", task="daily_compliance_evaluation")
    except Exception as e:
        logger.error("scheduled_task_failed", task="daily_compliance_evaluation", error=str(e))


async def _check_overdue_filings() -> None:
    try:
        from sqlalchemy import select
        from app.models.database import AsyncSessionLocal
        from app.models.rjsc_forms import RJSCFormFiling

        async with AsyncSessionLocal() as db:
            today = date.today()
            result = await db.execute(
                select(RJSCFormFiling).where(
                    RJSCFormFiling.filing_status.in_(["PENDING", "OVERDUE"]),
                    RJSCFormFiling.due_date < today,
                )
            )
            overdue = result.scalars().all()
            for filing in overdue:
                filing.filing_status = "OVERDUE"
            await db.commit()
            if overdue:
                logger.info("overdue_filings_updated", count=len(overdue))
    except Exception as e:
        logger.error("scheduled_task_failed", task="check_overdue_filings", error=str(e))


async def _process_webhook_retries() -> None:
    try:
        from app.services.webhook_service import process_retries
        count = await process_retries()
        if count:
            logger.info("webhook_retries_processed", count=count)
    except Exception as e:
        logger.error("scheduled_task_failed", task="webhook_retries", error=str(e))


async def _send_pending_notifications() -> None:
    try:
        from app.worker.tasks import send_pending_notifications
        send_pending_notifications.delay()
        logger.info("scheduled_task_completed", task="send_pending_notifications")
    except Exception as e:
        logger.error("scheduled_task_failed", task="send_pending_notifications", error=str(e))


async def _database_health_check() -> None:
    try:
        from app.models.database import AsyncSessionLocal
        from sqlalchemy import text
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        logger.debug("db_health_check_ok")
    except Exception as e:
        logger.error("db_health_check_failed", error=str(e))


async def _cleanup_expired_notifications() -> None:
    try:
        from app.worker.tasks import cleanup_expired_notifications
        cleanup_expired_notifications.delay()
        logger.info("scheduled_task_completed", task="cleanup_expired_notifications")
    except Exception as e:
        logger.error("scheduled_task_failed", task="cleanup_expired_notifications", error=str(e))


async def _queue_deadline_warnings() -> None:
    try:
        from app.worker.tasks import queue_deadline_warning_notifications
        queue_deadline_warning_notifications.delay()
        logger.info("scheduled_task_completed", task="deadline_warnings")
    except Exception as e:
        logger.error("scheduled_task_failed", task="deadline_warnings", error=str(e))


def create_scheduler() -> AsyncIOScheduler:
    sched = AsyncIOScheduler(timezone="UTC")

    sched.add_job(_run_daily_compliance_evaluation, CronTrigger(hour=0, minute=0), id="daily_compliance_eval", replace_existing=True)
    sched.add_job(_check_overdue_filings, IntervalTrigger(minutes=10), id="check_overdue_filings", replace_existing=True)
    sched.add_job(_process_webhook_retries, IntervalTrigger(minutes=5), id="webhook_retries", replace_existing=True)
    sched.add_job(_send_pending_notifications, IntervalTrigger(minutes=10), id="send_pending_notifications", replace_existing=True)
    sched.add_job(_database_health_check, IntervalTrigger(minutes=5), id="db_health_check", replace_existing=True)
    sched.add_job(_queue_deadline_warnings, CronTrigger(hour=8, minute=0), id="deadline_warnings", replace_existing=True)
    sched.add_job(_cleanup_expired_notifications, CronTrigger(hour=3, minute=0), id="cleanup_expired_notifications", replace_existing=True)

    return sched


async def start_scheduler() -> None:
    global scheduler
    if os.environ.get("ENABLE_SCHEDULER", "true").lower() != "true":
        logger.info("scheduler_disabled_by_env")
        return
    if scheduler is not None:
        return
    scheduler = create_scheduler()
    scheduler.start()
    logger.info("scheduler_started", jobs=len(scheduler.get_jobs()))


async def stop_scheduler() -> None:
    global scheduler
    if scheduler is not None:
        scheduler.shutdown(wait=False)
        scheduler = None
        logger.info("scheduler_stopped")