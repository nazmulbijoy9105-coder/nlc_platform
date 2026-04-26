"""
NEUM LEX COUNSEL — Celery Worker Application
app/worker/celery_app.py

Celery application configured for async background tasks and scheduled cron jobs.
Reads all configuration from settings (never hardcoded).

WORKER TYPES:
  1. Default worker:     processes task queue (compliance evals, notifications)
  2. Beat scheduler:     fires scheduled tasks (daily cron, deadline checks)
  3. Flower monitor:     optional web UI for task monitoring

START COMMANDS (see also: Dockerfile + docker-compose.yml):
  # Default worker (processes tasks):
  celery -A app.worker.celery_app worker --loglevel=info --concurrency=4

  # Beat scheduler (fires scheduled tasks):
  celery -A app.worker.celery_app beat --loglevel=info --scheduler redbeat.RedBeatScheduler

  # Both in one process (development only — NOT for production):
  celery -A app.worker.celery_app worker --beat --loglevel=info

  # Flower monitoring UI:
  celery -A app.worker.celery_app flower --port=5555

TASK QUEUES:
  compliance:   Compliance evaluation tasks (high priority, time-sensitive)
  notifications: Notification delivery (email, dashboard, WhatsApp)
  documents:    AI document generation and PDF rendering (CPU-intensive)
  maintenance:  Cron jobs, cleanup, log retention

AI Constitution Article 1: All compliance evaluations run through the
deterministic rule engine. No AI involvement in scoring decisions.
AI Constitution Article 3: Document generation tasks always set
human_approved=False and in_review_queue=True.
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

from celery import Celery
from celery.signals import (
    celeryd_init,
    task_failure,
    task_postrun,
    task_prerun,
    task_retry,
    task_success,
    worker_ready,
    worker_shutdown,
)

# ── Path setup ────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# CELERY APPLICATION
# ═══════════════════════════════════════════════════════════════════════

def _get_redis_url() -> str:
    """Resolve Redis URL from settings or environment."""
    try:
        from app.core.config import get_settings
        return get_settings().redis_url
    except Exception:
        return os.environ.get("REDIS_URL", "redis://localhost:6379/0")


def _get_celery_broker() -> str:
    try:
        from app.core.config import get_settings
        s = get_settings()
        return s.celery_broker_url or s.redis_url
    except Exception:
        return os.environ.get("CELERY_BROKER_URL",
                              os.environ.get("REDIS_URL", "redis://localhost:6379/0"))


def _get_celery_backend() -> str:
    try:
        from app.core.config import get_settings
        s = get_settings()
        return s.celery_result_backend or s.redis_url
    except Exception:
        return os.environ.get("CELERY_RESULT_BACKEND",
                              os.environ.get("REDIS_URL", "redis://localhost:6379/0"))


# Create Celery application
celery_app = Celery(
    "nlc_worker",
    broker=_get_celery_broker(),
    backend=_get_celery_backend(),
    include=[
        "app.worker.tasks",          # All task definitions
    ],
)

# ═══════════════════════════════════════════════════════════════════════
# CELERY CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════

celery_app.conf.update(

    # ── Serialization ─────────────────────────────────────────────
    # Use JSON — never pickle (security risk)
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # ── Timezone ──────────────────────────────────────────────────
    # Always UTC internally; display in Asia/Dhaka where needed
    timezone="UTC",
    enable_utc=True,

    # ── Result Backend ────────────────────────────────────────────
    result_backend=_get_celery_backend(),
    result_expires=86400,          # Results kept for 24 hours
    result_persistent=True,        # Persist to Redis on restart

    # ── Task Routing — 4 queues ───────────────────────────────────
    task_default_queue="default",
    task_queues={
        "compliance": {
            "exchange": "compliance",
            "routing_key": "compliance.*",
        },
        "notifications": {
            "exchange": "notifications",
            "routing_key": "notifications.*",
        },
        "documents": {
            "exchange": "documents",
            "routing_key": "documents.*",
        },
        "maintenance": {
            "exchange": "maintenance",
            "routing_key": "maintenance.*",
        },
        "default": {
            "exchange": "default",
            "routing_key": "default",
        },
    },
    task_routes={
        # Compliance tasks → compliance queue (high priority)
        "app.worker.tasks.evaluate_company_compliance":     {"queue": "compliance"},
        "app.worker.tasks.evaluate_all_companies":          {"queue": "compliance"},
        "app.worker.tasks.trigger_rescue_reevaluation":     {"queue": "compliance"},

        # Notification tasks → notifications queue
        "app.worker.tasks.send_pending_notifications":      {"queue": "notifications"},
        "app.worker.tasks.queue_deadline_warning_notifications": {"queue": "notifications"},
        "app.worker.tasks.send_single_notification":        {"queue": "notifications"},

        # Document tasks → documents queue (CPU-intensive)
        "app.worker.tasks.generate_ai_document_async":      {"queue": "documents"},
        "app.worker.tasks.render_pdf":                      {"queue": "documents"},
        "app.worker.tasks.process_ai_review_queue":         {"queue": "documents"},

        # Maintenance tasks → maintenance queue (low priority)
        "app.worker.tasks.monthly_score_snapshot_all":      {"queue": "maintenance"},
        "app.worker.tasks.cleanup_old_activity_logs":       {"queue": "maintenance"},
        "app.worker.tasks.cleanup_expired_notifications":   {"queue": "maintenance"},
        "app.worker.tasks.database_health_check":           {"queue": "maintenance"},
        "app.worker.tasks.sync_sro_registry":               {"queue": "maintenance"},
    },

    # ── Worker Configuration ──────────────────────────────────────
    worker_prefetch_multiplier=2,  # Fetch 2 tasks per worker at a time
    worker_max_tasks_per_child=500, # Restart worker process every 500 tasks (memory safety)
    worker_max_memory_per_child=256000,  # 256MB max per child process
    task_acks_late=True,           # Ack only after task completes (safer)
    task_reject_on_worker_lost=True,  # Re-queue if worker dies mid-task

    # ── Task Time Limits ──────────────────────────────────────────
    # Hard limits — worker killed after these seconds
    task_time_limit=600,            # 10 minutes hard limit for all tasks
    task_soft_time_limit=540,       # 9 minutes soft limit (SoftTimeLimitExceeded raised)

    # Per-task overrides (set in @celery_app.task decorator via time_limit=)
    # evaluate_all_companies: up to 30 minutes (large portfolio)

    # ── Retry Configuration ───────────────────────────────────────
    task_max_retries=3,
    task_default_retry_delay=60,   # 1 minute before first retry

    # ── Beat Scheduler ────────────────────────────────────────────
    # Using redbeat (Redis-backed beat scheduler) for HA deployments.
    # If redbeat not installed, falls back to default file-based scheduler.
    beat_scheduler="redbeat.RedBeatScheduler",
    redbeat_redis_url=_get_redis_url(),
    redbeat_key_prefix="nlc:beat:",
    redbeat_lock_timeout=30,       # 30 second lock to prevent duplicate beats

    # ── Beat Schedule ─────────────────────────────────────────────
    # Defined in app.worker.beat_schedule — imported below
    beat_schedule_filename="/tmp/celerybeat-schedule",

    # ── Logging ───────────────────────────────────────────────────
    worker_hijack_root_logger=False,   # Use our structlog configuration
    worker_log_format=(
        "%(asctime)s [%(levelname)s] [%(processName)s] %(message)s"
    ),
    worker_task_log_format=(
        "%(asctime)s [%(levelname)s] [%(task_name)s] [%(task_id)s] %(message)s"
    ),

    # ── Monitoring ────────────────────────────────────────────────
    worker_send_task_events=True,  # Enable task event monitoring (Flower)
    task_send_sent_event=True,     # Send 'sent' event for each task

    # ── Security ─────────────────────────────────────────────────
    task_always_eager=False,       # Never run tasks synchronously in production
                                   # Override in tests: task_always_eager=True
)

# ── Import beat schedule (must come after celery_app is created) ──────
from datetime import UTC

from app.worker.beat_schedule import BEAT_SCHEDULE

celery_app.conf.beat_schedule = BEAT_SCHEDULE


# ═══════════════════════════════════════════════════════════════════════
# SIGNAL HANDLERS
# ═══════════════════════════════════════════════════════════════════════

@celeryd_init.connect
def configure_worker(sender: str | None = None, conf: Any = None, **kwargs: Any) -> None:
    """Called when a new Celery worker process starts."""
    try:
        import structlog
        structlog.configure(
            processors=[
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.stdlib.add_log_level,
                structlog.processors.JSONRenderer(),
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
        )
    except ImportError:
        pass  # structlog optional

    logger.info(
        f"[Worker] Initialised: {sender} | "
        f"Queues: compliance, notifications, documents, maintenance"
    )


@worker_ready.connect
def on_worker_ready(sender: Any = None, **kwargs: Any) -> None:
    """Called when worker is ready to accept tasks."""
    logger.info("[Worker] Ready to accept tasks.")


@worker_shutdown.connect
def on_worker_shutdown(sender: Any = None, **kwargs: Any) -> None:
    """Called when worker is shutting down."""
    logger.info("[Worker] Shutting down gracefully.")


@task_prerun.connect
def on_task_prerun(
    task_id: str | None = None,
    task: Any = None,
    args: tuple | None = None,
    kwargs: dict | None = None,
    **extra: Any,
) -> None:
    """Log task start with structured context."""
    logger.info(
        f"[Task] START  task={task.name} id={task_id} "
        f"args={args!r:.200} kwargs={kwargs!r:.200}"
    )


@task_postrun.connect
def on_task_postrun(
    task_id: str | None = None,
    task: Any = None,
    args: tuple | None = None,
    kwargs: dict | None = None,
    retval: Any = None,
    state: str | None = None,
    **extra: Any,
) -> None:
    """Log task completion."""
    logger.info(
        f"[Task] END    task={task.name} id={task_id} state={state}"
    )


@task_success.connect
def on_task_success(
    sender: Any = None,
    result: Any = None,
    **kwargs: Any,
) -> None:
    """Log successful task completion."""
    pass  # Already logged in task_postrun — avoid duplication


@task_failure.connect
def on_task_failure(
    task_id: str | None = None,
    exception: Exception | None = None,
    traceback: Any = None,
    sender: Any = None,
    args: tuple | None = None,
    kwargs: dict | None = None,
    einfo: Any = None,
    **extra: Any,
) -> None:
    """
    Handle task failure.
    Logs the error with full context. Does not suppress the exception.
    For compliance evaluation failures: the company will be re-evaluated
    on the next daily cron run.
    """
    logger.error(
        f"[Task] FAILED task={sender.name if sender else 'unknown'} "
        f"id={task_id} error={exception!r} args={args!r:.100}"
    )

    # Attempt to log to activity log if the task had a company_id
    if kwargs and kwargs.get("company_id"):
        try:
            import asyncio

            # Fire-and-forget activity log — do not let this crash the signal handler
            async def _log_failure() -> None:
                from datetime import datetime

                from app.models.database import AsyncSessionLocal
                from app.models.infrastructure import UserActivityLog
                async with AsyncSessionLocal() as db, db.begin():
                    log = UserActivityLog(
                        action="TASK_FAILURE",
                        resource_type="CeleryTask",
                        description=(
                            f"Task {sender.name if sender else 'unknown'} "
                            f"failed: {exception!r:.200}"
                        ),
                        detail={
                            "task_id":    task_id,
                            "task_name":  sender.name if sender else None,
                            "company_id": str(kwargs.get("company_id", "")),
                            "error":      repr(exception)[:500],
                        },
                        logged_at=datetime.now(UTC),
                    )
                    db.add(log)

            asyncio.run(_log_failure())
        except Exception as log_err:
            logger.warning(f"[Task] Could not log failure to DB: {log_err}")


@task_retry.connect
def on_task_retry(
    request: Any = None,
    reason: Any = None,
    einfo: Any = None,
    **kwargs: Any,
) -> None:
    """Log task retry attempts."""
    logger.warning(
        f"[Task] RETRY  task={request.task} id={request.id} "
        f"retries={request.retries} reason={reason!r:.200}"
    )


# ═══════════════════════════════════════════════════════════════════════
# HEALTH CHECK HELPER
# ═══════════════════════════════════════════════════════════════════════

def check_worker_health() -> dict[str, Any]:
    """
    Check Celery worker health.
    Returns dict with: active_workers, active_tasks, queued_tasks.
    Used by FastAPI health check endpoint.
    """
    try:
        inspect = celery_app.control.inspect(timeout=2.0)

        active   = inspect.active()   or {}
        reserved = inspect.reserved() or {}

        active_workers = list(active.keys())
        active_count   = sum(len(v) for v in active.values())
        queued_count   = sum(len(v) for v in reserved.values())

        return {
            "status":         "healthy" if active_workers else "no_workers",
            "active_workers": len(active_workers),
            "active_tasks":   active_count,
            "queued_tasks":   queued_count,
            "worker_names":   active_workers[:5],  # First 5 worker names
        }
    except Exception as e:
        return {
            "status":         "unhealthy",
            "error":          str(e),
            "active_workers": 0,
            "active_tasks":   0,
            "queued_tasks":   0,
        }


# ── Module-level alias for direct import convenience ─────────────────
app = celery_app
