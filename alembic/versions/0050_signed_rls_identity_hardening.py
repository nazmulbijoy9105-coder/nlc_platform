"""Install cryptographically verified RLS identity and reconcile tenant policies.

Revision ID: 0050_signed_rls_identity_hardening
Revises: 0049_evaluation_runs_and_identity_rls

The earlier 0049 revision is retained for schema compatibility, but its raw
GUC sentinel policies are replaced here before the release can be deployed.
"""
import os

from alembic import op
import sqlalchemy as sa

revision = "0050_signed_rls_identity_hardening"
down_revision = "0049_evaluation_runs_and_identity_rls"
branch_labels = None
depends_on = None

COMPANY_TABLES = (
    "agms",
    "annual_returns",
    "audits",
    "compliance_flags",
    "compliance_score_history",
    "directors",
    "documents",
    "registered_office_history",
    "rescue_plans",
    "rescue_steps",
    "rjsc_form_filings",
    "share_transfers",
    "shareholders",
    "statutory_registers",
    "tasks",
    "compliance_calendar_events",
    "compliance_evaluation_runs",
)

RLS_TABLES = (
    "companies",
    *COMPANY_TABLES,
    "users",
    "company_user_access",
    "compliance_events",
    "quotations",
    "document_access_log",
    "user_activity_logs",
    "legal_rules",
    "legal_rule_versions",
    "sro_registry",
    "regulatory_rules",
    "ai_output_log",
    "ai_prompt_templates",
    "engagements",
    "notifications",
)


