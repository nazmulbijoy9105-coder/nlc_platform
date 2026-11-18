"""Merge the independently governed alias and finding-context branches.

Revision ID: 0121_merge_alias_and_finding_context_heads
Revises: 0118_legal_rule_alias_overlap_guard, 0120_governed_finding_context_catalog

This is an Alembic graph merge only. Both parent migrations remain intact;
the merge performs no DDL and changes no application data.
"""
revision = "0121_merge_alias_and_finding_context_heads"
down_revision = (
    "0118_legal_rule_alias_overlap_guard",
    "0120_governed_finding_context_catalog",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    raise RuntimeError(
        "0121 is a forward-only graph merge; do not split governed migration history."
    )
