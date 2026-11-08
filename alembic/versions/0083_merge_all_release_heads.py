"""Merge every independently restored release history into one head.

Revision ID: 0083_merge_all_release_heads
Revises: 0059_guard_user_privilege_updates, 0076_company_charge_evidence, 0082_agm_share_event_provenance

The security guard, company-charge evidence and legal AGM/share evidence
histories are independent on restored installations. This schema-neutral
revision makes all three part of one canonical upgrade target.
"""
from typing import Sequence, Union

revision: str = "0083_merge_all_release_heads"
down_revision: Union[str, Sequence[str], None] = (
    "0059_guard_user_privilege_updates",
    "0076_company_charge_evidence",
    "0082_agm_share_event_provenance",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No schema changes; join all independent release histories."""
    pass


def downgrade() -> None:
    """No schema changes to reverse."""
    pass
