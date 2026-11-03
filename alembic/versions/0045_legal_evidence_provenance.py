"""Add explicit legal evidence verification fields.

Revision ID: 0045_legal_evidence_provenance
Revises: 0044_webhook_schema_reconcile
"""
from alembic import op

revision = "0045_legal_evidence_provenance"
down_revision = "0044_webhook_schema_reconcile"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Company-level evidence review provenance. Existing legacy booleans are
    # deliberately NOT promoted to verified evidence.
    op.execute("""
        ALTER TABLE companies
        ADD COLUMN IF NOT EXISTS directors_verified BOOLEAN NOT NULL DEFAULT FALSE,
        ADD COLUMN IF NOT EXISTS directors_verified_at TIMESTAMPTZ NULL,
        ADD COLUMN IF NOT EXISTS directors_verified_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
        ADD COLUMN IF NOT EXISTS directors_verification_evidence_ref TEXT NULL,
        ADD COLUMN IF NOT EXISTS is_private_subsidiary_of_public_company BOOLEAN NULL,
        ADD COLUMN IF NOT EXISTS subsidiary_status_verified BOOLEAN NOT NULL DEFAULT FALSE,
        ADD COLUMN IF NOT EXISTS subsidiary_status_verified_at TIMESTAMPTZ NULL,
        ADD COLUMN IF NOT EXISTS subsidiary_status_verified_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
        ADD COLUMN IF NOT EXISTS subsidiary_status_evidence_ref TEXT NULL,
        ADD COLUMN IF NOT EXISTS moa_aoa_verified BOOLEAN NOT NULL DEFAULT FALSE,
        ADD COLUMN IF NOT EXISTS moa_aoa_verified_at TIMESTAMPTZ NULL,
        ADD COLUMN IF NOT EXISTS moa_aoa_verified_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
        ADD COLUMN IF NOT EXISTS moa_aoa_evidence_ref TEXT NULL,
        ADD COLUMN IF NOT EXISTS first_auditor_appointment_verified BOOLEAN NOT NULL DEFAULT FALSE,
        ADD COLUMN IF NOT EXISTS first_auditor_appointment_verified_at TIMESTAMPTZ NULL,
        ADD COLUMN IF NOT EXISTS first_auditor_appointment_verified_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
        ADD COLUMN IF NOT EXISTS first_auditor_appointment_evidence_ref TEXT NULL
    """)

    # AGM evidence is verified separately from its legacy database defaults.
    op.execute("""
        ALTER TABLE agms
        ADD COLUMN IF NOT EXISTS members_present_verified BOOLEAN NOT NULL DEFAULT FALSE,
        ADD COLUMN IF NOT EXISTS members_present_evidence_ref TEXT NULL,
        ADD COLUMN IF NOT EXISTS members_present_verified_at TIMESTAMPTZ NULL,
        ADD COLUMN IF NOT EXISTS members_present_verified_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
        ADD COLUMN IF NOT EXISTS quorum_required_verified BOOLEAN NOT NULL DEFAULT FALSE,
        ADD COLUMN IF NOT EXISTS quorum_evidence_ref TEXT NULL,
        ADD COLUMN IF NOT EXISTS quorum_verified_at TIMESTAMPTZ NULL,
        ADD COLUMN IF NOT EXISTS quorum_verified_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
        ADD COLUMN IF NOT EXISTS auditor_reappointment_verified BOOLEAN NOT NULL DEFAULT FALSE,
        ADD COLUMN IF NOT EXISTS auditor_reappointment_evidence_ref TEXT NULL,
        ADD COLUMN IF NOT EXISTS auditor_reappointment_verified_at TIMESTAMPTZ NULL,
        ADD COLUMN IF NOT EXISTS auditor_reappointment_verified_by UUID NULL REFERENCES users(id) ON DELETE SET NULL
    """)

    op.execute("""
        ALTER TABLE audits
        ADD COLUMN IF NOT EXISTS audit_completion_verified BOOLEAN NOT NULL DEFAULT FALSE,
        ADD COLUMN IF NOT EXISTS audit_completion_evidence_ref TEXT NULL,
        ADD COLUMN IF NOT EXISTS audit_completion_verified_at TIMESTAMPTZ NULL,
        ADD COLUMN IF NOT EXISTS audit_completion_verified_by UUID NULL REFERENCES users(id) ON DELETE SET NULL
    """)

    op.execute("""
        DO $
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'ck_agms_quorum_required_positive'
            ) THEN
                ALTER TABLE agms
                ADD CONSTRAINT ck_agms_quorum_required_positive
                CHECK (quorum_required IS NULL OR quorum_required > 0);
            END IF;
        END
        $$;
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE agms DROP CONSTRAINT IF EXISTS ck_agms_quorum_required_positive")
    op.execute("""
        ALTER TABLE agms
        DROP COLUMN IF EXISTS auditor_reappointment_verified_by,
        DROP COLUMN IF EXISTS auditor_reappointment_verified_at,
        DROP COLUMN IF EXISTS auditor_reappointment_evidence_ref,
        DROP COLUMN IF EXISTS auditor_reappointment_verified,
        DROP COLUMN IF EXISTS quorum_verified_by,
        DROP COLUMN IF EXISTS quorum_verified_at,
        DROP COLUMN IF EXISTS quorum_evidence_ref,
        DROP COLUMN IF EXISTS quorum_required_verified,
        DROP COLUMN IF EXISTS members_present_verified_by,
        DROP COLUMN IF EXISTS members_present_verified_at,
        DROP COLUMN IF EXISTS members_present_evidence_ref,
        DROP COLUMN IF EXISTS members_present_verified
    """)
    op.execute("""
        ALTER TABLE audits
        DROP COLUMN IF EXISTS audit_completion_verified_by,
        DROP COLUMN IF EXISTS audit_completion_verified_at,
        DROP COLUMN IF EXISTS audit_completion_evidence_ref,
        DROP COLUMN IF EXISTS audit_completion_verified
    """)
    op.execute("""
        ALTER TABLE companies
        DROP COLUMN IF EXISTS first_auditor_appointment_evidence_ref,
        DROP COLUMN IF EXISTS first_auditor_appointment_verified_by,
        DROP COLUMN IF EXISTS first_auditor_appointment_verified_at,
        DROP COLUMN IF EXISTS first_auditor_appointment_verified,
        DROP COLUMN IF EXISTS moa_aoa_evidence_ref,
        DROP COLUMN IF EXISTS moa_aoa_verified_by,
        DROP COLUMN IF EXISTS moa_aoa_verified_at,
        DROP COLUMN IF EXISTS moa_aoa_verified,
        DROP COLUMN IF EXISTS subsidiary_status_evidence_ref,
        DROP COLUMN IF EXISTS subsidiary_status_verified_by,
        DROP COLUMN IF EXISTS subsidiary_status_verified_at,
        DROP COLUMN IF EXISTS subsidiary_status_verified,
        DROP COLUMN IF EXISTS is_private_subsidiary_of_public_company,
        DROP COLUMN IF EXISTS directors_verification_evidence_ref,
        DROP COLUMN IF EXISTS directors_verified_by,
        DROP COLUMN IF EXISTS directors_verified_at,
        DROP COLUMN IF EXISTS directors_verified
    """)
