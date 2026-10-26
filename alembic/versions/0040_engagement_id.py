"""add engagement_id to rescue_plans (RES-010)

Revision ID: 0040_engagement_id
Revises: 0039_add_evaluation_status
"""
from alembic import op
import sqlalchemy as sa

revision = "0040_engagement_id"
down_revision = "0039_add_evaluation_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "rescue_plans",
        sa.Column(
            "engagement_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="FK to engagements.id — links rescue plan to commercial engagement (RES-010)",
        ),
    )
    op.create_index(
        "ix_rescue_plans_engagement_id",
        "rescue_plans",
        ["engagement_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_rescue_plans_engagement_id", table_name="rescue_plans")
    op.drop_column("rescue_plans", "engagement_id")
