"""Merge the AGM/legal and legacy rescue-error migration branches.

Revision ID: 0054_merge_release_heads
Revises: 0053_agm_minutes_unknown_default, b10c91ac6860

The rescue-generation-error migration branched from 0043 while the AGM,
evidence-provenance, signed-RLS, and unreleased-score migrations descend
from 0045. This merge joins both complete histories without changing schema.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0054_merge_release_heads"
down_revision: Union[str, Sequence[str], None] = (
    "0053_agm_minutes_unknown_default",
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
