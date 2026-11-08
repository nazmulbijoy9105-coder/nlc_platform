"""Join finance billing with the legal-release notification branch.

Revision ID: 0060_merge_finance_release_heads
Revises: 0058_suppress_unreleased_rule_notifications, 0059_financial_billing_core

No schema change. Both branches are retained: legal-release controls remain
forward-only, while finance role separation and billing tables are installed
on the sibling branch. This revision restores a single canonical Alembic head.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0060_merge_finance_release_heads"
down_revision: Union[str, Sequence[str], None] = (
    "0058_suppress_unreleased_rule_notifications",
    "0059_financial_billing_core",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    # Forward-only security and finance history.
    pass
