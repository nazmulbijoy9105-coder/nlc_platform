"""Reconcile webhook schema and tenant RLS on existing installations.

Revision ID: 0043_webhook_schema_reconcile
Revises: 0042_dedup_key

The webhook models and migration 0037 exist in source, but the deployed
schema inspected for this release is at 0042 and lacks both webhook tables.
This idempotent reconciliation makes the missing schema explicit.
"""
from alembic import op

revision = "0043_webhook_schema_reconcile"
down_revision = "0042_dedup_key"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS webhook_endpoints (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
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
        CREATE TABLE IF NOT EXISTS webhook_deliveries (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            endpoint_id UUID NOT NULL REFERENCES webhook_endpoints(id) ON DELETE CASCADE,
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
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_webhook_endpoints_user ON webhook_endpoints(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_webhook_endpoints_active ON webhook_endpoints(is_active)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_endpoint ON webhook_deliveries(endpoint_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_pending ON webhook_deliveries(status) WHERE status = 'PENDING'")
    op.execute("CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_retry ON webhook_deliveries(next_retry_at) WHERE status = 'PENDING' AND next_retry_at IS NOT NULL")

    op.execute("ALTER TABLE webhook_endpoints ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE webhook_deliveries ENABLE ROW LEVEL SECURITY")
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_policies
                WHERE schemaname = 'public' AND tablename = 'webhook_endpoints'
                  AND policyname = 'webhook_endpoints_owner_scope'
            ) THEN
                CREATE POLICY webhook_endpoints_owner_scope ON webhook_endpoints
                USING (
                    current_setting('app.current_user_id', true) = 'ADMIN'
                    OR user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
                )
                WITH CHECK (
                    current_setting('app.current_user_id', true) = 'ADMIN'
                    OR user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
                );
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM pg_policies
                WHERE schemaname = 'public' AND tablename = 'webhook_deliveries'
                  AND policyname = 'webhook_deliveries_owner_scope'
            ) THEN
                CREATE POLICY webhook_deliveries_owner_scope ON webhook_deliveries
                USING (
                    current_setting('app.current_user_id', true) = 'ADMIN'
                    OR EXISTS (
                        SELECT 1 FROM webhook_endpoints e
                        WHERE e.id = webhook_deliveries.endpoint_id
                          AND e.user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
                    )
                )
                WITH CHECK (
                    current_setting('app.current_user_id', true) = 'ADMIN'
                    OR EXISTS (
                        SELECT 1 FROM webhook_endpoints e
                        WHERE e.id = webhook_deliveries.endpoint_id
                          AND e.user_id = NULLIF(current_setting('app.current_user_id', true), '')::uuid
                    )
                );
            END IF;
        END
        $$
    """)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nlc_app_role') THEN
                GRANT SELECT, INSERT, UPDATE, DELETE ON webhook_endpoints TO nlc_app_role;
                GRANT SELECT, INSERT, UPDATE, DELETE ON webhook_deliveries TO nlc_app_role;
            END IF;
        END
        $$
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS webhook_deliveries")
    op.execute("DROP TABLE IF EXISTS webhook_endpoints")
