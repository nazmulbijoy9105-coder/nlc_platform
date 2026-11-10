"""At-least-once dispatcher and idempotent consumers for the event outbox."""
from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)

MAX_DISPATCH_ATTEMPTS = 8

REASSESSMENT_EVENTS = {
    "company.created",
    "company.fact.asserted",
    "filing.agm.recorded",
    "filing.agm.held_recorded",
    "filing.annual_return.recorded",
    "company.director.changed",
    "company.shareholder.changed",
    "company.share_transfer.changed",
    "company.registered_office.changed",
    "company.charge.recorded",
}

FILING_RECEIPT_EVENTS = {"filing.receipt.recorded", "filing.annual_return.filed"}
EVIDENCE_VERIFICATION_EVENTS = {
    "evidence.verification.completed",
    "company.fact.verified",
    "company.charge.evidence_state_changed",
}
AUDIT_ONLY_EVENTS = {
    "evidence.document.approved",
    "evidence.document.released",
}


@celery_app.task(
    bind=True,
    name="app.worker.tasks.dispatch_domain_event_outbox",
    queue="maintenance",
    max_retries=2,
    default_retry_delay=30,
    time_limit=300,
    soft_time_limit=270,
)
def dispatch_domain_event_outbox(self, batch_size: int = 100) -> dict[str, Any]:
    """Dispatch committed events; poison events move to a visible dead-letter state.

    Broker publication and the outbox state update cannot be one distributed
    transaction. Stable task IDs aid traceability; database consumer receipts
    provide the idempotency boundary for lifecycle, receipt and evidence work.
    """
    if batch_size < 1 or batch_size > 500:
        raise ValueError("batch_size must be between 1 and 500")

    async def _dispatch() -> dict[str, Any]:
        from app.models.database import AsyncSessionLocal, set_admin_context
        from app.models.domain_event import DomainEventOutbox
        from app.worker.tasks.core import (
            process_ai_review_queue,
            queue_deadline_warning_notifications,
        )

        now = datetime.now(UTC)
        queued = 0
        failed = 0
        dead_lettered = 0
        async with AsyncSessionLocal() as db:
            await set_admin_context(db)
            result = await db.execute(
                select(DomainEventOutbox)
                .where(
                    DomainEventOutbox.processed_at.is_(None),
                    DomainEventOutbox.dead_lettered_at.is_(None),
                    DomainEventOutbox.available_at <= now,
                )
                .order_by(DomainEventOutbox.occurred_at, DomainEventOutbox.id)
                .limit(batch_size)
                .with_for_update(skip_locked=True)
            )
            events = list(result.scalars().all())
            for event in events:
                event.attempts += 1
                try:
                    if event.event_type in REASSESSMENT_EVENTS:
                        consume_company_lifecycle_event.apply_async(
                            kwargs={"event_id": str(event.id)},
                            queue="compliance",
                            task_id=f"domain-event-{event.id}-lifecycle",
                        )
                        queued += 1
                    elif event.event_type in FILING_RECEIPT_EVENTS:
                        consume_filing_receipt_event.apply_async(
                            kwargs={"event_id": str(event.id)},
                            queue="compliance",
                            task_id=f"domain-event-{event.id}-filing-receipt",
                        )
                        queued += 1
                    elif event.event_type in EVIDENCE_VERIFICATION_EVENTS:
                        consume_evidence_verification_event.apply_async(
                            kwargs={"event_id": str(event.id)},
                            queue="compliance",
                            task_id=f"domain-event-{event.id}-evidence",
                        )
                        queued += 1
                    elif event.event_type == "deadline.calendar.generated":
                        queue_deadline_warning_notifications.apply_async(
                            kwargs={"warning_days": [30, 15, 7, 3, 1]},
                            queue="notifications",
                            task_id=f"domain-event-{event.id}",
                        )
                        queued += 1
                    elif event.event_type == "evidence.document.generated":
                        process_ai_review_queue.apply_async(
                            kwargs={"alert_threshold_hours": 0},
                            queue="documents",
                            task_id=f"domain-event-{event.id}",
                        )
                        queued += 1
                    elif event.event_type not in AUDIT_ONLY_EVENTS:
                        raise ValueError(
                            f"No dispatcher registered for event type: {event.event_type}"
                        )
                    # Audit-only approval/release events are intentionally retained.
                    event.processed_at = datetime.now(UTC)
                    event.locked_at = None
                    event.last_error = None
                except Exception as exc:
                    failed += 1
                    event.locked_at = None
                    event.last_error = str(exc)[:2000]
                    if event.attempts >= MAX_DISPATCH_ATTEMPTS:
                        event.dead_lettered_at = datetime.now(UTC)
                        event.dead_letter_reason = str(exc)[:2000]
                        dead_lettered += 1
                    else:
                        event.available_at = now + timedelta(
                            seconds=min(30 * (2 ** min(event.attempts, 7)), 3600)
                        )
                    logger.exception("domain_event_dispatch_failed event_id=%s", event.id)
            await db.commit()
        return {
            "selected": len(events),
            "queued": queued,
            "failed": failed,
            "dead_lettered": dead_lettered,
        }

    from app.worker.tasks.core import run_async
    return run_async(_dispatch())


