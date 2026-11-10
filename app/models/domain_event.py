"""Transactional domain-event outbox for the company lifecycle."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base
from .mixins import UUIDPrimaryKeyMixin


class DomainEventOutbox(UUIDPrimaryKeyMixin, Base):
    """Durable event written in the same transaction as its aggregate change.

    Delivery is at-least-once. Consumers must deduplicate by event.id.
    Payloads must contain identifiers and changed-field metadata, never secrets
    or raw personal/company document contents.
    """

    __tablename__ = "domain_event_outbox"
    __table_args__ = (
        CheckConstraint("replay_count >= 0", name="ck_domain_event_replay_count_nonnegative"),
        Index(
            "ix_domain_event_outbox_pending",
            "processed_at",
            "available_at",
            "occurred_at",
        ),
        Index("ix_domain_event_outbox_company_created", "company_id", "occurred_at"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    event_type: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    aggregate_type: Mapped[str] = mapped_column(String(80), nullable=False)
    aggregate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    schema_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    correlation_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    dead_lettered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dead_letter_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    replay_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_replayed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DomainEventConsumption(UUIDPrimaryKeyMixin, Base):
    """Transactional idempotency receipt for a named event consumer."""

    __tablename__ = "domain_event_consumptions"
    __table_args__ = (
        UniqueConstraint("event_id", "consumer_name", name="uq_domain_event_consumer"),
        Index("ix_domain_event_consumptions_company", "company_id", "processed_at"),
    )

    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("domain_event_outbox.id", ondelete="CASCADE"),
        nullable=False,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    consumer_name: Mapped[str] = mapped_column(String(120), nullable=False)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )
    outcome: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
