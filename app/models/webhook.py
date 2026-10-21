"""
app/models/webhook.py — Webhook endpoint and delivery models.

Enterprise customers register webhook URLs to receive real-time
compliance event notifications (score changes, new flags, rescue plans).
"""
from __future__ import annotations

import uuid
from datetime import datetime, UTC
from typing import TYPE_CHECKING

from sqlalchemy import String, Integer, Boolean, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .mixins import TimestampMixin, UUIDPrimaryKeyMixin
from .base import Base

if TYPE_CHECKING:
    from .user import User


# Event type constants — subscribe to these in webhook endpoints
class WebhookEvent:
    COMPLIANCE_EVALUATED = "compliance.evaluated"
    FLAG_CREATED_BLACK = "compliance.flag.created.black"
    FLAG_CREATED_RED = "compliance.flag.created.red"
    FLAG_RESOLVED = "compliance.flag.resolved"
    RESCUE_PLAN_CREATED = "rescue.plan.created"
    RESCUE_STEP_COMPLETED = "rescue.step.completed"
    DEADLINE_APPROACHING_7D = "deadline.approaching.7d"
    DEADLINE_APPROACHING_3D = "deadline.approaching.3d"
    DEADLINE_APPROACHING_1D = "deadline.approaching.1d"
    DOCUMENT_APPROVED = "document.approved"
    DOCUMENT_RELEASED = "document.released"
    SUBSCRIPTION_EXPIRED = "subscription.expired"

    ALL_EVENTS = [
        COMPLIANCE_EVALUATED, FLAG_CREATED_BLACK, FLAG_CREATED_RED,
        FLAG_RESOLVED, RESCUE_PLAN_CREATED, RESCUE_STEP_COMPLETED,
        DEADLINE_APPROACHING_7D, DEADLINE_APPROACHING_3D, DEADLINE_APPROACHING_1D,
        DOCUMENT_APPROVED, DOCUMENT_RELEASED, SUBSCRIPTION_EXPIRED,
    ]


class DeliveryStatus:
    PENDING = "PENDING"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"


class WebhookEndpoint(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A customer-configured webhook URL that receives event notifications."""
    __tablename__ = "webhook_endpoints"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    secret: Mapped[str] = mapped_column(
        String(128), nullable=False,
        comment="HMAC-SHA256 signing secret. Auto-generated on creation."
    )
    events: Mapped[list[str]] = mapped_column(
        ARRAY(String(50)), nullable=False, default=list,
        comment="Event types this endpoint subscribes to. Empty = all events."
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    last_delivery_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    last_response_code: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="webhook_endpoints")
    deliveries: Mapped[list["WebhookDelivery"]] = relationship(
        "WebhookDelivery", back_populates="endpoint", lazy="selectin",
        order_by="WebhookDelivery.created_at.desc()"
    )

    def __repr__(self) -> str:
        return f"<WebhookEndpoint url={self.url[:50]}... active={self.is_active}>"


class WebhookDelivery(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A single webhook delivery attempt (or scheduled retry)."""
    __tablename__ = "webhook_deliveries"

    endpoint_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("webhook_endpoints.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=DeliveryStatus.PENDING, server_default="PENDING"
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, server_default="3")
    response_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    next_retry_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    endpoint: Mapped["WebhookEndpoint"] = relationship("WebhookEndpoint", back_populates="deliveries")

    def __repr__(self) -> str:
        return f"<WebhookDelivery event={self.event_type} status={self.status} attempts={self.attempts}>"
