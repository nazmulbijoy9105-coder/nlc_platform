"""
NEUM LEX COUNSEL — ORM LAYER
mixins.py — Reusable column mixins applied across all 28 models.
Every model in the system uses UUIDs, created_at, updated_at.
Soft-delete pattern (is_active) applied where schema mandates.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class UUIDPrimaryKeyMixin:
    """UUID primary key — no sequential integers exposed in API."""
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
        default=uuid.uuid4,
    )


class TimestampMixin:
    """created_at / updated_at on every table. Auto-maintained by triggers."""
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """is_active soft-delete pattern. Never hard-delete records."""
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=text("TRUE"),
        nullable=False,
    )


class FullMixin(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Convenience: UUID PK + timestamps + soft-delete."""
    pass


class AuditMixin(UUIDPrimaryKeyMixin, TimestampMixin):
    """For append-only audit tables: UUID PK + timestamps, NO soft-delete."""
    pass