def upgrade() -> None:
    secret = os.environ.get("NLC_RLS_HMAC_SECRET", "")
    if len(secret) < 32:
        raise RuntimeError(
            "NLC_RLS_HMAC_SECRET must contain at least 32 characters before "
            "applying signed RLS identity hardening"
        )

    # The runtime role is deliberately non-superuser and cannot bypass RLS.
    # Preserve LOGIN on an existing role; a newly-created role has no password
    # and must receive its credential out-of-band before runtime cutover.
    op.execute("""
        DO $role$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nlc_app_role') THEN
                CREATE ROLE nlc_app_role LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
                    NOINHERIT NOREPLICATION NOBYPASSRLS;
            END IF;
        END
        $role$;
    """)
    op.execute("""
        ALTER ROLE nlc_app_role NOSUPERUSER NOCREATEDB NOCREATEROLE
            NOINHERIT NOREPLICATION NOBYPASSRLS
    """)
    op.execute("GRANT nlc_app_role TO CURRENT_USER")

    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE SCHEMA IF NOT EXISTS nlc_private")
    op.execute("REVOKE ALL ON SCHEMA nlc_private FROM PUBLIC, nlc_app_role")
    op.execute("""
        CREATE TABLE IF NOT EXISTS nlc_private.rls_signing_key (
            singleton boolean PRIMARY KEY DEFAULT TRUE CHECK (singleton),
            secret text NOT NULL,
            created_at timestamptz NOT NULL DEFAULT now()
        )
    """)
    op.execute("REVOKE ALL ON TABLE nlc_private.rls_signing_key FROM PUBLIC, nlc_app_role")

    bind = op.get_bind()
    existing_secret = bind.execute(
        sa.text("SELECT secret FROM nlc_private.rls_signing_key WHERE singleton = true")
    ).scalar_one_or_none()
    if existing_secret is None:
        bind.execute(
            sa.text(
                "INSERT INTO nlc_private.rls_signing_key (singleton, secret) "
                "VALUES (true, :secret)"
            ),
            {"secret": secret},
        )
    elif existing_secret != secret:
        raise RuntimeError(
            "NLC_RLS_HMAC_SECRET does not match the provisioned database key; "
            "use a separately reviewed key-rotation migration"
        )

    # All identity decisions are based on a database-verifiable HMAC, never
    # the caller-controlled app.current_user_id setting by itself.
    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_current_user_principal()
        RETURNS text
        LANGUAGE plpgsql
        STABLE
        SECURITY DEFINER
        SET search_path = pg_catalog, public, nlc_private
        AS $function$
        DECLARE
            principal text;
            supplied_signature text;
            stored_secret text;
            expected_signature text;
        BEGIN
            principal := current_setting('app.current_user_id', true);
            supplied_signature := current_setting('app.current_user_signature', true);
            IF principal IS NULL OR supplied_signature IS NULL THEN
                RETURN NULL;
            END IF;

            SELECT secret INTO stored_secret
            FROM nlc_private.rls_signing_key
            WHERE singleton = true;
            IF stored_secret IS NULL THEN
                RETURN NULL;
            END IF;

            expected_signature := encode(
                public.hmac(
                    convert_to(principal, 'UTF8'),
                    convert_to(stored_secret, 'UTF8'),
                    'sha256'
                ),
                'hex'
            );
            IF supplied_signature <> expected_signature THEN
                RETURN NULL;
            END IF;

            IF principal IN ('ADMIN', 'AUTH', 'CATALOG', 'ANONYMOUS') THEN
                RETURN principal;
            END IF;
            IF principal !~* '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' THEN
                RETURN NULL;
            END IF;
            RETURN lower(principal);
        END
        $function$
    """)
    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_current_user_id()
        RETURNS uuid
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $function$
            SELECT CASE
                WHEN public.nlc_current_user_principal() ~*
                    '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
                THEN public.nlc_current_user_principal()::uuid
                ELSE NULL
            END
        $function$
    """)
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
    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_current_user_is_staff()
        RETURNS boolean
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $function$
            SELECT COALESCE(
                public.nlc_current_user_principal() = 'ADMIN'
                OR EXISTS (
                    SELECT 1 FROM public.users u
                    WHERE u.id = public.nlc_current_user_id()
                      AND u.is_active IS TRUE
                      AND u.role::text IN ('SUPER_ADMIN', 'ADMIN_STAFF', 'LEGAL_STAFF')
                ),
                FALSE
            )
        $function$
    """)
    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_can_access_company(p_company_id uuid)
        RETURNS boolean
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $function$
            SELECT public.nlc_current_user_is_staff()
                OR (
                    public.nlc_current_user_id() IS NOT NULL
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
                    )
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
            SELECT public.nlc_current_user_is_staff()
                OR (
                    public.nlc_current_user_id() IS NOT NULL
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
                    )
                )
        $function$
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_can_access_document(p_document_id uuid)
        RETURNS boolean
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $function$
            SELECT EXISTS (
                SELECT 1 FROM public.documents d
                WHERE d.id = p_document_id
                  AND public.nlc_can_access_company(d.company_id)
            )
        $function$
    """)

    for signature in (
        "nlc_current_user_principal()",
        "nlc_current_user_id()",
        "nlc_current_user_context_valid()",
        "nlc_current_user_is_staff()",
        "nlc_can_access_company(uuid)",
        "nlc_can_edit_company(uuid)",
        "nlc_can_access_document(uuid)",
    ):
        op.execute(f"REVOKE ALL ON FUNCTION public.{signature} FROM PUBLIC")
        op.execute(f"GRANT EXECUTE ON FUNCTION public.{signature} TO nlc_app_role")

    # Drop every existing permissive policy on the managed tables. PostgreSQL
    # OR-combines permissive policies, so retaining one legacy policy would
    # defeat the new actor/tenant boundary.
    table_sql = ", ".join("'" + name + "'" for name in RLS_TABLES)
    op.execute(f"""
        DO $policies$
        DECLARE p record;
        BEGIN
            FOR p IN
                SELECT schemaname, tablename, policyname
                FROM pg_policies
                WHERE schemaname = 'public'
                  AND tablename = ANY (ARRAY[{table_sql}])
            LOOP
                EXECUTE format(
                    'DROP POLICY %I ON %I.%I',
                    p.policyname, p.schemaname, p.tablename
                );
            END LOOP;
        END
        $policies$;
    """)

    for table in RLS_TABLES:
        op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE public.{table} FORCE ROW LEVEL SECURITY")

    op.execute("""
        CREATE POLICY companies_tenant_select ON public.companies
        FOR SELECT USING (public.nlc_can_access_company(id))
    """)
    op.execute("""
        CREATE POLICY companies_tenant_insert ON public.companies
        FOR INSERT WITH CHECK (public.nlc_can_edit_company(id))
    """)
    op.execute("""
        CREATE POLICY companies_tenant_update ON public.companies
        FOR UPDATE
        USING (public.nlc_can_edit_company(id))
        WITH CHECK (public.nlc_can_edit_company(id))
    """)
    op.execute("""
        CREATE POLICY companies_tenant_delete ON public.companies
        FOR DELETE USING (public.nlc_can_edit_company(id))
    """)

    for table in COMPANY_TABLES:
        op.execute(f"""
            CREATE POLICY {table}_tenant_select ON public.{table}
            FOR SELECT USING (public.nlc_can_access_company(company_id))
        """)
        op.execute(f"""
            CREATE POLICY {table}_tenant_insert ON public.{table}
            FOR INSERT WITH CHECK (public.nlc_can_edit_company(company_id))
        """)
        op.execute(f"""
            CREATE POLICY {table}_tenant_update ON public.{table}
            FOR UPDATE
            USING (public.nlc_can_edit_company(company_id))
            WITH CHECK (public.nlc_can_edit_company(company_id))
        """)
        op.execute(f"""
            CREATE POLICY {table}_tenant_delete ON public.{table}
            FOR DELETE USING (public.nlc_can_edit_company(company_id))
        """)

    op.execute("""
        CREATE POLICY users_self_or_staff_select ON public.users
        FOR SELECT
        USING (
            id = public.nlc_current_user_id()
            OR public.nlc_current_user_is_staff()
            OR public.nlc_current_user_principal() = 'AUTH'
        )
    """)
    op.execute("""
        CREATE POLICY users_self_update ON public.users
        FOR UPDATE
        USING (id = public.nlc_current_user_id())
        WITH CHECK (id = public.nlc_current_user_id())
    """)
    op.execute("""
        CREATE POLICY users_staff_write ON public.users
        FOR ALL
        USING (public.nlc_current_user_is_staff())
        WITH CHECK (public.nlc_current_user_is_staff())
    """)
    op.execute("""
        CREATE POLICY users_auth_insert ON public.users
        FOR INSERT
        WITH CHECK (
            public.nlc_current_user_principal() = 'AUTH'
            AND role::text = 'CLIENT_VIEW_ONLY'
            AND is_active IS TRUE
        )
    """)
    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_protect_user_security_fields()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $function$
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
        END
        $function$
    """)
    op.execute("DROP TRIGGER IF EXISTS users_protect_security_fields ON public.users")
    op.execute("""
        CREATE TRIGGER users_protect_security_fields
        BEFORE UPDATE ON public.users
        FOR EACH ROW EXECUTE FUNCTION public.nlc_protect_user_security_fields()
    """)

    op.execute("""
        CREATE POLICY company_user_access_self_read ON public.company_user_access
        FOR SELECT
        USING (
            user_id = public.nlc_current_user_id()
            OR public.nlc_current_user_is_staff()
        )
    """)
    op.execute("""
        CREATE POLICY company_user_access_staff_write ON public.company_user_access
        FOR ALL
        USING (public.nlc_current_user_is_staff())
        WITH CHECK (public.nlc_current_user_is_staff())
    """)

    op.execute("""
        CREATE POLICY notifications_actor_tenant_select ON public.notifications
        FOR SELECT
        USING (
            public.nlc_current_user_is_staff()
            OR user_id = public.nlc_current_user_id()
            OR (
                user_id IS NULL
                AND company_id IS NOT NULL
                AND public.nlc_can_access_company(company_id)
            )
        )
    """)
    op.execute("""
        CREATE POLICY notifications_actor_tenant_insert ON public.notifications
        FOR INSERT
        WITH CHECK (
            public.nlc_current_user_is_staff()
            OR (
                user_id = public.nlc_current_user_id()
                AND (company_id IS NULL OR public.nlc_can_access_company(company_id))
            )
        )
    """)
    op.execute("""
        CREATE POLICY notifications_actor_tenant_update ON public.notifications
        FOR UPDATE
        USING (public.nlc_current_user_is_staff() OR user_id = public.nlc_current_user_id())
        WITH CHECK (public.nlc_current_user_is_staff() OR user_id = public.nlc_current_user_id())
    """)

    op.execute("""
        CREATE POLICY compliance_events_company_read ON public.compliance_events
        FOR SELECT
        USING (public.nlc_can_access_company(company_id))
    """)
    op.execute("""
        CREATE POLICY compliance_events_company_insert ON public.compliance_events
        FOR INSERT
        WITH CHECK (public.nlc_can_edit_company(company_id))
    """)
    op.execute("""
        CREATE POLICY quotations_company_read ON public.quotations
        FOR SELECT
        USING (
            public.nlc_current_user_is_staff()
            OR (company_id IS NOT NULL AND public.nlc_can_access_company(company_id))
        )
    """)
    op.execute("""
        CREATE POLICY quotations_staff_write ON public.quotations
        FOR ALL
        USING (public.nlc_current_user_is_staff())
        WITH CHECK (public.nlc_current_user_is_staff())
    """)
    op.execute("""
        CREATE POLICY document_access_log_actor_tenant_select ON public.document_access_log
        FOR SELECT
        USING (
            public.nlc_current_user_is_staff()
            OR accessed_by = public.nlc_current_user_id()
            OR public.nlc_can_access_document(document_id)
        )
    """)
    op.execute("""
        CREATE POLICY document_access_log_actor_tenant_insert ON public.document_access_log
        FOR INSERT
        WITH CHECK (
            public.nlc_current_user_is_staff()
            OR (
                accessed_by = public.nlc_current_user_id()
                AND public.nlc_can_access_document(document_id)
            )
        )
    """)

    # Exactly one policy is installed on user_activity_logs. It binds both
    # the actor and (where present) the company to the verified identity.
    op.execute("""
        CREATE POLICY user_activity_logs_actor_tenant ON public.user_activity_logs
        FOR ALL
        USING (
            public.nlc_current_user_is_staff()
            OR (
                user_id = public.nlc_current_user_id()
                AND (company_id IS NULL OR public.nlc_can_access_company(company_id))
            )
        )
        WITH CHECK (
            public.nlc_current_user_is_staff()
            OR (
                user_id = public.nlc_current_user_id()
                AND (company_id IS NULL OR public.nlc_can_access_company(company_id))
            )
        )
    """)

    op.execute("""
        CREATE POLICY legal_rules_authenticated_read ON public.legal_rules
        FOR SELECT
        USING (
            public.nlc_current_user_principal() IN ('AUTH', 'CATALOG')
            OR public.nlc_current_user_is_staff()
            OR EXISTS (
                SELECT 1 FROM public.users u
                WHERE u.id = public.nlc_current_user_id() AND u.is_active IS TRUE
            )
        )
    """)
    op.execute("""
        CREATE POLICY legal_rules_staff_write ON public.legal_rules
        FOR ALL
        USING (public.nlc_current_user_is_staff())
        WITH CHECK (public.nlc_current_user_is_staff())
    """)
    for table in ("sro_registry", "regulatory_rules"):
        op.execute(f"""
            CREATE POLICY {table}_authenticated_read ON public.{table}
            FOR SELECT
            USING (
                public.nlc_current_user_principal() IN ('AUTH', 'CATALOG')
                OR public.nlc_current_user_is_staff()
                OR EXISTS (
                    SELECT 1 FROM public.users u
                    WHERE u.id = public.nlc_current_user_id() AND u.is_active IS TRUE
                )
            )
        """)
        op.execute(f"""
            CREATE POLICY {table}_staff_write ON public.{table}
            FOR ALL
            USING (public.nlc_current_user_is_staff())
            WITH CHECK (public.nlc_current_user_is_staff())
        """)
    for table in ("legal_rule_versions", "ai_output_log", "ai_prompt_templates", "engagements"):
        op.execute(f"""
            CREATE POLICY {table}_staff_only ON public.{table}
            FOR ALL
            USING (public.nlc_current_user_is_staff())
            WITH CHECK (public.nlc_current_user_is_staff())
        """)

    # Runtime privileges: RLS supplies row scope; SQL grants supply operation
    # scope. TRUNCATE, REFERENCES and TRIGGER are never granted to the app role.
    op.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
    op.execute("REVOKE CREATE ON SCHEMA public FROM nlc_app_role")
    op.execute("GRANT USAGE ON SCHEMA public TO nlc_app_role")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO nlc_app_role")
    op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO nlc_app_role")
    op.execute("REVOKE TRUNCATE, REFERENCES, TRIGGER ON ALL TABLES IN SCHEMA public FROM nlc_app_role")
    op.execute("REVOKE ALL ON TABLE public.alembic_version FROM nlc_app_role")
    for table in ("user_activity_logs", "document_access_log", "compliance_evaluation_runs", "compliance_events", "ai_output_log"):
        op.execute(f"REVOKE UPDATE, DELETE, TRUNCATE ON TABLE public.{table} FROM nlc_app_role")

    # Read-only rule parity is exposed through a narrow view, not tenant tables.
    op.execute("CREATE SCHEMA IF NOT EXISTS audit")
    op.execute("REVOKE ALL ON SCHEMA audit FROM PUBLIC, nlc_app_role")
    op.execute("REVOKE ALL ON audit.active_legal_rule_ids FROM PUBLIC")
    op.execute("""
        DO $audit_role$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nlc_ci_audit_role') THEN
                CREATE ROLE nlc_ci_audit_role LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
                    NOINHERIT NOREPLICATION NOBYPASSRLS;
            END IF;
        END
        $audit_role$;
    """)
    op.execute("""
        ALTER ROLE nlc_ci_audit_role NOSUPERUSER NOCREATEDB NOCREATEROLE
            NOINHERIT NOREPLICATION NOBYPASSRLS
    """)
    op.execute("GRANT USAGE ON SCHEMA audit TO nlc_ci_audit_role")
    op.execute("GRANT SELECT ON audit.active_legal_rule_ids TO nlc_ci_audit_role")


def downgrade() -> None:
    # Forward-only security migration. Reverting to raw GUC policies would
    # reintroduce caller-controlled identity and permissive-policy bypasses.
    pass
