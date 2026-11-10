from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, Mock

import pytest

from app.models.domain_event import DomainEventConsumption, DomainEventOutbox
from app.services.domain_events import DomainEventType, publish_domain_event


@pytest.mark.asyncio
async def test_publish_domain_event_adds_to_callers_transaction() -> None:
    db = Mock()
    db.add = Mock()
    db.flush = AsyncMock()

    company_id = uuid.uuid4()
    aggregate_id = uuid.uuid4()
    actor_id = uuid.uuid4()
    event = await publish_domain_event(
        db,
        company_id=company_id,
        event_type=DomainEventType.COMPANY_FACT_ASSERTED,
        aggregate_type="company_fact",
        aggregate_id=aggregate_id,
        actor_id=actor_id,
        payload={"fact_key": "incorporation_date", "trust_level": "USER_ASSERTED"},
        correlation_id="request-123",
    )

    assert isinstance(event, DomainEventOutbox)
    assert event.company_id == company_id
    assert event.aggregate_id == aggregate_id
    assert event.actor_id == actor_id
    assert event.event_type == "company.fact.asserted"
    assert event.schema_version == 1
    assert event.payload["fact_key"] == "incorporation_date"
    assert event.correlation_id == "request-123"
    db.add.assert_called_once_with(event)
    db.flush.assert_awaited_once()
    # The publisher deliberately does not commit: source mutation and event
    # must be committed or rolled back by the same service transaction.
    assert not hasattr(db, "commit") or not db.commit.called


@pytest.mark.asyncio
async def test_publish_domain_event_rejects_missing_contract_fields() -> None:
    db = Mock()
    db.add = Mock()
    db.flush = AsyncMock()

    with pytest.raises(ValueError, match="required"):
        await publish_domain_event(
            db,
            company_id=uuid.uuid4(),
            event_type="",
            aggregate_type="company_fact",
            aggregate_id=uuid.uuid4(),
        )

    db.add.assert_not_called()
    db.flush.assert_not_awaited()


def test_domain_event_dispatcher_is_registered_and_scheduled() -> None:
    from app.worker.beat_schedule import BEAT_SCHEDULE
    from app.worker.tasks.domain_events import dispatch_domain_event_outbox

    assert dispatch_domain_event_outbox.name == "app.worker.tasks.dispatch_domain_event_outbox"
    schedule = BEAT_SCHEDULE["dispatch-domain-event-outbox"]
    assert schedule["task"] == dispatch_domain_event_outbox.name
    assert schedule["kwargs"]["batch_size"] == 100


def test_domain_event_outbox_indexes_reference_real_timestamp_columns() -> None:
    from app.models.domain_event import DomainEventOutbox

    table = DomainEventOutbox.__table__
    column_names = set(table.columns.keys())
    indexed_columns = {
        column.name
        for index in table.indexes
        for column in index.columns
    }
    assert "occurred_at" in column_names
    assert "created_at" not in column_names
    assert indexed_columns <= column_names


def test_lifecycle_event_contracts_route_to_deterministic_consumers() -> None:
    from app.worker.tasks.domain_events import (
        EVIDENCE_VERIFICATION_EVENTS,
        FILING_RECEIPT_EVENTS,
        MAX_DISPATCH_ATTEMPTS,
        REASSESSMENT_EVENTS,
        consume_evidence_verification_event,
        consume_filing_receipt_event,
    )

    assert {
        DomainEventType.DIRECTOR_CHANGED,
        DomainEventType.SHAREHOLDER_CHANGED,
        DomainEventType.SHARE_TRANSFER_CHANGED,
        DomainEventType.REGISTERED_OFFICE_CHANGED,
        DomainEventType.COMPANY_CHARGE_RECORDED,
        DomainEventType.COMPANY_CHARGE_VERIFIED,
    }.issubset(REASSESSMENT_EVENTS)
    assert {
        DomainEventType.FILING_RECEIPT_RECORDED,
        DomainEventType.ANNUAL_RETURN_FILED,
    }.issubset(FILING_RECEIPT_EVENTS)
    assert {
        DomainEventType.EVIDENCE_VERIFICATION_COMPLETED,
        DomainEventType.COMPANY_FACT_VERIFIED,
    }.issubset(EVIDENCE_VERIFICATION_EVENTS)
    assert MAX_DISPATCH_ATTEMPTS == 8
    assert consume_filing_receipt_event.name == (
        "app.worker.tasks.consume_filing_receipt_event"
    )
    assert consume_evidence_verification_event.name == (
        "app.worker.tasks.consume_evidence_verification_event"
    )


def test_event_consumption_has_database_unique_idempotency_boundary() -> None:
    constraints = {
        tuple(column.name for column in constraint.columns)
        for constraint in DomainEventConsumption.__table__.constraints
        if hasattr(constraint, "columns") and constraint.__class__.__name__ == "UniqueConstraint"
    }
    assert ("event_id", "consumer_name") in constraints


def test_outbox_exposes_dead_letter_and_replay_metadata() -> None:
    columns = set(DomainEventOutbox.__table__.columns.keys())
    assert {
        "dead_lettered_at",
        "dead_letter_reason",
        "replay_count",
        "last_replayed_at",
    }.issubset(columns)
