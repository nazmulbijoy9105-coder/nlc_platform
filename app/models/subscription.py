"""Subscription plan catalogue, entitlement snapshots and immutable audit events."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    DateTime,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base
from .mixins import TimestampMixin, UUIDPrimaryKeyMixin


class SubscriptionPlan(TimestampMixin, Base):
    __tablename__ = "subscription_plans"
    __table_args__ = (
        CheckConstraint("length(plan_code) BETWEEN 2 AND 60", name="ck_subscription_plan_code_length"),
        CheckConstraint("length(plan_name) BETWEEN 2 AND 120", name="ck_subscription_plan_name_length"),
        CheckConstraint("grace_days BETWEEN 0 AND 30", name="ck_subscription_plan_grace_days"),
    )

    plan_code: Mapped[str] = mapped_column(String(60), primary_key=True)
    plan_name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    grace_days: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    updated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))


class SubscriptionPlanPrice(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "subscription_plan_prices"
    __table_args__ = (
        UniqueConstraint("plan_code", "billing_interval", name="uq_subscription_plan_price_interval"),
        CheckConstraint("billing_interval IN ('MONTHLY','QUARTERLY','ANNUAL','ONE_TIME')", name="ck_subscription_plan_price_interval"),
        CheckConstraint("amount_bdt > 0", name="ck_subscription_plan_price_amount"),
        CheckConstraint("tax_bdt >= 0", name="ck_subscription_plan_price_tax"),
        CheckConstraint("length(trim(tax_policy_reference)) BETWEEN 3 AND 500", name="ck_subscription_plan_price_tax_reference"),
        CheckConstraint("currency = 'BDT'", name="ck_subscription_plan_price_currency"),
        Index("ix_subscription_plan_prices_active", "plan_code", "is_active"),
    )

    plan_code: Mapped[str] = mapped_column(String(60), ForeignKey("subscription_plans.plan_code", ondelete="RESTRICT"), nullable=False)
    billing_interval: Mapped[str] = mapped_column(String(16), nullable=False)
    amount_bdt: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    tax_bdt: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    tax_policy_reference: Mapped[str] = mapped_column(Text, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="BDT", server_default="BDT")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))


class SubscriptionPlanFeature(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "subscription_plan_features"
    __table_args__ = (
        UniqueConstraint("plan_code", "feature_code", name="uq_subscription_plan_feature"),
        CheckConstraint("length(feature_code) BETWEEN 2 AND 80", name="ck_subscription_feature_code_length"),
        CheckConstraint("feature_code IN ('compliance_package','document_management','corporate_rescue')", name="ck_subscription_plan_feature_supported"),
    )

    plan_code: Mapped[str] = mapped_column(String(60), ForeignKey("subscription_plans.plan_code", ondelete="RESTRICT"), nullable=False)
    feature_code: Mapped[str] = mapped_column(String(80), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))


class ClientSubscriptionFeature(UUIDPrimaryKeyMixin, Base):
    """Immutable feature snapshot granted when a subscription request is created."""

    __tablename__ = "client_subscription_features"
    __table_args__ = (
        UniqueConstraint("subscription_id", "feature_code", name="uq_client_subscription_feature"),
        ForeignKeyConstraint(
            ["subscription_id", "company_id"],
            ["client_subscriptions.id", "client_subscriptions.company_id"],
            ondelete="RESTRICT",
            name="fk_client_subscription_features_subscription_company",
        ),
        CheckConstraint("length(feature_code) BETWEEN 2 AND 80", name="ck_client_subscription_feature_code_length"),
        CheckConstraint("feature_code IN ('compliance_package','document_management','corporate_rescue')", name="ck_client_subscription_feature_supported"),
        Index("ix_client_subscription_features_lookup", "company_id", "subscription_id", "feature_code"),
    )

    subscription_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    feature_code: Mapped[str] = mapped_column(String(80), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))


class SubscriptionEvent(UUIDPrimaryKeyMixin, Base):
    """Append-only subscription lifecycle evidence."""

    __tablename__ = "subscription_events"
    __table_args__ = (
        ForeignKeyConstraint(
            ["subscription_id", "company_id"],
            ["client_subscriptions.id", "client_subscriptions.company_id"],
            ondelete="RESTRICT",
            name="fk_subscription_events_subscription_company",
        ),
        ForeignKeyConstraint(
            ["invoice_id", "company_id"],
            ["invoices.id", "invoices.company_id"],
            ondelete="RESTRICT",
            name="fk_subscription_events_invoice_company",
        ),
        ForeignKeyConstraint(
            ["payment_id", "company_id"],
            ["payments.id", "payments.company_id"],
            ondelete="RESTRICT",
            name="fk_subscription_events_payment_company",
        ),
        CheckConstraint(
            "event_type IN ('REQUESTED','INVOICE_ISSUED','ACTIVATED','RENEWED','CANCEL_AT_PERIOD_END','CANCELLED','SUSPENDED','RESUMED','EXPIRED','PAST_DUE')",
            name="ck_subscription_event_type",
        ),
        Index("ix_subscription_events_company_created", "company_id", "created_at"),
    )

    subscription_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    payment_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    event_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
