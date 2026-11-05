"""Merge the independent AGM evidence and provenance migration branches.

Revision ID: 0048_merge_agm_evidence_heads
Revises: 0045_agm_evidence_nullability, 0046_legal_evidence_provenance, 0047_agm_unknown_defaults

The 0045 evidence quarantine and 0045 held-field/provenance work are separate
branches. This merge joins all three current heads without repeating schema
operations.
"""
revision = "0048_merge_agm_evidence_heads"
down_revision = (
    "0045_agm_evidence_nullability",
    "0046_legal_evidence_provenance",
    "0047_agm_unknown_defaults",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    # All schema and data operations are performed by the parent revisions.
    pass


def downgrade() -> None:
    # A merge revision has no independent downgrade operations.
    pass
