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
    "compliance_score_history",
    "directors",
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

FINANCIAL_TABLES = ("annual_returns", "audits", "compliance_evaluation_runs")
SENSITIVE_DOCUMENT_TYPES = ("AUDIT_REPORT", "ANNUAL_RETURN", "DUE_DILIGENCE")

# PostgreSQL views execute with the view owner's privileges by default. These
# views expose tenant, compliance, deadline and revenue aggregates; all must
# evaluate underlying table permissions and RLS as the invoking runtime role.
RLS_VIEWS = (
    "vw_admin_dashboard_kpis",
    "vw_company_flag_summary",
    "vw_risk_distribution",
    "vw_upcoming_deadlines",
    "vw_revenue_pipeline",
)

RLS_TABLES = (
    "companies",
    *COMPANY_TABLES,
    "rescue_audit_log",
    "compliance_flags",
    "documents",
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
    "webhook_endpoints",
    "webhook_deliveries",
)


def upgrade() -> None:
    secret = os.environ.get("NLC_RLS_HMAC_SECRET", "")
    if len(secret) < 32:
        raise RuntimeError(
            "NLC_RLS_HMAC_SECRET must contain at least 32 characters before "
            "applying signed RLS identity hardening"
        )

    # Roles are provisioned out-of-band by the database administrator.
    # Schema migrations must never require CREATEROLE or alter login credentials.
    # Validate exact security attributes before changing any RLS objects.
    op.execute("""
        DO $role_preflight$
        DECLARE
            app_role record;
            audit_role record;
            migration_role record;
        BEGIN
            -- The SECURITY DEFINER RLS helpers query FORCE-RLS tables whose
            -- policies call those same helpers. Their owner must bypass RLS
            -- (or be superuser) to avoid recursive policy evaluation.
            SELECT rolsuper, rolbypassrls
              INTO migration_role
              FROM pg_roles
             WHERE rolname = current_user;

            IF NOT FOUND THEN
                RAISE EXCEPTION 'Unable to inspect migration role %', current_user;
            END IF;

            IF NOT migration_role.rolsuper AND NOT migration_role.rolbypassrls THEN
                RAISE EXCEPTION
                    'Migration role % must have BYPASSRLS or SUPERUSER to own the SECURITY DEFINER RLS helpers',
                    current_user;
            END IF;

            SELECT rolcanlogin, rolsuper, rolcreatedb, rolcreaterole,
                   rolinherit, rolreplication, rolbypassrls
              INTO app_role
              FROM pg_roles
             WHERE rolname = 'nlc_app_role';

            IF NOT FOUND THEN
                RAISE EXCEPTION
                    'Required role nlc_app_role is missing; provision it out-of-band before migration 0050';
            END IF;

            IF NOT app_role.rolcanlogin
               OR app_role.rolsuper
               OR app_role.rolcreatedb
               OR app_role.rolcreaterole
               OR app_role.rolinherit
               OR app_role.rolreplication
               OR app_role.rolbypassrls THEN
                RAISE EXCEPTION
                    'nlc_app_role has unsafe attributes; require LOGIN, NOSUPERUSER, NOCREATEDB, NOCREATEROLE, NOINHERIT, NOREPLICATION and NOBYPASSRLS';
            END IF;

            SELECT rolcanlogin, rolsuper, rolcreatedb, rolcreaterole,
                   rolinherit, rolreplication, rolbypassrls
              INTO audit_role
              FROM pg_roles
             WHERE rolname = 'nlc_ci_audit_role';

            IF NOT FOUND THEN
                RAISE EXCEPTION
                    'Required role nlc_ci_audit_role is missing; provision it out-of-band before migration 0050';
            END IF;

            IF NOT audit_role.rolcanlogin
               OR audit_role.rolsuper
               OR audit_role.rolcreatedb
               OR audit_role.rolcreaterole
               OR audit_role.rolinherit
               OR audit_role.rolreplication
               OR audit_role.rolbypassrls THEN
                RAISE EXCEPTION
                    'nlc_ci_audit_role has unsafe attributes; require LOGIN, NOSUPERUSER, NOCREATEDB, NOCREATEROLE, NOINHERIT, NOREPLICATION and NOBYPASSRLS';
            END IF;

            -- NOINHERIT does not prevent SET ROLE. Reject memberships in
            -- either direction so neither principal can inherit or assume
            -- another role, and no other role can assume these principals.
            IF EXISTS (
                SELECT 1
                  FROM pg_auth_members membership
                  JOIN pg_roles granted_role ON granted_role.oid = membership.roleid
                  JOIN pg_roles member_role ON member_role.oid = membership.member
                 WHERE granted_role.rolname IN ('nlc_app_role', 'nlc_ci_audit_role')
                    OR member_role.rolname IN ('nlc_app_role', 'nlc_ci_audit_role')
            ) THEN
                RAISE EXCEPTION
                    'nlc_app_role and nlc_ci_audit_role must have no role memberships in either direction';
            END IF;
        END
        $role_preflight$;
    """)

    # Validate the complete RLS target inventory before making any schema
    # changes. A database claiming to be at 0042 but missing a table created
    # by 0038 must stop for explicit drift reconciliation, not silently skip
    # or recreate potentially lost audit evidence.
    bind = op.get_bind()
    missing_rls_tables = [
        table
        for table in RLS_TABLES
        if bind.execute(
            sa.text("SELECT to_regclass(:qualified_name)"),
            {"qualified_name": f"public.{table}"},
        ).scalar_one() is None
    ]
    if missing_rls_tables:
        raise RuntimeError(
            "RLS migration preflight found missing expected public tables: "
            + ", ".join(sorted(missing_rls_tables))
            + ". Reconcile schema drift and audit evidence before retrying."
        )

    missing_rls_views = [
        view
        for view in RLS_VIEWS
        if bind.execute(
            sa.text("SELECT to_regclass(:qualified_name)"),
            {"qualified_name": f"public.{view}"},
        ).scalar_one() is None
    ]
    if missing_rls_views:
        raise RuntimeError(
            "RLS migration preflight found missing expected public views: "
            + ", ".join(sorted(missing_rls_views))
            + ". Reconcile the view inventory before retrying."
        )

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
        CREATE OR REPLACE FUNCTION public.nlc_current_user_is_rule_admin()
        RETURNS boolean
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $function$
            SELECT EXISTS (
                SELECT 1 FROM public.users u
                WHERE u.id = public.nlc_current_user_id()
                  AND u.is_active IS TRUE
                  AND u.role::text IN ('SUPER_ADMIN', 'ADMIN_STAFF')
            )
        $function$
    """)
    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_current_user_is_revenue_staff()
        RETURNS boolean
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $function$
            SELECT EXISTS (
                SELECT 1 FROM public.users u
                WHERE u.id = public.nlc_current_user_id()
                  AND u.is_active IS TRUE
                  AND u.role::text IN ('SUPER_ADMIN', 'ADMIN_STAFF')
            )
        $function$
    """)
    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_current_user_is_super_admin()
        RETURNS boolean
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $function$
            SELECT EXISTS (
                SELECT 1 FROM public.users u
                WHERE u.id = public.nlc_current_user_id()
                  AND u.is_active IS TRUE
                  AND u.role::text = 'SUPER_ADMIN'
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
        CREATE OR REPLACE FUNCTION public.nlc_can_view_financials_company(p_company_id uuid)
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
                          AND cua.can_view_financials IS TRUE
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


    for signature in (
        "nlc_current_user_principal()",
        "nlc_current_user_id()",
        "nlc_current_user_context_valid()",
        "nlc_current_user_is_staff()",
        "nlc_current_user_is_rule_admin()",
        "nlc_current_user_is_revenue_staff()",
        "nlc_current_user_is_super_admin()",
        "nlc_can_access_company(uuid)",
        "nlc_can_view_financials_company(uuid)",
        "nlc_can_manage_financials_company(uuid)",
        "nlc_can_edit_company(uuid)",
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
        read_fn = "nlc_can_view_financials_company" if table in FINANCIAL_TABLES else "nlc_can_access_company"
        write_fn = "nlc_can_manage_financials_company" if table in FINANCIAL_TABLES else "nlc_can_edit_company"
        op.execute(f"""
            CREATE POLICY {table}_tenant_select ON public.{table}
            FOR SELECT USING (public.{read_fn}(company_id))
        """)
        op.execute(f"""
            CREATE POLICY {table}_tenant_insert ON public.{table}
            FOR INSERT WITH CHECK (public.{write_fn}(company_id))
        """)
        op.execute(f"""
            CREATE POLICY {table}_tenant_update ON public.{table}
            FOR UPDATE
            USING (public.{write_fn}(company_id))
            WITH CHECK (public.{write_fn}(company_id))
        """)
        op.execute(f"""
            CREATE POLICY {table}_tenant_delete ON public.{table}
            FOR DELETE USING (public.{write_fn}(company_id))
        """)

    # Rescue audit records are tenant-scoped through their parent plan.
    # They are append-only: the actor must be the signed current user and
    # must have edit access to the plan's company.
    op.execute("""
        CREATE POLICY rescue_audit_log_tenant_select ON public.rescue_audit_log
        FOR SELECT
        USING (
            EXISTS (
                SELECT 1
                FROM public.rescue_plans rp
                WHERE rp.id = rescue_audit_log.rescue_plan_id
                  AND public.nlc_can_access_company(rp.company_id)
            )
        )
    """)
    op.execute("""
        CREATE POLICY rescue_audit_log_tenant_insert ON public.rescue_audit_log
        FOR INSERT
        WITH CHECK (
            actor_user_id = public.nlc_current_user_id()
            AND EXISTS (
                SELECT 1
                FROM public.rescue_plans rp
                WHERE rp.id = rescue_audit_log.rescue_plan_id
                  AND public.nlc_can_edit_company(rp.company_id)
            )
        )
    """)

    # Compliance flags may expose tax, audit, annual-return and capital data.
    op.execute("""
        CREATE POLICY compliance_flags_tenant_select ON public.compliance_flags
        FOR SELECT
        USING (
            public.nlc_can_access_company(company_id)
            AND (
                NOT (
                    rule_id LIKE 'TAX-%' OR rule_id LIKE 'VAT-%'
                    OR rule_id LIKE 'AUD-%' OR rule_id LIKE 'ACC-%'
                    OR rule_id LIKE 'AR-%' OR rule_id LIKE 'CAP-%'
                )
                OR public.nlc_can_view_financials_company(company_id)
            )
        )
    """)
    op.execute("""
        CREATE POLICY compliance_flags_tenant_insert ON public.compliance_flags
        FOR INSERT WITH CHECK (public.nlc_can_edit_company(company_id))
    """)
    op.execute("""
        CREATE POLICY compliance_flags_tenant_update ON public.compliance_flags
        FOR UPDATE
        USING (public.nlc_can_edit_company(company_id))
        WITH CHECK (public.nlc_can_edit_company(company_id))
    """)
    op.execute("""
        CREATE POLICY compliance_flags_tenant_delete ON public.compliance_flags
        FOR DELETE USING (public.nlc_can_edit_company(company_id))
    """)

    # Document visibility depends on document classification, not just tenant.
    op.execute("""
        CREATE POLICY documents_tenant_select ON public.documents
        FOR SELECT USING (
            public.nlc_can_access_company(company_id)
            AND (
                document_type::text NOT IN ('AUDIT_REPORT', 'ANNUAL_RETURN', 'DUE_DILIGENCE')
                OR public.nlc_can_view_financials_company(company_id)
            )
        )
    """)
    op.execute("""
        CREATE POLICY documents_tenant_insert ON public.documents
        FOR INSERT
        WITH CHECK (
            public.nlc_can_edit_company(company_id)
            AND (
                document_type::text NOT IN ('AUDIT_REPORT', 'ANNUAL_RETURN', 'DUE_DILIGENCE')
                OR public.nlc_can_manage_financials_company(company_id)
            )
        )
    """)
    op.execute("""
        CREATE POLICY documents_tenant_update ON public.documents
        FOR UPDATE
        USING (
            public.nlc_can_edit_company(company_id)
            AND (
                document_type::text NOT IN ('AUDIT_REPORT', 'ANNUAL_RETURN', 'DUE_DILIGENCE')
                OR public.nlc_can_manage_financials_company(company_id)
            )
        )
        WITH CHECK (
            public.nlc_can_edit_company(company_id)
            AND (
                document_type::text NOT IN ('AUDIT_REPORT', 'ANNUAL_RETURN', 'DUE_DILIGENCE')
                OR public.nlc_can_manage_financials_company(company_id)
            )
        )
    """)
    op.execute("""
        CREATE POLICY documents_tenant_delete ON public.documents
        FOR DELETE
        USING (
            public.nlc_can_edit_company(company_id)
            AND (
                document_type::text NOT IN ('AUDIT_REPORT', 'ANNUAL_RETURN', 'DUE_DILIGENCE')
                OR public.nlc_can_manage_financials_company(company_id)
            )
        )
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

    # Trigger execution does not require callers to hold EXECUTE. This
    # SECURITY DEFINER function must never be callable directly by PUBLIC.
    op.execute("REVOKE ALL ON FUNCTION public.nlc_protect_user_security_fields() FROM PUBLIC")

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
        CREATE POLICY webhook_endpoints_owner_select ON public.webhook_endpoints
        FOR SELECT USING (
            public.nlc_current_user_is_staff()
            OR user_id = public.nlc_current_user_id()
        )
    """)
    op.execute("""
        CREATE POLICY webhook_endpoints_owner_insert ON public.webhook_endpoints
        FOR INSERT WITH CHECK (
            public.nlc_current_user_is_staff()
            OR user_id = public.nlc_current_user_id()
        )
    """)
    op.execute("""
        CREATE POLICY webhook_endpoints_owner_update ON public.webhook_endpoints
        FOR UPDATE
        USING (public.nlc_current_user_is_staff() OR user_id = public.nlc_current_user_id())
        WITH CHECK (public.nlc_current_user_is_staff() OR user_id = public.nlc_current_user_id())
    """)
    op.execute("""
        CREATE POLICY webhook_endpoints_owner_delete ON public.webhook_endpoints
        FOR DELETE USING (
            public.nlc_current_user_is_staff()
            OR user_id = public.nlc_current_user_id()
        )
    """)
    op.execute("""
        CREATE POLICY webhook_deliveries_owner_select ON public.webhook_deliveries
        FOR SELECT USING (
            public.nlc_current_user_is_staff()
            OR EXISTS (
                SELECT 1 FROM public.webhook_endpoints e
                WHERE e.id = webhook_deliveries.endpoint_id
                  AND e.user_id = public.nlc_current_user_id()
            )
        )
    """)
    op.execute("""
        CREATE POLICY webhook_deliveries_owner_insert ON public.webhook_deliveries
        FOR INSERT WITH CHECK (
            public.nlc_current_user_is_staff()
            OR EXISTS (
                SELECT 1 FROM public.webhook_endpoints e
                WHERE e.id = webhook_deliveries.endpoint_id
                  AND e.user_id = public.nlc_current_user_id()
            )
        )
    """)
    op.execute("""
        CREATE POLICY webhook_deliveries_owner_update ON public.webhook_deliveries
        FOR UPDATE
        USING (
            public.nlc_current_user_is_staff()
            OR EXISTS (
                SELECT 1 FROM public.webhook_endpoints e
                WHERE e.id = webhook_deliveries.endpoint_id
                  AND e.user_id = public.nlc_current_user_id()
            )
        )
        WITH CHECK (
            public.nlc_current_user_is_staff()
            OR EXISTS (
                SELECT 1 FROM public.webhook_endpoints e
                WHERE e.id = webhook_deliveries.endpoint_id
                  AND e.user_id = public.nlc_current_user_id()
            )
        )
    """)
    op.execute("""
        CREATE POLICY webhook_deliveries_owner_delete ON public.webhook_deliveries
        FOR DELETE USING (
            public.nlc_current_user_is_staff()
            OR EXISTS (
                SELECT 1 FROM public.webhook_endpoints e
                WHERE e.id = webhook_deliveries.endpoint_id
                  AND e.user_id = public.nlc_current_user_id()
            )
        )
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
        USING (
            public.nlc_current_user_is_staff()
            OR user_id = public.nlc_current_user_id()
            OR (
                user_id IS NULL
                AND company_id IS NOT NULL
                AND public.nlc_can_access_company(company_id)
            )
        )
        WITH CHECK (
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
        CREATE OR REPLACE FUNCTION public.nlc_guard_notification_acknowledgement()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $function$
        BEGIN
            IF public.nlc_current_user_is_staff() THEN
                RETURN NEW;
            END IF;

            IF OLD.notification_status::text <> 'PENDING'
               OR NEW.notification_status::text <> 'ACKNOWLEDGED'
               OR NEW.acknowledged_at IS NULL THEN
                RAISE EXCEPTION 'Clients may only acknowledge pending notifications'
                    USING ERRCODE = '42501';
            END IF;

            IF (to_jsonb(NEW) - ARRAY['notification_status', 'acknowledged_at', 'updated_at'])
               IS DISTINCT FROM
               (to_jsonb(OLD) - ARRAY['notification_status', 'acknowledged_at', 'updated_at']) THEN
                RAISE EXCEPTION 'Clients may not modify notification content or delivery fields'
                    USING ERRCODE = '42501';
            END IF;
            RETURN NEW;
        END
        $function$
    """)
    op.execute("DROP TRIGGER IF EXISTS notifications_guard_client_ack ON public.notifications")
    op.execute("""
        CREATE TRIGGER notifications_guard_client_ack
        BEFORE UPDATE ON public.notifications
        FOR EACH ROW EXECUTE FUNCTION public.nlc_guard_notification_acknowledgement()
    """)
    op.execute("REVOKE ALL ON FUNCTION public.nlc_guard_notification_acknowledgement() FROM PUBLIC")

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
                )
            )
        )
    """)
    op.execute("""
        CREATE POLICY quotations_staff_write ON public.quotations
        FOR ALL
        USING (public.nlc_current_user_is_revenue_staff())
        WITH CHECK (public.nlc_current_user_is_revenue_staff())
    """)
    op.execute("""
        CREATE POLICY document_access_log_actor_tenant_select ON public.document_access_log
        FOR SELECT
        USING (
            public.nlc_current_user_is_staff()
            OR accessed_by = public.nlc_current_user_id()
            OR EXISTS (
                SELECT 1 FROM public.documents d
                WHERE d.id = document_id
            )
        )
    """)
    op.execute("""
        CREATE POLICY document_access_log_actor_tenant_insert ON public.document_access_log
        FOR INSERT
        WITH CHECK (
            public.nlc_current_user_is_staff()
            OR (
                accessed_by = public.nlc_current_user_id()
                AND EXISTS (
                    SELECT 1 FROM public.documents d
                    WHERE d.id = document_id
                )
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
        CREATE POLICY legal_rules_super_admin_insert ON public.legal_rules
        FOR INSERT
        WITH CHECK (public.nlc_current_user_is_super_admin())
    """)
    op.execute("""
        CREATE POLICY legal_rules_super_admin_update ON public.legal_rules
        FOR UPDATE
        USING (public.nlc_current_user_is_super_admin())
        WITH CHECK (public.nlc_current_user_is_super_admin())
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
    op.execute("""
        CREATE POLICY legal_rule_versions_rule_admin_read ON public.legal_rule_versions
        FOR SELECT
        USING (public.nlc_current_user_is_rule_admin())
    """)
    op.execute("""
        CREATE POLICY legal_rule_versions_super_admin_insert ON public.legal_rule_versions
        FOR INSERT
        WITH CHECK (public.nlc_current_user_is_super_admin())
    """)
    for table in ("ai_output_log", "ai_prompt_templates"):
        op.execute(f"""
            CREATE POLICY {table}_staff_only ON public.{table}
            FOR ALL
            USING (public.nlc_current_user_is_staff())
            WITH CHECK (public.nlc_current_user_is_staff())
        """)
    # Engagements contain commercial fees and revenue-pipeline facts. Legal
    # staff is staff for legal operations, but must not read commercial data.
    op.execute("""
        CREATE POLICY engagements_revenue_staff_only ON public.engagements
        FOR ALL
        USING (public.nlc_current_user_is_revenue_staff())
        WITH CHECK (public.nlc_current_user_is_revenue_staff())
    """)

    # Runtime privileges: RLS supplies row scope; SQL grants supply operation
    # scope. TRUNCATE, REFERENCES and TRIGGER are never granted to the app role.
    op.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
    op.execute("REVOKE CREATE ON SCHEMA public FROM nlc_app_role")
    op.execute("GRANT USAGE ON SCHEMA public TO nlc_app_role")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO nlc_app_role")
    op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO nlc_app_role")
    # Views owned by a BYPASSRLS migration role must not evaluate underlying
    # rows with owner privileges. PostgreSQL 15+ security_invoker makes the
    # caller's SELECT grants and row-level policies apply to the base tables.
    for view in RLS_VIEWS:
        op.execute(
            f"ALTER VIEW public.{view} SET (security_invoker = true)"
        )
    op.execute("REVOKE TRUNCATE, REFERENCES, TRIGGER ON ALL TABLES IN SCHEMA public FROM nlc_app_role")
    op.execute("REVOKE ALL ON TABLE public.rescue_audit_log FROM PUBLIC")
    op.execute("REVOKE ALL ON TABLE public.alembic_version FROM nlc_app_role")
    # Rule history is append-only. Only a SUPER_ADMIN may create a version;
    # no human or service session may rewrite or erase historical snapshots.
    op.execute("REVOKE DELETE, TRUNCATE ON TABLE public.legal_rules FROM nlc_app_role")
    op.execute("GRANT SELECT, INSERT, UPDATE ON TABLE public.legal_rules TO nlc_app_role")
    op.execute("REVOKE UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER ON TABLE public.legal_rule_versions FROM nlc_app_role")
    op.execute("GRANT SELECT, INSERT ON TABLE public.legal_rule_versions TO nlc_app_role")
    for table in ("user_activity_logs", "document_access_log", "compliance_evaluation_runs", "compliance_events", "ai_output_log", "rescue_audit_log"):
        op.execute(f"REVOKE UPDATE, DELETE, TRUNCATE ON TABLE public.{table} FROM nlc_app_role")

    # Enforce append-only rule history even if a future grant/policy regresses.
    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_reject_legal_rule_version_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $function$
        BEGIN
            RAISE EXCEPTION 'legal_rule_versions is append-only'
                USING ERRCODE = '55000';
        END
        $function$
    """)
    op.execute("REVOKE ALL ON FUNCTION public.nlc_reject_legal_rule_version_mutation() FROM PUBLIC")
    op.execute("DROP TRIGGER IF EXISTS legal_rule_versions_reject_row_mutation ON public.legal_rule_versions")
    op.execute("""
        CREATE TRIGGER legal_rule_versions_reject_row_mutation
        BEFORE UPDATE OR DELETE ON public.legal_rule_versions
        FOR EACH ROW EXECUTE FUNCTION public.nlc_reject_legal_rule_version_mutation()
    """)
    op.execute("DROP TRIGGER IF EXISTS legal_rule_versions_reject_truncate ON public.legal_rule_versions")
    op.execute("""
        CREATE TRIGGER legal_rule_versions_reject_truncate
        BEFORE TRUNCATE ON public.legal_rule_versions
        FOR EACH STATEMENT EXECUTE FUNCTION public.nlc_reject_legal_rule_version_mutation()
    """)

    # Read-only rule parity is exposed through a narrow view, not tenant tables.
    op.execute("CREATE SCHEMA IF NOT EXISTS audit")
    op.execute("REVOKE ALL ON SCHEMA audit FROM PUBLIC, nlc_app_role")
    op.execute("REVOKE ALL ON audit.active_legal_rule_ids FROM PUBLIC")
    op.execute("GRANT USAGE ON SCHEMA audit TO nlc_ci_audit_role")
    op.execute("GRANT SELECT ON audit.active_legal_rule_ids TO nlc_ci_audit_role")


def downgrade() -> None:
    # Forward-only security migration. Reverting to raw GUC policies would
    # reintroduce caller-controlled identity and permissive-policy bypasses.
    pass
