"""Merge the historical Articles verification branch into the canonical release graph.

The deployed/test database may already be stamped at 0048_articles_verification.
Keep that historical revision reachable, then join it to the canonical
subscription head without rewriting or stamping existing database history.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0077_merge_legacy_articles_head"
down_revision: Union[str, Sequence[str], None] = (
    "0076_subscription_entitlements",
    "0048_articles_verification",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No schema changes; this revision joins the two existing histories."""
    pass


def downgrade() -> None:
    """No schema changes to reverse."""
    pass
