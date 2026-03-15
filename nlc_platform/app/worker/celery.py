# Celery worker configuration
from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "nlc_platform",
    broker=settings.CELERY_BROKER_URL_REDIS,
    backend=settings.CELERY_RESULT_BACKEND_REDIS,
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "check-filing-deadlines": {
            "task": "app.worker.tasks.check_filing_deadlines",
            "schedule": crontab(hour=9, minute=0),
        },
        "check-overdue-filings": {
            "task": "app.worker.tasks.check_overdue_filings",
            "schedule": crontab(hour=10, minute=0),
        },
        "send-daily-summary": {
            "task": "app.worker.tasks.send_daily_summary",
            "schedule": crontab(hour=8, minute=0),
        },
    },
)
