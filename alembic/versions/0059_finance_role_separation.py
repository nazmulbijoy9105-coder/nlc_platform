"""Separate finance privileges from general legal staff privileges.

Revision ID: 0059_finance_role_separation
Revises: 0058_suppress_unreleased_rule_notifications

Human sessions remain bound to their signed user UUID. Billing-specific
helpers grant internal finance privileges only to SUPER_ADMIN and ADMIN_STAFF;
client company permissions are evaluated separately.
"""
from alembic import op

revision = "0059_finance_role_separation"
down_revision = "0058_suppress_unreleased_rule_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_current_user_is_finance_staff()
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
    """)

    op.execute("""
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
                        SELECT 1
                        FROM public.users u
                        WHERE u.id = public.nlc_current_user_id()
                          AND u.is_active IS TRUE
                    )
                    AND EXISTS (
                        SELECT 1
                        FROM public.company_user_access cua
                        WHERE cua.company_id = p_company_id
                          AND cua.user_id = public.nlc_current_user_id()
                          AND cua.is_active IS TRUE
                          AND cua.can_view_financials IS TRUE
                    )
                )
        $function$
    """)

    op.execute("""
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
                        SELECT 1
                        FROM public.users u
                        WHERE u.id = public.nlc_current_user_id()
                          AND u.is_active IS TRUE
                    )
                    AND EXISTS (
                        SELECT 1
                        FROM public.company_user_access cua
                        WHERE cua.company_id = p_company_id
                          AND cua.user_id = public.nlc_current_user_id()
                          AND cua.is_active IS TRUE
                          AND cua.can_edit IS TRUE
                          AND cua.can_view_financials IS TRUE
                    )
                )
        $function$
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_can_manage_billing_company(p_company_id uuid)
        RETURNS boolean
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $function$
            SELECT public.nlc_current_user_is_finance_staff()
        $function$
    """)

    for signature in (
        "nlc_current_user_is_finance_staff()",
        "nlc_can_view_billing_company(uuid)",
        "nlc_can_submit_payment_company(uuid)",
        "nlc_can_manage_billing_company(uuid)",
    ):
        op.execute(f"REVOKE ALL ON FUNCTION public.{signature} FROM PUBLIC")
        op.execute(f"GRANT EXECUTE ON FUNCTION public.{signature} TO nlc_app_role")


def downgrade() -> None:
    # Forward-only security migration. Removing these helpers could weaken
    # billing authorization after financial tables have adopted them.
    pass
