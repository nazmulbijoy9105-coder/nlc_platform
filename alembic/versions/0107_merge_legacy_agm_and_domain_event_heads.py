"""Join the legacy AGM evidence merge head to the completed domain-event chain.

Revision ID: 0107_merge_legacy_agm_and_domain_event_heads
Revises: 0048_merge_agm_evidence_heads, 0106_domain_event_processing_controls

The three historical 0048 merge revisions are retained. The legal-evidence
merge branches and their descendants are already ancestors of
0106_domain_event_processing_controls; this final no-op merge joins the
remaining 0048 AGM merge node to that complete history without rewriting or
discarding any deployed revision.
"""

revision = "0107_merge_legacy_agm_and_domain_event_heads"
down_revision = (
    "0048_merge_agm_evidence_heads",
    "0106_domain_event_processing_controls",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    """No schema change; join the two existing migration histories."""
    pass


def downgrade() -> None:
    """No schema change to reverse."""
    pass
