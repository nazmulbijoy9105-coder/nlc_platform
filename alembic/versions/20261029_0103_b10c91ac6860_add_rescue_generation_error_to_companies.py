"""add rescue_generation_error to companies

NEUM LEX COUNSEL — Database Migration
Revision:  b10c91ac6860
Previous:  0042_dedup_key
Created:   2026-10-29 01:03:54.282664+06:00

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
revision: str = 'b10c91ac6860'
down_revision: Union[str, None] = '0043_reconcile_notification_dedup_key'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply this migration."""
    op.add_column('companies', sa.Column('rescue_generation_error', sa.Text(), nullable=True))


def downgrade() -> None:
    """
    Roll back this migration.
    Drops the rescue_generation_error column. Data in this column is
    transient error text; no business data is lost.
    """
    op.drop_column('companies', 'rescue_generation_error')
