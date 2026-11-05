"""Create tenant-scoped billing, offline payment and online intent foundations.

Revision ID: 0059_financial_billing_core
Revises: 0058_finance_role_separation
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0059_financial_billing_core"
down_revision = "0058_finance_role_separation"
branch_labels = None
depends_on = None

TABLES = (
    "invoices",
    "invoice_lines",
    "payment_submissions",
    "payments",
    "payment_allocations",
    "payment_ledger_events",
    "payment_intents",
    "payment_provider_events",
    "client_subscriptions",
)


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    money = sa.Numeric(15, 2)

    op.create_unique_constraint("uq_engagements_id_company", "engagements", ["id", "company_id"])

    op.create_table(
        "invoices",
        sa.Column("id", uuid, primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("company_id", uuid, sa.ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("engagement_id", uuid, nullable=True),
        sa.Column("invoice_number", sa.String(40), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="BDT"),
        sa.Column("subtotal_bdt", money, nullable=False),
        sa.Column("tax_bdt", money, nullable=False, server_default="0"),
        sa.Column("total_bdt", money, nullable=False),
        sa.Column("paid_bdt", money, nullable=False, server_default="0"),
        sa.Column("balance_bdt", money, nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="DRAFT"),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("due_at", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", uuid, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("invoice_number", name="uq_invoices_invoice_number"),
        sa.UniqueConstraint("id", "company_id", name="uq_invoices_id_company"),
        sa.ForeignKeyConstraint(["engagement_id", "company_id"], ["engagements.id", "engagements.company_id"], ondelete="RESTRICT", name="fk_invoices_engagement_company"),
        sa.CheckConstraint("subtotal_bdt >= 0 AND tax_bdt >= 0 AND total_bdt >= 0", name="ck_invoice_amounts_nonnegative"),
        sa.CheckConstraint("paid_bdt >= 0 AND balance_bdt >= 0", name="ck_invoice_balances_nonnegative"),
        sa.CheckConstraint("currency = 'BDT'", name="ck_invoice_currency_bdt"),
        sa.CheckConstraint("paid_bdt <= total_bdt", name="ck_invoice_paid_not_over_total"),
        sa.CheckConstraint("total_bdt = subtotal_bdt + tax_bdt", name="ck_invoice_total_matches_components"),
        sa.CheckConstraint("balance_bdt = total_bdt - paid_bdt", name="ck_invoice_balance_matches_paid"),
        sa.CheckConstraint("status IN ('DRAFT','ISSUED','PARTIALLY_PAID','PAID','VOID','OVERDUE')", name="ck_invoice_status"),
    )
    op.create_index("ix_invoices_company_status", "invoices", ["company_id", "status"])
    op.create_index("ix_invoices_company_due", "invoices", ["company_id", "due_at"])

    op.create_table(
        "invoice_lines",
        sa.Column("id", uuid, primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("invoice_id", uuid, nullable=False),
        sa.Column("company_id", uuid, sa.ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 2), nullable=False, server_default="1"),
        sa.Column("unit_price_bdt", money, nullable=False),
        sa.Column("line_total_bdt", money, nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["invoice_id", "company_id"], ["invoices.id", "invoices.company_id"], ondelete="RESTRICT", name="fk_invoice_lines_invoice_company"),
        sa.CheckConstraint("quantity > 0 AND unit_price_bdt >= 0 AND line_total_bdt >= 0", name="ck_invoice_line_amounts"),
    )
    op.create_index("ix_invoice_lines_company_invoice", "invoice_lines", ["company_id", "invoice_id"])

    op.create_table(
        "payment_submissions",
        sa.Column("id", uuid, primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("company_id", uuid, sa.ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("invoice_id", uuid, nullable=False),
        sa.Column("submitted_by", uuid, sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("method", sa.String(32), nullable=False),
        sa.Column("amount_bdt", money, nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="BDT"),
        sa.Column("payer_reference", sa.String(160), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("evidence_document_id", uuid, sa.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(24), nullable=False, server_default="PENDING_REVIEW"),
        sa.Column("reviewed_by", uuid, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("cheque_cleared_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["invoice_id", "company_id"], ["invoices.id", "invoices.company_id"], ondelete="RESTRICT", name="fk_payment_submissions_invoice_company"),
        sa.CheckConstraint("amount_bdt > 0", name="ck_payment_submission_amount_positive"),
        sa.CheckConstraint("currency = 'BDT'", name="ck_payment_submission_currency_bdt"),
        sa.CheckConstraint("method IN ('BANK_TRANSFER','CASH','CHEQUE','BKASH_MANUAL','NAGAD_MANUAL')", name="ck_payment_submission_method"),
        sa.CheckConstraint("status IN ('PENDING_REVIEW','APPROVED','REJECTED')", name="ck_payment_submission_status"),
    )
    op.create_index("ix_payment_submissions_company_status", "payment_submissions", ["company_id", "status"])
    op.create_index("ix_payment_submissions_invoice", "payment_submissions", ["invoice_id"])

    op.create_table(
        "payments",
        sa.Column("id", uuid, primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("company_id", uuid, sa.ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("payment_number", sa.String(40), nullable=False),
        sa.Column("method", sa.String(32), nullable=False),
        sa.Column("channel", sa.String(16), nullable=False, server_default="OFFLINE"),
        sa.Column("amount_bdt", money, nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="BDT"),
        sa.Column("provider_name", sa.String(40), nullable=True),
        sa.Column("provider_transaction_id", sa.String(160), nullable=True),
        sa.Column("payer_reference", sa.String(160), nullable=True),
        sa.Column("status", sa.String(24), nullable=False, server_default="SETTLED"),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_by", uuid, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", uuid, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("payment_number", name="uq_payments_payment_number"),
        sa.UniqueConstraint("id", "company_id", name="uq_payments_id_company"),
        sa.UniqueConstraint("provider_transaction_id", name="uq_payments_provider_transaction_id"),
        sa.CheckConstraint("method IN ('BANK_TRANSFER','CASH','CHEQUE','BKASH_MANUAL','NAGAD_MANUAL','BKASH_ONLINE','NAGAD_ONLINE','SSLCOMMERZ')", name="ck_payment_method"),
        sa.CheckConstraint("channel IN ('ONLINE','OFFLINE')", name="ck_payment_channel"),
        sa.CheckConstraint("status IN ('SETTLED','REVERSED','REFUNDED','DISPUTED')", name="ck_payment_status"),
        sa.CheckConstraint("amount_bdt > 0", name="ck_payment_amount_positive"),
        sa.CheckConstraint("currency = 'BDT'", name="ck_payment_currency_bdt"),
    )
    op.create_index("ix_payments_company_received", "payments", ["company_id", "received_at"])

    op.create_table(
        "payment_allocations",
        sa.Column("id", uuid, primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("company_id", uuid, sa.ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("payment_id", uuid, nullable=False),
        sa.Column("invoice_id", uuid, nullable=False),
        sa.Column("amount_bdt", money, nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="BDT"),
        sa.Column("created_by", uuid, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.UniqueConstraint("payment_id", "invoice_id", name="uq_payment_allocation_payment_invoice"),
        sa.ForeignKeyConstraint(["payment_id", "company_id"], ["payments.id", "payments.company_id"], ondelete="RESTRICT", name="fk_payment_allocations_payment_company"),
        sa.ForeignKeyConstraint(["invoice_id", "company_id"], ["invoices.id", "invoices.company_id"], ondelete="RESTRICT", name="fk_payment_allocations_invoice_company"),
        sa.CheckConstraint("amount_bdt > 0", name="ck_payment_allocation_amount_positive"),
        sa.CheckConstraint("currency = 'BDT'", name="ck_payment_allocation_currency_bdt"),
    )
    op.create_index("ix_payment_allocations_company_invoice", "payment_allocations", ["company_id", "invoice_id"])

    op.create_table(
        "payment_ledger_events",
        sa.Column("id", uuid, primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("company_id", uuid, sa.ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("payment_id", uuid, nullable=True),
        sa.Column("invoice_id", uuid, nullable=True),
        sa.Column("submission_id", uuid, nullable=True),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("amount_bdt", money, nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="BDT"),
        sa.Column("reference", sa.String(200), nullable=True),
        sa.Column("actor_id", uuid, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["payment_id", "company_id"], ["payments.id", "payments.company_id"], ondelete="RESTRICT", name="fk_payment_ledger_payment_company"),
        sa.ForeignKeyConstraint(["invoice_id", "company_id"], ["invoices.id", "invoices.company_id"], ondelete="RESTRICT", name="fk_payment_ledger_invoice_company"),
        sa.ForeignKeyConstraint(["submission_id", "company_id"], ["payment_submissions.id", "payment_submissions.company_id"], ondelete="RESTRICT", name="fk_payment_ledger_submission_company"),
        sa.CheckConstraint("amount_bdt > 0", name="ck_payment_ledger_event_amount_positive"),
        sa.CheckConstraint("event_type IN ('PAYMENT_VERIFIED','PAYMENT_ALLOCATED','PAYMENT_REVERSED','PAYMENT_REFUNDED','PAYMENT_DISPUTED','SUBMISSION_REJECTED')", name="ck_payment_ledger_event_type"),
        sa.CheckConstraint("currency = 'BDT'", name="ck_payment_ledger_event_currency_bdt"),
    )
    op.create_index("ix_payment_ledger_events_company_created", "payment_ledger_events", ["company_id", "created_at"])

    op.create_table(
        "payment_intents",
        sa.Column("id", uuid, primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("company_id", uuid, sa.ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("invoice_id", uuid, nullable=False),
        sa.Column("provider_name", sa.String(40), nullable=False),
        sa.Column("idempotency_key", sa.String(120), nullable=False),
        sa.Column("provider_order_id", sa.String(120), nullable=False),
        sa.Column("amount_bdt", money, nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="BDT"),
        sa.Column("status", sa.String(24), nullable=False, server_default="CREATED"),
        sa.Column("checkout_url", sa.Text(), nullable=True),
        sa.Column("provider_transaction_id", sa.String(160), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", uuid, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("provider_name", "idempotency_key", name="uq_payment_intent_provider_idempotency"),
        sa.UniqueConstraint("provider_order_id", name="uq_payment_intent_provider_order"),
        sa.UniqueConstraint("provider_transaction_id", name="uq_payment_intent_provider_transaction"),
        sa.CheckConstraint("provider_name IN ('SSLCOMMERZ','BKASH','NAGAD')", name="ck_payment_intent_provider"),
        sa.CheckConstraint("status IN ('CREATED','PENDING','SUCCEEDED','FAILED','EXPIRED','CANCELLED')", name="ck_payment_intent_status"),
        sa.ForeignKeyConstraint(["invoice_id", "company_id"], ["invoices.id", "invoices.company_id"], ondelete="RESTRICT", name="fk_payment_intents_invoice_company"),
        sa.CheckConstraint("amount_bdt > 0", name="ck_payment_intent_amount_positive"),
        sa.CheckConstraint("currency = 'BDT'", name="ck_payment_intent_currency_bdt"),
    )
    op.create_index("ix_payment_intents_company_status", "payment_intents", ["company_id", "status"])

    op.create_table(
        "payment_provider_events",
        sa.Column("id", uuid, primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("provider_name", sa.String(40), nullable=False),
        sa.Column("provider_event_id", sa.String(160), nullable=False),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("payload_redacted", postgresql.JSONB(), nullable=True),
        sa.Column("processing_status", sa.String(24), nullable=False, server_default="RECEIVED"),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.UniqueConstraint("provider_name", "provider_event_id", name="uq_payment_provider_event"),
        sa.CheckConstraint("processing_status IN ('RECEIVED','PROCESSING','PROCESSED','FAILED')", name="ck_payment_provider_event_status"),
    )
    op.create_index("ix_payment_provider_events_status_received", "payment_provider_events", ["processing_status", "received_at"])

    op.create_table(
        "client_subscriptions",
        sa.Column("id", uuid, primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("company_id", uuid, sa.ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("plan_code", sa.String(60), nullable=False),
        sa.Column("plan_name", sa.String(120), nullable=False),
        sa.Column("billing_interval", sa.String(16), nullable=False),
        sa.Column("amount_bdt", money, nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="BDT"),
        sa.Column("status", sa.String(24), nullable=False, server_default="PENDING"),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("renews_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("auto_renew", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_by", uuid, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("amount_bdt >= 0", name="ck_subscription_amount_nonnegative"),
        sa.CheckConstraint("currency = 'BDT'", name="ck_subscription_currency_bdt"),
        sa.CheckConstraint("billing_interval IN ('MONTHLY','QUARTERLY','ANNUAL','ONE_TIME')", name="ck_subscription_billing_interval"),
        sa.CheckConstraint("status IN ('PENDING','ACTIVE','PAST_DUE','CANCELLED','EXPIRED','SUSPENDED')", name="ck_subscription_status"),
    )
    op.create_index("ix_client_subscriptions_company_status", "client_subscriptions", ["company_id", "status"])

    # RLS is forced on every new financial table. Client access uses the
    # dedicated billing helpers; legal staff do not inherit finance access.
    for table in TABLES:
        op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE public.{table} FORCE ROW LEVEL SECURITY")

    op.execute("""
        CREATE POLICY invoices_billing_select ON public.invoices
        FOR SELECT
        USING (
            public.nlc_can_view_billing_company(company_id)
            AND (status <> 'DRAFT' OR public.nlc_current_user_is_finance_staff())
        )
    """)
    op.execute("""
        CREATE POLICY invoices_finance_insert ON public.invoices
        FOR INSERT WITH CHECK (
            public.nlc_can_manage_billing_company(company_id)
            AND status = 'DRAFT'
            AND paid_bdt = 0
            AND balance_bdt = total_bdt
        )
    """)
    op.execute("""
        CREATE POLICY invoices_finance_update ON public.invoices
        FOR UPDATE
        USING (public.nlc_can_manage_billing_company(company_id))
        WITH CHECK (public.nlc_can_manage_billing_company(company_id))
    """)

    op.execute("""
        CREATE POLICY invoice_lines_billing_select ON public.invoice_lines
        FOR SELECT
        USING (
            public.nlc_can_view_billing_company(invoice_lines.company_id)
            AND (
                public.nlc_current_user_is_finance_staff()
                OR EXISTS (
                    SELECT 1 FROM public.invoices i
                    WHERE i.id = invoice_lines.invoice_id
                      AND i.company_id = invoice_lines.company_id
                      AND i.status <> 'DRAFT'
                )
            )
        )
    """)
    op.execute("""
        CREATE POLICY invoice_lines_finance_insert ON public.invoice_lines
        FOR INSERT WITH CHECK (
            public.nlc_can_manage_billing_company(company_id)
            AND EXISTS (
                SELECT 1 FROM public.invoices i
                WHERE i.id = invoice_lines.invoice_id
                  AND i.company_id = invoice_lines.company_id
                  AND i.status = 'DRAFT'
            )
        )
    """)
    op.execute("""
        CREATE POLICY invoice_lines_finance_update ON public.invoice_lines
        FOR UPDATE
        USING (public.nlc_can_manage_billing_company(company_id))
        WITH CHECK (public.nlc_can_manage_billing_company(company_id))
    """)

    op.execute("""
        CREATE POLICY payment_submissions_billing_select ON public.payment_submissions
        FOR SELECT USING (public.nlc_can_view_billing_company(company_id))
    """)
    op.execute("""
        CREATE POLICY payment_submissions_submit_insert ON public.payment_submissions
        FOR INSERT
        WITH CHECK (
            public.nlc_can_submit_payment_company(company_id)
            AND (
                public.nlc_current_user_is_finance_staff()
                OR submitted_by = public.nlc_current_user_id()
            )
            AND status = 'PENDING_REVIEW'
            AND reviewed_by IS NULL
            AND reviewed_at IS NULL
            AND review_note IS NULL
            AND cheque_cleared_at IS NULL
            AND (
                evidence_document_id IS NULL
                OR EXISTS (
                    SELECT 1 FROM public.documents d
                    WHERE d.id = payment_submissions.evidence_document_id
                      AND d.company_id = payment_submissions.company_id
                )
            )
            AND EXISTS (
                SELECT 1 FROM public.invoices i
                WHERE i.id = payment_submissions.invoice_id
                  AND i.company_id = payment_submissions.company_id
                  AND i.status IN ('ISSUED','PARTIALLY_PAID')
                  AND payment_submissions.amount_bdt <= i.balance_bdt
            )
        )
    """)
    op.execute("""
        CREATE POLICY payment_submissions_finance_update ON public.payment_submissions
        FOR UPDATE
        USING (public.nlc_can_manage_billing_company(company_id))
        WITH CHECK (public.nlc_can_manage_billing_company(company_id))
    """)

    op.execute("""
        CREATE POLICY payments_billing_select ON public.payments
        FOR SELECT USING (public.nlc_can_view_billing_company(company_id))
    """)
    op.execute("""
        CREATE POLICY payments_finance_insert ON public.payments
        FOR INSERT WITH CHECK (
            public.nlc_can_manage_billing_company(company_id)
            AND status = 'SETTLED'
            AND verified_at IS NOT NULL
        )
    """)
    op.execute("""
        CREATE POLICY payments_finance_update ON public.payments
        FOR UPDATE
        USING (public.nlc_can_manage_billing_company(company_id))
        WITH CHECK (public.nlc_can_manage_billing_company(company_id))
    """)

    op.execute("""
        CREATE POLICY payment_allocations_billing_select ON public.payment_allocations
        FOR SELECT USING (public.nlc_can_view_billing_company(company_id))
    """)
    op.execute("""
        CREATE POLICY payment_allocations_finance_insert ON public.payment_allocations
        FOR INSERT WITH CHECK (
            public.nlc_can_manage_billing_company(company_id)
            AND EXISTS (
                SELECT 1 FROM public.payments p
                WHERE p.id = payment_allocations.payment_id
                  AND p.company_id = payment_allocations.company_id
                  AND p.status = 'SETTLED'
            )
            AND EXISTS (
                SELECT 1 FROM public.invoices i
                WHERE i.id = payment_allocations.invoice_id
                  AND i.company_id = payment_allocations.company_id
                  AND i.status IN ('ISSUED','PARTIALLY_PAID','OVERDUE')
                  AND payment_allocations.amount_bdt <= i.balance_bdt
            )
        )
    """)

    op.execute("""
        CREATE POLICY payment_ledger_finance_select ON public.payment_ledger_events
        FOR SELECT USING (public.nlc_can_manage_billing_company(company_id))
    """)
    op.execute("""
        CREATE POLICY payment_ledger_finance_insert ON public.payment_ledger_events
        FOR INSERT WITH CHECK (public.nlc_can_manage_billing_company(company_id))
    """)

    op.execute("""
        CREATE POLICY payment_intents_billing_select ON public.payment_intents
        FOR SELECT USING (public.nlc_can_view_billing_company(company_id))
    """)
    op.execute("""
        CREATE POLICY payment_intents_submit_insert ON public.payment_intents
        FOR INSERT
        WITH CHECK (
            public.nlc_can_submit_payment_company(company_id)
            AND (
                public.nlc_current_user_is_finance_staff()
                OR created_by = public.nlc_current_user_id()
            )
            AND status = 'CREATED'
            AND provider_transaction_id IS NULL
            AND verified_at IS NULL
            AND checkout_url IS NULL
            AND EXISTS (
                SELECT 1 FROM public.invoices i
                WHERE i.id = payment_intents.invoice_id
                  AND i.company_id = payment_intents.company_id
                  AND i.status IN ('ISSUED','PARTIALLY_PAID')
                  AND payment_intents.amount_bdt <= i.balance_bdt
            )
        )
    """)
    op.execute("""
        CREATE POLICY payment_intents_finance_update ON public.payment_intents
        FOR UPDATE
        USING (public.nlc_can_manage_billing_company(company_id))
        WITH CHECK (public.nlc_can_manage_billing_company(company_id))
    """)

    op.execute("""
        CREATE POLICY payment_provider_events_finance_all ON public.payment_provider_events
        FOR ALL
        USING (public.nlc_current_user_is_finance_staff())
        WITH CHECK (public.nlc_current_user_is_finance_staff())
    """)

    op.execute("""
        CREATE POLICY subscriptions_billing_select ON public.client_subscriptions
        FOR SELECT USING (public.nlc_can_view_billing_company(company_id))
    """)
    op.execute("""
        CREATE POLICY subscriptions_finance_insert ON public.client_subscriptions
        FOR INSERT WITH CHECK (
            public.nlc_can_manage_billing_company(company_id)
            AND status = 'PENDING'
        )
    """)
    op.execute("""
        CREATE POLICY subscriptions_finance_update ON public.client_subscriptions
        FOR UPDATE
        USING (public.nlc_can_manage_billing_company(company_id))
        WITH CHECK (public.nlc_can_manage_billing_company(company_id))
    """)

    # Once issued, invoice commercial terms and line items are immutable.
    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_guard_invoice_update()
        RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, public AS $function$
        BEGIN
            IF OLD.status <> 'DRAFT' AND (
                NEW.company_id IS DISTINCT FROM OLD.company_id
                OR NEW.engagement_id IS DISTINCT FROM OLD.engagement_id
                OR NEW.invoice_number IS DISTINCT FROM OLD.invoice_number
                OR NEW.currency IS DISTINCT FROM OLD.currency
                OR NEW.subtotal_bdt IS DISTINCT FROM OLD.subtotal_bdt
                OR NEW.tax_bdt IS DISTINCT FROM OLD.tax_bdt
                OR NEW.total_bdt IS DISTINCT FROM OLD.total_bdt
                OR NEW.due_at IS DISTINCT FROM OLD.due_at
                OR NEW.notes IS DISTINCT FROM OLD.notes
                OR NEW.created_by IS DISTINCT FROM OLD.created_by
            ) THEN
                RAISE EXCEPTION 'issued invoice terms are immutable' USING ERRCODE = '55000';
            END IF;
            IF NEW.status IS DISTINCT FROM OLD.status AND NOT (
                (OLD.status = 'DRAFT' AND NEW.status IN ('ISSUED','VOID'))
                OR (OLD.status = 'ISSUED' AND NEW.status IN ('PARTIALLY_PAID','PAID','OVERDUE','VOID'))
                OR (OLD.status = 'OVERDUE' AND NEW.status IN ('PARTIALLY_PAID','PAID','VOID'))
                OR (OLD.status = 'PARTIALLY_PAID' AND NEW.status IN ('PAID','OVERDUE'))
            ) THEN
                RAISE EXCEPTION 'invalid invoice state transition: % -> %', OLD.status, NEW.status
                    USING ERRCODE = '55000';
            END IF;
            RETURN NEW;
        END
        $function$
    """)
    op.execute("REVOKE ALL ON FUNCTION public.nlc_guard_invoice_update() FROM PUBLIC")
    op.execute("""
        CREATE TRIGGER invoices_guard_update
        BEFORE UPDATE ON public.invoices
        FOR EACH ROW EXECUTE FUNCTION public.nlc_guard_invoice_update()
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_guard_invoice_line_mutation()
        RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, public AS $function$
        DECLARE invoice_state text;
        BEGIN
            SELECT status INTO invoice_state
            FROM public.invoices
            WHERE id = OLD.invoice_id AND company_id = OLD.company_id
            FOR UPDATE;
            IF invoice_state IS DISTINCT FROM 'DRAFT' THEN
                RAISE EXCEPTION 'invoice lines are immutable after invoice issue'
                    USING ERRCODE = '55000';
            END IF;
            IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
            RETURN NEW;
        END
        $function$
    """)
    op.execute("REVOKE ALL ON FUNCTION public.nlc_guard_invoice_line_mutation() FROM PUBLIC")
    op.execute("""
        CREATE TRIGGER invoice_lines_guard_mutation
        BEFORE UPDATE OR DELETE ON public.invoice_lines
        FOR EACH ROW EXECUTE FUNCTION public.nlc_guard_invoice_line_mutation()
    """)

    # A settled payment's amount, method and provider identity cannot be edited.
    # Reversals/refunds/disputes are separate ledger events plus a terminal status.
    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_guard_payment_update()
        RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, public AS $function$
        BEGIN
            IF (
                NEW.company_id IS DISTINCT FROM OLD.company_id
                OR NEW.payment_number IS DISTINCT FROM OLD.payment_number
                OR NEW.method IS DISTINCT FROM OLD.method
                OR NEW.channel IS DISTINCT FROM OLD.channel
                OR NEW.amount_bdt IS DISTINCT FROM OLD.amount_bdt
                OR NEW.currency IS DISTINCT FROM OLD.currency
                OR NEW.provider_name IS DISTINCT FROM OLD.provider_name
                OR NEW.provider_transaction_id IS DISTINCT FROM OLD.provider_transaction_id
                OR NEW.payer_reference IS DISTINCT FROM OLD.payer_reference
                OR NEW.received_at IS DISTINCT FROM OLD.received_at
                OR NEW.verified_by IS DISTINCT FROM OLD.verified_by
                OR NEW.verified_at IS DISTINCT FROM OLD.verified_at
                OR NEW.created_by IS DISTINCT FROM OLD.created_by
            ) THEN
                RAISE EXCEPTION 'payment receipt facts are immutable' USING ERRCODE = '55000';
            END IF;
            IF NEW.status IS DISTINCT FROM OLD.status AND NOT (
                OLD.status = 'SETTLED' AND NEW.status IN ('REVERSED','REFUNDED','DISPUTED')
            ) THEN
                RAISE EXCEPTION 'invalid payment state transition: % -> %', OLD.status, NEW.status
                    USING ERRCODE = '55000';
            END IF;
            RETURN NEW;
        END
        $function$
    """)
    op.execute("REVOKE ALL ON FUNCTION public.nlc_guard_payment_update() FROM PUBLIC")
    op.execute("""
        CREATE TRIGGER payments_guard_update
        BEFORE UPDATE ON public.payments
        FOR EACH ROW EXECUTE FUNCTION public.nlc_guard_payment_update()
    """)

    # Client-submitted payment claims cannot self-approve or rewrite their facts.
    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_guard_payment_submission_update()
        RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, public AS $function$
        BEGIN
            IF (
                NEW.company_id IS DISTINCT FROM OLD.company_id
                OR NEW.invoice_id IS DISTINCT FROM OLD.invoice_id
                OR NEW.submitted_by IS DISTINCT FROM OLD.submitted_by
                OR NEW.method IS DISTINCT FROM OLD.method
                OR NEW.amount_bdt IS DISTINCT FROM OLD.amount_bdt
                OR NEW.currency IS DISTINCT FROM OLD.currency
                OR NEW.payer_reference IS DISTINCT FROM OLD.payer_reference
                OR NEW.paid_at IS DISTINCT FROM OLD.paid_at
                OR NEW.evidence_document_id IS DISTINCT FROM OLD.evidence_document_id
            ) THEN
                RAISE EXCEPTION 'payment submission facts are immutable' USING ERRCODE = '55000';
            END IF;
            IF OLD.status <> 'PENDING_REVIEW'
                OR NEW.status NOT IN ('APPROVED','REJECTED')
                OR NEW.reviewed_by IS NULL
                OR NEW.reviewed_at IS NULL THEN
                RAISE EXCEPTION 'invalid payment submission review transition' USING ERRCODE = '55000';
            END IF;
            IF NEW.status = 'APPROVED' AND OLD.method = 'CHEQUE' AND NEW.cheque_cleared_at IS NULL THEN
                RAISE EXCEPTION 'cheque must be cleared before payment approval' USING ERRCODE = '55000';
            END IF;
            IF NEW.status = 'REJECTED' AND COALESCE(length(trim(NEW.review_note)), 0) = 0 THEN
                RAISE EXCEPTION 'rejection reason is required' USING ERRCODE = '55000';
            END IF;
            RETURN NEW;
        END
        $function$
    """)
    op.execute("REVOKE ALL ON FUNCTION public.nlc_guard_payment_submission_update() FROM PUBLIC")
    op.execute("""
        CREATE TRIGGER payment_submissions_guard_update
        BEFORE UPDATE ON public.payment_submissions
        FOR EACH ROW EXECUTE FUNCTION public.nlc_guard_payment_submission_update()
    """)

    # Payment intents are created as CREATED by the customer and advanced only
    # by the verified provider/service path.
    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_guard_payment_intent_update()
        RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, public AS $function$
        BEGIN
            IF (
                NEW.company_id IS DISTINCT FROM OLD.company_id
                OR NEW.invoice_id IS DISTINCT FROM OLD.invoice_id
                OR NEW.provider_name IS DISTINCT FROM OLD.provider_name
                OR NEW.idempotency_key IS DISTINCT FROM OLD.idempotency_key
                OR NEW.provider_order_id IS DISTINCT FROM OLD.provider_order_id
                OR NEW.amount_bdt IS DISTINCT FROM OLD.amount_bdt
                OR NEW.currency IS DISTINCT FROM OLD.currency
                OR NEW.created_by IS DISTINCT FROM OLD.created_by
            ) THEN
                RAISE EXCEPTION 'payment intent facts are immutable' USING ERRCODE = '55000';
            END IF;
            IF NEW.status IS DISTINCT FROM OLD.status AND NOT (
                (OLD.status = 'CREATED' AND NEW.status IN ('PENDING','FAILED','EXPIRED','CANCELLED'))
                OR (OLD.status = 'PENDING' AND NEW.status IN ('SUCCEEDED','FAILED','EXPIRED','CANCELLED'))
            ) THEN
                RAISE EXCEPTION 'invalid payment intent state transition: % -> %', OLD.status, NEW.status
                    USING ERRCODE = '55000';
            END IF;
            RETURN NEW;
        END
        $function$
    """)
    op.execute("REVOKE ALL ON FUNCTION public.nlc_guard_payment_intent_update() FROM PUBLIC")
    op.execute("""
        CREATE TRIGGER payment_intents_guard_update
        BEFORE UPDATE ON public.payment_intents
        FOR EACH ROW EXECUTE FUNCTION public.nlc_guard_payment_intent_update()
    """)

    # Append-only payment history: no UPDATE or DELETE can rewrite a posted event.
    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_reject_payment_ledger_event_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $function$
        BEGIN
            RAISE EXCEPTION 'payment ledger events are append-only'
                USING ERRCODE = '55000';
        END
        $function$
    """)
    op.execute("REVOKE ALL ON FUNCTION public.nlc_reject_payment_ledger_event_mutation() FROM PUBLIC")
    op.execute("""
        CREATE TRIGGER payment_ledger_events_append_only
        BEFORE UPDATE OR DELETE ON public.payment_ledger_events
        FOR EACH ROW EXECUTE FUNCTION public.nlc_reject_payment_ledger_event_mutation()
    """)

    # Operation privileges are narrower than table ownership. RLS controls rows;
    # finance helpers control billing mutations. Ledger and allocation rows are
    # append-only and receive no UPDATE or DELETE privilege.
    mutable_tables = (
        "invoices", "invoice_lines", "payment_submissions", "payments",
        "payment_intents", "payment_provider_events", "client_subscriptions",
    )
    insert_only_tables = ("payment_allocations", "payment_ledger_events")
    for table in mutable_tables:
        op.execute(f"GRANT SELECT, INSERT, UPDATE ON TABLE public.{table} TO nlc_app_role")
        op.execute(f"REVOKE DELETE, TRUNCATE, REFERENCES, TRIGGER ON TABLE public.{table} FROM nlc_app_role")
    for table in insert_only_tables:
        op.execute(f"GRANT SELECT, INSERT ON TABLE public.{table} TO nlc_app_role")
        op.execute(f"REVOKE UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER ON TABLE public.{table} FROM nlc_app_role")


def downgrade() -> None:
    # Forward-only financial security migration. Removing financial RLS or
    # append-only ledger protections is not a safe automatic rollback.
    pass
