"""
NEUM LEX COUNSEL — Celery Task Registry
app/worker/tasks/__init__.py

All tasks imported here so Celery autodiscovers them via include=["app.worker.tasks"].
"""
from app.worker.tasks.notify import deliver_pending_notifications

__all__ = [
    "deliver_pending_notifications",
]
