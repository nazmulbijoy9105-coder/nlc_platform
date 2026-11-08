"""
NEUM LEX COUNSEL — ORM LAYER
filings.py — AGM, Audit, AnnualReturn models
These are the primary data sources for the rule engine evaluation.
AGM-001 through AGM-006, AUD-001 through AUD-003, AR-001 through AR-004
all read from these tables.
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
    from datetime import date, datetime
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
    short_notice_consent_obtained: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    short_notice_consent_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    short_notice_consent_evidence_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    short_notice_consent_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    short_notice_consent_verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notice_days_before: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # AGM-003: notice defective (< 21 days)
    notice_defective: Mapped[bool] = mapped_column(Boolean, default=False)
    # AGM-004: no notice sent at all
    notice_missing: Mapped[bool] = mapped_column(Boolean, default=False)

    # ── Held ──────────────────────────────────────────────────────
    agm_held: Mapped[bool] = mapped_column(Boolean, default=False)
    agm_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    venue: Mapped[str | None] = mapped_column(String(255), nullable=True)
    accounts_adopted: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    agm_held_without_audit: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    # AGM-001 / AGM-002: default flags
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    delay_days: Mapped[int] = mapped_column(Integer, default=0)

    # ── Held-status evidence ──────────────────────────────────────
    agm_held_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    agm_held_evidence_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    agm_held_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    agm_held_verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    member_register_snapshot_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    member_register_evidence_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    member_register_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    member_register_verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    entitled_members_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── Quorum ────────────────────────────────────────────────────
    # AGM-005: quorum not met
    quorum_met: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=None)
    members_present: Mapped[int] = mapped_column(Integer, default=0)
    members_present_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    members_present_evidence_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    members_present_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    members_present_verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    quorum_required: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
        comment="Applicable quorum; UNKNOWN until member count and Articles are verified"
    )
    quorum_required_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    quorum_evidence_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    quorum_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    quorum_verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    quorum_basis: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # ── Auditor ───────────────────────────────────────────────────
    # AGM-006: auditor not reappointed at AGM
    auditor_reappointed: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=None)
    auditor_reappointment_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    auditor_reappointment_evidence_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    auditor_reappointment_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    auditor_reappointment_verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # ── Minutes ───────────────────────────────────────────────────
    minutes_prepared: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=None)
    minutes_document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    # ── Filing ────────────────────────────────────────────────────
    minutes_filed_rjsc: Mapped[bool] = mapped_column(Boolean, default=False)
    rjsc_filing_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # ── Relationships ─────────────────────────────────────────────
    company: Mapped[Company] = relationship("Company", back_populates="agms")
    notice_evidence: Mapped[list["AGMNoticeEvidence"]] = relationship(
        "AGMNoticeEvidence", back_populates="agm", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<AGM company={self.company_id} FY={self.financial_year} held={self.agm_held}>"


# ═══════════════════════════════════════════════════════════════════
# AGM PER-RECIPIENT NOTICE / CONSENT EVIDENCE
# ═══════════════════════════════════════════════════════════════════
class AGMNoticeEvidence(FullMixin, Base):
    """Per-entitled-member service, consent and accidental-omission evidence."""
    __tablename__ = "agm_notice_evidence"
    __table_args__ = (
        UniqueConstraint("agm_id", "recipient_key", name="uq_agm_notice_recipient"),
        CheckConstraint("notice_delivery_status IN ('SERVED','NOT_SERVED','NOT_RECEIVED','UNKNOWN')", name="ck_agm_notice_delivery_status"),
        CheckConstraint(
            "NOT entitled_member_verified OR "
            "(entitlement_evidence_ref IS NOT NULL AND btrim(entitlement_evidence_ref) <> '' "
            "AND entitlement_verified_at IS NOT NULL AND entitlement_verified_by IS NOT NULL)",
            name="ck_agm_notice_entitlement_provenance",
        ),
        CheckConstraint(
            "NOT notice_verified OR "
            "(notice_evidence_ref IS NOT NULL AND btrim(notice_evidence_ref) <> '' "
            "AND notice_delivery_status <> 'UNKNOWN' AND notice_verified_at IS NOT NULL AND notice_verified_by IS NOT NULL)",
            name="ck_agm_notice_service_provenance",
        ),
        CheckConstraint(
            "NOT consent_verified OR "
            "(consent_given IS NOT NULL AND consent_evidence_ref IS NOT NULL "
            "AND btrim(consent_evidence_ref) <> '' AND consent_verified_at IS NOT NULL AND consent_verified_by IS NOT NULL)",
            name="ck_agm_notice_consent_provenance",
        ),
        CheckConstraint(
            "NOT omission_verified OR "
            "(omission_accidental IS NOT NULL AND omission_evidence_ref IS NOT NULL "
            "AND btrim(omission_evidence_ref) <> '' AND omission_verified_at IS NOT NULL AND omission_verified_by IS NOT NULL)",
            name="ck_agm_notice_omission_provenance",
        ),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    agm_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agms.id", ondelete="CASCADE"), nullable=False, index=True)
    shareholder_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("shareholders.id", ondelete="RESTRICT"), nullable=True)
    recipient_key: Mapped[str] = mapped_column(String(160), nullable=False)
    recipient_name: Mapped[str] = mapped_column(String(300), nullable=False)

    entitled_member_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    entitlement_evidence_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    entitlement_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    entitlement_verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)

    notice_delivery_status: Mapped[str] = mapped_column(String(24), nullable=False, default="UNKNOWN", server_default="UNKNOWN")
    notice_sent_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notice_evidence_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    notice_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    notice_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notice_verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)

    consent_given: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    consent_received_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    consent_evidence_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    consent_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    consent_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consent_verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)

    omission_accidental: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    omission_evidence_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    omission_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    omission_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    omission_verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)

    agm: Mapped[AGM] = relationship("AGM", back_populates="notice_evidence")
    company: Mapped[Company] = relationship("Company")


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
    audit_completion_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    audit_completion_evidence_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    audit_completion_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    audit_completion_verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
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

# RJSC-005: Filing lifecycle state transition validation.
# Every PATCH handler must validate `next_status` against this map.
VALID_TRANSITIONS: dict[str, set[str]] = {
    "PENDING":       {"FILED", "CANCELLED"},
    "FILED":         {"REJECTED", "SUPERSEDED"},
    "REJECTED":      {"PENDING"},
    "SUPERSEDED":    set(),
    "CANCELLED":     set(),
    "OVERDUE":       {"FILED", "CANCELLED"},
    "HELD":          {"MINUTES_FILED", "CANCELLED"},
    "MINUTES_FILED": set(),
    "COMPLETED":     set(),
    "IN_PROGRESS":   {"COMPLETED", "CANCELLED"},
}

def validate_filing_transition(current_status: str, next_status: str) -> bool:
    """Return True if the transition is allowed, False otherwise."""
    return next_status in VALID_TRANSITIONS.get(current_status, set())


class InvalidFilingTransitionError(ValueError):
    """Raised when a filing lifecycle transition is not allowed."""
    def __init__(self, current: str, next_: str):
        super().__init__(
            f"Invalid filing transition: {current} -> {next_}. "
            f"Allowed from {current}: {VALID_TRANSITIONS.get(current, set())}"
        )
