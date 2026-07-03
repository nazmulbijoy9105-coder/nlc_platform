"""merge reg_004 and v2_compliance fields

NEUM LEX COUNSEL — Database Migration
Revision:  759a8770c786
Previous:  6b203d92f6a8
Created:   2026-07-03 21:32:01.885435+06:00

Release Governance Protocol (Part III §7):
  [ ] Legal review completed
  [ ] AI Constitution compliance verified
  [ ] Staging tested (minimum 48 hours)
  [ ] Super Admin approval obtained
  [ ] Rollback plan documented (downgrade() below)
  [ ] Client communication prepared if schema affects UI

NEVER run downgrade() on production without explicit approval.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# ── Revision identifiers ──────────────────────────────────────────────
revision: str = '759a8770c786'
down_revision: Union[str, None] = '6b203d92f6a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply this migration."""
    pass


def downgrade() -> None:
    """
    Roll back this migration.
    Document what data may be lost on downgrade.
    """
    pass
