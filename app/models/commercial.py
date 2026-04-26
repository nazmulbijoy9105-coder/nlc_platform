"""
NEUM LEX COUNSEL — ORM LAYER
commercial.py — Task, Engagement, Quotation models
Revenue intelligence engine — admin-only.
AI Constitution Article 2.2: Revenue data never exposed to client roles.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base
from .enums import (
    ComplexityLevel,
    EngagementStatus,
    RevenueTier,
    TaskPriority,
    TaskStatus,
)
from .mixins import FullMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    import uuid
    from datetime import date, datetime
    from decimal import Decimal

    from .company import Company


# ═══════════════════════════════════════════════════════════════════
# TASK
# ═══════════════════════════════════════════════════════════════════
class Task(FullMixin, Base):
    """Client-visible action items generated from compliance flags."""
    __tablename__ = "tasks"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Task Details ──────────────────────────────────────────────
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    task_status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, name="task_status"),
        default=TaskStatus.PENDING,
        nullable=False,
    )
    priority: Mapped[TaskPriority] = mapped_column(
        Enum(TaskPriority, name="task_priority"),
        default=TaskPriority.MEDIUM,
        nullable=False,
        index=True,
    )

    # ── Dates ─────────────────────────────────────────────────────
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Assignment ────────────────────────────────────────────────
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    # ── Source ────────────────────────────────────────────────────
    source_flag_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
        comment="compliance_flags.id that generated this task"
    )
    source_rescue_step_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    # ── Relationships ─────────────────────────────────────────────
    company: Mapped[Company] = relationship("Company", back_populates="tasks")

    def __repr__(self) -> str:
        return f"<Task {self.title[:40]} [{self.task_status}]>"


# ═══════════════════════════════════════════════════════════════════
# ENGAGEMENT
# ═══════════════════════════════════════════════════════════════════
class Engagement(FullMixin, Base):
    """
    Revenue pipeline record.
    IDENTIFIED → QUOTED → CONFIRMED → IN_PROGRESS → COMPLETED.
    Admin-only — client roles cannot see this table.
    """
    __tablename__ = "engagements"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Engagement Details ────────────────────────────────────────
    engagement_title: Mapped[str] = mapped_column(String(500), nullable=False)
    engagement_type: Mapped[str] = mapped_column(
        String(100), nullable=False,
        comment="COMPLIANCE_FILING | RESCUE | REGULARIZATION | ADVISORY"
    )
    engagement_status: Mapped[EngagementStatus] = mapped_column(
        Enum(EngagementStatus, name="engagement_status"),
        default=EngagementStatus.IDENTIFIED,
        nullable=False,
        index=True,
    )
    revenue_tier: Mapped[RevenueTier] = mapped_column(
        Enum(RevenueTier, name="revenue_tier"), nullable=False, index=True
    )
    complexity: Mapped[ComplexityLevel] = mapped_column(
        Enum(ComplexityLevel, name="complexity_level"),
        default=ComplexityLevel.MEDIUM,
        nullable=False,
    )

    # ── Source ────────────────────────────────────────────────────
    triggered_by_risk_band: Mapped[str | None] = mapped_column(
        String(20), nullable=True,
        comment="Risk band that triggered this engagement identification"
    )
    rescue_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    # ── Dates ─────────────────────────────────────────────────────
    identified_date: Mapped[date] = mapped_column(Date, nullable=False)
    quoted_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    confirmed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    started_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    completed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    target_completion_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # ── Commercial (Admin-only) ───────────────────────────────────
    estimated_fee_bdt: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True
    )
    quoted_fee_bdt: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True
    )
    confirmed_fee_bdt: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True
    )
    invoiced_bdt: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True
    )
    collected_bdt: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True
    )

    # ── Assignment ────────────────────────────────────────────────
    assigned_staff_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    # ── Notes ─────────────────────────────────────────────────────
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ─────────────────────────────────────────────
    company: Mapped[Company] = relationship(
        "Company", back_populates="engagements"
    )
    quotations: Mapped[list[Quotation]] = relationship(
        "Quotation", back_populates="engagement", lazy="selectin"
    )

    def __repr__(self) -> str:
        return (
            f"<Engagement {self.engagement_title[:30]} "
            f"[{self.engagement_status}] BDT {self.confirmed_fee_bdt}>"
        )


# ═══════════════════════════════════════════════════════════════════
# QUOTATION
# ═══════════════════════════════════════════════════════════════════
class Quotation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Fee quotation linked to an engagement."""
    __tablename__ = "quotations"

    engagement_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("engagements.id", ondelete="CASCADE"),
        nullable=False,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Quotation ─────────────────────────────────────────────────
    quotation_number: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False
    )
    quotation_date: Mapped[date] = mapped_column(Date, nullable=False)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)

    # ── Fee Breakdown ─────────────────────────────────────────────
    professional_fee_bdt: Mapped[Decimal] = mapped_column(
        Numeric(15, 2), nullable=False
    )
    government_fee_bdt: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True
    )
    vat_bdt: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True
    )
    total_bdt: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)

    # ── Status ────────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        String(50), default="DRAFT",
        comment="DRAFT | SENT | ACCEPTED | REJECTED | SUPERSEDED"
    )
    accepted_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Line Items ────────────────────────────────────────────────
    line_items: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ─────────────────────────────────────────────
    engagement: Mapped[Engagement] = relationship(
        "Engagement", back_populates="quotations"
    )

    def __repr__(self) -> str:
        return f"<Quotation {self.quotation_number} BDT {self.total_bdt} [{self.status}]>"
