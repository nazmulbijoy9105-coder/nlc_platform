from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, Mock

import pytest

from app.models.domain_event import DomainEventOutbox
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
