"""Harden tenant RLS coverage and application-role privileges.

Revision ID: 0049_tenant_rls_hardening
Revises: 0048_articles_verification

This migration is deliberately additive and does not change the Render database
connection role. Runtime-role cutover is a separate release gate because login,
worker, and administrative paths must first be proven to use the correct role.
"""
import os

from alembic import op
import sqlalchemy as sa

revision = "0049_tenant_rls_hardening"
down_revision = "0048_articles_verification"
branch_labels = None
depends_on = None



def _execute_sql_script(sql: str) -> None:
    """Execute a PostgreSQL script statement-by-statement for asyncpg."""
    start = 0
    i = 0
    single_quoted = False
    dollar_tag = None
    while i < len(sql):
        if dollar_tag:
            if sql.startswith(dollar_tag, i):
                i += len(dollar_tag)
                dollar_tag = None
                continue
            i += 1
            continue
        char = sql[i]
        if single_quoted:
            if char == "'" and i + 1 < len(sql) and sql[i + 1] == "'":
                i += 2
                continue
            if char == "'":
                single_quoted = False
            i += 1
            continue
        if char == "'":
            single_quoted = True
            i += 1
            continue
        if char == "$":
            end = sql.find("$", i + 1)
            if end != -1:
                tag = sql[i:end + 1]
                if all(c.isalnum() or c == "_" for c in tag[1:-1]):
                    dollar_tag = tag
                    i = end + 1
                    continue
        if char == ";":
            statement = sql[start:i].strip()
            if statement:
                op.execute(statement)
            start = i + 1
        i += 1
    tail = sql[start:].strip()
    if tail:
        op.execute(tail)

