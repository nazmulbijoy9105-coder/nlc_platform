"""
NEUM LEX COUNSEL — ORM LAYER
company.py — Company + CompanyUserAccess models
This is the central model. Every other table references company_id.
Multi-tenant isolation enforced via PostgreSQL RLS on this table.
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
from sqlalchemy.dialects.postgresql import ARRAY, TSVECTOR, UUID
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

    # ── Trade License ───────────────────────────────────────────
    trade_license_obtained: Mapped[bool] = mapped_column(Boolean, default=False)
    trade_license_expiry: Mapped[date | None] = mapped_column(Date, nullable=True)

    # ── Tax Return Tracking ─────────────────────────────────────
    tax_return_filed_for_current_fy: Mapped[bool] = mapped_column(Boolean, default=False)
    last_tax_return_filed: Mapped[date | None] = mapped_column(Date, nullable=True)

    # ── Advance Tax (Quarterly) ──────────────────────────────────
    advance_tax_q1_paid: Mapped[bool] = mapped_column(Boolean, default=False)
    advance_tax_q2_paid: Mapped[bool] = mapped_column(Boolean, default=False)
    advance_tax_q3_paid: Mapped[bool] = mapped_column(Boolean, default=False)
    advance_tax_q4_paid: Mapped[bool] = mapped_column(Boolean, default=False)

    # ── TDS ─────────────────────────────────────────────────────
    tds_deposited_up_to_date: Mapped[bool] = mapped_column(Boolean, default=True)
    last_tds_deposit_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # ── VAT Returns ─────────────────────────────────────────────
    last_vat_return_filed: Mapped[date | None] = mapped_column(Date, nullable=True)
    vat_annual_return_filed_for_fy: Mapped[bool] = mapped_column(Boolean, default=False)

    # ── Minimum Tax & Clearance ──────────────────────────────────
    minimum_tax_paid: Mapped[bool] = mapped_column(Boolean, default=True)
    tax_clearance_obtained: Mapped[bool] = mapped_column(Boolean, default=False)
    # ── Compliance Data (0027 — DEAD rule inputs) ─────────────────
    moa_aoa_filed: Mapped[bool | None] = mapped_column(Boolean, server_default="true", nullable=True)
    capital_reduction_pending: Mapped[bool | None] = mapped_column(Boolean, server_default="false", nullable=True)
    special_resolution_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    special_resolution_filed: Mapped[bool | None] = mapped_column(Boolean, server_default="false", nullable=True)
    register_of_directors_interests: Mapped[bool | None] = mapped_column(Boolean, server_default="true", nullable=True)
    register_of_contracts: Mapped[bool | None] = mapped_column(Boolean, server_default="true", nullable=True)
    winding_up_petition_filed: Mapped[bool | None] = mapped_column(Boolean, server_default="false", nullable=True)
    liquidator_appointed: Mapped[bool | None] = mapped_column(Boolean, server_default="false", nullable=True)
    court_ordered_winding_up: Mapped[bool | None] = mapped_column(Boolean, server_default="false", nullable=True)
    voluntary_winding_up: Mapped[bool | None] = mapped_column(Boolean, server_default="false", nullable=True)
    investigation_order: Mapped[bool | None] = mapped_column(Boolean, server_default="false", nullable=True)
    factory_license_obtained: Mapped[bool | None] = mapped_column(Boolean, server_default="false", nullable=True)
    factory_license_expiry: Mapped[date | None] = mapped_column(Date, nullable=True)
    labour_court_order_pending: Mapped[bool | None] = mapped_column(Boolean, server_default="false", nullable=True)
    bsec_listed: Mapped[bool | None] = mapped_column(Boolean, server_default="false", nullable=True)
    bsec_quarterly_report_filed: Mapped[bool | None] = mapped_column(Boolean, server_default="true", nullable=True)
    cg_certificate_obtained: Mapped[bool | None] = mapped_column(Boolean, server_default="true", nullable=True)
    board_independent_director: Mapped[bool | None] = mapped_column(Boolean, server_default="true", nullable=True)
    audit_committee_established: Mapped[bool | None] = mapped_column(Boolean, server_default="true", nullable=True)
    agm_adjourned_without_notice: Mapped[bool | None] = mapped_column(Boolean, server_default="false", nullable=True)
    name_change_pending: Mapped[bool | None] = mapped_column(Boolean, server_default="false", nullable=True)
    name_change_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    name_change_sr_passed: Mapped[bool | None] = mapped_column(Boolean, server_default="false", nullable=True)
    object_clause_change_pending: Mapped[bool | None] = mapped_column(Boolean, server_default="false", nullable=True)
    object_clause_change_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    aoa_alteration_pending: Mapped[bool | None] = mapped_column(Boolean, server_default="false", nullable=True)
    aoa_alteration_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    foreign_exchange_violation: Mapped[bool | None] = mapped_column(Boolean, server_default="false", nullable=True)
    annual_turnover_bdt: Mapped[Decimal | None] = mapped_column(Numeric(20, 2), nullable=True)
    # ── 0031: Board/Accounts/Director extended (Companies Act) ──
    last_board_meeting_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    board_meeting_notice_given: Mapped[bool | None] = mapped_column(Boolean, server_default="true", nullable=True)
    board_minutes_prepared: Mapped[bool | None] = mapped_column(Boolean, server_default="true", nullable=True)
    financial_statements_presented: Mapped[bool | None] = mapped_column(Boolean, server_default="true", nullable=True)
    financial_statements_filed: Mapped[bool | None] = mapped_column(Boolean, server_default="true", nullable=True)
    books_of_account_kept: Mapped[bool | None] = mapped_column(Boolean, server_default="true", nullable=True)
    director_consent_filed: Mapped[bool | None] = mapped_column(Boolean, server_default="true", nullable=True)
    director_office_of_profit: Mapped[bool | None] = mapped_column(Boolean, server_default="false", nullable=True)
    managing_director_appointment_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    member_count: Mapped[int | None] = mapped_column(Integer, server_default="0", nullable=True)
    business_commencement_declaration_filed: Mapped[bool | None] = mapped_column(Boolean, server_default="true", nullable=True)
    tax_return_deadline_extended: Mapped[bool] = mapped_column(Boolean, default=False)

    # ── Director Disqualification ────────────────────────────────
    any_director_disqualified: Mapped[bool] = mapped_column(Boolean, default=False)
    disqualification_details: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), nullable=True
    )

    # ── Penalty History ─────────────────────────────────────────
    penalty_notices_received: Mapped[int] = mapped_column(Integer, default=0)
    penalty_notices_resolved: Mapped[int] = mapped_column(Integer, default=0)

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

    # ── BSEC Corporate Governance ──────────────────────────────────────
    # ── Labour Compliance ──────────────────────────────────────────────

    # ── Bankruptcy / Winding Up ────────────────────────────────────────
    # ── Escalation / Strike-Off ────────────────────────────────────────
    # ── Foreign Exchange / FDI ─────────────────────────────────────────
    # ── RJSC Form Filings ──────────────────────────────────────────────

    # ── Annual Return Attachments ──────────────────────────────────────
    # ── Capital / Resolutions ──────────────────────────────────────────
    # ── Corporate Structure Changes ────────────────────────────────────

    # ── Statutory Registers ────────────────────────────────────────────
        String(500),
        nullable=False,
        server_default="registered_office",
    )

    # ── AGM Details ────────────────────────────────────────────────────

    # ── Audit Details ──────────────────────────────────────────────────

    # ── Office / Address ───────────────────────────────────────────────

    # ── Financial ──────────────────────────────────────────────────────

    # ── Shareholders ───────────────────────────────────────────────────

    # ── Misc ────────────────────────────────────────────────────────────
    minimum_directors_met: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")



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
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
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
