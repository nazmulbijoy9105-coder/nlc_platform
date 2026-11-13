"""Add immutable statutory rule outcome snapshots to evaluation runs.

Revision ID: 0111_rule_outcome_ledger
Revises: 0110_legal_provenance_acl
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0111_rule_outcome_ledger"
down_revision = "0110_legal_provenance_acl"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "compliance_evaluation_runs",
        sa.Column(
            "rule_outcomes_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Immutable one-row-per-active-legal-rule outcome ledger; absence of a finding is NOT_EVALUATED.",
        ),
    )
    op.add_column(
        "compliance_evaluation_runs",
        sa.Column("rule_outcomes_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "compliance_evaluation_runs",
        sa.Column("rule_catalogue_count", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("compliance_evaluation_runs", "rule_catalogue_count")
    op.drop_column("compliance_evaluation_runs", "rule_outcomes_hash")
    op.drop_column("compliance_evaluation_runs", "rule_outcomes_snapshot")
