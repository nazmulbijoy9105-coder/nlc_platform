"""Reconcile webhook schema and tenant RLS on existing installations."""
from alembic import op

revision = "0044_webhook_schema_reconcile"
down_revision = "b10c91ac6860"
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
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    for statement in (
        "CREATE INDEX IF NOT EXISTS idx_webhook_endpoints_user ON webhook_endpoints(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_webhook_endpoints_active ON webhook_endpoints(is_active)",
        "CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_endpoint ON webhook_deliveries(endpoint_id)",
        "CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_pending ON webhook_deliveries(status) WHERE status = 'PENDING'",
        "CREATE INDEX IF NOT EXISTS idx_webhook_deliveries_retry ON webhook_deliveries(next_retry_at) WHERE status = 'PENDING' AND next_retry_at IS NOT NULL",
    ):
        op.execute(statement)

    op.execute("ALTER TABLE webhook_deliveries ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()")
    op.execute("ALTER TABLE webhook_endpoints ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE webhook_deliveries ENABLE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS webhook_endpoints_owner_scope ON webhook_endpoints")
    # Fail closed until migration 0049 installs signed identity verification.
    op.execute("""
        CREATE POLICY webhook_endpoints_owner_scope ON webhook_endpoints
        USING (FALSE)
        WITH CHECK (FALSE)
    """)
    op.execute("DROP POLICY IF EXISTS webhook_deliveries_owner_scope ON webhook_deliveries")
    op.execute("""
        CREATE POLICY webhook_deliveries_owner_scope ON webhook_deliveries
        USING (FALSE)
        WITH CHECK (FALSE)
    """)
    op.execute("""
        DO $
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nlc_app_role') THEN
                REVOKE ALL PRIVILEGES ON webhook_endpoints FROM nlc_app_role;
                REVOKE ALL PRIVILEGES ON webhook_deliveries FROM nlc_app_role;
                GRANT SELECT, INSERT, UPDATE, DELETE ON webhook_endpoints TO nlc_app_role;
                GRANT SELECT, INSERT, UPDATE, DELETE ON webhook_deliveries TO nlc_app_role;
            END IF;
        END
        $$
    """)


def downgrade() -> None:
    # The reconciliation may have adopted tables created by the earlier 0037
    # migration. Never drop customer webhook data when reverting this revision.
    op.execute("DROP POLICY IF EXISTS webhook_deliveries_owner_scope ON webhook_deliveries")
    op.execute("DROP POLICY IF EXISTS webhook_endpoints_owner_scope ON webhook_endpoints")
    op.execute("ALTER TABLE IF EXISTS webhook_deliveries DISABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE IF EXISTS webhook_endpoints DISABLE ROW LEVEL SECURITY")
