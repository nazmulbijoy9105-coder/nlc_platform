"""persist rescue source rule IDs

Revision ID: 0092_rescue_source_rule_ids
Revises: 0091_calendar_legal_provenance
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0092_rescue_source_rule_ids"
down_revision = "0091_calendar_legal_provenance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "rescue_plans",
        sa.Column(
            "source_rule_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
            comment="Released statutory rule IDs supporting this rescue plan",
        ),
    )
    op.alter_column("rescue_plans", "source_rule_ids", server_default=None)


def downgrade() -> None:
    op.drop_column("rescue_plans", "source_rule_ids")
