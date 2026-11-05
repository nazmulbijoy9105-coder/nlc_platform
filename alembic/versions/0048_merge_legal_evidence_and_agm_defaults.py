"""Merge the legal evidence and AGM unknown-default migration heads.

The legal-evidence and AGM-default migrations both descend from 0045. This
merge revision makes Alembic's graph unambiguous so production can upgrade to
one head after the schema/catalog preflight has passed.

Revision ID: 0048_merge_legal_evidence_and_agm_defaults
Revises: 0046_legal_evidence_provenance, 0047_agm_unknown_defaults
"""
from alembic import op

revision = "0048_merge_legal_evidence_and_agm_defaults"
down_revision = (
    "0046_legal_evidence_provenance",
    "0047_agm_unknown_defaults",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Merge-only revision. The parent revisions perform the additive schema
    # reconciliation and evidence-default hardening.
    pass


def downgrade() -> None:
    # A merge point has no independent schema effect.
    pass
