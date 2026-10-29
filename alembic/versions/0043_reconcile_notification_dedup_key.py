"""Reconcile notification deduplication schema (COM-006).

Revision ID: 0043_reconcile_notification_dedup_key
Revises: 0042_dedup_key
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0043_reconcile_notification_dedup_key"
down_revision = "0042_dedup_key"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not inspector.has_table("notifications"):
        raise RuntimeError(
            "Cannot reconcile COM-006: notifications table is missing"
        )

    columns = {
        column["name"]
        for column in inspector.get_columns("notifications")
    }

    if "deduplication_key" not in columns:
        op.add_column(
            "notifications",
            sa.Column(
                "deduplication_key",
                sa.String(200),
                nullable=True,
                comment="Idempotency key — same key = same logical notification (COM-006)",
            ),
        )

    indexes = {
        index["name"]
        for index in inspect(bind).get_indexes("notifications")
    }

    if "ix_notifications_dedup_key" not in indexes:
        op.create_index(
            "ix_notifications_dedup_key",
            "notifications",
            ["company_id", "deduplication_key"],
            unique=True,
        )


def downgrade() -> None:
    # Keep the reconciled schema intact during downgrade: these objects
    # may have existed before this migration and may be required by the app.
    pass
