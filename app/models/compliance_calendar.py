"""Proactive Compliance Calendar – persistent statutory deadlines."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean, Date, DateTime, Enum, ForeignKey, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base
from .enums import CalendarEventType, CalendarEventStatus
from .mixins import FullMixin

if TYPE_CHECKING:
    from .company import Company


class ComplianceCalendarEvent(FullMixin, Base):
    __tablename__ = "compliance_calendar_events"
    __table_args__ = (
        UniqueConstraint(
            "company_id", "event_type", "period_label",
            name="uq_company_event_period",
        ),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    event_type: Mapped[CalendarEventType] = mapped_column(
        Enum(CalendarEventType, name="calendar_event_type"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    reminder_30_days: Mapped[date | None] = mapped_column(Date, nullable=True)
    reminder_14_days: Mapped[date | None] = mapped_column(Date, nullable=True)
    reminder_7_days: Mapped[date | None] = mapped_column(Date, nullable=True)

    period_label: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[CalendarEventStatus] = mapped_column(
        Enum(CalendarEventStatus, name="calendar_event_status"),
        default=CalendarEventStatus.UPCOMING,
        nullable=False,
        index=True,
    )

    is_statutory: Mapped[bool] = mapped_column(Boolean, default=True)
    statutory_basis: Mapped[str | None] = mapped_column(String(200), nullable=True)

    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    evidence_document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    assigned_to: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    company: Mapped["Company"] = relationship("Company", back_populates="calendar_events")
