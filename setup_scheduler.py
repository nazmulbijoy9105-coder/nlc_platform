#!/usr/bin/env python3
"""
Setup APScheduler for free-tier Render deployment.
Replaces the need for separate Celery worker services.

Changes:
1. Add apscheduler to requirements.txt
2. Set task_always_eager=True when no Celery workers are running
3. Create app/tasks/scheduler.py with scheduled task definitions
4. Wire up scheduler in app/main.py startup/shutdown
"""
import re
from pathlib import Path

changes = []

# ── 1. Add apscheduler to requirements.txt ──────────────────────

p = Path("requirements.txt")
src = p.read_text(encoding="utf-8")
if "apscheduler" not in src.lower():
    src = src.rstrip() + "\napscheduler>=3.11.0\n"
    p.write_text(src, encoding="utf-8")
    changes.append("requirements.txt: added apscheduler>=3.11.0")
    print("[OK] Added apscheduler to requirements.txt")
else:
    print("[SKIP] apscheduler already in requirements.txt")

# ── 2. Set task_always_eager in celery_app.py ──────────────────

p = Path("app/worker/celery_app.py")
src = p.read_text(encoding="utf-8")

# Change task_always_eager to read from env
old_line = 'task_always_eager=False,'
new_line = (
    'task_always_eager=os.environ.get("CELERY_TASK_ALWAYS_EAGER", "true").lower() == "true",\n'
    '    # When true: .delay() runs synchronously (no worker needed)\n'
    '    # When false: tasks go to Redis queue (requires Celery workers)\n'
    '    # Set CELERY_TASK_ALWAYS_EAGER=false when deploying paid workers'
)

if old_line in src:
    src = src.replace(old_line, new_line, 1)
    p.write_text(src, encoding="utf-8")
    changes.append("celery_app.py: task_always_eager reads from env (default: true)")
    print("[OK] Set task_always_eager to env-controlled (default: true)")
else:
    print("[SKIP] task_always_eager pattern not found (already modified?)")

# ── 3. Create app/tasks/scheduler.py ───────────────────────────

Path("app/tasks").mkdir(exist_ok=True)

