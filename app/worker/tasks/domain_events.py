"""At-least-once dispatcher for the transactional domain-event outbox."""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select

from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)

REASSESSMENT_EVENTS = {
    "company.fact.asserted",
    "company.fact.verified",
    "filing.agm.recorded",
    "filing.agm.held_recorded",
    "filing.annual_return.recorded",
    "filing.annual_return.filed",
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
    """Dispatch committed events and mark them handled.

    The database transaction is locked with SKIP LOCKED, allowing multiple
    workers. Delivery is at-least-once: a crash after broker publish but before
    commit can enqueue the same event again. Consumers therefore receive the
    stable event UUID as task_id and must remain idempotent.
    """
    if batch_size < 1 or batch_size > 500:
        raise ValueError("batch_size must be between 1 and 500")

    async def _dispatch() -> dict[str, Any]:
        from app.models.database import AsyncSessionLocal, set_admin_context
        from app.models.domain_event import DomainEventOutbox
        from app.worker.tasks.core import (
            evaluate_company_compliance,
            process_ai_review_queue,
        )

        now = datetime.now(UTC)
        queued = 0
        failed = 0
        async with AsyncSessionLocal() as db:
            await set_admin_context(db)
            result = await db.execute(
                select(DomainEventOutbox)
                .where(
                    DomainEventOutbox.processed_at.is_(None),
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
                        evaluate_company_compliance.apply_async(
                            kwargs={
                                "company_id": str(event.company_id),
                                "trigger_source": f"DOMAIN_EVENT:{event.event_type}",
                            },
                            queue="compliance",
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
                    # Deadline and document approval/release events remain
                    # durable and queryable for their dedicated consumers.
                    event.processed_at = datetime.now(UTC)
                    event.locked_at = None
                    event.last_error = None
                except Exception as exc:
                    failed += 1
                    event.locked_at = None
                    event.last_error = str(exc)[:2000]
                    event.available_at = now + timedelta(
                        seconds=min(30 * (2 ** min(event.attempts, 7)), 3600)
                    )
                    logger.exception("domain_event_dispatch_failed event_id=%s", event.id)
            await db.commit()
        return {"selected": len(events), "queued": queued, "failed": failed}

    from app.worker.tasks.core import run_async
    return run_async(_dispatch())
