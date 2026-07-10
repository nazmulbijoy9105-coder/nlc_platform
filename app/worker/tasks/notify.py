"""
NEUM LEX COUNSEL — Notification Delivery Celery Task
app/worker/tasks/notify.py

Celery task: deliver_pending_notifications
Registered via app/worker/tasks/__init__.py autodiscovery.

Wraps the synchronous send_pending_notifications logic already in tasks.py
as a properly registered sub-module task so Celery autodiscovers it via
include=["app.worker.tasks"].

NOTE: The full delivery implementation lives in tasks.py
      (send_pending_notifications). This module exposes a lightweight
      wrapper that the beat schedule can reference directly, and that
      NotificationService.queue_for_new_flags can trigger.
"""
from __future__ import annotations

import logging

from app.worker.celery_app import celery_app

logger = logging.getLogger("nlc.notifications")


@celery_app.task(
    name="app.worker.tasks.deliver_pending_notifications",
    queue="notifications",
    max_retries=2,
    default_retry_delay=60,
    time_limit=600,
    soft_time_limit=550,
    bind=True,
)
def deliver_pending_notifications(self, batch_size: int = 50) -> dict:
    """
    Process all PENDING notifications and attempt delivery.
    Registered as the canonical notification delivery task.

    Delegates to the full implementation in tasks.py via import to
    avoid duplicating the SES/WhatsApp/dashboard logic.
    """
    # Import here to avoid circular imports at module load time
    from app.worker.tasks import send_pending_notifications

    logger.info(
        f"[notify] deliver_pending_notifications delegating to "
        f"send_pending_notifications batch_size={batch_size}"
    )
    return send_pending_notifications(batch_size=batch_size)
