"""Quarantine legacy AGM quorum/auditor defaults without losing source values.

Revision ID: 0055_quarantine_unverified_agm_defaults
Revises: 0054_merge_release_heads

The earlier nullability migration removed server defaults but left historical
TRUE/2 values in existing rows. Those values are not evidence of quorum or
auditor reappointment. Preserve them in archival columns and expose active
values only when the full provenance tuple is present.
"""
from alembic import op

revision = "0055_quarantine_unverified_agm_defaults"
down_revision = "0054_merge_release_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE agms
        ADD COLUMN IF NOT EXISTS quorum_required_legacy INTEGER NULL,
        ADD COLUMN IF NOT EXISTS quorum_met_legacy BOOLEAN NULL,
        ADD COLUMN IF NOT EXISTS auditor_reappointed_legacy BOOLEAN NULL
    """)

    # Preserve the exact historical values before changing active evidence.
    op.execute("""
        UPDATE agms
        SET
            quorum_required_legacy = COALESCE(quorum_required_legacy, quorum_required),
            quorum_met_legacy = COALESCE(quorum_met_legacy, quorum_met),
            auditor_reappointed_legacy = COALESCE(
                auditor_reappointed_legacy,
                auditor_reappointed
            )
    """)

    # A quorum threshold is usable only with its verified source, timestamp,
    # and reviewer identity. TRUE/2 defaults without that provenance are UNKNOWN.
    op.execute("""
        UPDATE agms
        SET quorum_required = NULL
        WHERE quorum_required IS NOT NULL
          AND NOT (
              quorum_required_verified IS TRUE
              AND NULLIF(BTRIM(quorum_evidence_ref), '') IS NOT NULL
              AND quorum_verified_at IS NOT NULL
              AND quorum_verified_by IS NOT NULL
          )
    """)

    # A quorum result depends on both independently verified attendance and
    # an independently verified quorum basis. Do not retain an orphaned TRUE
    # or FALSE result when either input is unverified.
    op.execute("""
        UPDATE agms
        SET quorum_met = NULL
        WHERE quorum_met IS NOT NULL
          AND NOT (
              members_present_verified IS TRUE
              AND NULLIF(BTRIM(members_present_evidence_ref), '') IS NOT NULL
              AND members_present_verified_at IS NOT NULL
              AND members_present_verified_by IS NOT NULL
              AND quorum_required_verified IS TRUE
              AND NULLIF(BTRIM(quorum_evidence_ref), '') IS NOT NULL
              AND quorum_verified_at IS NOT NULL
              AND quorum_verified_by IS NOT NULL
              AND quorum_required IS NOT NULL
          )
    """)

    # Auditor reappointment is retained only when the record has complete,
    # reviewer-bound provenance. The old TRUE default is not a legal fact.
    op.execute("""
        UPDATE agms
        SET auditor_reappointed = NULL
        WHERE auditor_reappointed IS NOT NULL
          AND NOT (
              auditor_reappointment_verified IS TRUE
              AND NULLIF(BTRIM(auditor_reappointment_evidence_ref), '') IS NOT NULL
              AND auditor_reappointment_verified_at IS NOT NULL
              AND auditor_reappointment_verified_by IS NOT NULL
          )
    """)


def downgrade() -> None:
    # Forward-only: restoring unverified historical defaults would recreate
    # false evidence. The *_legacy columns are retained for audit provenance.
    pass
