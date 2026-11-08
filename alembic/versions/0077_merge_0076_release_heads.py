"""Merge the two independent 0076 release migrations.

Revision ID: 0077_merge_0076_release_heads
Revises: 0076_manual_mobile_wallet_methods, 0076_subscription_entitlements

This merge is intentionally schema-neutral. It makes the Alembic graph
unambiguous before any further schema changes are introduced.
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
    # A merge revision has no schema effect; branch ancestry is retained.
    pass
