"""Validate signed runtime identity and normalize activity-log RLS policies.

Revision ID: 0051_signed_rls_identity_validation
Revises: 0050_agm_evidence_verification

The signing key and HMAC verification are provisioned by 0049. This migration
adds an explicit validity helper, requires active users for tenant access, and
removes legacy permissive activity-log policies that would be OR-combined.
"""
from alembic import op

revision = "0051_signed_rls_identity_validation"
down_revision = "0050_agm_evidence_verification"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_current_user_context_valid()
        RETURNS boolean
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $function$
            SELECT public.nlc_current_user_principal() IS NOT NULL
        $function$
    """)
    op.execute(
        "REVOKE ALL ON FUNCTION public.nlc_current_user_context_valid() FROM PUBLIC"
    )
    op.execute("""
        DO $grant$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nlc_app_role') THEN
                GRANT EXECUTE ON FUNCTION public.nlc_current_user_context_valid() TO nlc_app_role;
            END IF;
        END;
        $grant$
    """)

    # Membership alone is insufficient: deactivated accounts must lose
    # tenant access even if a stale membership row remains active.
    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_can_access_company(p_company_id uuid)
        RETURNS boolean
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $function$
            SELECT
                public.nlc_current_user_is_staff()
                OR (
                    public.nlc_current_user_id() IS NOT NULL
                    AND EXISTS (
                        SELECT 1
                        FROM public.users active_user
                        WHERE active_user.id = public.nlc_current_user_id()
                          AND active_user.is_active IS TRUE
                    )
                    AND EXISTS (
                        SELECT 1
                        FROM public.company_user_access cua
                        WHERE cua.company_id = p_company_id
                          AND cua.user_id = public.nlc_current_user_id()
                          AND cua.is_active IS TRUE
                    )
                )
        $function$
    """)

    # PostgreSQL combines permissive policies with OR. Remove every legacy
    # policy on this table before installing the single strict actor+tenant
    # policy; merely adding a stricter policy would not narrow existing access.
    op.execute("""
        DO $policies$
        DECLARE
            p record;
        BEGIN
            FOR p IN
                SELECT policyname
                FROM pg_policies
                WHERE schemaname = 'public'
                  AND tablename = 'user_activity_logs'
            LOOP
                EXECUTE format(
                    'DROP POLICY %I ON public.user_activity_logs',
                    p.policyname
                );
            END LOOP;
        END;
        $policies$
    """)
    op.execute("""
        CREATE POLICY user_activity_logs_actor_tenant
        ON public.user_activity_logs
        FOR ALL
        USING (
            public.nlc_current_user_is_staff()
            OR (
                user_id = public.nlc_current_user_id()
                AND (
                    company_id IS NULL
                    OR public.nlc_can_access_company(company_id)
                )
            )
        )
        WITH CHECK (
            public.nlc_current_user_is_staff()
            OR (
                user_id = public.nlc_current_user_id()
                AND (
                    company_id IS NULL
                    OR public.nlc_can_access_company(company_id)
                )
            )
        )
    """)

    # Evidence tables are legally significant records. Company membership
    # permits read access only; submissions, reviews and revocations require
    # trusted staff identity. Remove all earlier permissive membership-wide
    # write policies before installing operation-specific policies.
    evidence_tables = (
        "articles_verifications",
        "articles_verification_events",
        "agm_evidence_verifications",
        "agm_evidence_verification_events",
    )
    for table in evidence_tables:
        op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE public.{table} FORCE ROW LEVEL SECURITY")
        op.execute(f"""
            DO $evidence_policies$
            DECLARE p record;
            BEGIN
                FOR p IN
                    SELECT policyname
                    FROM pg_policies
                    WHERE schemaname = 'public' AND tablename = '{table}'
                LOOP
                    EXECUTE format(
                        'DROP POLICY %I ON public.{table}',
                        p.policyname
                    );
                END LOOP;
            END;
            $evidence_policies$
        """)
        op.execute(f"""
            CREATE POLICY {table}_company_read
            ON public.{table}
            FOR SELECT
            USING (public.nlc_can_access_company(company_id))
        """)
        if table.endswith("_events"):
            op.execute(f"""
                CREATE POLICY {table}_staff_insert
                ON public.{table}
                FOR INSERT
                WITH CHECK (
                    public.nlc_current_user_is_staff()
                    AND public.nlc_can_access_company(company_id)
                )
            """)
            op.execute(
                f"REVOKE UPDATE, DELETE, TRUNCATE ON TABLE public.{table} FROM nlc_app_role"
            )
        else:
            op.execute(f"""
                CREATE POLICY {table}_staff_insert
                ON public.{table}
                FOR INSERT
                WITH CHECK (
                    public.nlc_current_user_is_staff()
                    AND public.nlc_can_access_company(company_id)
                )
            """)
            op.execute(f"""
                CREATE POLICY {table}_staff_update
                ON public.{table}
                FOR UPDATE
                USING (
                    public.nlc_current_user_is_staff()
                    AND public.nlc_can_access_company(company_id)
                )
                WITH CHECK (
                    public.nlc_current_user_is_staff()
                    AND public.nlc_can_access_company(company_id)
                )
            """)
            op.execute(
                f"REVOKE DELETE, TRUNCATE ON TABLE public.{table} FROM nlc_app_role"
            )



def downgrade() -> None:
    # Forward-only security migration: dropping the active-user check or
    # restoring legacy permissive policies would weaken tenant isolation.
    pass
