"""Quarantine current customer-facing legal scores and active rule signals.

Revision ID: 0061_legal_release_quarantine
Revises: 0060_financial_billing_core

This migration preserves immutable score history. It clears only current
company score state and neutralizes active flags so pre-release calculations
cannot remain presented as current legal findings. It does not approve,
delete, or rewrite legal rule definitions.
"""
from alembic import op

revision = "0061_legal_release_quarantine"
down_revision = "0060_financial_billing_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # risk_band may already contain this value in branches that carried the
    # earlier release gate. Keep this idempotent for the canonical chain.
    with op.get_context().autocommit_block():
        op.execute(
            "ALTER TYPE public.risk_band "
            "ADD VALUE IF NOT EXISTS 'NOT_EVALUATED'"
        )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS audit.legal_release_quarantine_events (
            id BIGSERIAL PRIMARY KEY,
            migration_revision TEXT NOT NULL,
            occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            affected_company_count INTEGER NOT NULL,
            affected_active_flag_count INTEGER NOT NULL,
            suppressed_legal_notification_count INTEGER NOT NULL,
            reason TEXT NOT NULL,
            details JSONB NOT NULL DEFAULT '{}'::jsonb
        )
        """
    )

    op.execute(
        """
        DO $quarantine$
        DECLARE
            company_count INTEGER := 0;
            active_flag_count INTEGER := 0;
            legal_notification_count INTEGER := 0;
        BEGIN
            UPDATE public.companies
               SET current_compliance_score = NULL,
                   current_risk_band = 'NOT_EVALUATED',
                   current_exposure_band = NULL,
                   rescue_required = FALSE,
                   updated_at = NOW();
            GET DIAGNOSTICS company_count = ROW_COUNT;

            UPDATE public.compliance_flags
               SET severity = 'NOT_EVALUATED',
                   score_impact = 0,
                   exposure_band = NULL,
                   statutory_basis = 'NOT VALIDATED — independent counsel review required',
                   description = (
                       'Internal review signal only. This rule is not approved for '
                       'legal determinations. No breach, liability, penalty or '
                       'compliance status is determined.'
                   ),
                   updated_at = NOW()
             WHERE flag_status = 'ACTIVE';
            GET DIAGNOSTICS active_flag_count = ROW_COUNT;

            UPDATE public.notifications
               SET notification_status = 'SUPPRESSED',
                   failure_reason = (
                       'Suppressed: legal rule/deadline alert is not independently '
                       'validated or approved for customer delivery.'
                   ),
                   updated_at = NOW()
             WHERE notification_status = 'PENDING'
               AND (
                   notification_type ~ '^[A-Z]{2,5}-[0-9]{3}            GET DIAGNOSTICS legal_notification_count = ROW_COUNT;

            INSERT INTO audit.legal_release_quarantine_events (
                migration_revision,
                affected_company_count,
                affected_active_flag_count,
                suppressed_legal_notification_count,
                reason,
                details
            )
            VALUES (
                '0061_legal_release_quarantine',
                company_count,
                active_flag_count,
                legal_notification_count,
                'Legal scoring and statutory calendar remain unreleased pending individual independent counsel approval.',
                jsonb_build_object(
                    'current_company_scores', 'cleared_to_null',
                    'current_company_risk_band', 'NOT_EVALUATED',
                    'active_compliance_flags', 'NOT_EVALUATED / score_impact 0 / no exposure band',
                    'immutable_score_history', 'preserved_without_mutation',
                    'legal_rule_definitions', 'preserved; public API release gate remains closed',
                    'pending_rule_and_legal_alert_notifications', 'suppressed; operational billing/payment/security notifications preserved',
                    'rescue_required', FALSE
                )
            );
        END
        $quarantine$;
        """
    )


def downgrade() -> None:
    # Irreversible by design: restoring prior scores, active findings or
    # deadline notifications could re-publish unapproved legal conclusions.
    # Immutable score history remains available for audit.
    pass

                   OR notification_type LIKE '%_DEADLINE_WARNING'
                   OR notification_type LIKE 'DEADLINE_%'
                   OR notification_type IN (
                       'COMPLIANCE_ALERT', 'LEGAL_ALERT', 'RISK_ALERT', 'RULE_ALERT'
                   )
               )
               AND notification_type !~ (
                   '^(BILLING_|PAYMENT_|SUBSCRIPTION_|ACCOUNT_SECURITY_)'
               )
               AND notification_type !~ (
                   '(COMPLIANCE|LEGAL|RISK|RULE_ALERT|TAX_|VAT_|AGM_|BSEC_|LABOUR_|LABOR_|TRADE_LICENCE_|TRADE_LICENSE_|SRO_)'
               );
            GET DIAGNOSTICS legal_notification_count = ROW_COUNT;

            INSERT INTO audit.legal_release_quarantine_events (
                migration_revision,
                affected_company_count,
                affected_active_flag_count,
                suppressed_deadline_notification_count,
                reason,
                details
            )
            VALUES (
                '0061_legal_release_quarantine',
                company_count,
                active_flag_count,
                deadline_notification_count,
                'Legal scoring and statutory calendar remain unreleased pending individual independent counsel approval.',
                jsonb_build_object(
                    'current_company_scores', 'cleared_to_null',
                    'current_company_risk_band', 'NOT_EVALUATED',
                    'active_compliance_flags', 'NOT_EVALUATED / score_impact 0 / no exposure band',
                    'immutable_score_history', 'preserved_without_mutation',
                    'legal_rule_definitions', 'preserved; public API release gate remains closed',
                    'rescue_required', FALSE
                )
            );
        END
        $quarantine$;
        """
    )


