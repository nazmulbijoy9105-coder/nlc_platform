"""Replace legacy Articles raw-GUC policies with signed staff-write RLS.

Revision ID: 0078_articles_evidence_signed_rls
Revises: 0077_merge_legacy_articles_head

Company members may read their own company's Articles evidence. Only a
verified signed staff principal may submit or update verification records.
Events remain append-only; verification source/decision triggers are preserved.
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
            "public.nlc_can_access_company(uuid)",
            "public.nlc_current_user_is_staff()",
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
            USING (public.nlc_can_access_company(company_id))
        """)
        op.execute(f"""
            CREATE POLICY {table}_staff_insert
            ON public.{table}
            FOR INSERT
            WITH CHECK (
                public.nlc_current_user_is_staff()
                AND public.nlc_can_access_company(company_id)
            )
        """)

        if table.endswith("_events"):
            # The append-only trigger remains in place. SQL privileges also
            # prohibit mutation even if a future policy is accidentally added.
            op.execute(
                f"REVOKE UPDATE, DELETE, TRUNCATE ON TABLE public.{table} "
                "FROM nlc_app_role"
            )
        else:
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
                f"REVOKE DELETE, TRUNCATE ON TABLE public.{table} "
                "FROM nlc_app_role"
            )


def downgrade() -> None:
    # Forward-only. Restoring the historical unsigned ADMIN policy would
    # reintroduce a caller-controlled authorization bypass.
    pass
