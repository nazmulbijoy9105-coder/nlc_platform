"""Add evidence-only NOT_EVALUATED to persisted severity values.

Revision ID: 0056_add_not_evaluated_severity
Revises: 0055_quarantine_unverified_agm_defaults

This revision contains only the PostgreSQL enum addition. Do not use the new
value in this migration: PostgreSQL makes a newly added enum value usable only
after this revision's transaction commits. env.py enables transaction_per_migration
so subsequent revisions and application code run after that commit.
"""
from alembic import op

revision = "0056_add_not_evaluated_severity"
down_revision = "0055_quarantine_unverified_agm_defaults"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE severity_level "
        "ADD VALUE IF NOT EXISTS 'NOT_EVALUATED' AFTER 'BLACK'"
    )


def downgrade() -> None:
    # PostgreSQL enum values cannot be safely removed after rows may use them.
    pass
