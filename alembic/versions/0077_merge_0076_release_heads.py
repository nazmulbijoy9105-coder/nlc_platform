"""Merge the two independent 0076 release migrations.

Revision ID: 0077_merge_0076_release_heads
Revises: 0076_manual_mobile_wallet_methods, 0076_subscription_entitlements

Schema-neutral merge. Both 0076 revisions descend from 0075; this revision
restores a single Alembic head before any new schema work.
"""
from alembic import op

revision = "0077_merge_0076_release_heads"
down_revision = (
    "0076_manual_mobile_wallet_methods",
    "0076_subscription_entitlements",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
