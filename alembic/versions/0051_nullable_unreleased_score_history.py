"""Allow monthly score history to represent unreleased evaluations.

Revision ID: 0051_nullable_unreleased_score_history
Revises: 0050_signed_rls_identity_hardening

Existing immutable history is preserved. New NOT_EVALUATED snapshots store NULL
rather than an internal provisional numeric result.
"""
from alembic import op
import sqlalchemy as sa

revision = "0051_nullable_unreleased_score_history"
down_revision = "0050_signed_rls_identity_hardening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "compliance_score_history",
        "score",
        existing_type=sa.Integer(),
        nullable=True,
    )


def downgrade() -> None:
    # Forward-only: converting withheld NULL scores into invented numeric
    # values would corrupt the legal audit trail.
    pass
