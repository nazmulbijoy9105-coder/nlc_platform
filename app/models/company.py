"""
NEUM LEX COUNSEL — ORM LAYER
company.py — Company + CompanyUserAccess models
This is the central model. Every other table references company_id.
Multi-tenant isolation enforced via PostgreSQL RLS on this table.
"""
from __future__ import annotations

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
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base
from .enums import (
    CompanyStatus,
    CompanyType,
    ExposureBand,
    LifecycleStage,
    RevenueTier,
    RiskBand,
)
from .mixins import FullMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    import uuid
    from datetime import date, datetime
    from decimal import Decimal

    from .commercial import Engagement, Task
    from .compliance import ComplianceFlag, ComplianceScoreHistory
    from .documents import AIOutputLog, Document
    from .filings import AGM, AnnualReturn, Audit
    from .infrastructure import Notification, RegisteredOfficeHistory, StatutoryRegister
    from .people import Director, Shareholder, ShareTransfer
    from .rescue import RescuePlan
    from .user import User


class Company(FullMixin, Base):
    __tablename__ = "companies"

    # ── Core Identity ─────────────────────────────────────────────
    registration_number: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    company_name: Mapped[str] = mapped_column(String(500), nullable=False)
    company_name_search: Mapped[str | None] = mapped_column(
        TSVECTOR, nullable=True,
        comment="Auto-maintained by pg trigger for full-text search"
    )
    company_type: Mapped[CompanyType] = mapped_column(
        Enum(CompanyType, name="company_type"), nullable=False
    )
    company_status: Mapped[CompanyStatus] = mapped_column(
        Enum(CompanyStatus, name="company_status"),
        default=CompanyStatus.ACTIVE,
        nullable=False,
        index=True,
    )
    lifecycle_stage: Mapped[LifecycleStage] = mapped_column(
        Enum(LifecycleStage, name="lifecycle_stage"),
        default=LifecycleStage.INCORPORATION,
        nullable=False,
    )

    # ── Incorporation ─────────────────────────────────────────────
    incorporation_date: Mapped[date] = mapped_column(Date, nullable=False)
    financial_year_end: Mapped[date] = mapped_column(Date, nullable=False)
    registered_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    industry_sector: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tin_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    vat_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    authorized_capital_bdt: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 2), nullable=True
    )
    paid_up_capital_bdt: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 2), nullable=True
    )

    # ── Compliance State ──────────────────────────────────────────
    current_compliance_score: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    current_risk_band: Mapped[RiskBand | None] = mapped_column(
        Enum(RiskBand, name="risk_band"), nullable=True, index=True
    )
    current_exposure_band: Mapped[ExposureBand | None] = mapped_column(
        Enum(ExposureBand, name="exposure_band"), nullable=True
    )
    last_evaluated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rescue_required: Mapped[bool] = mapped_column(
        Boolean, default=False, index=True
    )
    rescue_triggered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── AGM State ─────────────────────────────────────────────────
    first_agm_held: Mapped[bool] = mapped_column(Boolean, default=False)
    last_agm_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    agm_default_count: Mapped[int] = mapped_column(Integer, default=0)

    # ── Audit State ───────────────────────────────────────────────
    first_auditor_appointed: Mapped[bool] = mapped_column(Boolean, default=False)
    last_audit_signed_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # ── Returns State ─────────────────────────────────────────────
    last_return_filed_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    unfiled_returns_count: Mapped[int] = mapped_column(Integer, default=0)

    # ── Revenue Intelligence ──────────────────────────────────────
    # Admin-only — never exposed to client-facing roles
    revenue_tier: Mapped[RevenueTier | None] = mapped_column(
        Enum(RevenueTier, name="revenue_tier"), nullable=True
    )
    estimated_fee_bdt: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True
    )
    client_since: Mapped[date | None] = mapped_column(Date, nullable=True)
    assigned_staff_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # ── Notes ─────────────────────────────────────────────────────
    internal_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ─────────────────────────────────────────────
    user_access: Mapped[list[CompanyUserAccess]] = relationship(
        "CompanyUserAccess", back_populates="company", lazy="selectin"
    )
    directors: Mapped[list[Director]] = relationship(
        "Director", back_populates="company", lazy="selectin"
    )
    shareholders: Mapped[list[Shareholder]] = relationship(
        "Shareholder", back_populates="company", lazy="selectin"
    )
    share_transfers: Mapped[list[ShareTransfer]] = relationship(
        "ShareTransfer", back_populates="company", lazy="noload"
    )
    agms: Mapped[list[AGM]] = relationship(
        "AGM", back_populates="company", lazy="selectin",
        order_by="AGM.financial_year.desc()"
    )
    audits: Mapped[list[Audit]] = relationship(
        "Audit", back_populates="company", lazy="selectin"
    )
    annual_returns: Mapped[list[AnnualReturn]] = relationship(
        "AnnualReturn", back_populates="company", lazy="selectin",
        order_by="AnnualReturn.financial_year.desc()"
    )
    compliance_flags: Mapped[list[ComplianceFlag]] = relationship(
        "ComplianceFlag", back_populates="company", lazy="selectin"
    )
    score_history: Mapped[list[ComplianceScoreHistory]] = relationship(
        "ComplianceScoreHistory", back_populates="company", lazy="noload",
        order_by="ComplianceScoreHistory.calculated_at.desc()"
    )
    rescue_plans: Mapped[list[RescuePlan]] = relationship(
        "RescuePlan", back_populates="company", lazy="selectin"
    )
    tasks: Mapped[list[Task]] = relationship(
        "Task", back_populates="company", lazy="noload"
    )
    engagements: Mapped[list[Engagement]] = relationship(
        "Engagement", back_populates="company", lazy="selectin"
    )
    documents: Mapped[list[Document]] = relationship(
        "Document", back_populates="company", lazy="noload"
    )
    notifications: Mapped[list[Notification]] = relationship(
        "Notification", back_populates="company", lazy="noload"
    )
    statutory_registers: Mapped[list[StatutoryRegister]] = relationship(
        "StatutoryRegister", back_populates="company", lazy="selectin"
    )
    office_history: Mapped[list[RegisteredOfficeHistory]] = relationship(
        "RegisteredOfficeHistory", back_populates="company", lazy="noload"
    )
    ai_outputs: Mapped[list[AIOutputLog]] = relationship(
        "AIOutputLog", back_populates="company", lazy="noload"
    )

    # ── Helpers ───────────────────────────────────────────────────
    @property
    def is_high_risk(self) -> bool:
        return self.current_risk_band in (RiskBand.RED, RiskBand.BLACK)

    @property
    def active_flags(self) -> list[ComplianceFlag]:
        from .enums import FlagStatus
        return [f for f in self.compliance_flags if f.flag_status == FlagStatus.ACTIVE]

    def __repr__(self) -> str:
        return f"<Company {self.registration_number} — {self.company_name}>"


class CompanyUserAccess(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Junction: which users can access which companies.
    RLS uses this table to enforce company-level isolation.
    """
    __tablename__ = "company_user_access"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    can_edit: Mapped[bool] = mapped_column(Boolean, default=False)
    can_view_financials: Mapped[bool] = mapped_column(Boolean, default=False)
    granted_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    granted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Relationships ─────────────────────────────────────────────
    company: Mapped[Company] = relationship(
        "Company", back_populates="user_access"
    )
    user: Mapped[User] = relationship(
        "User", back_populates="company_access"
    )

    def __repr__(self) -> str:
        return f"<CompanyUserAccess company={self.company_id} user={self.user_id}>"