def upgrade() -> None:
    # Ensure the non-bypass runtime role exists in fresh CI databases too.
    # Production already has this role; this is intentionally a no-op there.
    _execute_sql_script("""
        DO $role$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nlc_app_role') THEN
                CREATE ROLE nlc_app_role
                    NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
                    NOINHERIT NOREPLICATION NOBYPASSRLS;
            END IF;
        END
        $role$
    """)
    # SECURITY DEFINER helpers read membership and role records without
    # recursively invoking RLS on those same tables. search_path is pinned to
    # prevent object-shadowing attacks. The migration owner owns these helpers.
    # App-side HMAC is verified in PostgreSQL. The runtime role cannot read
    # the signing key or invoke any function that signs an arbitrary principal.
    signing_key = os.environ.get("JWT_SECRET_KEY", "")
    if len(signing_key) < 32:
        raise RuntimeError("JWT_SECRET_KEY (minimum 32 characters) is required for signed RLS context")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public")
    op.execute("""
        CREATE TABLE IF NOT EXISTS public.nlc_rls_security_config (
            singleton boolean PRIMARY KEY DEFAULT TRUE CHECK (singleton),
            signing_key bytea NOT NULL,
            updated_at timestamptz NOT NULL DEFAULT now()
        )
    """)
    op.get_bind().execute(
        sa.text("""
            INSERT INTO public.nlc_rls_security_config(singleton, signing_key)
            VALUES (TRUE, :signing_key)
            ON CONFLICT (singleton) DO UPDATE
            SET signing_key = EXCLUDED.signing_key, updated_at = now()
        """),
        {"signing_key": signing_key.encode("utf-8")},
    )
    _execute_sql_script("""
        REVOKE ALL ON TABLE public.nlc_rls_security_config FROM PUBLIC;
        DO $secret_privileges$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nlc_app_role') THEN
                REVOKE ALL ON TABLE public.nlc_rls_security_config FROM nlc_app_role;
            END IF;
        END
        $secret_privileges$;
    """)
    _execute_sql_script("""
        CREATE OR REPLACE FUNCTION public.nlc_current_user_context_valid()
        RETURNS boolean
        LANGUAGE plpgsql
        STABLE
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $$
        DECLARE
            principal text;
            supplied_signature text;
            key_bytes bytea;
            expected_signature text;
        BEGIN
            principal := current_setting('app.current_user_id', true);
            supplied_signature := current_setting('app.current_user_signature', true);
            IF principal IS NULL OR supplied_signature IS NULL
               OR principal = '' OR supplied_signature !~ '^[0-9a-f]{64}$' THEN
                RETURN FALSE;
            END IF;
            SELECT cfg.signing_key INTO key_bytes
            FROM public.nlc_rls_security_config AS cfg
            WHERE cfg.singleton IS TRUE;
            IF key_bytes IS NULL THEN
                RETURN FALSE;
            END IF;
            expected_signature := encode(
                public.hmac(convert_to(principal, 'UTF8'), key_bytes, 'sha256'),
                'hex'
            );
            RETURN expected_signature = lower(supplied_signature);
        EXCEPTION WHEN OTHERS THEN
            RETURN FALSE;
        END;
        $$
    """)
    _execute_sql_script("""
        CREATE OR REPLACE FUNCTION public.nlc_current_user_id()
        RETURNS uuid
        LANGUAGE plpgsql
        STABLE
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $$
        DECLARE
            principal text;
        BEGIN
            IF NOT public.nlc_current_user_context_valid() THEN
                RETURN NULL;
            END IF;
            principal := current_setting('app.current_user_id', true);
            IF principal !~* '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' THEN
                RETURN NULL;
            END IF;
            RETURN principal::uuid;
        END;
        $$
    """)
    # Login needs one narrowly-scoped lookup before a user ID is available
    # for the normal transaction-local RLS context. It is callable only by the
    # backend application role and returns one matching account row.
    _execute_sql_script("""
        CREATE OR REPLACE FUNCTION public.nlc_auth_user_by_email(p_email text)
        RETURNS SETOF public.users
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS 'SELECT u.* FROM public.users u WHERE lower(u.email) = lower(btrim(p_email)) LIMIT 1'
    """)
    op.execute("REVOKE ALL ON FUNCTION public.nlc_auth_user_by_email(text) FROM PUBLIC")
    _execute_sql_script("""
        DO $auth_grant$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nlc_app_role') THEN
                GRANT EXECUTE ON FUNCTION public.nlc_auth_user_by_email(text) TO nlc_app_role;
            END IF;
        END
        $auth_grant$
    """)

    _execute_sql_script("""
        CREATE OR REPLACE FUNCTION public.nlc_current_user_is_staff()
        RETURNS boolean
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $
            SELECT (
                public.nlc_current_user_context_valid()
                AND current_setting('app.current_user_id', true) = 'ADMIN'
            ) OR EXISTS (
                SELECT 1
                FROM public.users u
                WHERE u.id = public.nlc_current_user_id()
                  AND u.is_active IS TRUE
                  AND u.role::text IN ('SUPER_ADMIN', 'ADMIN_STAFF', 'LEGAL_STAFF')
            )
        $;
    """)

    _execute_sql_script("""
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

    _execute_sql_script("""
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
    _execute_sql_script("""
        REVOKE ALL ON FUNCTION public.nlc_current_user_context_valid() FROM PUBLIC;
        REVOKE ALL ON FUNCTION public.nlc_current_user_id() FROM PUBLIC;
        REVOKE ALL ON FUNCTION public.nlc_current_user_is_staff() FROM PUBLIC;
        REVOKE ALL ON FUNCTION public.nlc_can_access_company(uuid) FROM PUBLIC;
        REVOKE ALL ON FUNCTION public.nlc_can_access_document(uuid) FROM PUBLIC;
        DO $grant$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nlc_app_role') THEN
                GRANT EXECUTE ON FUNCTION public.nlc_current_user_context_valid() TO nlc_app_role;
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
    _execute_sql_script("""
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
        "articles_verification_events",
    )
    for table in tenant_tables:
        _execute_sql_script(f"""
            ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY;
            DROP POLICY IF EXISTS {table}_company_policy ON public.{table};
            DROP POLICY IF EXISTS {table}_tenant_access ON public.{table};
            CREATE POLICY {table}_tenant_access ON public.{table}
                FOR ALL
                USING (public.nlc_can_access_company(company_id))
                WITH CHECK (public.nlc_can_access_company(company_id));
        """)

    # Commercial engagements are staff-only. Replace the legacy ADMIN
    # sentinel check so authenticated staff requests use their real user ID.
    _execute_sql_script("""
        ALTER TABLE public.engagements ENABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS engagements_admin_only ON public.engagements;
        DROP POLICY IF EXISTS engagements_staff_only ON public.engagements;
        CREATE POLICY engagements_staff_only ON public.engagements
            FOR ALL
            USING (public.nlc_current_user_is_staff())
            WITH CHECK (public.nlc_current_user_is_staff());
    """)

    # PostgreSQL views otherwise execute with the view owner's privileges and
    # can bypass base-table RLS. Force invoker permissions for every dashboard
    # view so the same tenant policies apply to view queries.
    for view in (
        "vw_admin_dashboard_kpis",
        "vw_company_flag_summary",
        "vw_revenue_pipeline",
        "vw_risk_distribution",
        "vw_upcoming_deadlines",
    ):
        op.execute(sa.text(f"ALTER VIEW public.{view} SET (security_invoker = true)"))

    # Membership rows: users may inspect their own active/inactive grants;
    # only current staff may grant, change, or revoke memberships.
    _execute_sql_script("""
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

    # User records: self access is required for authentication/profile
    # workflows. A trigger prevents self-service role or activation changes;
    # only current staff may change those authorization-critical attributes.
    _execute_sql_script("""
        CREATE OR REPLACE FUNCTION public.nlc_protect_user_security_fields()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $$
        BEGIN
            IF NOT public.nlc_current_user_is_staff()
               AND (
                   NEW.role IS DISTINCT FROM OLD.role
                   OR NEW.is_active IS DISTINCT FROM OLD.is_active
               ) THEN
                RAISE EXCEPTION 'Only authorized staff may change user role or activation state'
                    USING ERRCODE = '42501';
            END IF;
            RETURN NEW;
        END;
        $$
    """)
    _execute_sql_script("""
        DROP TRIGGER IF EXISTS users_protect_security_fields ON public.users;
        CREATE TRIGGER users_protect_security_fields
            BEFORE UPDATE ON public.users
            FOR EACH ROW
            EXECUTE FUNCTION public.nlc_protect_user_security_fields();
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

    # Rescue audit rows inherit tenant scope through their rescue plan.
    _execute_sql_script("""
        ALTER TABLE public.rescue_audit_log ENABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS rescue_audit_log_tenant_access ON public.rescue_audit_log;
        CREATE POLICY rescue_audit_log_tenant_access ON public.rescue_audit_log
            FOR ALL
            USING (
                public.nlc_current_user_is_staff()
                OR EXISTS (
                    SELECT 1
                    FROM public.rescue_plans rp
                    WHERE rp.id = rescue_audit_log.rescue_plan_id
                      AND public.nlc_can_access_company(rp.company_id)
                )
            )
            WITH CHECK (
                public.nlc_current_user_is_staff()
                OR EXISTS (
                    SELECT 1
                    FROM public.rescue_plans rp
                    WHERE rp.id = rescue_audit_log.rescue_plan_id
                      AND public.nlc_can_access_company(rp.company_id)
                )
            );
    """)

    # Access-log rows inherit the tenant boundary from their parent document.
    _execute_sql_script("""
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
    _execute_sql_script("""
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

    # Webhooks are user-owned, not company-owned. Replace the earlier policy
    # that attempted to cast the ADMIN sentinel to UUID and denied staff access.
    _execute_sql_script("""
        ALTER TABLE public.webhook_endpoints ENABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS webhook_endpoints_owner_scope ON public.webhook_endpoints;
        CREATE POLICY webhook_endpoints_owner_scope ON public.webhook_endpoints
            FOR ALL
            USING (
                public.nlc_current_user_is_staff()
                OR user_id = public.nlc_current_user_id()
            )
            WITH CHECK (
                public.nlc_current_user_is_staff()
                OR user_id = public.nlc_current_user_id()
            );

        ALTER TABLE public.webhook_deliveries ENABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS webhook_deliveries_owner_scope ON public.webhook_deliveries;
        CREATE POLICY webhook_deliveries_owner_scope ON public.webhook_deliveries
            FOR ALL
            USING (
                public.nlc_current_user_is_staff()
                OR EXISTS (
                    SELECT 1
                    FROM public.webhook_endpoints e
                    WHERE e.id = webhook_deliveries.endpoint_id
                      AND e.user_id = public.nlc_current_user_id()
                )
            )
            WITH CHECK (
                public.nlc_current_user_is_staff()
                OR EXISTS (
                    SELECT 1
                    FROM public.webhook_endpoints e
                    WHERE e.id = webhook_deliveries.endpoint_id
                      AND e.user_id = public.nlc_current_user_id()
                )
            );
    """)

    # Global reference/corpus data is readable to authenticated sessions.
    # Mutations remain staff-only. The migration version table is not a
    # runtime API and is explicitly unavailable to the application role.
    for table in ("ai_prompt_templates", "legal_rules", "legal_rule_versions", "regulatory_rules", "sro_registry"):
        _execute_sql_script(f"""
            ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY;
            DROP POLICY IF EXISTS {table}_authenticated_read ON public.{table};
            DROP POLICY IF EXISTS {table}_staff_write ON public.{table};
            CREATE POLICY {table}_authenticated_read ON public.{table}
                FOR SELECT
                USING (
                    public.nlc_current_user_is_staff()
                    OR EXISTS (
                        SELECT 1
                        FROM public.users u
                        WHERE u.id = public.nlc_current_user_id()
                          AND u.is_active IS TRUE
                    )
                );
            CREATE POLICY {table}_staff_write ON public.{table}
                FOR ALL
                USING (public.nlc_current_user_is_staff())
                WITH CHECK (public.nlc_current_user_is_staff());
        """)

    # TRUNCATE bypasses RLS. Runtime code must not be able to create triggers or
    # foreign keys. New tables may not inherit old default grants, so explicitly
    # grant the DML operations needed by the API before narrowing audit tables.
    _execute_sql_script("""
        DO $privileges$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nlc_app_role') THEN
                REVOKE CREATE ON SCHEMA public FROM nlc_app_role;
                GRANT USAGE ON SCHEMA public TO nlc_app_role;
                EXECUTE 'ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM nlc_app_role';
                EXECUTE 'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO nlc_app_role';

                GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE
                    public.agms,
                    public.annual_returns,
                    public.audits,
                    public.companies,
                    public.company_user_access,
                    public.compliance_flags,
                    public.compliance_score_history,
                    public.directors,
                    public.documents,
                    public.engagements,
                    public.notifications,
                    public.registered_office_history,
                    public.rescue_plans,
                    public.rescue_steps,
                    public.rjsc_form_filings,
                    public.share_transfers,
                    public.shareholders,
                    public.statutory_registers,
                    public.tasks,
                    public.ai_output_log,
                    public.compliance_calendar_events,
                    public.compliance_events,
                    public.quotations,
                    public.articles_verifications,
                    public.articles_verification_events,
                    public.rescue_audit_log,
                    public.webhook_endpoints,
                    public.webhook_deliveries,
                    public.document_access_log,
                    public.user_activity_logs,
                    public.users,
                    public.ai_prompt_templates,
                    public.legal_rules,
                    public.legal_rule_versions,
                    public.regulatory_rules,
                    public.sro_registry
                TO nlc_app_role;
                GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO nlc_app_role;
                GRANT SELECT ON TABLE
                    public.vw_admin_dashboard_kpis,
                    public.vw_company_flag_summary,
                    public.vw_revenue_pipeline,
                    public.vw_risk_distribution,
                    public.vw_upcoming_deadlines
                TO nlc_app_role;
                REVOKE INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER ON TABLE
                    public.vw_admin_dashboard_kpis,
                    public.vw_company_flag_summary,
                    public.vw_revenue_pipeline,
                    public.vw_risk_distribution,
                    public.vw_upcoming_deadlines
                FROM nlc_app_role;

                REVOKE TRUNCATE, REFERENCES, TRIGGER ON ALL TABLES IN SCHEMA public FROM nlc_app_role;
                REVOKE UPDATE, DELETE, TRUNCATE ON TABLE public.user_activity_logs FROM nlc_app_role;
                REVOKE UPDATE, DELETE, TRUNCATE ON TABLE public.document_access_log FROM nlc_app_role;
                REVOKE UPDATE, DELETE, TRUNCATE ON TABLE public.articles_verification_events FROM nlc_app_role;
                REVOKE UPDATE, DELETE, TRUNCATE ON TABLE public.rescue_audit_log FROM nlc_app_role;
                REVOKE ALL ON TABLE public.alembic_version FROM nlc_app_role;
            END IF;
        END
        $privileges$;
    """)


def downgrade() -> None:
    # Forward-only security hardening. Removing tenant policies would reopen
    # cross-tenant access; use a reviewed forward migration for any correction.
    pass
