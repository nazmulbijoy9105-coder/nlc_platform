"""Reconcile missing webhook and rescue schema at the 0044 boundary.

Revision ID: 0044_webhook_schema_reconcile
Revises: b10c91ac6860

This migration may reconstruct missing *schema* objects so the release can
continue, but it cannot restore historical webhook or rescue-audit rows.
Every reconstructed table is explicitly marked in PostgreSQL metadata.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0044_webhook_schema_reconcile"
down_revision = "b10c91ac6860"
branch_labels = None
depends_on = None

REQUIRED_TABLES = (
    "webhook_endpoints",
    "webhook_deliveries",
    "rescue_audit_log",
)


def _create_missing_tables() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("webhook_endpoints", schema="public"):
        op.create_table(
            "webhook_endpoints",
            sa.Column(
                "id", postgresql.UUID(as_uuid=True), primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "user_id", postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False,
            ),
            sa.Column("url", sa.String(500), nullable=False),
            sa.Column(
                "secret", sa.String(128), nullable=False,
                server_default=sa.text("gen_random_uuid()::text"),
            ),
            sa.Column(
                "events", postgresql.ARRAY(sa.String(50)), nullable=False,
                server_default=sa.text("'{}'"),
            ),
            sa.Column(
                "is_active", sa.Boolean(), nullable=False,
                server_default=sa.text("TRUE"),
            ),
            sa.Column("last_delivery_at", sa.TIMESTAMP(timezone=True)),
            sa.Column("last_response_code", sa.Integer()),
            sa.Column(
                "created_at", sa.TIMESTAMP(timezone=True),
                server_default=sa.text("NOW()"), nullable=False,
            ),
            sa.Column(
                "updated_at", sa.TIMESTAMP(timezone=True),
                server_default=sa.text("NOW()"), nullable=False,
            ),
            schema="public",
        )
        op.execute("""
            COMMENT ON TABLE public.webhook_endpoints IS
            'SCHEMA-ONLY RECONSTRUCTION by Alembic 0044. Historical endpoint rows were not restored; verify external backups before relying on historical configuration.'
        """)

    if not inspector.has_table("webhook_deliveries", schema="public"):
        op.create_table(
            "webhook_deliveries",
            sa.Column(
                "id", postgresql.UUID(as_uuid=True), primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "endpoint_id", postgresql.UUID(as_uuid=True),
                sa.ForeignKey("webhook_endpoints.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("event_type", sa.String(50), nullable=False),
            sa.Column("payload", postgresql.JSONB(), nullable=False),
            sa.Column(
                "status", sa.String(20), nullable=False,
                server_default=sa.text("'PENDING'"),
            ),
            sa.Column("attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("max_attempts", sa.Integer(), nullable=False, server_default=sa.text("3")),
            sa.Column("response_code", sa.Integer()),
            sa.Column("response_body", sa.Text()),
            sa.Column("error_message", sa.Text()),
            sa.Column("delivered_at", sa.TIMESTAMP(timezone=True)),
            sa.Column("next_retry_at", sa.TIMESTAMP(timezone=True)),
            sa.Column(
                "created_at", sa.TIMESTAMP(timezone=True),
                server_default=sa.text("NOW()"), nullable=False,
            ),
            sa.Column(
                "updated_at", sa.TIMESTAMP(timezone=True),
                server_default=sa.text("NOW()"), nullable=False,
            ),
            schema="public",
        )
        op.execute("""
            COMMENT ON TABLE public.webhook_deliveries IS
            'SCHEMA-ONLY RECONSTRUCTION by Alembic 0044. Historical delivery and retry rows were not restored; do not interpret an empty table as proof that no deliveries occurred.'
        """)

    if not inspector.has_table("rescue_audit_log", schema="public"):
        op.create_table(
            "rescue_audit_log",
            sa.Column(
                "id", postgresql.UUID(as_uuid=True), primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "rescue_plan_id", postgresql.UUID(as_uuid=True),
                sa.ForeignKey("rescue_plans.id", ondelete="RESTRICT"),
                nullable=False,
            ),
            sa.Column(
                "finding_id", postgresql.UUID(as_uuid=True),
                sa.ForeignKey("compliance_flags.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("rule_id", sa.String(50), nullable=False),
            sa.Column("rule_version", sa.String(20), nullable=False),
            sa.Column("action_performed", sa.String(200), nullable=False),
            sa.Column(
                "actor_user_id", postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False,
            ),
            sa.Column("evidence_ref", sa.String(500)),
            sa.Column("outcome", sa.String(50), nullable=False),
            sa.Column("notes", sa.Text()),
            sa.Column(
                "created_at", sa.TIMESTAMP(timezone=True),
                server_default=sa.text("NOW()"), nullable=False,
            ),
            sa.Column(
                "updated_at", sa.TIMESTAMP(timezone=True),
                server_default=sa.text("NOW()"), nullable=False,
            ),
            schema="public",
        )
        op.execute("""
            COMMENT ON TABLE public.rescue_audit_log IS
            'SCHEMA-ONLY RECONSTRUCTION by Alembic 0044. Historical rescue audit rows were not restored. This empty table is not evidence that no rescue actions occurred.'
        """)


def upgrade() -> None:
    # The database is marked at b10c91ac6860, downstream of 0037/0038, but
    # physical schema inspection found the three historical tables missing.
    # Reconstruct only their schema, never fabricate historical records.
    _create_missing_tables()

    bind = op.get_bind()
    missing = [
        table
        for table in REQUIRED_TABLES
        if bind.execute(
            sa.text("SELECT to_regclass(:qualified_name)"),
            {"qualified_name": f"public.{table}"},
        ).scalar_one() is None
    ]
    if missing:
        raise RuntimeError(
            "Webhook/rescue schema reconciliation failed; still missing: "
            + ", ".join(sorted(missing))
        )

    for statement in (
        "CREATE INDEX IF NOT EXISTS idx_webhook_endpoints_user ON public.webhook_endpoints(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_webhook_endpoints_active ON public.webhook_endpoints(is_active)",
        "CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_endpoint ON public.webhook_deliveries(endpoint_id)",
        "CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_pending ON public.webhook_deliveries(status) WHERE status = 'PENDING'",
        "CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_retry ON public.webhook_deliveries(next_retry_at) WHERE status = 'PENDING' AND next_retry_at IS NOT NULL",
        "CREATE INDEX IF NOT EXISTS ix_rescue_audit_log_plan_id ON public.rescue_audit_log(rescue_plan_id)",
        "CREATE INDEX IF NOT EXISTS ix_rescue_audit_log_actor_id ON public.rescue_audit_log(actor_user_id)",
        "CREATE INDEX IF NOT EXISTS ix_rescue_audit_log_finding_id ON public.rescue_audit_log(finding_id)",
        "CREATE INDEX IF NOT EXISTS ix_rescue_audit_log_created_at ON public.rescue_audit_log(created_at)",
    ):
        op.execute(statement)

    op.execute(
        "ALTER TABLE public.webhook_deliveries "
        "ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"
    )

    # Close these sensitive tables until 0050 installs signed-identity RLS.
    for table in REQUIRED_TABLES:
        op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE public.{table} FORCE ROW LEVEL SECURITY")
        op.execute(f"REVOKE ALL ON TABLE public.{table} FROM PUBLIC")
        op.execute(f"""
            DO $policies$
            DECLARE p record;
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nlc_app_role') THEN
                    EXECUTE 'REVOKE ALL ON TABLE public.{table} FROM nlc_app_role';
                END IF;
                FOR p IN
                    SELECT policyname FROM pg_policies
                    WHERE schemaname = 'public' AND tablename = '{table}'
                LOOP
                    EXECUTE format('DROP POLICY %I ON public.{table}', p.policyname);
                END LOOP;
            END
            $policies$;
        """)


def downgrade() -> None:
    # Forward-only: do not drop reconstructed tables or reopen legacy GUC access.
    pass
