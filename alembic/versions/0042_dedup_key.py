"""add deduplication_key to notifications (COM-006)

Revision ID: 0042_dedup_key
Revises: 0041_rejected_by
"""
from alembic import op
import sqlalchemy as sa

revision = "0042_dedup_key"
down_revision = "0041_rejected_by"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "notifications",
        sa.Column(
            "deduplication_key",
            sa.String(200),
            nullable=True,
            comment="Idempotency key — same key = same logical notification (COM-006)",
        ),
    )
    op.create_index(
        "ix_notifications_dedup_key",
        "notifications",
        ["company_id", "deduplication_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_notifications_dedup_key", table_name="notifications")
    op.drop_column("notifications", "deduplication_key")
