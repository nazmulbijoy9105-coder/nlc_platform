"""
NEUM LEX COUNSEL — ORM LAYER
filings.py — AGM, Audit, AnnualReturn models
These are the primary data sources for the rule engine evaluation.
AGM-001 through AGM-006, AUD-001 through AUD-003, AR-001 through AR-004
all read from these tables.
"""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base
from .mixins import FullMixin

if TYPE_CHECKING:
    import uuid
    from datetime import date
    from decimal import Decimal

    from .company import Company


# ═══════════════════════════════════════════════════════════════════
# AGM
# ═══════════════════════════════════════════════════════════════════
class AGM(FullMixin, Base):
    __tablename__ = "agms"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Period ────────────────────────────────────────────────────
    financial_year: Mapped[int] = mapped_column(Integer, nullable=False)
    agm_type: Mapped[str] = mapped_column(
        String(50), default="ANNUAL",
        comment="ANNUAL | EXTRAORDINARY | FIRST"
    )

    # ── Scheduling ────────────────────────────────────────────────
    agm_deadline: Mapped[date | None] = mapped_column(
        Date, nullable=True, index=True,
        comment="Calculated: incorporation+548d (first) or FY end+182d (subsequent)"
    )
    notice_sent_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notice_days_before: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # AGM-003: notice defective (< 21 days)
    notice_defective: Mapped[bool] = mapped_column(Boolean, default=False)
    # AGM-004: no notice sent at all
    notice_missing: Mapped[bool] = mapped_column(Boolean, default=False)

    # ── Held ──────────────────────────────────────────────────────
    agm_held: Mapped[bool] = mapped_column(Boolean, default=False)
    agm_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # AGM-001 / AGM-002: default flags
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    delay_days: Mapped[int] = mapped_column(Integer, default=0)

    # ── Quorum ────────────────────────────────────────────────────
    # AGM-005: quorum not met
    quorum_met: Mapped[bool] = mapped_column(Boolean, default=True)
    members_present: Mapped[int] = mapped_column(Integer, default=0)
    quorum_required: Mapped[int] = mapped_column(
        Integer, default=2, comment="Section 83 CA 1994 — 2 members for private"
    )

    # ── Auditor ───────────────────────────────────────────────────
    # AGM-006: auditor not reappointed at AGM
    auditor_reappointed: Mapped[bool] = mapped_column(Boolean, default=True)

    # ── Minutes ───────────────────────────────────────────────────
    minutes_prepared: Mapped[bool] = mapped_column(Boolean, default=False)
    minutes_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    # ── Filing ────────────────────────────────────────────────────
    minutes_filed_rjsc: Mapped[bool] = mapped_column(Boolean, default=False)
    rjsc_filing_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # ── Relationships ─────────────────────────────────────────────
    company: Mapped[Company] = relationship("Company", back_populates="agms")

    def __repr__(self) -> str:
        return f"<AGM company={self.company_id} FY={self.financial_year} held={self.agm_held}>"


# ═══════════════════════════════════════════════════════════════════
# AUDIT
# ═══════════════════════════════════════════════════════════════════
class Audit(FullMixin, Base):
    __tablename__ = "audits"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Period ────────────────────────────────────────────────────
    financial_year: Mapped[int] = mapped_column(Integer, nullable=False)
    audit_type: Mapped[str] = mapped_column(
        String(50), default="ANNUAL",
        comment="ANNUAL | FIRST_AUDITOR"
    )

    # ── Auditor ───────────────────────────────────────────────────
    auditor_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    auditor_firm: Mapped[str | None] = mapped_column(String(500), nullable=True)
    icab_number: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
        comment="ICAB registration number of audit firm"
    )
    # AUD-002: first auditor not appointed within 30 days
    first_auditor_appointed: Mapped[bool] = mapped_column(Boolean, default=False)
    first_auditor_appointment_date: Mapped[date | None] = mapped_column(
        Date, nullable=True
    )
    first_auditor_delay_days: Mapped[int] = mapped_column(Integer, default=0)

    # ── Completion ────────────────────────────────────────────────
    # AUD-001: audit not complete before AGM
    audit_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    audit_signed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # AUD-003: BLACK OVERRIDE — AGM held without audit
    agm_held_without_audit: Mapped[bool] = mapped_column(
        Boolean, default=False, index=True,
        comment="AUD-003: BLACK override — AGM held without completed audit"
    )
    is_missing: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    delay_days: Mapped[int] = mapped_column(Integer, default=0)

    # ── Report ────────────────────────────────────────────────────
    report_qualified: Mapped[bool] = mapped_column(Boolean, default=False)
    qualification_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    # ── Relationships ─────────────────────────────────────────────
    company: Mapped[Company] = relationship("Company", back_populates="audits")

    def __repr__(self) -> str:
        return f"<Audit company={self.company_id} FY={self.financial_year} complete={self.audit_complete}>"


# ═══════════════════════════════════════════════════════════════════
# ANNUAL RETURN
# ═══════════════════════════════════════════════════════════════════
class AnnualReturn(FullMixin, Base):
    __tablename__ = "annual_returns"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Period ────────────────────────────────────────────────────
    financial_year: Mapped[int] = mapped_column(Integer, nullable=False)
    filing_deadline: Mapped[date | None] = mapped_column(
        Date, nullable=True,
        comment="AGM date + 30 days (Section 190 CA 1994)"
    )

    # ── Filing ────────────────────────────────────────────────────
    # AR-001: default
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    filed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    delay_days: Mapped[int] = mapped_column(Integer, default=0)
    rjsc_receipt_number: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # ── Completeness ──────────────────────────────────────────────
    # AR-004: filed but incomplete
    is_complete: Mapped[bool] = mapped_column(Boolean, default=True)
    missing_attachments: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Fee ───────────────────────────────────────────────────────
    filing_fee_paid_bdt: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    late_fee_paid_bdt: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )

    # ── Relationships ─────────────────────────────────────────────
    company: Mapped[Company] = relationship(
        "Company", back_populates="annual_returns"
    )

    def __repr__(self) -> str:
        return (
            f"<AnnualReturn company={self.company_id} "
            f"FY={self.financial_year} default={self.is_default}>"
        )
