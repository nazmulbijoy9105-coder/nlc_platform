"""Merge the parallel AGM evidence revisions into one Alembic head.

Revision ID: 0048_merge_agm_evidence_heads
Revises: 0046_legal_evidence_provenance, 0047_agm_unknown_defaults

The two revisions are intentionally independent: 0046 adds evidence provenance,
while 0047 removes fabricated defaults from AGM conclusions. This merge makes
the migration graph linear again without changing customer data.
"""
from alembic import op

revision = "0048_merge_agm_evidence_heads"
down_revision = (
    "0046_legal_evidence_provenance",
    "0047_agm_unknown_defaults",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Merge-only revision; both parent revisions have already been applied.
    pass


def downgrade() -> None:
    # Merge-only revision; retain both parent revisions on downgrade.
    pass
