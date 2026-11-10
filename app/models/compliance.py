"""
NEUM LEX COUNSEL — ORM LAYER
compliance.py — ComplianceFlag, ComplianceScoreHistory, ComplianceEvent
These are the primary OUTPUT of the rule engine evaluation.
Every flag maps to an ILRMF rule. Score history is tamper-evident.
AI Constitution Article 4: Score formula fixed. History immutable.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base
from .enums import (
    EventAction,
    ExposureBand,
    FlagStatus,
    RevenueTier,
    RiskBand,
    SeverityLevel,
)
from .mixins import AuditMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    import uuid
    from datetime import date, datetime

    from .company import Company


# ═══════════════════════════════════════════════════════════════════
# COMPLIANCE FLAG
# ═══════════════════════════════════════════════════════════════════
class ComplianceFlag(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    One row per triggered rule per company per evaluation.
    Every flag must include: rule_id, statutory_basis, score_impact,
    severity, revenue_tier, rule_version, detail (explainability).
    AI Constitution Article 2.3 — Explainability mandate.
    """
    __tablename__ = "compliance_flags"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    # ── Rule Reference ────────────────────────────────────────────
    rule_id: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True,
        comment="e.g. AGM-001, AUD-003, TR-005"
    )
    rule_version: Mapped[str] = mapped_column(
        String(20), nullable=False,
        comment="Rule version at time of evaluation — legal defensibility"
    )
    flag_code: Mapped[str] = mapped_column(String(100), nullable=False)
    statutory_basis: Mapped[str] = mapped_column(
        String(500), nullable=False,
        comment="e.g. Section 81, Companies Act 1994"
    )

    # ── Assessment ────────────────────────────────────────────────
    severity: Mapped[SeverityLevel] = mapped_column(
        Enum(SeverityLevel, name="severity_level"), nullable=False, index=True
    )
    score_impact: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="Negative points deducted from base 100"
    )
    exposure_band: Mapped[ExposureBand | None] = mapped_column(
        Enum(ExposureBand, name="exposure_band"), nullable=True
    )
    revenue_tier: Mapped[RevenueTier] = mapped_column(
        Enum(RevenueTier, name="revenue_tier"), nullable=False
    )

    # ── Status ────────────────────────────────────────────────────
    # Mirrors the rule engine's evaluation classification. This is distinct
    # from legal score release and must never be inferred from severity.
    evaluation_state: Mapped[str] = mapped_column(String(32), nullable=False)
    flag_status: Mapped[FlagStatus] = mapped_column(
        Enum(FlagStatus, name="flag_status"),
        default=FlagStatus.ACTIVE,
        nullable=False,
    )
    # Links preserved duplicate records to the canonical active flag.
    # DUPLICATE is an administrative record state, not legal resolution.
    duplicate_of_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("compliance_flags.id", ondelete="RESTRICT"),
        nullable=True,
    )
    triggered_date: Mapped[date] = mapped_column(Date, nullable=False)
    resolved_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Explainability (AI Constitution 2.3) ─────────────────────
    description: Mapped[str] = mapped_column(Text, nullable=False)
    detail: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment="Structured explanation: delay_days, calculation_basis, etc."
    )
    fact_provenance_snapshot: Mapped[list[dict]] = mapped_column(
        JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"),
        comment="Immutable source/trust/verification snapshot for every fact used by this finding; [] means legacy or no facts attached."
    )

    # ── Notification ─────────────────────────────────────────────
    notification_sent: Mapped[bool] = mapped_column(Boolean, default=False)

    # ── Relationships ─────────────────────────────────────────────
    company: Mapped[Company] = relationship(
        "Company", back_populates="compliance_flags"
    )

    def __repr__(self) -> str:
        return f"<ComplianceFlag {self.rule_id} [{self.severity}] company={self.company_id}>"


