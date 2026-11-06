"""add webhook tables

Revision ID: 0037_add_webhook_tables
Revises: 0036_nullable_bools
"""
from alembic import op
import sqlalchemy as sa

revision = "0037_add_webhook_tables"
down_revision = "0036_nullable_bools"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "webhook_endpoints",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("secret", sa.String(128), nullable=False, server_default=sa.text("gen_random_uuid()::text")),
        sa.Column("events", sa.dialects.postgresql.ARRAY(sa.String(50)), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("TRUE")),
        sa.Column("last_delivery_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("last_response_code", sa.Integer, nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("idx_webhook_endpoints_user", "webhook_endpoints", ["user_id"])
    op.create_index("idx_webhook_endpoints_active", "webhook_endpoints", ["is_active"])

    op.create_table(
        "webhook_deliveries",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("endpoint_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("webhook_endpoints.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("payload", sa.dialects.postgresql.JSONB, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'PENDING'")),  # PENDING, DELIVERED, FAILED
        sa.Column("attempts", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("max_attempts", sa.Integer, nullable=False, server_default=sa.text("3")),
        sa.Column("response_code", sa.Integer, nullable=True),
        sa.Column("response_body", sa.Text, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("delivered_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("next_retry_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("idx_webhook_deliveries_endpoint", "webhook_deliveries", ["endpoint_id"])
    op.create_index("idx_webhook_deliveries_pending", "webhook_deliveries", ["status"], postgresql_where=sa.text("status = 'PENDING'"))
    op.create_index("idx_webhook_deliveries_retry", "webhook_deliveries", ["next_retry_at"], postgresql_where=sa.text("status = 'PENDING' AND next_retry_at IS NOT NULL"))

    # Keep endpoint secrets and delivery payloads closed until signed RLS
    # policies are installed by migration 0050. Do not expose these tables
    # through the legacy caller-controlled identity GUC.
    for table in ("webhook_endpoints", "webhook_deliveries"):
        op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE public.{table} FORCE ROW LEVEL SECURITY")
        op.execute(f"REVOKE ALL ON TABLE public.{table} FROM PUBLIC")
        op.execute(f"""
            DO $role$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nlc_app_role') THEN
                    EXECUTE 'REVOKE ALL ON TABLE public.{table} FROM nlc_app_role';
                END IF;
            END
            $role$;
        """)


def downgrade() -> None:
    # Forward-only: webhook endpoint secrets and delivery payloads are
    # operational evidence and must not be erased by schema rollback.
    pass
