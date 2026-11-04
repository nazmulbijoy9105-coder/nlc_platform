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
    CheckConstraint,
    DateTime,
    Date,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    UniqueConstraint,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base
from .mixins import AuditMixin, FullMixin

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
    __table_args__ = (UniqueConstraint("company_id", "id", name="uq_agms_company_id_id"),)

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
    scheduled_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    notice_sent_date: Mapped[date | None] = mapped_column(Date, nullable=True)
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

    # ── Quorum ────────────────────────────────────────────────────
    # AGM-005: quorum not met
    quorum_met: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=None)
    members_present: Mapped[int] = mapped_column(Integer, default=0)
    members_present_evidence_ref: Mapped[str | None] = mapped_column(String(500), nullable=True)
    members_total_at_agm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    members_total_evidence_ref: Mapped[str | None] = mapped_column(String(500), nullable=True)
    quorum_required: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=None,
        comment="Section 85(2)(b) statutory default; Articles may provide otherwise"
    )
    quorum_basis: Mapped[str | None] = mapped_column(String(64), nullable=True)
    articles_quorum_verified: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    articles_quorum_required: Mapped[int | None] = mapped_column(Integer, nullable=True)
    articles_quorum_verified_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    articles_quorum_verified_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    articles_quorum_evidence_ref: Mapped[str | None] = mapped_column(String(500), nullable=True)
    quorum_met: Mapped[bool | None] = mapped_column(Boolean, nullable=True, default=True)
    members_present: Mapped[int] = mapped_column(Integer, default=0)
    quorum_required: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=2,
        comment="Section 85(2)(b) statutory default; Articles may provide otherwise"
    )
    quorum_basis: Mapped[str | None] = mapped_column(String(64), nullable=True)

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

# AGM SOURCE EVIDENCE — VERSION-PINNED REVIEW
# ═══════════════════════════════════════════════════════════════════
class AGMEvidenceVerification(FullMixin, Base):
    """Reviewed source evidence for one AGM's membership or attendance count."""

    __tablename__ = "agm_evidence_verifications"
    __table_args__ = (
        CheckConstraint("evidence_kind IN ('MEMBERS_REGISTER', 'ATTENDANCE_REGISTER')", name="ck_agm_evidence_kind"),
        CheckConstraint("status IN ('PENDING', 'VERIFIED', 'REJECTED', 'REVOKED', 'SUPERSEDED')", name="ck_agm_evidence_status"),
        CheckConstraint("source_document_version >= 1", name="ck_agm_evidence_version"),
        CheckConstraint("source_checksum_sha256 ~ '^[0-9a-f]{64}$'", name="ck_agm_evidence_checksum"),
        CheckConstraint("verified_count IS NULL OR verified_count >= 0", name="ck_agm_evidence_count"),
        CheckConstraint("status <> 'VERIFIED' OR evidence_kind <> 'MEMBERS_REGISTER' OR verified_count >= 1", name="ck_agm_evidence_member_count_positive"),
        CheckConstraint("status <> 'VERIFIED' OR reviewed_by IS DISTINCT FROM submitted_by", name="ck_agm_evidence_four_eyes"),
        CheckConstraint("(status = 'REVOKED' AND revoked_by IS NOT NULL AND revoked_by IS DISTINCT FROM reviewed_by AND revoked_at IS NOT NULL AND revocation_reason IS NOT NULL) OR (status <> 'REVOKED' AND revoked_by IS NULL AND revoked_at IS NULL AND revocation_reason IS NULL)", name="ck_agm_evidence_revocation_metadata"),
        CheckConstraint(
            "(status = 'PENDING' AND reviewed_by IS NULL AND reviewed_at IS NULL AND verified_count IS NULL) OR "
            "(status = 'VERIFIED' AND reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL AND verified_count IS NOT NULL) OR "
            "(status IN ('REJECTED', 'REVOKED', 'SUPERSEDED') AND reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)",
            name="ck_agm_evidence_review_metadata",
        ),
        UniqueConstraint("company_id", "id", name="uq_agm_evidence_company_id"),
        ForeignKeyConstraint(
            ["company_id", "agm_id"], ["agms.company_id", "agms.id"],
            ondelete="CASCADE", name="fk_agm_evidence_company_agm",
        ),
        ForeignKeyConstraint(
            ["company_id", "document_id"], ["documents.company_id", "documents.id"],
            ondelete="RESTRICT", name="fk_agm_evidence_company_document",
        ),
        Index("uq_agm_evidence_pending_kind", "agm_id", "evidence_kind", unique=True, postgresql_where=text("status = 'PENDING'")),
        Index("uq_agm_evidence_verified_kind", "agm_id", "evidence_kind", unique=True, postgresql_where=text("status = 'VERIFIED'")),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    agm_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    meeting_date: Mapped[date] = mapped_column(Date, nullable=False)
    evidence_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    source_checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    source_document_version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING", server_default="PENDING")
    submitted_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reviewer_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    revoked_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revocation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class AGMEvidenceVerificationEvent(AuditMixin, Base):
    """Append-only history of AGM evidence submission and review decisions."""

    __tablename__ = "agm_evidence_verification_events"
    __table_args__ = (
        CheckConstraint("action IN ('SUBMITTED', 'VERIFIED', 'REJECTED', 'REVOKED', 'SUPERSEDED')", name="ck_agm_evidence_event_action"),
        ForeignKeyConstraint(
            ["company_id", "verification_id"],
            ["agm_evidence_verifications.company_id", "agm_evidence_verifications.id"],
            ondelete="RESTRICT", name="fk_agm_evidence_events_company_parent",
        ),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    verification_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    actor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    previous_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    new_status: Mapped[str] = mapped_column(String(20), nullable=False)
    source_checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

