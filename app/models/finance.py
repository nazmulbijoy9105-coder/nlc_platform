"""Commercial billing, payment and subscription persistence models.

Money is stored as exact NUMERIC(15,2) BDT values. Financial events are
append-only; corrections are represented by reversal/adjustment events.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base
from .mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Invoice(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint("invoice_number", name="uq_invoices_invoice_number"),
        UniqueConstraint("id", "company_id", name="uq_invoices_id_company"),
        ForeignKeyConstraint(["engagement_id", "company_id"], ["engagements.id", "engagements.company_id"], ondelete="RESTRICT", name="fk_invoices_engagement_company"),
        CheckConstraint("subtotal_bdt >= 0 AND tax_bdt >= 0 AND total_bdt >= 0", name="ck_invoice_amounts_nonnegative"),
        CheckConstraint("paid_bdt >= 0 AND balance_bdt >= 0", name="ck_invoice_balances_nonnegative"),
        CheckConstraint("paid_bdt <= total_bdt", name="ck_invoice_paid_not_over_total"),
        CheckConstraint("total_bdt = subtotal_bdt + tax_bdt", name="ck_invoice_total_matches_components"),
        CheckConstraint("balance_bdt = total_bdt - paid_bdt", name="ck_invoice_balance_matches_paid"),
        CheckConstraint("status IN ('DRAFT','ISSUED','PARTIALLY_PAID','PAID','VOID','OVERDUE')", name="ck_invoice_status"),
        CheckConstraint("currency = 'BDT'", name="ck_invoice_currency_bdt"),
        Index("ix_invoices_company_status", "company_id", "status"),
        Index("ix_invoices_company_due", "company_id", "due_at"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    engagement_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    invoice_number: Mapped[str] = mapped_column(String(40), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="BDT")
    subtotal_bdt: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    tax_bdt: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0.00"), server_default="0")
    total_bdt: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    paid_bdt: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0.00"))
    balance_bdt: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="DRAFT")
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    lines: Mapped[list[InvoiceLine]] = relationship("InvoiceLine", back_populates="invoice", lazy="selectin")


class InvoiceLine(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "invoice_lines"
    __table_args__ = (
        CheckConstraint("quantity > 0 AND unit_price_bdt >= 0 AND line_total_bdt >= 0", name="ck_invoice_line_amounts"),
        Index("ix_invoice_lines_company_invoice", "company_id", "invoice_id"),
        ForeignKeyConstraint(["invoice_id", "company_id"], ["invoices.id", "invoices.company_id"], ondelete="RESTRICT", name="fk_invoice_lines_invoice_company"),
    )

    invoice_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("1.00"))
    unit_price_bdt: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    line_total_bdt: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    invoice: Mapped[Invoice] = relationship("Invoice", back_populates="lines")


class PaymentSubmission(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "payment_submissions"
    __table_args__ = (
        UniqueConstraint("id", "company_id", name="uq_payment_submissions_id_company"),
        CheckConstraint("amount_bdt > 0", name="ck_payment_submission_amount_positive"),
        CheckConstraint("method IN ('BANK_TRANSFER','CASH','CHEQUE','BKASH_MANUAL','NAGAD_MANUAL')", name="ck_payment_submission_method"),
        CheckConstraint("method NOT IN ('BANK_TRANSFER','CHEQUE','BKASH_MANUAL','NAGAD_MANUAL') OR NULLIF(BTRIM(payer_reference), '') IS NOT NULL", name="ck_payment_submission_reference_required"),
        CheckConstraint("status IN ('PENDING_REVIEW','APPROVED','REJECTED')", name="ck_payment_submission_status"),
        CheckConstraint("currency = 'BDT'", name="ck_payment_submission_currency_bdt"),
        Index("ix_payment_submissions_company_status", "company_id", "status"),
        Index("ix_payment_submissions_invoice", "invoice_id"),
        Index(
            "uq_payment_submission_manual_reference",
            "method",
            text("lower(btrim(payer_reference))"),
            unique=True,
            postgresql_where=text(
                "payer_reference IS NOT NULL AND method IN ('BANK_TRANSFER','CHEQUE','BKASH_MANUAL','NAGAD_MANUAL')"
            ),
        ),
        ForeignKeyConstraint(["invoice_id", "company_id"], ["invoices.id", "invoices.company_id"], ondelete="RESTRICT", name="fk_payment_submissions_invoice_company"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    invoice_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    submitted_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    method: Mapped[str] = mapped_column(String(32), nullable=False)
    amount_bdt: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="BDT")
    payer_reference: Mapped[str | None] = mapped_column(String(160), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    evidence_document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="PENDING_REVIEW")
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    cheque_cleared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Payment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "payments"
    __table_args__ = (
        UniqueConstraint("payment_number", name="uq_payments_payment_number"),
        UniqueConstraint("provider_transaction_id", name="uq_payments_provider_transaction_id"),
        UniqueConstraint("id", "company_id", name="uq_payments_id_company"),
        ForeignKeyConstraint(
            ["source_submission_id", "company_id"],
            ["payment_submissions.id", "payment_submissions.company_id"],
            ondelete="RESTRICT",
            name="fk_payments_source_submission_company",
        ),
        Index(
            "uq_payments_source_submission",
            "source_submission_id",
            unique=True,
            postgresql_where=text("source_submission_id IS NOT NULL"),
        ),
        CheckConstraint("amount_bdt > 0", name="ck_payment_amount_positive"),
        CheckConstraint("method IN ('BANK_TRANSFER','CASH','CHEQUE','SSLCOMMERZ','BKASH_MANUAL','NAGAD_MANUAL')", name="ck_payment_method"),
        CheckConstraint("method NOT IN ('BANK_TRANSFER','CHEQUE','BKASH_MANUAL','NAGAD_MANUAL') OR NULLIF(BTRIM(payer_reference), '') IS NOT NULL", name="ck_payment_reference_required"),
        CheckConstraint("channel IN ('ONLINE','OFFLINE')", name="ck_payment_channel"),
        CheckConstraint("status IN ('SETTLED','REVERSED','REFUNDED','DISPUTED')", name="ck_payment_status"),
        CheckConstraint("currency = 'BDT'", name="ck_payment_currency_bdt"),
        Index("ix_payments_company_received", "company_id", "received_at"),
        Index(
            "uq_payment_manual_reference",
            "method",
            text("lower(btrim(payer_reference))"),
            unique=True,
            postgresql_where=text(
                "payer_reference IS NOT NULL AND method IN ('BANK_TRANSFER','CHEQUE','BKASH_MANUAL','NAGAD_MANUAL')"
            ),
        ),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    payment_number: Mapped[str] = mapped_column(String(40), nullable=False)
    method: Mapped[str] = mapped_column(String(32), nullable=False)
    channel: Mapped[str] = mapped_column(String(16), nullable=False, default="OFFLINE")
    amount_bdt: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="BDT")
    provider_name: Mapped[str | None] = mapped_column(String(40), nullable=True)
    provider_transaction_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    payer_reference: Mapped[str | None] = mapped_column(String(160), nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="SETTLED")
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    source_submission_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class PaymentAllocation(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "payment_allocations"
    __table_args__ = (
        UniqueConstraint("payment_id", "invoice_id", name="uq_payment_allocation_payment_invoice"),
        CheckConstraint("amount_bdt > 0", name="ck_payment_allocation_amount_positive"),
        CheckConstraint("currency = 'BDT'", name="ck_payment_allocation_currency_bdt"),
        Index("ix_payment_allocations_company_invoice", "company_id", "invoice_id"),
        ForeignKeyConstraint(["payment_id", "company_id"], ["payments.id", "payments.company_id"], ondelete="RESTRICT", name="fk_payment_allocations_payment_company"),
        ForeignKeyConstraint(["invoice_id", "company_id"], ["invoices.id", "invoices.company_id"], ondelete="RESTRICT", name="fk_payment_allocations_invoice_company"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    payment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    invoice_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    amount_bdt: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="BDT")
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class PaymentLedgerEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "payment_ledger_events"
    __table_args__ = (
        CheckConstraint("amount_bdt > 0", name="ck_payment_ledger_event_amount_positive"),
        CheckConstraint("event_type IN ('PAYMENT_VERIFIED','PAYMENT_ALLOCATED','PAYMENT_REVERSED','PAYMENT_REFUNDED','PAYMENT_DISPUTED','SUBMISSION_REJECTED')", name="ck_payment_ledger_event_type"),
        CheckConstraint("currency = 'BDT'", name="ck_payment_ledger_event_currency_bdt"),
        Index("ix_payment_ledger_events_company_created", "company_id", "created_at"),
        ForeignKeyConstraint(["payment_id", "company_id"], ["payments.id", "payments.company_id"], ondelete="RESTRICT", name="fk_payment_ledger_payment_company"),
        ForeignKeyConstraint(["invoice_id", "company_id"], ["invoices.id", "invoices.company_id"], ondelete="RESTRICT", name="fk_payment_ledger_invoice_company"),
        ForeignKeyConstraint(["submission_id", "company_id"], ["payment_submissions.id", "payment_submissions.company_id"], ondelete="RESTRICT", name="fk_payment_ledger_submission_company"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    payment_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    submission_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    amount_bdt: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="BDT")
    reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    event_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class PaymentIntent(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "payment_intents"
    __table_args__ = (
        UniqueConstraint("provider_name", "idempotency_key", name="uq_payment_intent_provider_idempotency"),
        UniqueConstraint("provider_order_id", name="uq_payment_intent_provider_order"),
        UniqueConstraint("provider_transaction_id", name="uq_payment_intent_provider_transaction"),
        CheckConstraint("amount_bdt > 0", name="ck_payment_intent_amount_positive"),
        CheckConstraint("provider_name IN ('SSLCOMMERZ')", name="ck_payment_intent_provider"),
        CheckConstraint("status IN ('CREATED','PENDING','SUCCEEDED','FAILED','EXPIRED','CANCELLED')", name="ck_payment_intent_status"),
        CheckConstraint("currency = 'BDT'", name="ck_payment_intent_currency_bdt"),
        Index("ix_payment_intents_company_status", "company_id", "status"),
        ForeignKeyConstraint(["invoice_id", "company_id"], ["invoices.id", "invoices.company_id"], ondelete="RESTRICT", name="fk_payment_intents_invoice_company"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    invoice_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(40), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(120), nullable=False)
    provider_order_id: Mapped[str] = mapped_column(String(120), nullable=False)
    amount_bdt: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="BDT")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="CREATED")
    checkout_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider_transaction_id: Mapped[str | None] = mapped_column(String(160), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class PaymentProviderEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "payment_provider_events"
    __table_args__ = (
        UniqueConstraint("provider_name", "provider_event_id", name="uq_payment_provider_event"),
        Index("ix_payment_provider_events_status_received", "processing_status", "received_at"),
        CheckConstraint("processing_status IN ('RECEIVED','PROCESSING','PROCESSED','FAILED')", name="ck_payment_provider_event_status"),
    )

    provider_name: Mapped[str] = mapped_column(String(40), nullable=False)
    provider_event_id: Mapped[str] = mapped_column(String(160), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_redacted: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    processing_status: Mapped[str] = mapped_column(String(24), nullable=False, default="RECEIVED")
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class ClientSubscription(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "client_subscriptions"
    __table_args__ = (
        UniqueConstraint("id", "company_id", name="uq_client_subscriptions_id_company"),
        ForeignKeyConstraint(
            ["invoice_id", "company_id"],
            ["invoices.id", "invoices.company_id"],
            ondelete="RESTRICT",
            name="fk_client_subscriptions_invoice_company",
        ),
        CheckConstraint("amount_bdt >= 0", name="ck_subscription_amount_nonnegative"),
        CheckConstraint("tax_bdt >= 0", name="ck_client_subscription_tax_nonnegative"),
        CheckConstraint("grace_days BETWEEN 0 AND 30", name="ck_client_subscription_grace_days"),
        CheckConstraint("billing_interval IN ('MONTHLY','QUARTERLY','ANNUAL','ONE_TIME')", name="ck_subscription_billing_interval"),
        CheckConstraint("status IN ('PENDING','ACTIVE','PAST_DUE','CANCELLED','EXPIRED','SUSPENDED')", name="ck_subscription_status"),
        CheckConstraint("currency = 'BDT'", name="ck_subscription_currency_bdt"),
        CheckConstraint("grace_days BETWEEN 0 AND 30", name="ck_client_subscription_grace_days"),
        CheckConstraint("tax_bdt >= 0", name="ck_client_subscription_tax_nonnegative"),
        UniqueConstraint("id", "company_id", name="uq_client_subscriptions_id_company"),
        ForeignKeyConstraint(
            ["invoice_id", "company_id"],
            ["invoices.id", "invoices.company_id"],
            ondelete="RESTRICT",
            name="fk_client_subscriptions_invoice_company",
        ),
        Index("ix_client_subscriptions_company_status", "company_id", "status"),
        Index(
            "uq_client_subscriptions_invoice",
            "invoice_id",
            unique=True,
            postgresql_where=text("invoice_id IS NOT NULL"),
        ),
        Index("ix_client_subscriptions_period", "status", "ends_at", "grace_ends_at"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    plan_code: Mapped[str] = mapped_column(String(60), nullable=False)
    plan_name: Mapped[str] = mapped_column(String(120), nullable=False)
    billing_interval: Mapped[str] = mapped_column(String(16), nullable=False)
    amount_bdt: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    tax_bdt: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0.00"), server_default="0")
    tax_policy_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    tax_bdt: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=Decimal("0.00"))
    tax_policy_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    grace_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    grace_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    suspended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    suspension_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    activated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="BDT")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="PENDING")
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    renews_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    auto_renew: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    grace_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    grace_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    suspended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    suspension_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    activated_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