# ═══════════════════════════════════════════════════════════════════
# COMPLIANCE SCORE HISTORY
# ═══════════════════════════════════════════════════════════════════
class ComplianceScoreHistory(UUIDPrimaryKeyMixin, Base):
    """
    Monthly immutable score snapshots. Append-only — no updates.
    Tamper-evident: SHA-256 hash of company_id + score + band + date + version.
    AI Constitution Article 4: Score history preserved. Never overwritten.
    """
    __tablename__ = "compliance_score_history"

    __table_args__ = (
        UniqueConstraint("company_id", "snapshot_month", name="uq_score_snapshot_month"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Score ─────────────────────────────────────────────────────
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    risk_band: Mapped[RiskBand] = mapped_column(
        Enum(RiskBand, name="risk_band"), nullable=False
    )
    snapshot_month: Mapped[date] = mapped_column(
        Date, nullable=False,
        comment="First day of month — monthly snapshot"
    )
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    # ── Component Scores ──────────────────────────────────────────
    agm_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    audit_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    return_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    director_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    shareholding_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── Flags Summary ─────────────────────────────────────────────
    active_flags_count: Mapped[int] = mapped_column(Integer, default=0)
    black_flags_count: Mapped[int] = mapped_column(Integer, default=0)
    override_applied: Mapped[bool] = mapped_column(Boolean, default=False)

    # ── Tamper-Evidence ───────────────────────────────────────────
    score_hash: Mapped[str] = mapped_column(
        String(64), nullable=False,
        comment="SHA256(company_id+score+band+date+engine_version)"
    )
    engine_version: Mapped[str] = mapped_column(String(20), nullable=False)

    # ── Trigger ───────────────────────────────────────────────────
    evaluation_status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="COMPLETED",
        comment="PENDING | IN_PROGRESS | COMPLETED | NOT_RELEASED | FAILED (OPS-004)"
    )

    trigger_source: Mapped[str] = mapped_column(
        String(100), default="CRON",
        comment="CRON | API_REQUEST | RESCUE_STEP_COMPLETE | MANUAL"
    )

    # ── Relationships ─────────────────────────────────────────────
    company: Mapped[Company] = relationship(
        "Company", back_populates="score_history"
    )

    def __repr__(self) -> str:
        return (
            f"<ScoreHistory company={self.company_id} "
            f"month={self.snapshot_month} score={self.score} [{self.risk_band}]>"
        )


# ═══════════════════════════════════════════════════════════════════
# PER-EVALUATION IMMUTABLE SNAPSHOT
# ═══════════════════════════════════════════════════════════════════
class ComplianceEvaluationRun(UUIDPrimaryKeyMixin, Base):
    """
    Immutable record for every evaluation run.

    Monthly ComplianceScoreHistory remains a monthly trend snapshot. This
    table is the authoritative per-run record used to bind current company
    state and generated PDFs to the exact evaluation that produced them.
    """
    __tablename__ = "compliance_evaluation_runs"
    __table_args__ = (
        UniqueConstraint("company_id", "calculated_at", name="uq_eval_run_company_time"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    risk_band: Mapped[RiskBand] = mapped_column(
        Enum(RiskBand, name="risk_band"), nullable=False
    )
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    engine_version: Mapped[str] = mapped_column(String(50), nullable=False)
    score_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    previous_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    evaluation_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="COMPLETED", server_default="COMPLETED"
    )
    trigger_source: Mapped[str] = mapped_column(
        String(100), nullable=False, default="MANUAL", server_default="MANUAL"
    )
    active_flags_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    black_flags_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    flags_snapshot: Mapped[list[dict]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    fact_provenance_snapshot: Mapped[list[dict]] = mapped_column(
        JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"),
        comment="Immutable union of fact provenance used during this evaluation run."
    )
    score_breakdown_snapshot: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )

    company: Mapped["Company"] = relationship(
        "Company", back_populates="evaluation_runs"
    )


# ═══════════════════════════════════════════════════════════════════
# COMPLIANCE EVENT (audit trail of all compliance activities)
# ═══════════════════════════════════════════════════════════════════
class ComplianceEvent(AuditMixin, Base):
    """
    Append-only log of every compliance event per company.
    AI Constitution Article 6: 7-year retention mandatory.
    No UPDATE or DELETE on this table.
    """
    __tablename__ = "compliance_events"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    event_type: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True,
        comment="AGM_HELD | RETURN_FILED | AUDIT_COMPLETE | DIRECTOR_ADDED | etc."
    )
    event_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[EventAction] = mapped_column(
        Enum(EventAction, name="event_action"), nullable=False
    )
    performed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    reference_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
        comment="ID of related record (agm.id, audit.id, etc.)"
    )
    detail: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # ── Relationships ─────────────────────────────────────────────
    company: Mapped[Company] = relationship("Company")

    def __repr__(self) -> str:
        return f"<ComplianceEvent {self.event_type} company={self.company_id} date={self.event_date}>"
