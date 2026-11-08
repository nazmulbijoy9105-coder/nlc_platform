"""Merge the current independent release and historical Articles branches.

Revision ID: 0081_merge_release_and_articles_wallet_heads
Revises: 0077_merge_0076_release_heads, 0080_manual_mobile_wallet_methods

Both branches contain already-reviewed schema changes. This revision is
schema-neutral and makes the canonical upgrade target unambiguous for clean
installs and databases restored from either historical branch.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0081_merge_release_and_articles_wallet_heads"
down_revision: Union[str, Sequence[str], None] = (
    "0077_merge_0076_release_heads",
    "0080_manual_mobile_wallet_methods",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No schema changes; join the independent histories."""
    pass


def downgrade() -> None:
    """No schema changes to reverse."""
    pass
