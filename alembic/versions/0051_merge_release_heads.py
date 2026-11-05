"""Merge the legal-release and rescue-error migration histories.

Revision ID: 0051_merge_release_heads
Revises: 0050_add_not_evaluated_severity, b10c91ac6860

The legal-evidence/AGM branch and the rescue-generation-error migration
branched from different earlier revisions. This merge creates one Alembic
head without modifying database schema.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0051_merge_release_heads"
down_revision: Union[str, Sequence[str], None] = (
    "0050_add_not_evaluated_severity",
    "b10c91ac6860",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No schema change; join all supported migration histories."""
    pass


def downgrade() -> None:
    """No schema change to reverse."""
    pass
