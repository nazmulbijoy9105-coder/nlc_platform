"""Bind activity-log reads to tenant scope and writes to the signed actor.

Revision ID: 0088_strict_activity_log_actor_tenant
Revises: 0087_legal_staff_company_scope

Finance administrators retain portfolio-wide audit visibility. Legal staff
may inspect audit events only for assigned companies. Every human-created
activity event must identify the signed actor and an accessible company.
"""
from alembic import op
import sqlalchemy as sa

revision = "0088_strict_activity_log_actor_tenant"
down_revision = "0087_legal_staff_company_scope"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    required_helpers = (
        "public.nlc_current_user_principal()",
        "public.nlc_current_user_id()",
        "public.nlc_current_user_is_finance_staff()",
        "public.nlc_can_access_company(uuid)",
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
            "Strict activity-log policy requires signed actor and tenant helpers: "
            + ", ".join(missing)
        )

    op.execute(
        "DROP POLICY IF EXISTS user_activity_logs_actor_tenant "
        "ON public.user_activity_logs"
    )
    op.execute("""
        CREATE POLICY user_activity_logs_actor_tenant
        ON public.user_activity_logs
        FOR ALL
        USING (
            public.nlc_current_user_is_finance_staff()
            OR (
                user_id = public.nlc_current_user_id()
                AND (company_id IS NULL OR public.nlc_can_access_company(company_id))
            )
            OR (
                company_id IS NOT NULL
                AND public.nlc_can_access_company(company_id)
                AND EXISTS (
                    SELECT 1
                    FROM public.users actor
                    WHERE actor.id = public.nlc_current_user_id()
                      AND actor.is_active IS TRUE
                      AND actor.role::text = 'LEGAL_STAFF'
                )
            )
        )
        WITH CHECK (
            public.nlc_current_user_principal() = 'ADMIN'
            OR (
                user_id = public.nlc_current_user_id()
                AND (company_id IS NULL OR public.nlc_can_access_company(company_id))
            )
        )
    """)


def downgrade() -> None:
    # Forward-only: restoring the generic staff bypass would reopen
    # cross-tenant audit-log visibility and permit actor spoofing.
    pass
