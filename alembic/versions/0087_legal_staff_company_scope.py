"""Restrict legal staff RLS access to explicitly assigned companies.

Revision ID: 0087_legal_staff_company_scope
Revises: 0086_runtime_role_membership_preflight

General staff identity is not equivalent to portfolio-wide company access.
Only SUPER_ADMIN and ADMIN_STAFF retain global company and financial access.
LEGAL_STAFF must be assigned to the company or have an active company access
row; legal staff never inherit financial visibility from a company membership.
"""
from alembic import op
import sqlalchemy as sa

revision = "0087_legal_staff_company_scope"
down_revision = "0086_runtime_role_membership_preflight"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    required_helpers = (
        "public.nlc_current_user_principal()",
        "public.nlc_current_user_id()",
        "public.nlc_current_user_is_finance_staff()",
    )
    missing = [
        helper
        for helper in required_helpers
        if bind.execute(
            sa.text("SELECT to_regprocedure(:signature)"),
            {"signature": helper},
        ).scalar_one() is None
    ]
    if missing:
        raise RuntimeError(
            "Legal-staff RLS scope migration requires existing signed identity "
            "and finance helpers: " + ", ".join(missing)
        )

    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_can_access_company(p_company_id uuid)
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
                      AND (
                          u.role::text IN ('SUPER_ADMIN', 'ADMIN_STAFF')
                          OR (
                              u.role::text = 'LEGAL_STAFF'
                              AND (
                                  EXISTS (
                                      SELECT 1
                                      FROM public.companies c
                                      WHERE c.id = p_company_id
                                        AND c.assigned_staff_id = u.id
                                  )
                                  OR EXISTS (
                                      SELECT 1
                                      FROM public.company_user_access cua
                                      WHERE cua.company_id = p_company_id
                                        AND cua.user_id = u.id
                                        AND cua.is_active IS TRUE
                                  )
                              )
                          )
                          OR (
                              u.role::text IN ('CLIENT_DIRECTOR', 'CLIENT_VIEW_ONLY')
                              AND EXISTS (
                                  SELECT 1
                                  FROM public.company_user_access cua
                                  WHERE cua.company_id = p_company_id
                                    AND cua.user_id = u.id
                                    AND cua.is_active IS TRUE
                              )
                          )
                      )
                ),
                FALSE
            )
        $function$
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_can_edit_company(p_company_id uuid)
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
                      AND (
                          u.role::text IN ('SUPER_ADMIN', 'ADMIN_STAFF')
                          OR (
                              u.role::text = 'LEGAL_STAFF'
                              AND (
                                  EXISTS (
                                      SELECT 1
                                      FROM public.companies c
                                      WHERE c.id = p_company_id
                                        AND c.assigned_staff_id = u.id
                                  )
                                  OR EXISTS (
                                      SELECT 1
                                      FROM public.company_user_access cua
                                      WHERE cua.company_id = p_company_id
                                        AND cua.user_id = u.id
                                        AND cua.is_active IS TRUE
                                  )
                              )
                          )
                          OR (
                              u.role::text = 'CLIENT_DIRECTOR'
                              AND EXISTS (
                                  SELECT 1
                                  FROM public.company_user_access cua
                                  WHERE cua.company_id = p_company_id
                                    AND cua.user_id = u.id
                                    AND cua.is_active IS TRUE
                                    AND cua.can_edit IS TRUE
                              )
                          )
                      )
                ),
                FALSE
            )
        $function$
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_can_view_financials_company(p_company_id uuid)
        RETURNS boolean
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $function$
            SELECT public.nlc_current_user_is_finance_staff()
                OR (
                    public.nlc_current_user_id() IS NOT NULL
                    AND EXISTS (
                        SELECT 1
                        FROM public.users u
                        JOIN public.company_user_access cua
                          ON cua.user_id = u.id
                        WHERE u.id = public.nlc_current_user_id()
                          AND u.is_active IS TRUE
                          AND u.role::text IN ('CLIENT_DIRECTOR', 'CLIENT_VIEW_ONLY')
                          AND cua.company_id = p_company_id
                          AND cua.is_active IS TRUE
                          AND cua.can_view_financials IS TRUE
                    )
                )
        $function$
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_can_manage_financials_company(p_company_id uuid)
        RETURNS boolean
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $function$
            SELECT public.nlc_current_user_is_finance_staff()
                OR (
                    public.nlc_current_user_id() IS NOT NULL
                    AND EXISTS (
                        SELECT 1
                        FROM public.users u
                        JOIN public.company_user_access cua
                          ON cua.user_id = u.id
                        WHERE u.id = public.nlc_current_user_id()
                          AND u.is_active IS TRUE
                          AND u.role::text = 'CLIENT_DIRECTOR'
                          AND cua.company_id = p_company_id
                          AND cua.is_active IS TRUE
                          AND cua.can_edit IS TRUE
                          AND cua.can_view_financials IS TRUE
                    )
                )
        $function$
    """)

    for signature in (
        "nlc_can_access_company(uuid)",
        "nlc_can_edit_company(uuid)",
        "nlc_can_view_financials_company(uuid)",
        "nlc_can_manage_financials_company(uuid)",
    ):
        op.execute(f"REVOKE ALL ON FUNCTION public.{signature} FROM PUBLIC")
        op.execute(f"GRANT EXECUTE ON FUNCTION public.{signature} TO nlc_app_role")


def downgrade() -> None:
    # Forward-only: restoring broad legal-staff access would reopen tenant
    # and financial disclosure across the entire company portfolio.
    pass
