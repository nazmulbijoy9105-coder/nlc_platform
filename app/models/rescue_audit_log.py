"""NEUM LEX COUNSEL — rescue_audit_log.py — RescueAuditLog model.

RES-017: rescue audit trail. Records every action taken on a rescue plan:
finding_id, rule_id, rule_version, action_performed, actor_user_id,
evidence_ref, outcome, notes. Required for audit reproducibility.
"""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base
from .mixins import TimestampMixin, UUIDPrimaryKeyMixin


class RescueAuditLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Records every action taken on a rescue plan (RES-017)."""

    __tablename__ = "rescue_audit_log"
    __table_args__ = (
        Index("ix_rescue_audit_log_plan_id", "rescue_plan_id"),
        Index("ix_rescue_audit_log_actor_id", "actor_user_id"),
        Index("ix_rescue_audit_log_finding_id", "finding_id"),
        Index("ix_rescue_audit_log_created_at", "created_at"),
    )

    rescue_plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rescue_plans.id", ondelete="CASCADE"), nullable=False)
    finding_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("compliance_flags.id", ondelete="SET NULL"), nullable=True)
    rule_id: Mapped[str] = mapped_column(String(50), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(20), nullable=False)
    action_performed: Mapped[str] = mapped_column(String(200), nullable=False)
    actor_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    evidence_ref: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    outcome: Mapped[str] = mapped_column(String(50), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<RescueAuditLog plan={self.rescue_plan_id} rule={self.rule_id} action={self.action_performed} outcome={self.outcome}>"
