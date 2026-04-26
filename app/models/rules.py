"""
NEUM LEX COUNSEL — ORM LAYER
rules.py — LegalRule, LegalRuleVersion models
AI Constitution Article 1: ONLY Super Admin may modify rules.
Every change logged with change_reason + author + timestamp.
Previous version stored before any update.
Rule engine reads from legal_rules — AI cannot write to it.
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
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base
from .enums import RevenueTier, RuleType, SeverityLevel
from .mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    import uuid
    from datetime import date, datetime


class LegalRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    The 30 ILRMF rules — version-controlled master table.
    AI CANNOT modify, override, or bypass any row in this table.
    Modifications require Super Admin approval + change_reason.
    """
    __tablename__ = "legal_rules"

    # ── Identity ──────────────────────────────────────────────────
    rule_id: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False,
        comment="e.g. AGM-001, AUD-003, TR-005 — immutable identifier"
    )
    rule_name: Mapped[str] = mapped_column(String(500), nullable=False)
    rule_type: Mapped[RuleType] = mapped_column(
        Enum(RuleType, name="rule_type"), nullable=False, index=True
    )

    # ── Legal Basis ───────────────────────────────────────────────
    statutory_basis: Mapped[str] = mapped_column(
        String(1000), nullable=False,
        comment="e.g. Section 81, Companies Act 1994 (Bangladesh)"
    )
    statutory_effective_date: Mapped[date | None] = mapped_column(
        Date, nullable=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # ── Rule Logic ────────────────────────────────────────────────
    # Stored for reference only — actual logic is in Python rule engine
    rule_condition: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment="Reference-only condition definition (not executed by DB)"
    )

    # ── Scoring ───────────────────────────────────────────────────
    default_severity: Mapped[SeverityLevel] = mapped_column(
        Enum(SeverityLevel, name="severity_level"), nullable=False
    )
    score_impact: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
        comment="Maximum score deduction (graduated in engine)"
    )
    revenue_tier: Mapped[RevenueTier] = mapped_column(
        Enum(RevenueTier, name="revenue_tier"), nullable=False
    )
    is_black_override: Mapped[bool] = mapped_column(
        Boolean, default=False,
        comment="TRUE for AUD-003, TR-005, ESC-002, ESC-003"
    )

    # ── Version Control ───────────────────────────────────────────
    rule_version: Mapped[str] = mapped_column(
        String(20), nullable=False, default="1.0",
        comment="Increment on every change. Engine records this version per flag."
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    # ── Governance ────────────────────────────────────────────────
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    last_modified_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    last_modified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Relationships ─────────────────────────────────────────────
    versions: Mapped[list[LegalRuleVersion]] = relationship(
        "LegalRuleVersion", back_populates="rule",
        order_by="LegalRuleVersion.changed_at.desc()",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<LegalRule {self.rule_id} v{self.rule_version} [{self.default_severity}]>"


class LegalRuleVersion(UUIDPrimaryKeyMixin, Base):
    """
    Immutable audit trail of every rule change.
    Previous version stored in full before update.
    AI Constitution Article 1: Every rule modification logged.
    Append-only — no UPDATE or DELETE.
    """
    __tablename__ = "legal_rule_versions"

    rule_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("legal_rules.rule_id"),
        nullable=False, index=True
    )
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    change_reason: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="Mandatory: why was this rule changed?"
    )
    changed_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    previous_definition: Mapped[dict] = mapped_column(
        JSONB, nullable=False,
        comment="Full snapshot of rule before this change"
    )
    sro_reference: Mapped[str | None] = mapped_column(
        String(255), nullable=True,
        comment="RJSC SRO/circular that triggered this change"
    )

    # ── Relationships ─────────────────────────────────────────────
    rule: Mapped[LegalRule] = relationship(
        "LegalRule", back_populates="versions"
    )

    def __repr__(self) -> str:
        return f"<LegalRuleVersion {self.rule_id} v{self.version} @ {self.changed_at}>"
