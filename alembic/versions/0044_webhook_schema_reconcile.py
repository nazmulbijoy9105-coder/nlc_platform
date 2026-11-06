"""Reconcile webhook schema without silently recreating missing evidence.

Revision ID: 0044_webhook_schema_reconcile
Revises: b10c91ac6860
"""
from alembic import op
import sqlalchemy as sa

revision = "0044_webhook_schema_reconcile"
down_revision = "b10c91ac6860"
branch_labels = None
depends_on = None


REQUIRED_TABLES = (
    "webhook_endpoints",
    "webhook_deliveries",
    "rescue_audit_log",
)


def upgrade() -> None:
    # These objects are created by earlier revisions (0037/0038). If one is
    # missing, the database has drifted or lost operational/audit evidence.
    # Do not CREATE TABLE IF NOT EXISTS here: an empty replacement would hide
    # missing webhook configuration, delivery history, or rescue audit rows.
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
            "Webhook/rescue schema preflight found missing historical tables: "
            + ", ".join(sorted(missing))
            + ". Restore/reconcile schema and evidence from a verified backup "
            "before retrying; this migration will not recreate empty tables."
        )

    for statement in (
        "CREATE INDEX IF NOT EXISTS idx_webhook_endpoints_user ON public.webhook_endpoints(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_webhook_endpoints_active ON public.webhook_endpoints(is_active)",
        "CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_endpoint ON public.webhook_deliveries(endpoint_id)",
        "CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_pending ON public.webhook_deliveries(status) WHERE status = 'PENDING'",
        "CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_retry ON public.webhook_deliveries(next_retry_at) WHERE status = 'PENDING' AND next_retry_at IS NOT NULL",
    ):
        op.execute(statement)

    op.execute(
        "ALTER TABLE public.webhook_deliveries "
        "ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()"
    )

    # Do not install raw caller-settable GUC policies. Close webhook and
    # rescue-audit tables with FORCE RLS and no policies until 0050 installs
    # cryptographically verified signed-identity policies.
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
    # Forward-only: reintroducing raw-GUC policies would restore the
    # caller-controlled identity vulnerability.
    pass
