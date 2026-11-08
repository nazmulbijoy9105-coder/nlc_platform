"""Repair aggregate-view RLS and admin-only commercial access.

Revision ID: 0068_repair_aggregate_view_and_revenue_rls
Revises: 0067_unique_manual_wallet_references
"""
from alembic import op
import sqlalchemy as sa

revision = "0068_repair_aggregate_view_and_revenue_rls"
down_revision = "0067_unique_manual_wallet_references"
branch_labels = None
depends_on = None

AGGREGATE_VIEWS = (
    "vw_admin_dashboard_kpis",
    "vw_company_flag_summary",
    "vw_risk_distribution",
    "vw_upcoming_deadlines",
    "vw_revenue_pipeline",
)


def upgrade() -> None:
    bind = op.get_bind()

    missing_views = [
        view
        for view in AGGREGATE_VIEWS
        if bind.execute(
            sa.text("SELECT to_regclass(:qualified_name)"),
            {"qualified_name": f"public.{view}"},
        ).scalar_one() is None
    ]
    if missing_views:
        raise RuntimeError(
            "Aggregate-view security repair found missing public views: "
            + ", ".join(sorted(missing_views))
            + ". Reconcile schema drift before retrying."
        )

    protected_tables = bind.execute(
        sa.text(
            """
            SELECT c.relname, c.relrowsecurity
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public'
              AND c.relname IN ('engagements', 'quotations')
              AND c.relkind = 'r'
            """
        )
    ).all()
    enabled_tables = {row.relname for row in protected_tables if row.relrowsecurity}
    if enabled_tables != {"engagements", "quotations"}:
        raise RuntimeError(
            "engagements and quotations must exist with RLS enabled before "
            "their revenue-role policies can be repaired"
        )

    # A prior deployment may have applied migration 0050 before the
    # invoker-view and revenue-staff corrections were added to that revision.
    # Keep this forward migration idempotent and safe for both database states.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.nlc_can_view_billing_company(p_company_id uuid)
        RETURNS boolean
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $function$
            SELECT public.nlc_current_user_is_finance_staff()
                OR (
                    NOT public.nlc_current_user_is_staff()
                    AND public.nlc_current_user_id() IS NOT NULL
                    AND EXISTS (
                        SELECT 1 FROM public.users u
                        WHERE u.id = public.nlc_current_user_id()
                          AND u.is_active IS TRUE
                    )
                    AND EXISTS (
                        SELECT 1 FROM public.company_user_access cua
                        WHERE cua.company_id = p_company_id
                          AND cua.user_id = public.nlc_current_user_id()
                          AND cua.is_active IS TRUE
                          AND cua.can_view_financials IS TRUE
                    )
                )
        $function$
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.nlc_can_submit_payment_company(p_company_id uuid)
        RETURNS boolean
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $function$
            SELECT public.nlc_current_user_is_finance_staff()
                OR (
                    NOT public.nlc_current_user_is_staff()
                    AND public.nlc_current_user_id() IS NOT NULL
                    AND EXISTS (
                        SELECT 1 FROM public.users u
                        WHERE u.id = public.nlc_current_user_id()
                          AND u.is_active IS TRUE
                    )
                    AND EXISTS (
                        SELECT 1 FROM public.company_user_access cua
                        WHERE cua.company_id = p_company_id
                          AND cua.user_id = public.nlc_current_user_id()
                          AND cua.is_active IS TRUE
                          AND cua.can_edit IS TRUE
                          AND cua.can_view_financials IS TRUE
                    )
                )
        $function$
        """
    )
    op.execute(
        "REVOKE ALL ON FUNCTION public.nlc_can_view_billing_company(uuid) FROM PUBLIC"
    )
    op.execute(
        "GRANT EXECUTE ON FUNCTION public.nlc_can_view_billing_company(uuid) TO nlc_app_role"
    )
    op.execute(
        "REVOKE ALL ON FUNCTION public.nlc_can_submit_payment_company(uuid) FROM PUBLIC"
    )
    op.execute(
        "GRANT EXECUTE ON FUNCTION public.nlc_can_submit_payment_company(uuid) TO nlc_app_role"
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.nlc_current_user_is_revenue_staff()
        RETURNS boolean
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $function$
            SELECT COALESCE(
                public.nlc_current_user_principal() = 'ADMIN'
                OR EXISTS (
                    SELECT 1
                    FROM public.users u
                    WHERE u.id = public.nlc_current_user_id()
                      AND u.is_active IS TRUE
                      AND u.role::text IN ('SUPER_ADMIN', 'ADMIN_STAFF')
                ),
                FALSE
            )
        $function$
        """
    )
    op.execute(
        "REVOKE ALL ON FUNCTION public.nlc_current_user_is_revenue_staff() FROM PUBLIC"
    )
    op.execute(
        "GRANT EXECUTE ON FUNCTION public.nlc_current_user_is_revenue_staff() TO nlc_app_role"
    )

    for table in ("engagements", "quotations"):
        op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE public.{table} FORCE ROW LEVEL SECURITY")

    op.execute("DROP POLICY IF EXISTS engagements_staff_only ON public.engagements")
    op.execute(
        "DROP POLICY IF EXISTS engagements_revenue_staff_only ON public.engagements"
    )
    op.execute(
        """
        CREATE POLICY engagements_revenue_staff_only ON public.engagements
        FOR ALL
        USING (public.nlc_current_user_is_revenue_staff())
        WITH CHECK (public.nlc_current_user_is_revenue_staff())
        """
    )

    # General staff includes LEGAL_STAFF. The client-membership fallback
    # must not let legal staff inherit billing/quotation visibility.
    op.execute("DROP POLICY IF EXISTS quotations_company_read ON public.quotations")
    op.execute("DROP POLICY IF EXISTS quotations_staff_write ON public.quotations")
    op.execute(
        """
        CREATE POLICY quotations_company_read ON public.quotations
        FOR SELECT
        USING (
            public.nlc_current_user_is_revenue_staff()
            OR (
                NOT public.nlc_current_user_is_staff()
                AND public.nlc_current_user_id() IS NOT NULL
                AND EXISTS (
                    SELECT 1 FROM public.users u
                    WHERE u.id = public.nlc_current_user_id()
                      AND u.is_active IS TRUE
                )
                AND EXISTS (
                    SELECT 1 FROM public.company_user_access cua
                    WHERE cua.company_id = quotations.company_id
                      AND cua.user_id = public.nlc_current_user_id()
                      AND cua.is_active IS TRUE
                      AND cua.can_view_financials IS TRUE
                )
            )
        )
        """
    )
    op.execute(
        """
        CREATE POLICY quotations_staff_write ON public.quotations
        FOR ALL
        USING (public.nlc_current_user_is_revenue_staff())
        WITH CHECK (public.nlc_current_user_is_revenue_staff())
        """
    )

    for view in AGGREGATE_VIEWS:
        op.execute(
            f"ALTER VIEW public.{view} SET (security_invoker = true)"
        )


def downgrade() -> None:
    # Forward-only: reverting view ownership semantics or widening commercial
    # access would reintroduce cross-tenant or legal-staff revenue exposure.
    pass
