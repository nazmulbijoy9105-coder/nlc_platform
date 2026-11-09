"""Quarantine current customer-facing legal outputs pending independent review.

Revision ID: 0074_legal_release_quarantine
Revises: 0073_payment_allocations_append_only

This migration is forward-only. It preserves historical score records and
records the number of rows quarantined. It does not approve legal rules.
"""
from alembic import op

revision = "0074_legal_release_quarantine"
down_revision = "0073_payment_allocations_append_only"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS audit")

    # Commit the enum addition before using the new enum label in UPDATEs.
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
            suppressed_notification_count INTEGER NOT NULL,
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
            notification_count INTEGER := 0;
            stored_secret TEXT;
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

            -- The notification guard permits administrative changes only
            -- for a cryptographically verified staff principal. Use the
            -- migration's transaction-local ADMIN identity; never disable
            -- the trigger or widen client permissions.
            SELECT secret
              INTO stored_secret
              FROM nlc_private.rls_signing_key
             WHERE singleton IS TRUE;

            IF stored_secret IS NULL OR length(stored_secret) < 32 THEN
                RAISE EXCEPTION
                    '0074 requires the provisioned NLC RLS signing key for notification quarantine';
            END IF;

            PERFORM set_config('app.current_user_id', 'ADMIN', TRUE);
            PERFORM set_config(
                'app.current_user_signature',
                encode(
                    public.hmac(
                        convert_to('ADMIN', 'UTF8'),
                        convert_to(stored_secret, 'UTF8'),
                        'sha256'
                    ),
                    'hex'
                ),
                TRUE
            );

            -- Fail closed: preserve only explicitly operational notification
            -- namespaces. Unknown and legal/deadline notifications are suppressed.
            UPDATE public.notifications
               SET notification_status = 'SUPPRESSED',
                   failure_reason = (
                       'Suppressed pending independent legal validation and release approval.'
                   ),
                   updated_at = NOW()
             WHERE notification_status = 'PENDING'
               AND NOT (
                   notification_type IN ('SYSTEM', 'AI_REVIEW_QUEUE_ALERT')
                   OR (
                       notification_type ~ '^(BILLING_|PAYMENT_|SUBSCRIPTION_|ACCOUNT_SECURITY_)'
                       AND notification_type !~ (
                           '(COMPLIANCE|LEGAL|RISK|RULE_ALERT|TAX_|VAT_|AGM_|BSEC_|LABOUR_|LABOR_|TRADE_LICENCE_|TRADE_LICENSE_)'
                       )
                       AND notification_type NOT LIKE '%_DEADLINE_WARNING'
                       AND notification_type NOT LIKE 'DEADLINE_%'
                   )
               );
            GET DIAGNOSTICS notification_count = ROW_COUNT;

            -- Do not leave migration authority active for subsequent SQL.
            PERFORM set_config('app.current_user_id', '', TRUE);
            PERFORM set_config('app.current_user_signature', '', TRUE);

            INSERT INTO audit.legal_release_quarantine_events (
                migration_revision,
                affected_company_count,
                affected_active_flag_count,
                suppressed_notification_count,
                reason,
                details
            )
            VALUES (
                '0074_legal_release_quarantine',
                company_count,
                active_flag_count,
                notification_count,
                'Legal scoring and statutory alerts remain unreleased pending individual independent counsel approval.',
                jsonb_build_object(
                    'current_company_scores', 'cleared_to_null',
                    'current_company_risk_band', 'NOT_EVALUATED',
                    'active_compliance_flags', 'NOT_EVALUATED / score_impact 0 / no exposure band',
                    'immutable_score_history', 'preserved without mutation',
                    'legal_rule_definitions', 'preserved; release gate remains closed',
                    'notification_policy', 'only explicitly named operational prefixes preserved',
                    'rescue_required', FALSE
                )
            );
        END
        $quarantine$;
        """
    )


def downgrade() -> None:
    # Intentionally irreversible: restoring unverified legal scores, flags or
    # notifications could republish unsupported legal conclusions.
    pass
