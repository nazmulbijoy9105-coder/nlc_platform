"""Quarantine unverified historical AGM defaults while retaining source values.

Revision ID: 0045_agm_evidence_nullability
Revises: 0044_webhook_schema_reconcile

This migration is intentionally idempotent because 0045_agm_held_fields is a
sibling revision that may add some of the same structural columns. Legacy
values are preserved for audit only and are never treated as verified facts.
"""
from alembic import op
import sqlalchemy as sa

revision = "0045_agm_evidence_nullability"
down_revision = "0044_webhook_schema_reconcile"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Retain the exact historical values before quarantining them. The legacy
    # columns are archival only; application scoring must not read them.
    op.execute("""
        ALTER TABLE agms
        ADD COLUMN IF NOT EXISTS members_present_legacy INTEGER NULL,
        ADD COLUMN IF NOT EXISTS quorum_required_legacy INTEGER NULL,
        ADD COLUMN IF NOT EXISTS quorum_met_legacy BOOLEAN NULL,
        ADD COLUMN IF NOT EXISTS auditor_reappointed_legacy BOOLEAN NULL,
        ADD COLUMN IF NOT EXISTS minutes_prepared_legacy BOOLEAN NULL,
        ADD COLUMN IF NOT EXISTS venue VARCHAR(255) NULL,
        ADD COLUMN IF NOT EXISTS accounts_adopted BOOLEAN NULL,
        ADD COLUMN IF NOT EXISTS agm_held_without_audit BOOLEAN NULL
    """)
    op.execute("""
        UPDATE agms SET
            members_present_legacy = COALESCE(members_present_legacy, members_present),
            quorum_required_legacy = COALESCE(quorum_required_legacy, quorum_required),
            quorum_met_legacy = COALESCE(quorum_met_legacy, quorum_met),
            auditor_reappointed_legacy = COALESCE(auditor_reappointed_legacy, auditor_reappointed),
            minutes_prepared_legacy = COALESCE(minutes_prepared_legacy, minutes_prepared)
    """)

    # Make each field nullable before writing UNKNOWN (NULL). Updating first
    # would violate the old NOT NULL constraints on historical databases.
    op.alter_column(
        "agms", "members_present",
        existing_type=sa.Integer(), nullable=True, server_default=None,
    )
    op.alter_column(
        "agms", "quorum_required",
        existing_type=sa.Integer(), nullable=True, server_default=None,
    )
    op.alter_column(
        "agms", "quorum_met",
        existing_type=sa.Boolean(), nullable=True, server_default=None,
    )
    op.alter_column(
        "agms", "auditor_reappointed",
        existing_type=sa.Boolean(), nullable=True, server_default=None,
    )
    op.alter_column(
        "agms", "minutes_prepared",
        existing_type=sa.Boolean(), nullable=True, server_default=None,
    )

    # Only values indistinguishable from historical ORM defaults are reset.
    # Their original values remain in *_legacy columns for forensic review.
    op.execute("UPDATE agms SET members_present = NULL WHERE members_present = 0")
    op.execute("UPDATE agms SET quorum_required = NULL WHERE quorum_required = 2")
    op.execute("UPDATE agms SET quorum_met = NULL WHERE quorum_met IS TRUE")
    op.execute("UPDATE agms SET auditor_reappointed = NULL WHERE auditor_reappointed IS TRUE")
    op.execute("UPDATE agms SET minutes_prepared = NULL WHERE minutes_prepared IS FALSE")


def downgrade() -> None:
    # Forward-only: restoring the old defaults or deleting shared AGM columns
    # could fabricate evidence or remove columns owned by the sibling revision.
    pass
