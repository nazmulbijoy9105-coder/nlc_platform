"""Restrict staff RLS writes and reassert append-only score history.

Revision ID: 0122_rls_staff_scope_and_score_history
Revises: 0121_merge_alias_and_finding_context_heads

Legal staff may access only assigned/member companies. They must not grant
themselves arbitrary tenant memberships or mutate other users' accounts.
Compliance score history remains append-only even if earlier schema state
was manually drifted after migration 0113.
"""
from alembic import op

revision = "0122_rls_staff_scope_and_score_history"
down_revision = "0121_merge_alias_and_finding_context_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # A LEGAL_STAFF user is staff for company-scoped access, not an account or
    # tenant-membership administrator. Preserve the trusted ADMIN service
    # principal and SUPER_ADMIN / ADMIN_STAFF administrative workflows.
    op.execute(
        "DROP POLICY IF EXISTS users_staff_write ON public.users"
    )
    op.execute("""
        CREATE POLICY users_admin_write ON public.users
        FOR ALL
        USING (
            public.nlc_current_user_principal() = 'ADMIN'
            OR public.nlc_current_user_is_rule_admin()
        )
        WITH CHECK (
            public.nlc_current_user_principal() = 'ADMIN'
            OR public.nlc_current_user_is_rule_admin()
        )
    """)

    op.execute(
        "DROP POLICY IF EXISTS company_user_access_staff_write "
        "ON public.company_user_access"
    )
    op.execute("""
        CREATE POLICY company_user_access_admin_write
        ON public.company_user_access
        FOR ALL
        USING (
            public.nlc_current_user_principal() = 'ADMIN'
            OR public.nlc_current_user_is_rule_admin()
        )
        WITH CHECK (
            public.nlc_current_user_principal() = 'ADMIN'
            OR public.nlc_current_user_is_rule_admin()
        )
    """)

    # Staff can inspect membership records only for companies they can
    # legitimately access. A staff role alone is not a global tenant grant.
    op.execute(
        "DROP POLICY IF EXISTS company_user_access_self_read "
        "ON public.company_user_access"
    )
    op.execute("""
        CREATE POLICY company_user_access_scoped_read
        ON public.company_user_access
        FOR SELECT
        USING (
            user_id = public.nlc_current_user_id()
            OR public.nlc_current_user_principal() = 'ADMIN'
            OR public.nlc_current_user_is_rule_admin()
            OR (
                public.nlc_current_user_is_staff()
                AND public.nlc_can_access_company(company_id)
            )
        )
    """)

    # Reassert 0113's append-only invariant. This is deliberately idempotent:
    # it repairs a drifted database as well as a database where 0113 ran.
    op.execute(
        "REVOKE UPDATE, DELETE ON TABLE public.compliance_score_history "
        "FROM nlc_app_role"
    )
    op.execute(
        "DROP POLICY IF EXISTS compliance_score_history_tenant_update "
        "ON public.compliance_score_history"
    )
    op.execute(
        "DROP POLICY IF EXISTS compliance_score_history_tenant_delete "
        "ON public.compliance_score_history"
    )
    op.execute("""
        CREATE OR REPLACE FUNCTION public.prevent_compliance_score_history_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $function$
        BEGIN
            RAISE EXCEPTION
                'compliance_score_history is append-only: % is forbidden',
                TG_OP
                USING ERRCODE = '55000';
        END;
        $function$
    """)
    op.execute(
        "DROP TRIGGER IF EXISTS trg_compliance_score_history_append_only "
        "ON public.compliance_score_history"
    )
    op.execute("""
        CREATE TRIGGER trg_compliance_score_history_append_only
        BEFORE UPDATE OR DELETE ON public.compliance_score_history
        FOR EACH ROW
        EXECUTE FUNCTION public.prevent_compliance_score_history_mutation()
    """)
    op.execute(
        "REVOKE ALL ON FUNCTION "
        "public.prevent_compliance_score_history_mutation() FROM PUBLIC"
    )


def downgrade() -> None:
    raise RuntimeError(
        "0122 is forward-only: do not restore broad staff tenant writes or "
        "mutable compliance score history."
    )
