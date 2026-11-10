"""Small transactional publisher for NLC domain events."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain_event import DomainEventOutbox


class DomainEventType:
    COMPANY_CREATED = "company.created"
    COMPANY_FACT_ASSERTED = "company.fact.asserted"
    COMPANY_FACT_VERIFIED = "company.fact.verified"
    AGM_RECORDED = "filing.agm.recorded"
    AGM_HELD_RECORDED = "filing.agm.held_recorded"
    ANNUAL_RETURN_RECORDED = "filing.annual_return.recorded"
    ANNUAL_RETURN_FILED = "filing.annual_return.filed"
    DEADLINES_GENERATED = "deadline.calendar.generated"
    DOCUMENT_GENERATED = "evidence.document.generated"
    DOCUMENT_APPROVED = "evidence.document.approved"
    DOCUMENT_RELEASED = "evidence.document.released"


async def publish_domain_event(
    db: AsyncSession,
    *,
    company_id: uuid.UUID,
    event_type: str,
    aggregate_type: str,
    aggregate_id: uuid.UUID,
    actor_id: uuid.UUID | None = None,
    payload: dict[str, Any] | None = None,
    correlation_id: str | None = None,
) -> DomainEventOutbox:
    """Append an event without committing; caller owns the transaction.

    Keeping this insert in the caller's transaction guarantees that a domain
    mutation and its event are committed or rolled back together.
    """
    if not event_type or not aggregate_type:
        raise ValueError("Domain event type and aggregate type are required.")
    event = DomainEventOutbox(
        company_id=company_id,
        actor_id=actor_id,
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        schema_version=1,
        payload=payload or {},
        correlation_id=correlation_id,
    )
    db.add(event)
    await db.flush()
    return event
