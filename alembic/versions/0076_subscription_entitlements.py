"""Company-scoped subscription plans, immutable entitlement snapshots and audit history.

Revision ID: 0076_subscription_entitlements
Revises: 0075_director_transfer_evidence

This migration extends the existing billing foundation. It does not seed prices:
commercial plan pricing and feature grants must be explicitly configured by
authorized NLC finance administrators before customer subscriptions can be sold.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0076_subscription_entitlements"
down_revision = "0075_director_transfer_evidence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)

    op.create_table(
        "subscription_plans",
        sa.Column("plan_code", sa.String(60), primary_key=True),
        sa.Column("plan_name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("grace_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by", uuid, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updated_by", uuid, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("length(plan_code) BETWEEN 2 AND 60", name="ck_subscription_plan_code_length"),
        sa.CheckConstraint("length(plan_name) BETWEEN 2 AND 120", name="ck_subscription_plan_name_length"),
        sa.CheckConstraint("grace_days BETWEEN 0 AND 30", name="ck_subscription_plan_grace_days"),
    )

    op.create_table(
        "subscription_plan_prices",
        sa.Column("id", uuid, primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("plan_code", sa.String(60), sa.ForeignKey("subscription_plans.plan_code", ondelete="RESTRICT"), nullable=False),
        sa.Column("billing_interval", sa.String(16), nullable=False),
        sa.Column("amount_bdt", sa.Numeric(15, 2), nullable=False),
        sa.Column("tax_bdt", sa.Numeric(15, 2), nullable=False),
        sa.Column("tax_policy_reference", sa.Text(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="BDT"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("plan_code", "billing_interval", name="uq_subscription_plan_price_interval"),
        sa.CheckConstraint("billing_interval IN ('MONTHLY','QUARTERLY','ANNUAL','ONE_TIME')", name="ck_subscription_plan_price_interval"),
        sa.CheckConstraint("amount_bdt > 0", name="ck_subscription_plan_price_amount"),
        sa.CheckConstraint("tax_bdt >= 0", name="ck_subscription_plan_price_tax"),
        sa.CheckConstraint("length(trim(tax_policy_reference)) BETWEEN 3 AND 500", name="ck_subscription_plan_price_tax_reference"),
        sa.CheckConstraint("currency = 'BDT'", name="ck_subscription_plan_price_currency"),
    )
    op.create_index("ix_subscription_plan_prices_active", "subscription_plan_prices", ["plan_code", "is_active"])

    op.create_table(
        "subscription_plan_features",
        sa.Column("id", uuid, primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("plan_code", sa.String(60), sa.ForeignKey("subscription_plans.plan_code", ondelete="RESTRICT"), nullable=False),
        sa.Column("feature_code", sa.String(80), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("plan_code", "feature_code", name="uq_subscription_plan_feature"),
        sa.CheckConstraint("length(feature_code) BETWEEN 2 AND 80", name="ck_subscription_feature_code_length"),
        sa.CheckConstraint("feature_code IN ('compliance_package','document_management','corporate_rescue')", name="ck_subscription_plan_feature_supported"),
    )

    op.add_column("client_subscriptions", sa.Column("tax_bdt", sa.Numeric(15, 2), nullable=False, server_default="0"))
    op.add_column("client_subscriptions", sa.Column("tax_policy_reference", sa.Text(), nullable=True))
    op.add_column("client_subscriptions", sa.Column("invoice_id", uuid, nullable=True))
    op.add_column("client_subscriptions", sa.Column("grace_days", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("client_subscriptions", sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("client_subscriptions", sa.Column("grace_ends_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("client_subscriptions", sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("client_subscriptions", sa.Column("suspended_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("client_subscriptions", sa.Column("suspension_reason", sa.Text(), nullable=True))
    op.add_column("client_subscriptions", sa.Column("activated_by", uuid, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True))
    op.create_unique_constraint("uq_client_subscriptions_id_company", "client_subscriptions", ["id", "company_id"])
    op.create_check_constraint("ck_client_subscription_grace_days", "client_subscriptions", "grace_days BETWEEN 0 AND 30")
    op.create_check_constraint("ck_client_subscription_tax_nonnegative", "client_subscriptions", "tax_bdt >= 0")
    op.create_foreign_key(
        "fk_client_subscriptions_invoice_company",
        "client_subscriptions", "invoices",
        ["invoice_id", "company_id"], ["id", "company_id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "uq_client_subscriptions_invoice",
        "client_subscriptions",
        ["invoice_id"],
        unique=True,
        postgresql_where=sa.text("invoice_id IS NOT NULL"),
    )
    op.create_index(
        "ix_client_subscriptions_period",
        "client_subscriptions",
        ["status", "ends_at", "grace_ends_at"],
    )

    op.create_table(
        "client_subscription_features",
        sa.Column("id", uuid, primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("subscription_id", uuid, nullable=False),
        sa.Column("company_id", uuid, sa.ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("feature_code", sa.String(80), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("subscription_id", "feature_code", name="uq_client_subscription_feature"),
        sa.ForeignKeyConstraint(
            ["subscription_id", "company_id"],
            ["client_subscriptions.id", "client_subscriptions.company_id"],
            ondelete="RESTRICT",
            name="fk_client_subscription_features_subscription_company",
        ),
        sa.CheckConstraint("length(feature_code) BETWEEN 2 AND 80", name="ck_client_subscription_feature_code_length"),
        sa.CheckConstraint("feature_code IN ('compliance_package','document_management','corporate_rescue')", name="ck_client_subscription_feature_supported"),
    )
    op.create_index(
        "ix_client_subscription_features_lookup",
        "client_subscription_features",
        ["company_id", "subscription_id", "feature_code"],
    )

    op.create_table(
        "subscription_events",
        sa.Column("id", uuid, primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("subscription_id", uuid, nullable=False),
        sa.Column("company_id", uuid, sa.ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("actor_id", uuid, sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("invoice_id", uuid, nullable=True),
        sa.Column("payment_id", uuid, nullable=True),
        sa.Column("event_metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["subscription_id", "company_id"],
            ["client_subscriptions.id", "client_subscriptions.company_id"],
            ondelete="RESTRICT",
            name="fk_subscription_events_subscription_company",
        ),
        sa.ForeignKeyConstraint(
            ["invoice_id", "company_id"],
            ["invoices.id", "invoices.company_id"],
            ondelete="RESTRICT",
            name="fk_subscription_events_invoice_company",
        ),
        sa.ForeignKeyConstraint(
            ["payment_id", "company_id"],
            ["payments.id", "payments.company_id"],
            ondelete="RESTRICT",
            name="fk_subscription_events_payment_company",
        ),
        sa.CheckConstraint(
            "event_type IN ('REQUESTED','INVOICE_ISSUED','ACTIVATED','RENEWED','CANCEL_AT_PERIOD_END','CANCELLED','SUSPENDED','RESUMED','EXPIRED','PAST_DUE')",
            name="ck_subscription_event_type",
        ),
    )
    op.create_index("ix_subscription_events_company_created", "subscription_events", ["company_id", "created_at"])

    # Plan catalogue: active plans/prices/features are readable; only finance
    # staff can create or change commercial definitions. No implicit seed prices.
    for table in ("subscription_plans", "subscription_plan_prices", "subscription_plan_features",
                  "client_subscription_features", "subscription_events"):
        op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE public.{table} FORCE ROW LEVEL SECURITY")

    op.execute("""
        CREATE POLICY subscription_plans_read ON public.subscription_plans
        FOR SELECT USING (is_active IS TRUE OR public.nlc_current_user_is_finance_staff())
    """)
    op.execute("""
        CREATE POLICY subscription_plans_finance_write ON public.subscription_plans
        FOR ALL USING (public.nlc_current_user_is_finance_staff())
        WITH CHECK (public.nlc_current_user_is_finance_staff())
    """)
    op.execute("""
        CREATE POLICY subscription_prices_read ON public.subscription_plan_prices
        FOR SELECT USING (
            public.nlc_current_user_is_finance_staff()
            OR (is_active IS TRUE AND EXISTS (
                SELECT 1 FROM public.subscription_plans p
                WHERE p.plan_code = subscription_plan_prices.plan_code
                  AND p.is_active IS TRUE
            ))
        )
    """)
    op.execute("""
        CREATE POLICY subscription_prices_finance_write ON public.subscription_plan_prices
        FOR ALL USING (public.nlc_current_user_is_finance_staff())
        WITH CHECK (public.nlc_current_user_is_finance_staff())
    """)
    op.execute("""
        CREATE POLICY subscription_features_read ON public.subscription_plan_features
        FOR SELECT USING (
            public.nlc_current_user_is_finance_staff()
            OR EXISTS (
                SELECT 1 FROM public.subscription_plans p
                WHERE p.plan_code = subscription_plan_features.plan_code
                  AND p.is_active IS TRUE
            )
        )
    """)
    op.execute("""
        CREATE POLICY subscription_features_finance_write ON public.subscription_plan_features
        FOR ALL USING (public.nlc_current_user_is_finance_staff())
        WITH CHECK (public.nlc_current_user_is_finance_staff())
    """)

    # A customer can request only an active, explicitly priced plan for a
    # company where the DB-backed billing helper confirms edit+financial access.
    op.execute("DROP POLICY subscriptions_finance_insert ON public.client_subscriptions")
    op.execute("""
        CREATE POLICY subscriptions_request_insert ON public.client_subscriptions
        FOR INSERT WITH CHECK (
            status = 'PENDING'
            AND invoice_id IS NULL
            AND starts_at IS NULL
            AND ends_at IS NULL
            AND renews_at IS NULL
            AND grace_ends_at IS NULL
            AND cancelled_at IS NULL
            AND suspended_at IS NULL
            AND suspension_reason IS NULL
            AND activated_by IS NULL
            AND auto_renew IS FALSE
            AND cancel_at_period_end IS FALSE
            AND public.nlc_can_submit_payment_company(company_id)
            AND (
                public.nlc_current_user_is_finance_staff()
                OR created_by = public.nlc_current_user_id()
            )
            AND EXISTS (
                SELECT 1
                FROM public.subscription_plans p
                JOIN public.subscription_plan_prices pp ON pp.plan_code = p.plan_code
                WHERE p.plan_code = client_subscriptions.plan_code
                  AND p.plan_name = client_subscriptions.plan_name
                  AND p.grace_days = client_subscriptions.grace_days
                  AND p.is_active IS TRUE
                  AND pp.is_active IS TRUE
                  AND pp.billing_interval = client_subscriptions.billing_interval
                  AND pp.amount_bdt = client_subscriptions.amount_bdt
                  AND pp.tax_bdt = client_subscriptions.tax_bdt
                  AND pp.tax_policy_reference = client_subscriptions.tax_policy_reference
                  AND pp.currency = client_subscriptions.currency
                  AND length(trim(client_subscriptions.tax_policy_reference)) >= 3
            )
            AND EXISTS (
                SELECT 1 FROM public.subscription_plan_features pf
                WHERE pf.plan_code = client_subscriptions.plan_code
                  AND pf.enabled IS TRUE
            )
        )
    """)

    op.execute("""
        CREATE POLICY client_subscription_features_read ON public.client_subscription_features
        FOR SELECT USING (public.nlc_can_view_billing_company(company_id))
    """)
    op.execute("""
        CREATE POLICY client_subscription_features_insert ON public.client_subscription_features
        FOR INSERT WITH CHECK (
            NOT public.nlc_current_user_is_finance_staff()
            AND public.nlc_can_submit_payment_company(company_id)
            AND client_subscription_features.enabled IS TRUE
                AND EXISTS (
                    SELECT 1
                    FROM public.client_subscriptions s
                    JOIN public.subscription_plan_features pf
                      ON pf.plan_code = s.plan_code
                     AND pf.feature_code = client_subscription_features.feature_code
                    WHERE s.id = client_subscription_features.subscription_id
                      AND s.company_id = client_subscription_features.company_id
                      AND s.status = 'PENDING'
                      AND s.created_by = public.nlc_current_user_id()
                      AND pf.enabled IS TRUE
                )
        )
    """)

    op.execute("""
        CREATE POLICY subscription_events_read ON public.subscription_events
        FOR SELECT USING (public.nlc_can_view_billing_company(company_id))
    """)
    # FinanceService accepts overdue invoices for payment; keep the RLS
    # boundary aligned so customers can actually renew after the due date.
    op.execute("DROP POLICY payment_submissions_submit_insert ON public.payment_submissions")
    op.execute("""
        CREATE POLICY payment_submissions_submit_insert ON public.payment_submissions
        FOR INSERT WITH CHECK (
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
                  AND i.status IN ('ISSUED','PARTIALLY_PAID','OVERDUE')
                  AND payment_submissions.amount_bdt <= i.balance_bdt
            )
        )
    """)
    op.execute("""
        CREATE POLICY subscription_events_insert ON public.subscription_events
        FOR INSERT WITH CHECK (
            public.nlc_current_user_is_finance_staff()
            OR (
                event_type = 'REQUESTED'
                AND actor_id = public.nlc_current_user_id()
                AND public.nlc_can_submit_payment_company(company_id)
            )
        )
    """)
    op.execute("DROP POLICY subscriptions_finance_update ON public.client_subscriptions")
    op.execute("""
        CREATE POLICY subscriptions_lifecycle_update ON public.client_subscriptions
        FOR UPDATE
        USING (
            public.nlc_current_user_is_finance_staff()
            OR (
                public.nlc_can_submit_payment_company(company_id)
                AND created_by = public.nlc_current_user_id()
                AND status IN ('PENDING','ACTIVE')
            )
        )
        WITH CHECK (
            public.nlc_current_user_is_finance_staff()
            OR (
                public.nlc_can_submit_payment_company(company_id)
                AND created_by = public.nlc_current_user_id()
                AND (
                    (status = 'ACTIVE' AND cancel_at_period_end IS TRUE)
                    OR (status = 'CANCELLED' AND invoice_id IS NULL)
                )
            )
        )
    """)
    op.execute("DROP POLICY subscription_events_insert ON public.subscription_events")
    op.execute("""
        CREATE POLICY subscription_events_insert ON public.subscription_events
        FOR INSERT WITH CHECK (
            public.nlc_current_user_is_finance_staff()
            OR (
                actor_id = public.nlc_current_user_id()
                AND public.nlc_can_submit_payment_company(company_id)
                AND (
                    (
                        event_type = 'REQUESTED'
                        AND invoice_id IS NULL
                        AND payment_id IS NULL
                        AND EXISTS (
                            SELECT 1 FROM public.client_subscriptions s
                            WHERE s.id = subscription_events.subscription_id
                              AND s.company_id = subscription_events.company_id
                              AND s.created_by = public.nlc_current_user_id()
                              AND s.status = 'PENDING'
                        )
                    )
                    OR (
                        event_type = 'CANCEL_AT_PERIOD_END'
                        AND payment_id IS NULL
                        AND EXISTS (
                            SELECT 1 FROM public.client_subscriptions s
                            WHERE s.id = subscription_events.subscription_id
                              AND s.company_id = subscription_events.company_id
                              AND s.created_by = public.nlc_current_user_id()
                              AND s.status = 'ACTIVE'
                              AND s.cancel_at_period_end IS TRUE
                              AND s.invoice_id IS NOT DISTINCT FROM subscription_events.invoice_id
                        )
                    )
                    OR (
                        event_type = 'CANCELLED'
                        AND invoice_id IS NULL
                        AND payment_id IS NULL
                        AND EXISTS (
                            SELECT 1 FROM public.client_subscriptions s
                            WHERE s.id = subscription_events.subscription_id
                              AND s.company_id = subscription_events.company_id
                              AND s.created_by = public.nlc_current_user_id()
                              AND s.status = 'CANCELLED'
                              AND s.invoice_id IS NULL
                        )
                    )
                )
            )
        )
    """)

    # Subscription facts and snapshots cannot be rewritten after request;
    # only lifecycle fields and the one-time invoice link may advance.
    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_guard_client_subscription_update()
        RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, public AS $function$
        BEGIN
            IF (
                NEW.company_id IS DISTINCT FROM OLD.company_id
                OR NEW.plan_code IS DISTINCT FROM OLD.plan_code
                OR NEW.plan_name IS DISTINCT FROM OLD.plan_name
                OR NEW.billing_interval IS DISTINCT FROM OLD.billing_interval
                OR NEW.amount_bdt IS DISTINCT FROM OLD.amount_bdt
                OR NEW.tax_bdt IS DISTINCT FROM OLD.tax_bdt
                OR NEW.tax_policy_reference IS DISTINCT FROM OLD.tax_policy_reference
                OR NEW.currency IS DISTINCT FROM OLD.currency
                OR NEW.grace_days IS DISTINCT FROM OLD.grace_days
                OR NEW.created_by IS DISTINCT FROM OLD.created_by
                OR (OLD.invoice_id IS NOT NULL AND NEW.invoice_id IS DISTINCT FROM OLD.invoice_id)
            ) THEN
                RAISE EXCEPTION 'subscription commercial facts are immutable'
                    USING ERRCODE = '55000';
            END IF;
            IF NEW.status IS DISTINCT FROM OLD.status AND NOT (
                (OLD.status = 'PENDING' AND NEW.status IN ('ACTIVE','CANCELLED','SUSPENDED'))
                OR (OLD.status = 'ACTIVE' AND NEW.status IN ('PAST_DUE','CANCELLED','SUSPENDED','EXPIRED'))
                OR (OLD.status = 'PAST_DUE' AND NEW.status IN ('ACTIVE','CANCELLED','SUSPENDED','EXPIRED'))
                OR (OLD.status = 'SUSPENDED' AND NEW.status IN ('ACTIVE','CANCELLED','EXPIRED'))
            ) THEN
                RAISE EXCEPTION 'invalid subscription state transition: % -> %', OLD.status, NEW.status
                    USING ERRCODE = '55000';
            END IF;
            IF NOT public.nlc_current_user_is_finance_staff() AND NOT (
                (
                    OLD.status = 'ACTIVE'
                    AND NEW.status = 'ACTIVE'
                    AND NEW.cancel_at_period_end IS TRUE
                    AND OLD.cancel_at_period_end IS FALSE
                    AND NEW.auto_renew IS NOT DISTINCT FROM OLD.auto_renew
                    AND NEW.starts_at IS NOT DISTINCT FROM OLD.starts_at
                    AND NEW.ends_at IS NOT DISTINCT FROM OLD.ends_at
                    AND NEW.renews_at IS NOT DISTINCT FROM OLD.renews_at
                    AND NEW.grace_ends_at IS NOT DISTINCT FROM OLD.grace_ends_at
                    AND NEW.activated_by IS NOT DISTINCT FROM OLD.activated_by
                    AND NEW.cancelled_at IS NOT DISTINCT FROM OLD.cancelled_at
                    AND NEW.suspended_at IS NOT DISTINCT FROM OLD.suspended_at
                    AND NEW.suspension_reason IS NOT DISTINCT FROM OLD.suspension_reason
                )
                OR
                (
                    OLD.status = 'PENDING'
                    AND NEW.status = 'CANCELLED'
                    AND OLD.invoice_id IS NULL
                    AND NEW.invoice_id IS NULL
                    AND NEW.cancelled_at IS NOT NULL
                    AND NEW.auto_renew IS NOT DISTINCT FROM OLD.auto_renew
                    AND NEW.starts_at IS NOT DISTINCT FROM OLD.starts_at
                    AND NEW.ends_at IS NOT DISTINCT FROM OLD.ends_at
                    AND NEW.renews_at IS NOT DISTINCT FROM OLD.renews_at
                    AND NEW.grace_ends_at IS NOT DISTINCT FROM OLD.grace_ends_at
                    AND NEW.activated_by IS NOT DISTINCT FROM OLD.activated_by
                    AND NEW.suspended_at IS NOT DISTINCT FROM OLD.suspended_at
                    AND NEW.suspension_reason IS NOT DISTINCT FROM OLD.suspension_reason
                    AND NEW.cancel_at_period_end IS NOT DISTINCT FROM OLD.cancel_at_period_end
                )
            ) THEN
                RAISE EXCEPTION 'customer may only cancel an uninvoiced request or schedule cancellation at period end'
                    USING ERRCODE = '42501';
            END IF;
            IF OLD.invoice_id IS NULL AND NEW.invoice_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM public.invoices i
                WHERE i.id = NEW.invoice_id
                  AND i.company_id = NEW.company_id
                  AND i.status = 'ISSUED'
                  AND i.notes LIKE ('%Subscription ID: ' || NEW.id::text || '%')
                  AND i.subtotal_bdt = NEW.amount_bdt
                  AND i.tax_bdt = NEW.tax_bdt
                  AND i.total_bdt = NEW.amount_bdt + NEW.tax_bdt
            ) THEN
                RAISE EXCEPTION 'subscription invoice must be an issued invoice for the exact subscription amount'
                    USING ERRCODE = '55000';
            END IF;
            IF NEW.status = 'ACTIVE' AND OLD.status IS DISTINCT FROM 'ACTIVE' AND (
                NEW.invoice_id IS NULL OR NEW.starts_at IS NULL
                OR (NEW.billing_interval <> 'ONE_TIME' AND NEW.ends_at IS NULL)
                OR NOT EXISTS (
                    SELECT 1 FROM public.invoices i
                    WHERE i.id = NEW.invoice_id
                      AND i.company_id = NEW.company_id
                      AND i.status = 'PAID'
                      AND i.balance_bdt = 0
                      AND i.paid_bdt = i.total_bdt
                      AND COALESCE((
                          SELECT SUM(a.amount_bdt)
                          FROM public.payment_allocations a
                          JOIN public.payments p
                            ON p.id = a.payment_id
                           AND p.company_id = a.company_id
                          WHERE a.invoice_id = i.id
                            AND a.company_id = i.company_id
                            AND p.status = 'SETTLED'
                      ), 0) = i.total_bdt
                )
            ) THEN
                RAISE EXCEPTION 'subscription cannot activate without a fully settled invoice and valid term'
                    USING ERRCODE = '55000';
            END IF;
            RETURN NEW;
        END
        $function$
    """)
    op.execute("REVOKE ALL ON FUNCTION public.nlc_guard_client_subscription_update() FROM PUBLIC")
    op.execute("""
        CREATE TRIGGER client_subscriptions_guard_update
        BEFORE UPDATE ON public.client_subscriptions
        FOR EACH ROW EXECUTE FUNCTION public.nlc_guard_client_subscription_update()
    """)

    # Snapshots and lifecycle events are append-only.
    for table, trigger in (
        ("client_subscription_features", "client_subscription_features_append_only"),
        ("subscription_events", "subscription_events_append_only"),
    ):
        function = f"nlc_reject_{table}_mutation"
        op.execute(f"""
            CREATE OR REPLACE FUNCTION public.{function}()
            RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
            SET search_path = pg_catalog, public AS $function$
            BEGIN
                RAISE EXCEPTION '{table} are append-only' USING ERRCODE = '55000';
            END
            $function$
        """)
        op.execute(f"REVOKE ALL ON FUNCTION public.{function}() FROM PUBLIC")
        op.execute(f"""
            CREATE TRIGGER {trigger}
            BEFORE UPDATE OR DELETE ON public.{table}
            FOR EACH ROW EXECUTE FUNCTION public.{function}()
        """)

    # Runtime role: read/write according to RLS; never delete plan or audit data.
    for table in ("subscription_plans", "subscription_plan_prices", "subscription_plan_features",
                  "client_subscription_features"):
        op.execute(f"GRANT SELECT, INSERT, UPDATE ON TABLE public.{table} TO nlc_app_role")
        op.execute(f"REVOKE DELETE, TRUNCATE, REFERENCES, TRIGGER ON TABLE public.{table} FROM nlc_app_role")
    op.execute("GRANT SELECT, INSERT ON TABLE public.subscription_events TO nlc_app_role")
    op.execute("REVOKE UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER ON TABLE public.subscription_events FROM nlc_app_role")


def downgrade() -> None:
    # Forward-only: a no-op downgrade would move alembic_version backwards
    # while leaving subscription tables, RLS policies and triggers in place.
    # Refuse the operation so recovery must use a verified restore/rebuild plan.
    raise RuntimeError(
        "0074_subscription_entitlements is forward-only; restore a verified backup "
        "or apply a reviewed forward migration instead of downgrading."
    )