def downgrade() -> None:
    # Irreversible by design: restoring prior scores, active findings or
    # deadline notifications could re-publish unapproved legal conclusions.
    # Immutable score history remains available for audit.
    pass

                   OR notification_type LIKE '%_DEADLINE_WARNING'
                   OR notification_type LIKE 'DEADLINE_%'
                   OR notification_type IN (
                       'COMPLIANCE_ALERT', 'LEGAL_ALERT', 'RISK_ALERT', 'RULE_ALERT'
                   )
                   OR notification_type ~ (
                       '(COMPLIANCE|LEGAL|RISK|RULE_ALERT|TAX_|VAT_|AGM_|BSEC_|LABOUR_|LABOR_|TRADE_LICENCE_|TRADE_LICENSE_)'
                   )
               )
               AND (
                   notification_type !~ '^(BILLING_|PAYMENT_|SUBSCRIPTION_|ACCOUNT_SECURITY_)'
                   OR notification_type ~ (
                       '(COMPLIANCE|LEGAL|RISK|RULE_ALERT|TAX_|VAT_|AGM_|BSEC_|LABOUR_|LABOR_|TRADE_LICENCE_|TRADE_LICENSE_)'
                   )
               );
            GET DIAGNOSTICS legal_notification_count = ROW_COUNT;

            INSERT INTO audit.legal_release_quarantine_events (
                migration_revision,
                affected_company_count,
                affected_active_flag_count,
                suppressed_legal_notification_count,
                reason,
                details
            )
            VALUES (
                '0061_legal_release_quarantine',
                company_count,
                active_flag_count,
                legal_notification_count,
                'Legal scoring and statutory calendar remain unreleased pending individual independent counsel approval.',
                jsonb_build_object(
                    'current_company_scores', 'cleared_to_null',
                    'current_company_risk_band', 'NOT_EVALUATED',
                    'active_compliance_flags', 'NOT_EVALUATED / score_impact 0 / no exposure band',
                    'immutable_score_history', 'preserved_without_mutation',
                    'legal_rule_definitions', 'preserved; public API release gate remains closed',
                    'pending_rule_and_legal_alert_notifications', 'suppressed; operational billing/payment/security notifications preserved',
                    'rescue_required', FALSE
                )
            );
        END
        $quarantine$;
        """
    )


def downgrade() -> None:
    # Irreversible by design: restoring prior scores, active findings or
    # deadline notifications could re-publish unapproved legal conclusions.
    # Immutable score history remains available for audit.
    pass

                   OR notification_type LIKE '%_DEADLINE_WARNING'
                   OR notification_type LIKE 'DEADLINE_%'
                   OR notification_type IN (
                       'COMPLIANCE_ALERT', 'LEGAL_ALERT', 'RISK_ALERT', 'RULE_ALERT'
                   )
               )
               AND notification_type !~ (
                   '^(BILLING_|PAYMENT_|SUBSCRIPTION_|ACCOUNT_SECURITY_)'
               )
               AND notification_type !~ (
                   '(COMPLIANCE|LEGAL|RISK|RULE_ALERT|TAX_|VAT_|AGM_|BSEC_|LABOUR_|LABOR_|TRADE_LICENCE_|TRADE_LICENSE_)'
               );
            GET DIAGNOSTICS legal_notification_count = ROW_COUNT;

            INSERT INTO audit.legal_release_quarantine_events (
                migration_revision,
                affected_company_count,
                affected_active_flag_count,
                suppressed_deadline_notification_count,
                reason,
                details
            )
            VALUES (
                '0061_legal_release_quarantine',
                company_count,
                active_flag_count,
                deadline_notification_count,
                'Legal scoring and statutory calendar remain unreleased pending individual independent counsel approval.',
                jsonb_build_object(
                    'current_company_scores', 'cleared_to_null',
                    'current_company_risk_band', 'NOT_EVALUATED',
                    'active_compliance_flags', 'NOT_EVALUATED / score_impact 0 / no exposure band',
                    'immutable_score_history', 'preserved_without_mutation',
                    'legal_rule_definitions', 'preserved; public API release gate remains closed',
                    'rescue_required', FALSE
                )
            );
        END
        $quarantine$;
        """
    )


def downgrade() -> None:
    # Irreversible by design: restoring prior scores, active findings or
    # deadline notifications could re-publish unapproved legal conclusions.
    # Immutable score history remains available for audit.
    pass
