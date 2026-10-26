"""add rejected_by to quotations (COM-002)

Revision ID: 0041_rejected_by
Revises: 0040_engagement_id
"""
from alembic import op
import sqlalchemy as sa

revision = "0041_rejected_by"
down_revision = "0040_engagement_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "quotations",
        sa.Column(
            "rejected_by",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="FK to users.id — who rejected this quotation (COM-002)",
        ),
    )
    op.create_index(
        "ix_quotations_rejected_by",
        "quotations",
        ["rejected_by"],
    )


def downgrade() -> None:
    op.drop_index("ix_quotations_rejected_by", table_name="quotations")
    op.drop_column("quotations", "rejected_by")
