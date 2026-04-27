"""
NEUM LEX COUNSEL — ORM LAYER
rescue.py — RescuePlan, RescueStep models
8-step dependency-aware corporate rescue sequence.
Completing a rescue step triggers compliance re-evaluation.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base
from .enums import ComplexityLevel, RescueStepStatus, RevenueTier
from .mixins import FullMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    import uuid
    from datetime import date, datetime
    from decimal import Decimal

    from .company import Company


class RescuePlan(FullMixin, Base):
    """
    Auto-generated for every RED or BLACK company.
    One active plan per company at a time.
    Completing all steps triggers full compliance re-evaluation.
    """
    __tablename__ = "rescue_plans"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Plan Details ──────────────────────────────────────────────
    plan_name: Mapped[str] = mapped_column(String(500), nullable=False)
    revenue_tier: Mapped[RevenueTier] = mapped_column(
        Enum(RevenueTier, name="revenue_tier"), nullable=False
    )
    initial_risk_band: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="Risk band that triggered rescue (RED or BLACK)"
    )
    initial_score: Mapped[int] = mapped_column(Integer, nullable=False)
    years_in_default: Mapped[int] = mapped_column(Integer, default=0)

    # ── Status ────────────────────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    target_completion_date: Mapped[date | None] = mapped_column(
        Date, nullable=True
    )

    # ── Progress ──────────────────────────────────────────────────
    total_steps: Mapped[int] = mapped_column(Integer, default=8)
    completed_steps: Mapped[int] = mapped_column(Integer, default=0)
    blocked_steps: Mapped[int] = mapped_column(Integer, default=0)
    completion_percentage: Mapped[int] = mapped_column(Integer, default=0)

    # ── Commercial ────────────────────────────────────────────────
    # Admin-only — never exposed to client-facing roles
    quoted_fee_bdt: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True
    )
    confirmed_fee_bdt: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True
    )

    # ── Assigned ──────────────────────────────────────────────────
    assigned_staff_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    # ── Relationships ─────────────────────────────────────────────
    company: Mapped[Company] = relationship(
        "Company", back_populates="rescue_plans"
    )
    steps: Mapped[list[RescueStep]] = relationship(
        "RescueStep", back_populates="plan",
        order_by="RescueStep.step_number",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return (
            f"<RescuePlan company={self.company_id} "
            f"{self.completed_steps}/{self.total_steps} steps>"
        )


class RescueStep(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Individual steps in the rescue sequence.
    Steps are dependency-ordered — must follow the 8-step sequence.
    Completing a step triggers compliance re-evaluation in background.
    """
    __tablename__ = "rescue_steps"

    rescue_plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rescue_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Step Identity ─────────────────────────────────────────────
    step_number: Mapped[int] = mapped_column(
        Integer, nullable=False,
        comment="1=Retrospective Audit, 2=Ratify Transfers, ... 8=RJSC Acknowledgment"
    )
    step_title: Mapped[str] = mapped_column(String(500), nullable=False)
    step_description: Mapped[str] = mapped_column(Text, nullable=False)
    statutory_basis: Mapped[str | None] = mapped_column(String(500), nullable=True)
    complexity: Mapped[ComplexityLevel] = mapped_column(
        Enum(ComplexityLevel, name="complexity_level"),
        default=ComplexityLevel.MEDIUM,
        nullable=False,
    )

    # ── Timeline ──────────────────────────────────────────────────
    estimated_days_min: Mapped[int] = mapped_column(Integer, default=7)
    estimated_days_max: Mapped[int] = mapped_column(Integer, default=21)
    target_completion_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # ── Status ────────────────────────────────────────────────────
    step_status: Mapped[RescueStepStatus] = mapped_column(
        Enum(RescueStepStatus, name="rescue_step_status"),
        default=RescueStepStatus.PENDING,
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    blocked_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    completion_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Assignment ────────────────────────────────────────────────
    assigned_staff_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    # ── Trigger re-evaluation on COMPLETE ─────────────────────────
    triggers_reevaluation: Mapped[bool] = mapped_column(
        Boolean, default=True,
        comment="Step 8 completion triggers full compliance re-evaluation"
    )

    # ── Relationships ─────────────────────────────────────────────
    plan: Mapped[RescuePlan] = relationship(
        "RescuePlan", back_populates="steps"
    )

    def __repr__(self) -> str:
        return (
            f"<RescueStep {self.step_number}. {self.step_title} "
            f"[{self.step_status}]>"
        )
