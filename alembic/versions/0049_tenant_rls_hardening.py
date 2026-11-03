"""Harden tenant RLS coverage and application-role privileges.

Revision ID: 0049_tenant_rls_hardening
Revises: 0048_articles_verification

This migration is deliberately additive and does not change the Render database
connection role. Runtime-role cutover is a separate release gate because login,
worker, and administrative paths must first be proven to use the correct role.
"""
from alembic import op
import sqlalchemy as sa

revision = "0049_tenant_rls_hardening"
down_revision = "0048_articles_verification"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SECURITY DEFINER helpers read membership and role records without
    # recursively invoking RLS on those same tables. search_path is pinned to
    # prevent object-shadowing attacks. The migration owner owns these helpers.
    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_current_user_id()
        RETURNS uuid
        LANGUAGE plpgsql
        STABLE
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $$
        DECLARE
            v text;
        BEGIN
            v := current_setting('app.current_user_id', true);
            IF v IS NULL OR v !~* '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' THEN
                RETURN NULL;
            END IF;
            RETURN v::uuid;
        END;
        $$;
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_current_user_is_staff()
        RETURNS boolean
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $$
            SELECT
                current_setting('app.current_user_id', true) = 'ADMIN'
                OR EXISTS (
                    SELECT 1
                    FROM public.users u
                    WHERE u.id = public.nlc_current_user_id()
                      AND u.is_active IS TRUE
                      AND u.role::text IN ('SUPER_ADMIN', 'ADMIN_STAFF', 'LEGAL_STAFF')
                )
        $$;
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_can_access_company(p_company_id uuid)
        RETURNS boolean
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $$
            SELECT
                public.nlc_current_user_is_staff()
                OR (
                    public.nlc_current_user_id() IS NOT NULL
                    AND EXISTS (
                        SELECT 1
                        FROM public.company_user_access cua
                        WHERE cua.company_id = p_company_id
                          AND cua.user_id = public.nlc_current_user_id()
                          AND cua.is_active IS TRUE
                    )
                )
        $$;
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_can_access_document(p_document_id uuid)
        RETURNS boolean
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $$
            SELECT EXISTS (
                SELECT 1
                FROM public.documents d
                WHERE d.id = p_document_id
                  AND public.nlc_can_access_company(d.company_id)
            )
        $$;
    """)

    # Remove default PUBLIC execution on privileged helpers. Grant only to the
    # dedicated application role when it exists (CI databases may not create it).
    op.execute("""
        REVOKE ALL ON FUNCTION public.nlc_current_user_id() FROM PUBLIC;
        REVOKE ALL ON FUNCTION public.nlc_current_user_is_staff() FROM PUBLIC;
        REVOKE ALL ON FUNCTION public.nlc_can_access_company(uuid) FROM PUBLIC;
        REVOKE ALL ON FUNCTION public.nlc_can_access_document(uuid) FROM PUBLIC;
        DO $grant$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nlc_app_role') THEN
                GRANT EXECUTE ON FUNCTION public.nlc_current_user_id() TO nlc_app_role;
                GRANT EXECUTE ON FUNCTION public.nlc_current_user_is_staff() TO nlc_app_role;
                GRANT EXECUTE ON FUNCTION public.nlc_can_access_company(uuid) TO nlc_app_role;
                GRANT EXECUTE ON FUNCTION public.nlc_can_access_document(uuid) TO nlc_app_role;
            END IF;
        END
        $grant$;
    """)

    # Company rows use id; all other tenant tables use company_id. Keep
    # engagements_admin_only unchanged: commercial engagement records remain
    # staff-only under the existing policy.
    op.execute("""
        ALTER TABLE public.companies ENABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS companies_access_policy ON public.companies;
        CREATE POLICY companies_tenant_access ON public.companies
            FOR ALL
            USING (public.nlc_can_access_company(id))
            WITH CHECK (public.nlc_can_access_company(id));
    """)

    tenant_tables = (
        "agms",
        "annual_returns",
        "audits",
        "compliance_flags",
        "compliance_score_history",
        "directors",
        "documents",
        "notifications",
        "registered_office_history",
        "rescue_plans",
        "rescue_steps",
        "rjsc_form_filings",
        "share_transfers",
        "shareholders",
        "statutory_registers",
        "tasks",
        "ai_output_log",
        "compliance_calendar_events",
        "compliance_events",
        "quotations",
        "articles_verifications",
        "rescue_audit_log",
    )
    for table in tenant_tables:
        op.execute(sa.text(f"""
            ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY;
            DROP POLICY IF EXISTS {table}_company_policy ON public.{table};
            DROP POLICY IF EXISTS {table}_tenant_access ON public.{table};
            CREATE POLICY {table}_tenant_access ON public.{table}
                FOR ALL
                USING (public.nlc_can_access_company(company_id))
                WITH CHECK (public.nlc_can_access_company(company_id));
        """))

    # Membership rows: users may inspect their own active/inactive grants;
    # only current staff may grant, change, or revoke memberships.
    op.execute("""
        ALTER TABLE public.company_user_access ENABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS company_user_access_self_read ON public.company_user_access;
        DROP POLICY IF EXISTS company_user_access_staff_write ON public.company_user_access;
        CREATE POLICY company_user_access_self_read ON public.company_user_access
            FOR SELECT
            USING (
                user_id = public.nlc_current_user_id()
                OR public.nlc_current_user_is_staff()
            );
        CREATE POLICY company_user_access_staff_write ON public.company_user_access
            FOR ALL
            USING (public.nlc_current_user_is_staff())
            WITH CHECK (public.nlc_current_user_is_staff());
    """)

    # User records: self access is required for authenticated profile reads;
    # staff access supports administration. Login/registration must use the
    # separately configured auth connection or privileged auth function.
    op.execute("""
        ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS users_self_or_staff ON public.users;
        CREATE POLICY users_self_or_staff ON public.users
            FOR ALL
            USING (
                id = public.nlc_current_user_id()
                OR public.nlc_current_user_is_staff()
            )
            WITH CHECK (
                id = public.nlc_current_user_id()
                OR public.nlc_current_user_is_staff()
            );
    """)

    # Access-log rows inherit the tenant boundary from their parent document.
    op.execute("""
        ALTER TABLE public.document_access_log ENABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS document_access_log_document_tenant ON public.document_access_log;
        CREATE POLICY document_access_log_document_tenant ON public.document_access_log
            FOR ALL
            USING (
                public.nlc_current_user_is_staff()
                OR public.nlc_can_access_document(document_id)
            )
            WITH CHECK (
                public.nlc_current_user_is_staff()
                OR public.nlc_can_access_document(document_id)
            );
    """)

    # User activity records are scoped by both actor and (when present) company.
    op.execute("""
        ALTER TABLE public.user_activity_logs ENABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS user_activity_logs_actor_tenant ON public.user_activity_logs;
        CREATE POLICY user_activity_logs_actor_tenant ON public.user_activity_logs
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
            );
    """)

    # Global reference/corpus data is readable to authenticated sessions.
    # Mutations remain staff-only. The migration version table is not a
    # runtime API and is explicitly unavailable to the application role.
    for table in ("ai_prompt_templates", "legal_rules", "legal_rule_versions", "regulatory_rules", "sro_registry"):
        op.execute(sa.text(f"""
            ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY;
            DROP POLICY IF EXISTS {table}_authenticated_read ON public.{table};
            DROP POLICY IF EXISTS {table}_staff_write ON public.{table};
            CREATE POLICY {table}_authenticated_read ON public.{table}
                FOR SELECT
                USING (
                    public.nlc_current_user_id() IS NOT NULL
                    OR public.nlc_current_user_is_staff()
                );
            CREATE POLICY {table}_staff_write ON public.{table}
                FOR ALL
                USING (public.nlc_current_user_is_staff())
                WITH CHECK (public.nlc_current_user_is_staff());
        """))

    # TRUNCATE bypasses RLS. Runtime code must not be able to create triggers or
    # foreign keys. Preserve ordinary DML grants for application workflows.
    op.execute("""
        DO $privileges$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nlc_app_role') THEN
                REVOKE TRUNCATE, REFERENCES, TRIGGER ON ALL TABLES IN SCHEMA public FROM nlc_app_role;
                REVOKE ALL ON TABLE public.alembic_version FROM nlc_app_role;
            END IF;
        END
        $privileges$;
    """)


def downgrade() -> None:
    # Forward-only security hardening. Removing tenant policies would reopen
    # cross-tenant access; use a reviewed forward migration for any correction.
    pass
