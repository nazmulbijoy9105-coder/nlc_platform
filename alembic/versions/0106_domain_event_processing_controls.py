"""Add domain-event dead-letter controls and idempotent consumer receipts.

Revision ID: 0106_domain_event_processing_controls
Revises: 0105_domain_event_outbox
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0106_domain_event_processing_controls"
down_revision = "0105_domain_event_outbox"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "domain_event_outbox",
        sa.Column("dead_lettered_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "domain_event_outbox",
        sa.Column("dead_letter_reason", sa.Text(), nullable=True),
    )
    op.add_column(
        "domain_event_outbox",
        sa.Column("replay_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "domain_event_outbox",
        sa.Column("last_replayed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "ck_domain_event_replay_count_nonnegative",
        "domain_event_outbox",
        "replay_count >= 0",
    )
    op.create_index(
        "ix_domain_event_outbox_dead_lettered",
        "domain_event_outbox",
        ["dead_lettered_at", "occurred_at"],
    )

    op.create_table(
        "domain_event_consumptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "event_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("domain_event_outbox.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "company_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("consumer_name", sa.String(120), nullable=False),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "outcome",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.UniqueConstraint(
            "event_id", "consumer_name", name="uq_domain_event_consumer"
        ),
    )
    op.create_index(
        "ix_domain_event_consumptions_company",
        "domain_event_consumptions",
        ["company_id", "processed_at"],
    )

    op.execute(
        "ALTER TABLE public.domain_event_consumptions ENABLE ROW LEVEL SECURITY"
    )
    op.execute(
        "ALTER TABLE public.domain_event_consumptions FORCE ROW LEVEL SECURITY"
    )
    op.execute("""
        CREATE POLICY domain_event_consumptions_admin_only
        ON public.domain_event_consumptions
        FOR ALL
        USING (public.nlc_current_user_principal() = 'ADMIN')
        WITH CHECK (public.nlc_current_user_principal() = 'ADMIN')
    """)
    op.execute(
        "GRANT SELECT, INSERT ON TABLE public.domain_event_consumptions TO nlc_app_role"
    )
    op.execute(
        "REVOKE UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER "
        "ON TABLE public.domain_event_consumptions FROM nlc_app_role"
    )


def downgrade() -> None:
    op.drop_table("domain_event_consumptions")
    op.drop_index(
        "ix_domain_event_outbox_dead_lettered",
        table_name="domain_event_outbox",
    )
    op.drop_constraint(
        "ck_domain_event_replay_count_nonnegative",
        "domain_event_outbox",
        type_="check",
    )
    op.drop_column("domain_event_outbox", "last_replayed_at")
    op.drop_column("domain_event_outbox", "replay_count")
    op.drop_column("domain_event_outbox", "dead_letter_reason")
    op.drop_column("domain_event_outbox", "dead_lettered_at")