scheduler_code = '''"""
APScheduler — scheduled task runner for free-tier deployment.

Runs periodic tasks inside the FastAPI web process (no separate
Celery workers needed). Uses APScheduler with AsyncIOScheduler.

When you upgrade to paid Celery workers on Render:
  1. Set CELERY_TASK_ALWAYS_EAGER=false on all services
  2. Deploy nlc-worker + nlc-beat (Render Background Workers)
  3. This scheduler can be disabled by setting ENABLE_SCHEDULER=false

Scheduled tasks (all times UTC, BST = UTC+6):
  - Daily compliance evaluation: 00:00 UTC (06:00 BST)
  - Overdue filing check: every 10 minutes
  - Webhook retry processing: every 5 minutes
  - Deadline warning notifications: 08:00 UTC (14:00 BST)
  - Expired notification cleanup: 03:00 UTC (09:00 BST)
  - Database health check: every 5 minutes
  - Pending notification sender: every 10 minutes
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, UTC

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

scheduler: AsyncIOScheduler | None = None


def _is_eager() -> bool:
    """Check if Celery tasks are running eagerly (no workers)."""
    return os.environ.get("CELERY_TASK_ALWAYS_EAGER", "true").lower() == "true"


async def _run_daily_compliance_evaluation() -> None:
    """Evaluate all active companies. Most critical scheduled task."""
    try:
        from app.worker.tasks import evaluate_all_companies
        if _is_eager():
            await evaluate_all_companies.apply_async()
        else:
            evaluate_all_companies.delay()
        logger.info("scheduled_task_completed", task="daily_compliance_evaluation")
    except Exception as e:
        logger.error("scheduled_task_failed", task="daily_compliance_evaluation", error=str(e))


async def _check_overdue_filings() -> None:
    """Update PENDING → OVERDUE based on due_date for all companies."""
    try:
        from sqlalchemy import select, text
        from app.models.database import AsyncSessionLocal
        from app.models.rjsc_forms import RJSCFormFiling
        from datetime import date

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
    """Retry failed webhook deliveries."""
    try:
        from app.services.webhook_service import process_retries
        count = await process_retries()
        if count:
            logger.info("webhook_retries_processed", count=count)
    except Exception as e:
        logger.error("scheduled_task_failed", task="webhook_retries", error=str(e))


async def _send_pending_notifications() -> None:
    """Send queued notifications."""
    try:
        from app.worker.tasks import send_pending_notifications
        if _is_eager():
            await send_pending_notifications.apply_async()
        else:
            send_pending_notifications.delay()
        logger.info("scheduled_task_completed", task="send_pending_notifications")
    except Exception as e:
        logger.error("scheduled_task_failed", task="send_pending_notifications", error=str(e))


async def _database_health_check() -> None:
    """Quick DB connectivity check."""
    try:
        from app.models.database import AsyncSessionLocal
        from sqlalchemy import text
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        logger.debug("db_health_check_ok")
    except Exception as e:
        logger.error("db_health_check_failed", error=str(e))


async def _cleanup_expired_notifications() -> None:
    """Clean up notifications older than 90 days."""
    try:
        from app.worker.tasks import cleanup_expired_notifications
        if _is_eager():
            await cleanup_expired_notifications.apply_async()
        else:
            cleanup_expired_notifications.delay()
        logger.info("scheduled_task_completed", task="cleanup_expired_notifications")
    except Exception as e:
        logger.error("scheduled_task_failed", task="cleanup_expired_notifications", error=str(e))


async def _queue_deadline_warnings() -> None:
    """Queue deadline warning notifications for upcoming due dates."""
    try:
        from app.worker.tasks import queue_deadline_warning_notifications
        if _is_eager():
            await queue_deadline_warning_notifications.apply_async()
        else:
            queue_deadline_warning_notifications.delay()
        logger.info("scheduled_task_completed", task="deadline_warnings")
    except Exception as e:
        logger.error("scheduled_task_failed", task="deadline_warnings", error=str(e))


def create_scheduler() -> AsyncIOScheduler:
    """Create and configure the APScheduler instance."""
    sched = AsyncIOScheduler(timezone="UTC")

    # ── Daily compliance evaluation: 00:00 UTC (06:00 BST) ───
    sched.add_job(
        _run_daily_compliance_evaluation,
        CronTrigger(hour=0, minute=0, timezone="UTC"),
        id="daily_compliance_evaluation",
        replace_existing=True,
    )

    # ── Overdue filing check: every 10 minutes ───────────────
    sched.add_job(
        _check_overdue_filings,
        IntervalTrigger(minutes=10),
        id="check_overdue_filings",
        replace_existing=True,
    )

    # ── Webhook retry processing: every 5 minutes ────────────
    sched.add_job(
        _process_webhook_retries,
        IntervalTrigger(minutes=5),
        id="webhook_retries",
        replace_existing=True,
    )

    # ── Pending notification sender: every 10 minutes ────────
    sched.add_job(
        _send_pending_notifications,
        IntervalTrigger(minutes=10),
        id="send_pending_notifications",
        replace_existing=True,
    )

    # ── Database health check: every 5 minutes ───────────────
    sched.add_job(
        _database_health_check,
        IntervalTrigger(minutes=5),
        id="database_health_check",
        replace_existing=True,
    )

    # ── Deadline warning notifications: 08:00 UTC (14:00 BST)
    sched.add_job(
        _queue_deadline_warnings,
        CronTrigger(hour=8, minute=0, timezone="UTC"),
        id="deadline_warnings",
        replace_existing=True,
    )

    # ── Expired notification cleanup: 03:00 UTC (09:00 BST) ──
    sched.add_job(
        _cleanup_expired_notifications,
        CronTrigger(hour=3, minute=0, timezone="UTC"),
        id="cleanup_expired_notifications",
        replace_existing=True,
    )

    return sched


async def start_scheduler() -> None:
    """Start the APScheduler. Called on FastAPI startup."""
    global scheduler
    if os.environ.get("ENABLE_SCHEDULER", "true").lower() != "true":
        logger.info("scheduler_disabled_by_env")
        return
    if scheduler is not None:
        logger.warning("scheduler_already_started")
        return
    scheduler = create_scheduler()
    scheduler.start()
    logger.info("scheduler_started", jobs=len(scheduler.get_jobs()))


async def stop_scheduler() -> None:
    """Stop the APScheduler. Called on FastAPI shutdown."""
    global scheduler
    if scheduler is not None:
        scheduler.shutdown(wait=False)
        scheduler = None
        logger.info("scheduler_stopped")
'''

