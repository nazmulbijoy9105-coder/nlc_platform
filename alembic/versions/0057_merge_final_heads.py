"""Merge the two remaining migration heads into one.

Revision ID: 0057_merge_final_heads
Revises: 0051_merge_release_heads, 0056_add_not_evaluated_severity
"""
from alembic import op

revision = "0057_merge_final_heads"
down_revision = (
    "0051_merge_release_heads",
    "0056_add_not_evaluated_severity",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
