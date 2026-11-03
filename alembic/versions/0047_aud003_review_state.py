"""Normalize legacy AUD-003 active findings after removing automatic BLACK escalation.

Revision ID: 0047_aud003_review_state
Revises: 0046_schema_reconcile_agm

This runs after 0046 commits the NOT_EVALUATED severity enum value.
Active historical AUD-003 findings are reclassified as lawyer-review-only.
Companies with an affected cached score are marked NOT_EVALUATED so the
next controlled evaluation must recompute the authoritative score.
"""
from alembic import op

revision = "0047_aud003_review_state"
down_revision = "0046_schema_reconcile_agm"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        UPDATE legal_rules
        SET default_severity = 'NOT_EVALUATED',
            score_impact = 0,
            revenue_tier = 'COMPLIANCE_PACKAGE',
            is_black_override = FALSE,
            verification_status = 'PENDING',
            verified_by = NULL,
            verified_at = NULL,
            verification_notes = 'AUD-003 is case-specific lawyer judgment; no automatic invalidity or BLACK escalation.'
        WHERE rule_id = 'AUD-003'
    """)

    op.execute("""
        UPDATE compliance_flags
        SET severity = 'NOT_EVALUATED',
            score_impact = 0,
            revenue_tier = 'COMPLIANCE_PACKAGE',
            flag_code = 'AGM_HELD_WITHOUT_AUDIT_REQUIRES_LEGAL_REVIEW',
            evaluation_state = 'REQUIRES_LAWYER_JUDGMENT',
            description = 'The AGM record states that the meeting was held without a completed audit. A lawyer must review the accounts, auditor appointment, meeting record and applicable statutory provisions before determining legal consequences.'
        WHERE rule_id = 'AUD-003'
          AND flag_status = 'ACTIVE'
    """)

    # Do not leave a cached score/risk band that may have been forced to BLACK
    # solely by the old AUD-003 override. Require a fresh controlled evaluation.
    op.execute("""
        UPDATE companies
        SET current_compliance_score = NULL,
            current_risk_band = 'NOT_EVALUATED',
            last_evaluated_at = NULL
        WHERE id IN (
            SELECT DISTINCT company_id
            FROM compliance_flags
            WHERE rule_id = 'AUD-003'
              AND flag_status = 'ACTIVE'
          )
    """)


def downgrade():
    # Deliberately do not restore the unsupported automatic BLACK override or
    # re-instate historical cached scores. Reversal requires a reviewed release.
    pass
