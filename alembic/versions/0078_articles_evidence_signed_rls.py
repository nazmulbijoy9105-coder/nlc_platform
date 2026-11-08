"""Replace legacy Articles raw-GUC policies with signed staff-write RLS.

Revision ID: 0078_articles_evidence_signed_rls
Revises: 0077_merge_legacy_articles_head

Company members may read and submit their own company's Articles evidence.
Only a verified signed staff principal may review or update verification
records. Event actors are bound to the signed principal; event history remains
append-only and source/decision triggers are preserved.
"""
from alembic import op
import sqlalchemy as sa

revision = "0078_articles_evidence_signed_rls"
down_revision = "0077_merge_legacy_articles_head"
branch_labels = None
depends_on = None

EVIDENCE_TABLES = (
    "articles_verifications",
    "articles_verification_events",
)


def upgrade() -> None:
    bind = op.get_bind()

    missing_tables = [
        table
        for table in EVIDENCE_TABLES
        if bind.execute(
            sa.text("SELECT to_regclass(:name)"),
            {"name": f"public.{table}"},
        ).scalar_one() is None
    ]
    if missing_tables:
        raise RuntimeError(
            "Articles evidence RLS migration cannot proceed; missing tables: "
            + ", ".join(missing_tables)
        )

    missing_helpers = [
        signature
        for signature in (
            "public.nlc_current_user_principal()",
            "public.nlc_current_user_id()",
            "public.nlc_current_user_context_valid()",
            "public.nlc_can_access_company(uuid)",
            "public.nlc_current_user_is_staff()",
            "public.nlc_can_edit_company(uuid)",
        )
        if bind.execute(
            sa.text("SELECT to_regprocedure(:signature)"),
            {"signature": signature},
        ).scalar_one() is None
    ]
    if missing_helpers:
        raise RuntimeError(
            "Articles evidence RLS migration requires signed-RLS helpers: "
            + ", ".join(missing_helpers)
        )

    role_exists = bind.execute(
        sa.text("SELECT 1 FROM pg_roles WHERE rolname = 'nlc_app_role'")
    ).scalar_one_or_none()
    if role_exists is None:
        raise RuntimeError(
            "Articles evidence RLS migration requires the nlc_app_role runtime role"
        )

    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_can_access_articles_company(
            p_company_id uuid
        )
        RETURNS boolean
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $function$
            SELECT
                public.nlc_current_user_principal() = 'ADMIN'
                OR EXISTS (
                    SELECT 1
                    FROM public.users u
                    WHERE u.id = public.nlc_current_user_id()
                      AND u.is_active IS TRUE
                      AND u.role::text IN ('SUPER_ADMIN', 'ADMIN_STAFF')
                )
                OR EXISTS (
                    SELECT 1
                    FROM public.users u
                    JOIN public.companies c
                      ON c.assigned_staff_id = u.id
                    WHERE c.id = p_company_id
                      AND u.id = public.nlc_current_user_id()
                      AND u.is_active IS TRUE
                      AND u.role::text = 'LEGAL_STAFF'
                )
                OR EXISTS (
                    SELECT 1
                    FROM public.users u
                    JOIN public.company_user_access cua
                      ON cua.user_id = u.id
                    WHERE cua.company_id = p_company_id
                      AND u.id = public.nlc_current_user_id()
                      AND u.is_active IS TRUE
                      AND cua.is_active IS TRUE
                )
        $function$
    """)
    op.execute(
        "REVOKE ALL ON FUNCTION public.nlc_can_access_articles_company(uuid) FROM PUBLIC"
    )
    op.execute(
        "GRANT EXECUTE ON FUNCTION public.nlc_can_access_articles_company(uuid) TO nlc_app_role"
    )

    for table in EVIDENCE_TABLES:
        # FORCE ensures the table owner does not accidentally bypass the
        # tenant policy. The production runtime role must also remain
        # NOSUPERUSER and NOBYPASSRLS as checked by migration 0050.
        op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE public.{table} FORCE ROW LEVEL SECURITY")

        # PostgreSQL OR-combines permissive policies. Remove every previous
        # policy, including the historical unsigned ADMIN GUC policy.
        op.execute(f"""
            DO $articles_policy_cleanup$
            DECLARE
                existing_policy record;
            BEGIN
                FOR existing_policy IN
                    SELECT policyname
                    FROM pg_policies
                    WHERE schemaname = 'public'
                      AND tablename = '{table}'
                LOOP
                    EXECUTE format(
                        'DROP POLICY %I ON public.{table}',
                        existing_policy.policyname
                    );
                END LOOP;
            END;
            $articles_policy_cleanup$
        """)

        op.execute(f"""
            CREATE POLICY {table}_company_read
            ON public.{table}
            FOR SELECT
            USING (public.nlc_can_access_articles_company(company_id))
        """)
        if table == "articles_verifications":
            # Company editors may submit evidence; the signed principal must
            # match the submitter identity recorded in the evidence row.
            op.execute("""
                CREATE POLICY articles_verifications_member_submit
                ON public.articles_verifications
                FOR INSERT
                WITH CHECK (
                    submitted_by = public.nlc_current_user_id()
                    AND public.nlc_can_edit_company(company_id)
                    AND public.nlc_can_access_articles_company(company_id)
                )
            """)
        else:
            # Every event actor is bound to the authenticated signed principal.
            op.execute("""
                CREATE POLICY articles_verification_events_actor_insert
                ON public.articles_verification_events
                FOR INSERT
                WITH CHECK (
                    actor_id = public.nlc_current_user_id()
                    AND public.nlc_can_edit_company(company_id)
                    AND public.nlc_can_access_articles_company(company_id)
                )
            """)

        if table.endswith("_events"):
            # 0050 grants privileges only to tables that exist at that point in
            # the graph. Articles tables are restored later, so grant the
            # minimum required runtime privileges explicitly here.
            op.execute(
                f"GRANT SELECT, INSERT ON TABLE public.{table} TO nlc_app_role"
            )
            # The append-only trigger remains in place. SQL privileges also
            # prohibit mutation even if a future policy is accidentally added.
            op.execute(
                f"REVOKE UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER "
                f"ON TABLE public.{table} FROM nlc_app_role"
            )
        else:
            op.execute(
                f"GRANT SELECT, INSERT, UPDATE ON TABLE public.{table} TO nlc_app_role"
            )
            op.execute(
                f"REVOKE DELETE, TRUNCATE, REFERENCES, TRIGGER "
                f"ON TABLE public.{table} FROM nlc_app_role"
            )
            op.execute(f"""
                CREATE POLICY {table}_staff_update
                ON public.{table}
                FOR UPDATE
                USING (
                    public.nlc_current_user_is_staff()
                    AND public.nlc_can_access_articles_company(company_id)
                )
                WITH CHECK (
                    public.nlc_current_user_is_staff()
                    AND public.nlc_can_access_articles_company(company_id)
                )
            """)
            op.execute(
                f"REVOKE DELETE, TRUNCATE ON TABLE public.{table} "
                "FROM nlc_app_role"
            )


def downgrade() -> None:
    # Forward-only. Restoring the historical unsigned ADMIN policy would
    # reintroduce a caller-controlled authorization bypass.
    pass