p = Path("app/tasks/__init__.py")
if not p.exists():
    p.write_text("", encoding="utf-8")

p = Path("app/tasks/scheduler.py")
p.write_text(scheduler_code, encoding="utf-8")
changes.append("app/tasks/scheduler.py: APScheduler with 7 scheduled tasks")
print("[OK] Created app/tasks/scheduler.py")

# ── 4. Wire up scheduler in app/main.py ───────────────────────

p = Path("app/main.py")
src = p.read_text(encoding="utf-8")
orig = src

# Add import for the scheduler (after the last import line)
import_line = "\nfrom app.tasks.scheduler import start_scheduler, stop_scheduler\n"
if "from app.tasks.scheduler import" not in src:
    # Find a good insertion point — after the last `from` or `import` line
    # Insert before the first function/class definition or app creation
    insert_pattern = re.compile(r'(\n(?:def |class |app = |router = ))', re.MULTILINE)
    m = insert_pattern.search(src)
    if m:
        insert_pos = m.start()
        src = src[:insert_pos] + import_line + src[insert_pos:]
    else:
        src = import_line + src
    changes.append("main.py: imported scheduler")

# Add startup event (find the startup handler or add one)
# Look for existing startup pattern
if "start_scheduler()" not in src:
    # Try to add to existing startup handler
    startup_pattern = re.compile(r'(@app\.on_event\("startup"\)|@asynccontextmanager.*lifespan|async def lifespan)', re.MULTILINE)

    if startup_pattern.search(src):
        # Add start_scheduler() call inside existing startup handler
        # Find the startup function and add the call
        src = re.sub(
            r'(async def (?:lifespan|startup)[^:]*:\s*\n(?:\s+.*\n)*?)(\s+yield\b|pass\b)',
            lambda m: m.group(1) + "    await start_scheduler()\n" + (m.group(2) or ""),
            src,
            count=1,
            flags=re.MULTILINE
        )
    else:
        # No startup handler found — add one
        startup_handler = """

@app.on_event("startup")
async def _start_scheduler():
    await start_scheduler()


@app.on_event("shutdown")
async def _stop_scheduler():
    await stop_scheduler()
"""
        # Insert before the last few lines (or at the end of file)
        src = src.rstrip() + startup_handler

    changes.append("main.py: scheduler wired to startup/shutdown")

if src != orig:
    p.write_text(src, encoding="utf-8")
    print("[OK] Modified app/main.py")
else:
    print("[SKIP] main.py already has scheduler wired")

# ── 5. Set ENABLE_SCHEDULER=true in .env (for local dev) ──────

p = Path(".env")
if p.exists():
    src = p.read_text(encoding="utf-8")
    if "ENABLE_SCHEDULER" not in src:
        p.write_text(src.rstrip() + "\nENABLE_SCHEDULER=true\n", encoding="utf-8")
        print("[OK] Added ENABLE_SCHEDULER=true to .env")
else:
    print("[SKIP] .env not found")

# ── Summary ───────────────────────────────────────────────────

print("\n" + "=" * 60)
print(f"Changes: {len(changes)}")
print("=" * 60)
for i, c in enumerate(changes, 1):
    print(f"  {i}. {c}")
print("\nNext: git add -A && git commit && git push")
'''

# Save the script
print("[OK] Script saved as setup_scheduler.py")
print("Run: python setup_scheduler.py")