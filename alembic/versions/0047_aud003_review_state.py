"""Normalize legacy AUD-003 active findings after removing automatic BLACK escalation.

Revision ID: 0047_aud003_review_state
Revises: 0046_schema_reconcile_agm

This migration adds the NOT_EVALUATED severity enum value in an autocommit block before persisting lawyer-review findings.
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
    # PostgreSQL requires ALTER TYPE ADD VALUE to commit before the new enum
    # label is used by subsequent UPDATE statements. Use Alembic's explicit
    # autocommit block so this also works when the migration chain is wrapped
    # in a larger transaction by a deployment runner.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE severity_level ADD VALUE IF NOT EXISTS 'NOT_EVALUATED'")

    op.execute("""
        UPDATE legal_rules
        SET statutory_basis = 'Section 183, Companies Act 1994 (Bangladesh)',
            description = 'Audit is not complete as the scheduled AGM approaches. Section 183 requires the relevant audited accounts to be laid before the AGM. The evaluator raises a pre-AGM warning from the statutory notice window; it does not presume that resolutions are automatically invalid.',
            default_severity = 'RED',
            score_impact = 12,
            verification_status = 'PENDING',
            verified_by = NULL,
            verified_at = NULL,
            verification_notes = 'Citation and evaluator aligned; independent counsel verification remains pending.',
            rule_condition = jsonb_set(
                COALESCE(rule_condition, '{}'::jsonb),
                '{trigger}',
                to_jsonb('agm_scheduled_date IS NOT NULL AND audit_complete == False AND today >= agm_scheduled_date - AGM_NOTICE_MINIMUM_DAYS'::text),
                true
            )
        WHERE rule_id = 'AUD-002'
    """)

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