async def _consume_and_reevaluate(
    event_id: str,
    *,
    consumer_name: str,
    allowed_event_types: set[str],
) -> dict[str, Any]:
    """Claim once and reevaluate in the same database transaction as the receipt."""
    from app.models.database import AsyncSessionLocal, set_admin_context
    from app.models.domain_event import DomainEventConsumption, DomainEventOutbox
    from app.services.compliance_service import ComplianceService

    parsed_event_id = uuid.UUID(event_id)
    async with AsyncSessionLocal() as db:
        # set_admin_context starts the worker's signed transaction context;
        # keep the claim and domain side effect in that same transaction.
        await set_admin_context(db)
        event_result = await db.execute(
            select(DomainEventOutbox)
            .where(DomainEventOutbox.id == parsed_event_id)
            .with_for_update()
        )
        event = event_result.scalar_one_or_none()
        if event is None:
            raise ValueError("Domain event does not exist.")
        if event.event_type not in allowed_event_types:
            raise ValueError("Event type is not valid for this consumer.")

        claim = await db.execute(
            pg_insert(DomainEventConsumption)
            .values(
                event_id=event.id,
                company_id=event.company_id,
                consumer_name=consumer_name,
                outcome={"compliance_reevaluation": "completed"},
            )
            .on_conflict_do_nothing(index_elements=["event_id", "consumer_name"])
            .returning(DomainEventConsumption.id)
        )
        consumption_id = claim.scalar_one_or_none()
        if consumption_id is None:
            await db.rollback()
            return {
                "event_id": event_id,
                "consumer": consumer_name,
                "duplicate": True,
            }

        await ComplianceService(db).evaluate_company(
            company_id=event.company_id,
            trigger_source=f"DOMAIN_EVENT_CONSUMER:{consumer_name}",
        )
        await db.commit()
        return {
            "event_id": event_id,
            "consumer": consumer_name,
            "duplicate": False,
        }

async def _mark_consumer_dead_letter(event_id: str, error: Exception) -> None:
    from app.models.database import AsyncSessionLocal, set_admin_context
    from app.models.domain_event import DomainEventOutbox

    async with AsyncSessionLocal() as db:
        await set_admin_context(db)
        result = await db.execute(
            select(DomainEventOutbox)
            .where(DomainEventOutbox.id == uuid.UUID(event_id))
            .with_for_update()
        )
        event = result.scalar_one_or_none()
        if event is not None:
            now = datetime.now(UTC)
            event.dead_lettered_at = now
            event.dead_letter_reason = str(error)[:2000]
            event.last_error = str(error)[:2000]
            event.locked_at = None
            await db.commit()


def _run_consumer_task(
    task: Any,
    event_id: str,
    *,
    consumer_name: str,
    allowed_event_types: set[str],
) -> dict[str, Any]:
    from app.worker.tasks.core import run_async

    try:
        return run_async(
            _consume_and_reevaluate(
                event_id,
                consumer_name=consumer_name,
                allowed_event_types=allowed_event_types,
            )
        )
    except Exception as exc:
        if task.request.retries >= MAX_DISPATCH_ATTEMPTS - 1:
            run_async(_mark_consumer_dead_letter(event_id, exc))
            raise
        retry_delay = min(30 * (2 ** task.request.retries), 1800)
        raise task.retry(exc=exc, countdown=retry_delay)


@celery_app.task(
    bind=True,
    name="app.worker.tasks.consume_company_lifecycle_event",
    queue="compliance",
    max_retries=MAX_DISPATCH_ATTEMPTS - 1,
    time_limit=300,
    soft_time_limit=270,
)
def consume_company_lifecycle_event(self, event_id: str) -> dict[str, Any]:
    """Apply one lifecycle event's compliance update exactly once per consumer."""
    return _run_consumer_task(
        self,
        event_id,
        consumer_name="company_lifecycle_v1",
        allowed_event_types=REASSESSMENT_EVENTS,
    )


@celery_app.task(
    bind=True,
    name="app.worker.tasks.consume_filing_receipt_event",
    queue="compliance",
    max_retries=MAX_DISPATCH_ATTEMPTS - 1,
    time_limit=300,
    soft_time_limit=270,
)
def consume_filing_receipt_event(self, event_id: str) -> dict[str, Any]:
    """Consume a filing-receipt event once; it does not authenticate RJSC itself."""
    return _run_consumer_task(
        self,
        event_id,
        consumer_name="filing_receipt_v1",
        allowed_event_types=FILING_RECEIPT_EVENTS,
    )


@celery_app.task(
    bind=True,
    name="app.worker.tasks.consume_evidence_verification_event",
    queue="compliance",
    max_retries=MAX_DISPATCH_ATTEMPTS - 1,
    time_limit=300,
    soft_time_limit=270,
)
def consume_evidence_verification_event(self, event_id: str) -> dict[str, Any]:
    """Consume a staff verification decision once and refresh deterministic compliance."""
    return _run_consumer_task(
        self,
        event_id,
        consumer_name="evidence_verification_v1",
        allowed_event_types=EVIDENCE_VERIFICATION_EVENTS,
    )
