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

    # Password hashes and encrypted TOTP secrets live on users. Legal staff
    # must not be able to read other users' credential-bearing rows merely
    # because their role is operational staff. Login keeps the signed AUTH
    # principal; administrative user management keeps rule-admin access.
    op.execute(
        "DROP POLICY IF EXISTS users_self_or_staff_select ON public.users"
    )
    op.execute("""
        CREATE POLICY users_self_or_admin_select ON public.users
        FOR SELECT
        USING (
            id = public.nlc_current_user_id()
            OR public.nlc_current_user_principal() IN ('ADMIN', 'AUTH')
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

    # Read-only, non-PII production parity surface. The view is owned by the
    # migration owner (BYPASSRLS) and exposes only schema/security invariants
    # and aggregate counts to the restricted audit role.
    op.execute("CREATE SCHEMA IF NOT EXISTS audit")
    op.execute("""
        CREATE OR REPLACE VIEW audit.production_release_parity AS
        SELECT
            (SELECT version_num FROM public.alembic_version LIMIT 1)
                AS alembic_revision,
            to_regclass('public.legal_rule_identity_archive') IS NOT NULL
                AS identity_archive_present,
            to_regclass('public.legal_rule_identities') IS NOT NULL
                AS identities_present,
            to_regclass('public.legal_rule_aliases') IS NOT NULL
                AS aliases_present,
            to_regclass('public.legal_rule_revisions') IS NOT NULL
                AS revisions_present,
            to_regclass('public.compliance_finding_bindings') IS NOT NULL
                AS finding_bindings_present,
            to_regclass('public.compliance_finding_evidence') IS NOT NULL
                AS finding_evidence_present,
            to_regclass('public.legal_rule_finding_contexts') IS NOT NULL
                AS finding_contexts_present,
            to_regclass('public.legal_rule_finding_context_reviews') IS NOT NULL
                AS finding_context_reviews_present,
            (SELECT count(*) FROM public.legal_rule_identity_archive)
                AS identity_archive_rows,
            (SELECT count(*) FROM public.legal_rule_identities)
                AS canonical_identity_rows,
            (SELECT count(*) FROM public.legal_rule_aliases)
                AS canonical_alias_rows,
            (SELECT count(*) FROM public.legal_rule_aliases
              WHERE resolution_status = 'UNRESOLVED')
                AS unresolved_alias_rows,
            (SELECT count(*) FROM public.legal_rule_aliases
              WHERE resolution_status = 'RESOLVED')
                AS resolved_alias_rows,
            (SELECT count(*) FROM public.legal_rule_revisions)
                AS canonical_revision_rows,
            (SELECT count(*) FROM public.compliance_finding_bindings)
                AS historical_finding_binding_rows,
            (SELECT count(*) FROM public.compliance_finding_evidence)
                AS historical_finding_evidence_rows,
            (SELECT count(*) FROM public.legal_rules WHERE is_active)
                AS active_legal_rule_rows,
            (SELECT count(*) FROM public.legal_rules
              WHERE verification_status::text = 'VERIFIED')
                AS verified_legal_rule_rows,
            EXISTS (
                SELECT 1 FROM public.legal_rules
                 WHERE rule_id = 'INC-001'
                   AND NOT is_active
                   AND default_severity::text = 'NOT_EVALUATED'
                   AND score_impact = 0
                   AND NOT is_black_override
                   AND verification_status::text = 'PENDING'
            ) AS inc001_quarantined,
            EXISTS (
                SELECT 1 FROM public.legal_rules
                 WHERE rule_id = 'INC-002'
                   AND NOT is_active
                   AND default_severity::text = 'NOT_EVALUATED'
                   AND score_impact = 0
                   AND NOT is_black_override
                   AND verification_status::text = 'PENDING'
            ) AS inc002_quarantined,
            (
                SELECT c.relrowsecurity AND c.relforcerowsecurity
                  FROM pg_class c
                 WHERE c.oid = 'public.compliance_score_history'::regclass
            ) AS score_history_rls_forced,
            EXISTS (
                SELECT 1 FROM pg_trigger t
                 WHERE t.tgrelid = 'public.compliance_score_history'::regclass
                   AND t.tgname = 'trg_compliance_score_history_append_only'
                   AND NOT t.tgisinternal
            ) AS score_history_append_only_trigger,
            NOT has_table_privilege(
                'nlc_app_role', 'public.compliance_score_history', 'UPDATE'
            ) AND NOT has_table_privilege(
                'nlc_app_role', 'public.compliance_score_history', 'DELETE'
            ) AS score_history_app_mutation_revoked,
            NOT EXISTS (
                SELECT 1 FROM pg_policies
                 WHERE schemaname = 'public'
                   AND tablename = 'compliance_score_history'
                   AND cmd IN ('UPDATE', 'DELETE', 'ALL')
            ) AS score_history_mutation_policies_absent,
            EXISTS (
                SELECT 1 FROM pg_policies
                 WHERE schemaname = 'public'
                   AND tablename = 'users'
                   AND policyname = 'users_admin_write'
                   AND cmd = 'ALL'
            ) AND NOT EXISTS (
                SELECT 1 FROM pg_policies
                 WHERE schemaname = 'public'
                   AND tablename = 'users'
                   AND policyname = 'users_staff_write'
            ) AS users_write_scope_restricted,
            EXISTS (
                SELECT 1 FROM pg_policies
                 WHERE schemaname = 'public'
                   AND tablename = 'users'
                   AND policyname = 'users_self_or_admin_select'
            ) AS users_credential_reads_scoped,
            EXISTS (
                SELECT 1 FROM pg_policies
                 WHERE schemaname = 'public'
                   AND tablename = 'company_user_access'
                   AND policyname = 'company_user_access_admin_write'
                   AND cmd = 'ALL'
            ) AND NOT EXISTS (
                SELECT 1 FROM pg_policies
                 WHERE schemaname = 'public'
                   AND tablename = 'company_user_access'
                   AND policyname = 'company_user_access_staff_write'
            ) AS membership_write_scope_restricted,
            EXISTS (
                SELECT 1 FROM pg_policies
                 WHERE schemaname = 'public'
                   AND tablename = 'company_user_access'
                   AND policyname = 'company_user_access_scoped_read'
                   AND COALESCE(qual, '') LIKE '%nlc_can_access_company%'
            ) AS membership_reads_scoped,
            NOT EXISTS (
                SELECT 1 FROM pg_roles
                 WHERE rolname = 'nlc_app_role'
                   AND (rolsuper OR rolbypassrls)
            ) AS app_role_cannot_bypass_rls,
            pg_has_role(
                'nlc_migration_user', 'nlc_migration_owner', 'SET'
            ) AND NOT pg_has_role(
                'nlc_app_role', 'nlc_migration_owner', 'SET'
            ) AS migration_role_isolated,
            (
                SELECT position(
                    'nlc_migration_user' IN pg_get_functiondef(
                        'public.nlc_require_legal_rule_version_snapshot()'::regprocedure
                    )
                ) > 0
                AND position(
                    'nlc_migration_owner' IN pg_get_functiondef(
                        'public.nlc_require_legal_rule_version_snapshot()'::regprocedure
                    )
                ) > 0
            ) AS legal_rule_migration_guard_scoped,
            (
                SELECT count(*) = 7 AND bool_and(
                    c.relrowsecurity AND c.relforcerowsecurity
                )
                FROM unnest(ARRAY[
                    'public.companies'::regclass,
                    'public.company_user_access'::regclass,
                    'public.compliance_flags'::regclass,
                    'public.compliance_evaluation_runs'::regclass,
                    'public.compliance_score_history'::regclass,
                    'public.documents'::regclass,
                    'public.users'::regclass
                ]) AS required(oid)
                JOIN pg_class c ON c.oid = required.oid
            ) AS core_tenant_rls_forced
    """)
    op.execute(
        "REVOKE ALL ON audit.production_release_parity FROM PUBLIC"
    )
    op.execute(
        "GRANT USAGE ON SCHEMA audit TO nlc_ci_audit_role"
    )
    op.execute(
        "GRANT SELECT ON audit.production_release_parity TO nlc_ci_audit_role"
    )


def downgrade() -> None:
    raise RuntimeError(
        "0122 is forward-only: do not restore broad staff tenant writes or "
        "mutable compliance score history."
    )
