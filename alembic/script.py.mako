"""${message}

NEUM LEX COUNSEL — Database Migration
Revision:  ${up_revision}
Previous:  ${down_revision | comma,n}
Created:   ${create_date}

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
${imports if imports else ""}

# ── Revision identifiers ──────────────────────────────────────────────
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    """Apply this migration."""
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """
    Roll back this migration.
    Document what data may be lost on downgrade.
    """
    ${downgrades if downgrades else "pass"}
