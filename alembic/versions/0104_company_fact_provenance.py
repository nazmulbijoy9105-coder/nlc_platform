"""persist company fact provenance and finding snapshots

Revision ID: 0104_company_fact_provenance
Revises: 0093_verified_rule_audit_view, b10c91ac6860
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0104_company_fact_provenance"
down_revision = ("0093_verified_rule_audit_view", "b10c91ac6860")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "company_facts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fact_key", sa.String(120), nullable=False),
        sa.Column("fact_value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("trust_level", sa.String(40), nullable=False),
        sa.Column("asserted_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("observed_on", sa.Date(), nullable=False),
        sa.Column("source_reference", sa.Text(), nullable=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("authorized_uploader_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verification_status", sa.String(20), nullable=False, server_default="UNVERIFIED"),
        sa.Column("verified_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verification_note", sa.Text(), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("supersedes_fact_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("company_facts.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "(trust_level = 'USER_ASSERTED' AND document_id IS NULL AND authorized_uploader_id IS NULL AND uploaded_at IS NULL) OR "
            "(trust_level = 'AUTHORIZED_DOCUMENT_BACKED' AND document_id IS NOT NULL AND authorized_uploader_id IS NOT NULL AND uploaded_at IS NOT NULL)",
            name="ck_company_fact_trust_source",
        ),
        sa.CheckConstraint(
            "trust_level IN ('USER_ASSERTED', 'AUTHORIZED_DOCUMENT_BACKED')",
            name="ck_company_fact_trust_level",
        ),
        sa.CheckConstraint(
            "verification_status IN ('UNVERIFIED', 'VERIFIED', 'REJECTED', 'SUPERSEDED')",
            name="ck_company_fact_verification_status",
        ),
        sa.CheckConstraint(
            "(verification_status = 'VERIFIED' AND verified_by IS NOT NULL AND verified_at IS NOT NULL "
            "AND trust_level = 'AUTHORIZED_DOCUMENT_BACKED') OR "
            "(verification_status <> 'VERIFIED' AND verified_by IS NULL AND verified_at IS NULL)",
            name="ck_company_fact_verification_actor",
        ),
    )
    op.create_index("ix_company_facts_company_id", "company_facts", ["company_id"])
    op.create_index("ix_company_facts_fact_key", "company_facts", ["fact_key"])
    op.create_index("ix_company_facts_company_key_current", "company_facts", ["company_id", "fact_key", "is_current"])

    # Reuse the existing signed identity and tenant-access functions. The app
    # role cannot read or write facts outside its company membership/assignment.
    bind = op.get_bind()
    required_helpers = (
        "public.nlc_current_user_id()",
        "public.nlc_current_user_is_staff()",
        "public.nlc_can_access_company(uuid)",
        "public.nlc_can_edit_company(uuid)",
    )
    missing = [
        helper for helper in required_helpers
        if bind.execute(
            sa.text("SELECT to_regprocedure(:signature)"),
            {"signature": helper},
        ).scalar_one() is None
    ]
    if missing:
        raise RuntimeError(
            "Company-fact RLS requires existing signed identity helpers: "
            + ", ".join(missing)
        )
    op.execute("ALTER TABLE public.company_facts ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.company_facts FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY company_facts_tenant_read
        ON public.company_facts FOR SELECT
        USING (public.nlc_can_access_company(company_id))
    """)
    op.execute("""
        CREATE POLICY company_facts_actor_insert
        ON public.company_facts FOR INSERT
        WITH CHECK (
            asserted_by = public.nlc_current_user_id()
            AND public.nlc_can_edit_company(company_id)
            AND public.nlc_can_access_company(company_id)
        )
    """)
    op.execute("""
        CREATE POLICY company_facts_staff_verification_update
        ON public.company_facts FOR UPDATE
        USING (
            public.nlc_current_user_is_staff()
            AND public.nlc_can_access_company(company_id)
        )
        WITH CHECK (
            public.nlc_current_user_is_staff()
            AND public.nlc_can_access_company(company_id)
            AND (verified_by IS NULL OR verified_by = public.nlc_current_user_id())
        )
    """)
    op.execute("GRANT SELECT, INSERT, UPDATE ON TABLE public.company_facts TO nlc_app_role")
    op.execute("REVOKE DELETE, TRUNCATE, REFERENCES, TRIGGER ON TABLE public.company_facts FROM nlc_app_role")

    # Legacy findings have no reconstructable provenance; [] means unknown, not verified.
    op.add_column(
        "compliance_flags",
        sa.Column("fact_provenance_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
    )
    op.add_column(
        "compliance_evaluation_runs",
        sa.Column("fact_provenance_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
    )


def downgrade() -> None:
    op.drop_column("compliance_evaluation_runs", "fact_provenance_snapshot")
    op.drop_column("compliance_flags", "fact_provenance_snapshot")
    op.drop_index("ix_company_facts_company_key_current", table_name="company_facts")
    op.drop_index("ix_company_facts_fact_key", table_name="company_facts")
    op.drop_index("ix_company_facts_company_id", table_name="company_facts")
    op.execute("DROP POLICY IF EXISTS company_facts_staff_verification_update ON public.company_facts")
    op.execute("DROP POLICY IF EXISTS company_facts_actor_insert ON public.company_facts")
    op.execute("DROP POLICY IF EXISTS company_facts_tenant_read ON public.company_facts")
    op.execute("ALTER TABLE public.company_facts NO FORCE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.company_facts DISABLE ROW LEVEL SECURITY")
    op.drop_table("company_facts")
