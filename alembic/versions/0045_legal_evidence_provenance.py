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
        ADD COLUMN IF NOT EXISTS first_auditor_appointment_evidence_ref TEXT NULL,
        ADD COLUMN IF NOT EXISTS agm_history_verified BOOLEAN NOT NULL DEFAULT FALSE,
        ADD COLUMN IF NOT EXISTS agm_history_evidence_ref TEXT NULL,
        ADD COLUMN IF NOT EXISTS agm_history_verified_at TIMESTAMPTZ NULL,
        ADD COLUMN IF NOT EXISTS agm_history_verified_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
        ADD COLUMN IF NOT EXISTS agm_extension_granted_until DATE NULL,
        ADD COLUMN IF NOT EXISTS agm_extension_application_date DATE NULL,
        ADD COLUMN IF NOT EXISTS agm_extension_verified BOOLEAN NOT NULL DEFAULT FALSE,
        ADD COLUMN IF NOT EXISTS agm_extension_evidence_ref TEXT NULL,
        ADD COLUMN IF NOT EXISTS agm_extension_verified_at TIMESTAMPTZ NULL,
        ADD COLUMN IF NOT EXISTS agm_extension_verified_by UUID NULL REFERENCES users(id) ON DELETE SET NULL
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
        ADD COLUMN IF NOT EXISTS auditor_reappointment_verified_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
        ADD COLUMN IF NOT EXISTS short_notice_consent_obtained BOOLEAN NULL,
        ADD COLUMN IF NOT EXISTS short_notice_consent_verified BOOLEAN NOT NULL DEFAULT FALSE,
        ADD COLUMN IF NOT EXISTS short_notice_consent_evidence_ref TEXT NULL,
        ADD COLUMN IF NOT EXISTS short_notice_consent_verified_at TIMESTAMPTZ NULL,
        ADD COLUMN IF NOT EXISTS short_notice_consent_verified_by UUID NULL REFERENCES users(id) ON DELETE SET NULL
    """)

    op.execute("""
        ALTER TABLE audits
        ADD COLUMN IF NOT EXISTS audit_completion_verified BOOLEAN NOT NULL DEFAULT FALSE,
        ADD COLUMN IF NOT EXISTS audit_completion_evidence_ref TEXT NULL,
        ADD COLUMN IF NOT EXISTS audit_completion_verified_at TIMESTAMPTZ NULL,
        ADD COLUMN IF NOT EXISTS audit_completion_verified_by UUID NULL REFERENCES users(id) ON DELETE SET NULL
    """)

    op.execute("""
        ALTER TABLE agms
        ADD CONSTRAINT ck_agms_quorum_required_positive
        CHECK (quorum_required IS NULL OR quorum_required > 0),
        ADD CONSTRAINT ck_agms_attendance_verification_provenance
        CHECK (NOT members_present_verified OR (
            members_present_evidence_ref IS NOT NULL
            AND members_present_verified_at IS NOT NULL
            AND members_present_verified_by IS NOT NULL
        )),
        ADD CONSTRAINT ck_agms_quorum_verification_provenance
        CHECK (NOT quorum_required_verified OR (
            quorum_evidence_ref IS NOT NULL
            AND quorum_verified_at IS NOT NULL
            AND quorum_verified_by IS NOT NULL
        )),
        ADD CONSTRAINT ck_agms_auditor_reappointment_provenance
        CHECK (NOT auditor_reappointment_verified OR (
            auditor_reappointment_evidence_ref IS NOT NULL
            AND auditor_reappointment_verified_at IS NOT NULL
            AND auditor_reappointment_verified_by IS NOT NULL
        )),
        ADD CONSTRAINT ck_agms_short_notice_consent_provenance
        CHECK (NOT short_notice_consent_verified OR (
            short_notice_consent_obtained IS NOT NULL
            AND short_notice_consent_evidence_ref IS NOT NULL
            AND short_notice_consent_verified_at IS NOT NULL
            AND short_notice_consent_verified_by IS NOT NULL
        ))
    """)
    op.execute("""
        ALTER TABLE audits
        ADD CONSTRAINT ck_audits_completion_verification_provenance
        CHECK (NOT audit_completion_verified OR (
            audit_completion_evidence_ref IS NOT NULL
            AND audit_completion_verified_at IS NOT NULL
            AND audit_completion_verified_by IS NOT NULL
        ))
    """)
    op.execute("""
        ALTER TABLE companies
        ADD CONSTRAINT ck_companies_directors_verification_provenance
        CHECK (NOT directors_verified OR (
            directors_verification_evidence_ref IS NOT NULL
            AND directors_verified_at IS NOT NULL
            AND directors_verified_by IS NOT NULL
        )),
        ADD CONSTRAINT ck_companies_subsidiary_verification_provenance
        CHECK (NOT subsidiary_status_verified OR (
            is_private_subsidiary_of_public_company IS NOT NULL
            AND subsidiary_status_evidence_ref IS NOT NULL
            AND subsidiary_status_verified_at IS NOT NULL
            AND subsidiary_status_verified_by IS NOT NULL
        )),
        ADD CONSTRAINT ck_companies_moa_aoa_verification_provenance
        CHECK (NOT moa_aoa_verified OR (
            moa_aoa_evidence_ref IS NOT NULL
            AND moa_aoa_verified_at IS NOT NULL
            AND moa_aoa_verified_by IS NOT NULL
        )),
        ADD CONSTRAINT ck_companies_first_auditor_verification_provenance
        CHECK (NOT first_auditor_appointment_verified OR (
            first_auditor_appointment_evidence_ref IS NOT NULL
            AND first_auditor_appointment_verified_at IS NOT NULL
            AND first_auditor_appointment_verified_by IS NOT NULL
        )),
        ADD CONSTRAINT ck_companies_agm_history_verification_provenance
        CHECK (NOT agm_history_verified OR (
            agm_history_evidence_ref IS NOT NULL
            AND agm_history_verified_at IS NOT NULL
            AND agm_history_verified_by IS NOT NULL
        )),
        ADD CONSTRAINT ck_companies_agm_extension_verification_provenance
        CHECK (NOT agm_extension_verified OR (
            agm_extension_granted_until IS NOT NULL
            AND agm_extension_application_date IS NOT NULL
            AND agm_extension_evidence_ref IS NOT NULL
            AND agm_extension_verified_at IS NOT NULL
            AND agm_extension_verified_by IS NOT NULL
        ))
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE agms
        DROP CONSTRAINT IF EXISTS ck_agms_short_notice_consent_provenance,
        DROP CONSTRAINT IF EXISTS ck_agms_auditor_reappointment_provenance,
        DROP CONSTRAINT IF EXISTS ck_agms_quorum_verification_provenance,
        DROP CONSTRAINT IF EXISTS ck_agms_attendance_verification_provenance,
        DROP CONSTRAINT IF EXISTS ck_agms_quorum_required_positive
    """)
    op.execute("ALTER TABLE audits DROP CONSTRAINT IF EXISTS ck_audits_completion_verification_provenance")
    op.execute("""
        ALTER TABLE companies
        DROP CONSTRAINT IF EXISTS ck_companies_agm_extension_verification_provenance,
        DROP CONSTRAINT IF EXISTS ck_companies_first_auditor_verification_provenance,
        DROP CONSTRAINT IF EXISTS ck_companies_moa_aoa_verification_provenance,
        DROP CONSTRAINT IF EXISTS ck_companies_subsidiary_verification_provenance,
        DROP CONSTRAINT IF EXISTS ck_companies_directors_verification_provenance
    """)
    op.execute("""
        ALTER TABLE agms
        DROP COLUMN IF EXISTS auditor_reappointment_verified_by,
        DROP COLUMN IF EXISTS auditor_reappointment_verified_at,
        DROP COLUMN IF EXISTS auditor_reappointment_evidence_ref,
        DROP COLUMN IF EXISTS short_notice_consent_verified_by,
        DROP COLUMN IF EXISTS short_notice_consent_verified_at,
        DROP COLUMN IF EXISTS short_notice_consent_evidence_ref,
        DROP COLUMN IF EXISTS short_notice_consent_verified,
        DROP COLUMN IF EXISTS short_notice_consent_obtained,
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
        DROP COLUMN IF EXISTS agm_history_verified_by,
        DROP COLUMN IF EXISTS agm_history_verified_at,
        DROP COLUMN IF EXISTS agm_history_evidence_ref,
        DROP COLUMN IF EXISTS agm_history_verified,
        DROP COLUMN IF EXISTS agm_extension_verified_by,
        DROP COLUMN IF EXISTS agm_extension_verified_at,
        DROP COLUMN IF EXISTS agm_extension_evidence_ref,
        DROP COLUMN IF EXISTS agm_extension_verified,
        DROP COLUMN IF EXISTS agm_extension_application_date,
        DROP COLUMN IF EXISTS agm_extension_granted_until,
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
