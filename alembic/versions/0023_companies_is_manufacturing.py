"""add companies.is_manufacturing tri-state (R-003/R-008)

Revision ID: 0023_is_manufacturing
Revises: 0022_reconcile_rule_corpus
"""
from alembic import op
import sqlalchemy as sa

revision = "0023_is_manufacturing"
down_revision = "0022_reconcile_rule_corpus"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Nullable, no default: NULL = unknown. Metadata-only on PostgreSQL.
    op.add_column("companies", sa.Column("is_manufacturing", sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column("companies", "is_manufacturing")
