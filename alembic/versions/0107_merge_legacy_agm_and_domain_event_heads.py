"""Join the historical AGM evidence head to the current domain-event head.

Revision ID: 0107_merge_legacy_agm_and_domain_event_heads
Revises: 0048_merge_agm_evidence_heads, 0106_domain_event_processing_controls

This is a no-op merge. The domain-event branch carries the complete current
release chain through 0106; the legacy AGM merge revision is retained as a
separate historical node. This revision joins them without rewriting,
renaming, or deleting any applied migration.
"""

revision = "0107_merge_legacy_agm_and_domain_event_heads"
down_revision = (
    "0048_merge_agm_evidence_heads",
    "0106_domain_event_processing_controls",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    """No schema change; join both migration histories."""
    pass


def downgrade() -> None:
    """No schema change to reverse."""
    pass
