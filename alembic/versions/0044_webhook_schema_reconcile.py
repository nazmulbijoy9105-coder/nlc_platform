"""Reconcile webhook schema and keep it closed until signed RLS is installed.

Revision ID: 0044_webhook_schema_reconcile
Revises: b10c91ac6860
"""
from alembic import op

revision = "0044_webhook_schema_reconcile"
down_revision = "b10c91ac6860"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # These tables are reconciled here, but 0050 is the first migration that
    # installs cryptographically verified user identity. Do not install a
    # raw caller-settable GUC policy in this intermediate revision.
    op.execute("""
        CREATE TABLE IF NOT EXISTS public.webhook_endpoints (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES public.users(id) ON DELETE CASCADE,
            url VARCHAR(500) NOT NULL,
            secret VARCHAR(128) NOT NULL,
            events VARCHAR(50)[] NOT NULL DEFAULT '{}',
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            last_delivery_at TIMESTAMPTZ NULL,
            last_response_code INTEGER NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS public.webhook_deliveries (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            endpoint_id UUID NOT NULL REFERENCES public.webhook_endpoints(id) ON DELETE CASCADE,
            event_type VARCHAR(50) NOT NULL,
            payload JSONB NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
            attempts INTEGER NOT NULL DEFAULT 0,
            max_attempts INTEGER NOT NULL DEFAULT 3,
            response_code INTEGER NULL,
            response_body TEXT NULL,
            error_message TEXT NULL,
            delivered_at TIMESTAMPTZ NULL,
            next_retry_at TIMESTAMPTZ NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    for statement in (
        "CREATE INDEX IF NOT EXISTS idx_webhook_endpoints_user ON public.webhook_endpoints(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_webhook_endpoints_active ON public.webhook_endpoints(is_active)",
        "CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_endpoint ON public.webhook_deliveries(endpoint_id)",
        "CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_pending ON public.webhook_deliveries(status) WHERE status = 'PENDING'",
        "CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_retry ON public.webhook_deliveries(next_retry_at) WHERE status = 'PENDING' AND next_retry_at IS NOT NULL",
    ):
        op.execute(statement)

    op.execute("ALTER TABLE public.webhook_deliveries ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()")

    # Remove every legacy policy and force RLS with no replacement policy.
    # This intentionally denies app access if 0050 cannot complete.
    for table in ("webhook_endpoints", "webhook_deliveries"):
        op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE public.{table} FORCE ROW LEVEL SECURITY")
        op.execute(f"""
            DO $policies$
            DECLARE p record;
            BEGIN
                FOR p IN
                    SELECT policyname FROM pg_policies
                    WHERE schemaname = 'public' AND tablename = '{table}'
                LOOP
                    EXECUTE format('DROP POLICY %I ON public.{table}', p.policyname);
                END LOOP;
            END
            $policies$;
        """)
        op.execute(f"REVOKE ALL ON TABLE public.{table} FROM PUBLIC")
        op.execute(f"REVOKE ALL ON TABLE public.{table} FROM nlc_app_role")

    # Rescue audit records are also closed during the transition. The table
    # may be absent on a drifted legacy installation; 0050 preflight must
    # reject that installation rather than silently recreating its evidence.
    op.execute("""
        DO $rescue$
        BEGIN
            IF to_regclass('public.rescue_audit_log') IS NOT NULL THEN
                ALTER TABLE public.rescue_audit_log ENABLE ROW LEVEL SECURITY;
                ALTER TABLE public.rescue_audit_log FORCE ROW LEVEL SECURITY;
                EXECUTE 'REVOKE ALL ON TABLE public.rescue_audit_log FROM PUBLIC';
                EXECUTE 'REVOKE ALL ON TABLE public.rescue_audit_log FROM nlc_app_role';
                EXECUTE 'DROP POLICY IF EXISTS rescue_audit_log_tenant_scope ON public.rescue_audit_log';
            END IF;
        END
        $rescue$;
    """)


def downgrade() -> None:
    # Forward-only: reintroducing raw-GUC policies would restore the
    # caller-controlled identity vulnerability.
    pass
