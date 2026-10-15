"""
NEUM LEX COUNSEL — Celery Task Registry
app/worker/tasks/__init__.py

Importing .core registers every task defined there with Celery
(include=["app.worker.tasks"] only imports this package).
"""
from app.worker.tasks import core as _core  # noqa: F401  (task registration)
from app.worker.tasks.core import (
    evaluate_company_compliance,
    generate_ai_document_async,
    render_pdf,
    send_pending_notifications,
    trigger_rescue_reevaluation,
)
from app.worker.tasks.notify import deliver_pending_notifications

__all__ = [
    "deliver_pending_notifications",
    "evaluate_company_compliance",
    "generate_ai_document_async",
    "render_pdf",
    "send_pending_notifications",
    "trigger_rescue_reevaluation",
]
