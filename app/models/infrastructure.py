"""
NEUM LEX COUNSEL — ORM LAYER
infrastructure.py — Notification, SRORegistry, StatutoryRegister,
                    RegisteredOfficeHistory, UserActivityLog models
AI Constitution Article 6: Activity logs append-only, 7-year retention.
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
from .enums import (
    NotificationChannel,
    NotificationStatus,
    SroType,
)
from .mixins import AuditMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    import uuid
    from datetime import date, datetime


# ═══════════════════════════════════════════════════════════════════
# NOTIFICATION
# ═══════════════════════════════════════════════════════════════════
class Notification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "notifications"

    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # ── Content ───────────────────────────────────────────────────
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    notification_type: Mapped[str] = mapped_column(
        String(100), nullable=False,
        comment="AGM_DEADLINE | RETURN_DEADLINE | SCORE_DEGRADED | RESCUE_REQUIRED | etc."
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel, name="notification_channel"), nullable=False
    )
    notification_status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus, name="notification_status"),
        default=NotificationStatus.PENDING,
        nullable=False,
        index=True,
    )

    # ── Timing ────────────────────────────────────────────────────
    scheduled_for: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Reference ─────────────────────────────────────────────────
    days_until_deadline: Mapped[int | None] = mapped_column(Integer, nullable=True)
    related_flag_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)

    def __repr__(self) -> str:
        return f"<Notification {self.notification_type} [{self.notification_status}]>"


# ═══════════════════════════════════════════════════════════════════
# SRO REGISTRY
# ═══════════════════════════════════════════════════════════════════
class SRORegistry(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    RJSC Statutory Regulatory Orders and circulars.
    Mapped to affected ILRMF rule IDs.
    AI Constitution Article 1: SRO triggers rule review by Super Admin.
    """
    __tablename__ = "sro_registry"

    sro_number: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False
    )
    sro_type: Mapped[SroType] = mapped_column(
        Enum(SroType, name="sro_type"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(1000), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    gazette_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # ── Impact ────────────────────────────────────────────────────
    affected_rule_ids: Mapped[list | None] = mapped_column(
        JSONB, nullable=True,
        comment="Array of ILRMF rule_ids affected by this SRO"
    )
    rule_update_required: Mapped[bool] = mapped_column(Boolean, default=False)
    rule_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rule_updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    # ── Source ────────────────────────────────────────────────────
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    entered_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    verified_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    def __repr__(self) -> str:
        return f"<SRORegistry {self.sro_number} — {self.title[:50]}>"


# ═══════════════════════════════════════════════════════════════════
# STATUTORY REGISTER
# ═══════════════════════════════════════════════════════════════════
class StatutoryRegister(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    REG-001: Tracks which statutory registers a company maintains.
    Companies Act 1994 requires 6 registers for private companies.
    """
    __tablename__ = "statutory_registers"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    register_type: Mapped[str] = mapped_column(
        String(100), nullable=False,
        comment="register_of_members | register_of_directors | etc."
    )
    is_maintained: Mapped[bool] = mapped_column(Boolean, default=False)
    last_updated_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    location: Mapped[str | None] = mapped_column(
        String(500), nullable=True,
        comment="Physical or digital location of register"
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Relationships ─────────────────────────────────────────────
    company = relationship("Company", back_populates="statutory_registers")

    def __repr__(self) -> str:
        return (
            f"<StatutoryRegister {self.register_type} "
            f"maintained={self.is_maintained}>"
        )


# ═══════════════════════════════════════════════════════════════════
# REGISTERED OFFICE HISTORY
# ═══════════════════════════════════════════════════════════════════
class RegisteredOfficeHistory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    OFF-001: Every change to registered office address must be filed
    with RJSC within 30 days.
    """
    __tablename__ = "registered_office_history"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    address: Mapped[str] = mapped_column(Text, nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    change_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # ── Filing ────────────────────────────────────────────────────
    # OFF-001: change not filed within 30 days
    filed_with_rjsc: Mapped[bool] = mapped_column(Boolean, default=False)
    rjsc_filing_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    filing_delay_days: Mapped[int] = mapped_column(Integer, default=0)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)

    # ── Relationships ─────────────────────────────────────────────
    company = relationship("Company", back_populates="office_history")

    def __repr__(self) -> str:
        return f"<RegisteredOfficeHistory company={self.company_id} current={self.is_current}>"


# ═══════════════════════════════════════════════════════════════════
# USER ACTIVITY LOG
# ═══════════════════════════════════════════════════════════════════
class UserActivityLog(AuditMixin, Base):
    """
    Append-only master activity log.
    AI Constitution Article 6: 7-year retention. No UPDATE/DELETE.
    Every meaningful action in the system is logged here.
    DB permissions: INSERT only on this table (no UPDATE/DELETE).
    """
    __tablename__ = "user_activity_logs"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id"),
        nullable=True,
        index=True,
    )

    # ── Action ────────────────────────────────────────────────────
    action: Mapped[str] = mapped_column(
        String(200), nullable=False, index=True,
        comment="e.g. LOGIN | COMPANY_VIEW | SCORE_EVAL | RULE_MODIFIED | etc."
    )
    resource_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Context ───────────────────────────────────────────────────
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True,
        comment="UUID correlation ID from API request"
    )
    detail: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # ── Timestamp ─────────────────────────────────────────────────
    logged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    # ── Relationships ─────────────────────────────────────────────
    user = relationship("User", back_populates="activity_logs", lazy="noload")

    def __repr__(self) -> str:
        return (
            f"<UserActivityLog {self.action} "
            f"user={self.user_id} @ {self.logged_at}>"
        )
