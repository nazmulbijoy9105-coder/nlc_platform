"""Add transactional domain event outbox.

Revision ID: 0105_domain_event_outbox
Revises: 0104_company_fact_provenance
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0105_domain_event_outbox"
down_revision = "0104_company_fact_provenance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    required = (
        "public.nlc_current_user_id()",
        "public.nlc_can_access_company(uuid)",
        "public.nlc_can_edit_company(uuid)",
    )
    missing = [
        signature for signature in required
        if bind.execute(
            sa.text("SELECT to_regprocedure(:signature)"),
            {"signature": signature},
        ).scalar_one() is None
    ]
    if missing:
        raise RuntimeError(
            "Domain event outbox requires signed tenant helpers: " + ", ".join(missing)
        )

    op.create_table(
        "domain_event_outbox",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", sa.String(120), nullable=False),
        sa.Column("aggregate_type", sa.String(80), nullable=False),
        sa.Column("aggregate_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("correlation_id", sa.String(100), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.CheckConstraint("schema_version > 0", name="ck_domain_event_schema_version_positive"),
        sa.CheckConstraint("attempts >= 0", name="ck_domain_event_attempts_nonnegative"),
    )
    op.create_index("ix_domain_event_outbox_pending", "domain_event_outbox", ["processed_at", "available_at", "occurred_at"])
    op.create_index("ix_domain_event_outbox_company_created", "domain_event_outbox", ["company_id", "occurred_at"])
    op.create_index("ix_domain_event_outbox_event_type", "domain_event_outbox", ["event_type"])

    op.execute("ALTER TABLE public.domain_event_outbox ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.domain_event_outbox FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY domain_event_outbox_tenant_read
        ON public.domain_event_outbox FOR SELECT
        USING (public.nlc_can_access_company(company_id))
    """)
    op.execute("""
        CREATE POLICY domain_event_outbox_actor_insert
        ON public.domain_event_outbox FOR INSERT
        WITH CHECK (
            public.nlc_can_edit_company(company_id)
            AND public.nlc_can_access_company(company_id)
            AND (actor_id IS NULL OR actor_id = public.nlc_current_user_id())
        )
    """)
    op.execute("""
        CREATE POLICY domain_event_outbox_staff_update
        ON public.domain_event_outbox FOR UPDATE
        USING (public.nlc_can_access_company(company_id) AND public.nlc_current_user_is_staff())
        WITH CHECK (public.nlc_can_access_company(company_id) AND public.nlc_current_user_is_staff())
    """)
    op.execute("GRANT SELECT, INSERT, UPDATE ON TABLE public.domain_event_outbox TO nlc_app_role")
    op.execute("REVOKE DELETE, TRUNCATE, REFERENCES, TRIGGER ON TABLE public.domain_event_outbox FROM nlc_app_role")


def downgrade() -> None:
    op.drop_table("domain_event_outbox")
