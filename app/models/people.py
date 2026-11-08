"""
NEUM LEX COUNSEL — ORM LAYER
people.py — Director, Shareholder, ShareTransfer models
DIR rules and TR rules evaluate against these records.
AI Constitution Article 2: NID/passport are sensitive governance data.
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
from .enums import DirectorStatus, TransferStatus
from .mixins import FullMixin

if TYPE_CHECKING:
    import uuid
    from datetime import date
    from decimal import Decimal

    from .company import Company


# ═══════════════════════════════════════════════════════════════════
# DIRECTOR
# ═══════════════════════════════════════════════════════════════════
class Director(FullMixin, Base):
    __tablename__ = "directors"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Identity ──────────────────────────────────────────────────
    full_name: Mapped[str] = mapped_column(String(500), nullable=False)
    father_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    nid_number: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
        comment="Sensitive governance data — encrypted at application layer"
    )
    passport_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    nationality: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Appointment ───────────────────────────────────────────────
    appointment_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    appointment_filed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    appointment_filing_delayed: Mapped[bool] = mapped_column(Boolean, default=False)
    appointment_delay_days: Mapped[int] = mapped_column(Integer, default=0)

    # ── Evidence-bound statutory filing states ────────────────────
    form_xii_filed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    form_xii_filed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    form_xii_status_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    form_xii_evidence_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    form_xii_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    form_xii_verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    consent_filed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    consent_filed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    consent_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    consent_evidence_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    consent_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consent_verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # ── Resignation / Removal ─────────────────────────────────────
    director_status: Mapped[DirectorStatus] = mapped_column(
        Enum(DirectorStatus, name="director_status"),
        default=DirectorStatus.ACTIVE,
        nullable=False,
        index=True,
    )
    departure_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    departure_filed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    departure_filing_delayed: Mapped[bool] = mapped_column(Boolean, default=False)
    departure_delay_days: Mapped[int] = mapped_column(Integer, default=0)
    departed_still_liable: Mapped[bool] = mapped_column(
        Boolean, default=False, index=True,
        comment="DIR-004: departed director shown as active — personal liability risk"
    )

    # ── Shareholding ──────────────────────────────────────────────
    shares_held: Mapped[int] = mapped_column(Integer, default=0)
    is_managing_director: Mapped[bool] = mapped_column(Boolean, default=False)
    is_chairman: Mapped[bool] = mapped_column(Boolean, default=False)

    # ── Relationships ─────────────────────────────────────────────
    company: Mapped[Company] = relationship("Company", back_populates="directors")

    def __repr__(self) -> str:
        return f"<Director {self.full_name} [{self.director_status}]>"


# ═══════════════════════════════════════════════════════════════════
# SHAREHOLDER
# ═══════════════════════════════════════════════════════════════════
class Shareholder(FullMixin, Base):
    __tablename__ = "shareholders"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Identity ──────────────────────────────────────────────────
    shareholder_name: Mapped[str] = mapped_column(String(500), nullable=False)
    shareholder_type: Mapped[str] = mapped_column(
        String(50), default="INDIVIDUAL",
        comment="INDIVIDUAL | CORPORATE | FOREIGN"
    )
    nid_or_reg_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    nationality: Mapped[str | None] = mapped_column(String(100), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Shareholding ──────────────────────────────────────────────
    shares_held: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    share_class: Mapped[str] = mapped_column(String(50), default="ORDINARY")
    percentage_holding: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    share_certificate_issued: Mapped[bool] = mapped_column(Boolean, default=False)
    certificate_issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    certificate_delay_days: Mapped[int] = mapped_column(Integer, default=0)

    # ── RJSC Filing ───────────────────────────────────────────────
    change_filed_with_rjsc: Mapped[bool] = mapped_column(Boolean, default=True)
    rjsc_filing_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # ── Relationships ─────────────────────────────────────────────
    company: Mapped[Company] = relationship("Company", back_populates="shareholders")

    def __repr__(self) -> str:
        return f"<Shareholder {self.shareholder_name} — {self.shares_held} shares>"


# ═══════════════════════════════════════════════════════════════════
# SHARE TRANSFER
# ═══════════════════════════════════════════════════════════════════
class ShareTransfer(FullMixin, Base):
    __tablename__ = "share_transfers"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Parties ───────────────────────────────────────────────────
    transferor_name: Mapped[str] = mapped_column(String(500), nullable=False)
    transferee_name: Mapped[str] = mapped_column(String(500), nullable=False)
    transferor_shareholder_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shareholders.id"), nullable=True
    )
    transferee_shareholder_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shareholders.id"), nullable=True
    )

    # ── Transfer Details ──────────────────────────────────────────
    shares_transferred: Mapped[int] = mapped_column(Integer, nullable=False)
    transfer_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    consideration_bdt: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 2), nullable=True
    )
    transfer_status: Mapped[TransferStatus] = mapped_column(
        Enum(TransferStatus, name="transfer_status"),
        default=TransferStatus.COMPLETE,
        nullable=False,
    )

    # ── Compliance Checks ─────────────────────────────────────────
    # TR-001: Transfer instrument (Form 117) present?
    has_transfer_instrument: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=None)
    # TR-002: Stamp duty paid?
    stamp_duty_paid: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=None)
    stamp_duty_amount_bdt: Mapped[Decimal | None] = mapped_column(
        Numeric(15, 2), nullable=True
    )
    # TR-003: Board approval obtained?
    board_approval_obtained: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=None)
    board_approval_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # TR-004: Register updated?
    register_updated: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=None)
    register_update_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # TR-005: AoA restriction violation?
    aoa_restriction_violated: Mapped[bool | None] = mapped_column(
        Boolean, nullable=True, default=None,
        comment="Legacy reported state only; not a legal conclusion or BLACK override"
    )
    is_irregular: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    irregularity_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Evidence-bound transfer facts (None = unknown/unverified) ─
    transfer_instrument_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    transfer_instrument_evidence_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    form_117_filed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    form_117_evidence_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    stamp_duty_applicability_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    stamp_duty_evidence_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    board_approval_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    board_approval_evidence_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    aoa_restriction_apply: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    articles_clause_evidence_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    transfer_registered: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    transfer_registration_evidence_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    registration_refused: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    registration_refusal_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    refusal_decision_evidence_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    refusal_notice_sent: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    refusal_notice_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    refusal_notice_evidence_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    instrument_lodged_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    instrument_lodgement_evidence_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    register_update_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    register_update_evidence_ref: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ─────────────────────────────────────────────
    company: Mapped[Company] = relationship(
        "Company", back_populates="share_transfers"
    )

    def __repr__(self) -> str:
        return (
            f"<ShareTransfer {self.transferor_name} → {self.transferee_name} "
            f"({self.shares_transferred} shares)>"
        )


# ═══════════════════════════════════════════════════════════════════
# SHARE COMPLIANCE EVENTS — evidence-bound statutory triggers
# ═══════════════════════════════════════════════════════════════════
class ShareComplianceEvent(FullMixin, Base):
    """Verified allotment, capital-increase or transfer-registration event.

    A row is not a legal fact unless its event provenance is verified.
    Filing and certificate statuses have independent verification evidence.
    """
    __tablename__ = "share_compliance_events"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    share_transfer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("share_transfers.id", ondelete="RESTRICT"),
        nullable=True,
    )
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    event_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    event_evidence_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    event_verified_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )

    filing_form: Mapped[str | None] = mapped_column(String(16), nullable=True)
    filing_status: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    filing_status_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    filing_evidence_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    filing_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    filing_verified_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    filing_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    certificate_issued: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    certificate_status_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    certificate_evidence_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    certificate_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    certificate_verified_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    certificate_issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    company: Mapped[Company] = relationship(
        "Company", back_populates="share_compliance_events"
    )
