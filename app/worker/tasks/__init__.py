"""
NEUM LEX COUNSEL — Celery Task Registry
app/worker/tasks/__init__.py

Importing .core registers every task defined there with Celery
(include=["app.worker.tasks"] only imports this package).
"""
from app.worker.tasks import core as _core  # noqa: F401  (task registration)
from app.worker.tasks.core import (
    cleanup_expired_notifications,
    cleanup_old_activity_logs,
    database_health_check,
    evaluate_all_companies,
    evaluate_company_compliance,
    generate_ai_document_async,
    monthly_score_snapshot_all,
    process_ai_review_queue,
    process_due_subscriptions,
    queue_deadline_warning_notifications,
    render_pdf,
    send_pending_notifications,
    sync_sro_registry,
    trigger_rescue_reevaluation,
)
from app.worker.tasks.domain_events import (
    consume_company_lifecycle_event,
    consume_evidence_verification_event,
    consume_filing_receipt_event,
    dispatch_domain_event_outbox,
)
from app.worker.tasks.notify import deliver_pending_notifications

__all__ = [
    "cleanup_expired_notifications",
    "cleanup_old_activity_logs",
    "database_health_check",
    "deliver_pending_notifications",
    "dispatch_domain_event_outbox",
    "consume_company_lifecycle_event",
    "consume_evidence_verification_event",
    "consume_filing_receipt_event",
    "evaluate_all_companies",
    "evaluate_company_compliance",
    "generate_ai_document_async",
    "monthly_score_snapshot_all",
    "process_ai_review_queue",
    "process_due_subscriptions",
    "queue_deadline_warning_notifications",
    "render_pdf",
    "send_pending_notifications",
    "sync_sro_registry",
    "trigger_rescue_reevaluation",
]
