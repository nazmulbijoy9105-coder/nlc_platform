"""Reconcile existing webhook schema and keep evidence closed until signed RLS.

Revision ID: 0044_webhook_schema_reconcile
Revises: b10c91ac6860
"""
from alembic import op

revision = "0044_webhook_schema_reconcile"
down_revision = "b10c91ac6860"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 0037/0038 are the authoritative table-creation migrations. If an
    # installation already records a later revision but these evidence tables
    # are missing, do not silently create empty replacements and hide data
    # loss. Stop for backup/schema-drift reconciliation.
    op.execute("""
        DO $preflight$
        BEGIN
            IF to_regclass('public.webhook_endpoints') IS NULL THEN
                RAISE EXCEPTION
                    'Expected public.webhook_endpoints from migration 0037 is missing; restore/reconcile evidence before continuing';
            END IF;
            IF to_regclass('public.webhook_deliveries') IS NULL THEN
                RAISE EXCEPTION
                    'Expected public.webhook_deliveries from migration 0037 is missing; restore/reconcile evidence before continuing';
            END IF;
            IF to_regclass('public.rescue_audit_log') IS NULL THEN
                RAISE EXCEPTION
                    'Expected public.rescue_audit_log from migration 0038 is missing; restore/reconcile audit evidence before continuing';
            END IF;
        END
        $preflight$;
    """)

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

    # Remove every legacy raw-GUC policy and force RLS with no replacement
    # policy. This intentionally denies app access until migration 0050
    # installs HMAC-verified owner/staff policies.
    for table in ("webhook_endpoints", "webhook_deliveries", "rescue_audit_log"):
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
    # caller-controlled identity vulnerability; table data is retained.
    pass
