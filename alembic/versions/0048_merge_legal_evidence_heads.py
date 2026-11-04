"""Merge the legal evidence and AGM default migration heads.

This is a no-op merge revision. It makes `alembic upgrade head` deterministic
after both independent branches from 0045 have been applied.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0048_merge_legal_evidence_heads"
down_revision: Union[str, Sequence[str], None] = (
    "0046_legal_evidence_provenance",
    "0047_agm_unknown_defaults",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No schema change; this revision joins the two migration branches."""
    pass


def downgrade() -> None:
    """No schema change to reverse."""
    pass
