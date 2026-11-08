"""Suppress queued legal-rule notifications until counsel-approved release.

Revision ID: 0058_suppress_unreleased_rule_notifications
Revises: 0057_merge_final_heads
Create Date: 2026-11-06
"""
from alembic import op

revision = "0058_suppress_unreleased_rule_notifications"
down_revision = "0057_merge_final_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PostgreSQL requires a commit boundary before a newly-added enum value
    # can be used in UPDATE statements.
    with op.get_context().autocommit_block():
        op.execute(
            "ALTER TYPE public.notification_status "
            "ADD VALUE IF NOT EXISTS 'SUPPRESSED'"
        )

    # Rule IDs use the stable PREFIX-000 convention. Also suppress pending
    # generic legal alerts and any notification linked to a compliance flag.
    # Unrelated payment/subscription/operational notices remain untouched.
    op.execute(
        """
        UPDATE public.notifications
           SET notification_status = 'SUPPRESSED',
               failure_reason = (
                   'Suppressed: legal rule alert is not independently approved; '
                   're-evaluation is required after statutory score release.'
               ),
               updated_at = NOW()
         WHERE notification_status = 'PENDING'
           AND (
               notification_type ~ '^[A-Z]{2,5}-[0-9]{3}$'
               OR notification_type IN (
                   'COMPLIANCE_ALERT', 'LEGAL_ALERT', 'RISK_ALERT', 'RULE_ALERT'
               )
               OR related_flag_id IS NOT NULL
           )
        """
    )

    # A rule update must be preceded by a same-transaction, reviewer-bound
    # snapshot of the exact prior definition. The service writes that snapshot
    # before updating the rule; direct SQL cannot bypass version history.
    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_require_legal_rule_version_snapshot()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $function$
        DECLARE
            actor_id uuid;
        BEGIN
            actor_id := public.nlc_current_user_id();
            IF actor_id IS NULL OR NOT public.nlc_current_user_is_super_admin() THEN
                RAISE EXCEPTION 'Only an active SUPER_ADMIN may modify legal rules'
                    USING ERRCODE = '42501';
            END IF;

            IF NEW.rule_id IS DISTINCT FROM OLD.rule_id THEN
                RAISE EXCEPTION 'legal_rules.rule_id is immutable'
                    USING ERRCODE = '55000';
            END IF;

            IF NOT EXISTS (
                SELECT 1
                FROM public.legal_rule_versions v
                WHERE v.rule_id = OLD.rule_id
                  AND v.changed_by = actor_id
                  AND v.changed_at >= transaction_timestamp() - INTERVAL '15 minutes'
                  AND v.previous_definition->>'id' = OLD.id::text
                  AND v.previous_definition->>'rule_version' = COALESCE(OLD.rule_version, '1.0')
                  AND v.previous_definition->>'rule_name' IS NOT DISTINCT FROM OLD.rule_name
                  AND v.previous_definition->>'statutory_basis' IS NOT DISTINCT FROM OLD.statutory_basis
                  AND NULLIF(BTRIM(v.change_reason), '') IS NOT NULL
            ) THEN
                RAISE EXCEPTION 'A matching legal_rule_versions snapshot is required before changing a rule'
                    USING ERRCODE = '55000';
            END IF;

            RETURN NEW;
        END
        $function$
    """)
    op.execute("REVOKE ALL ON FUNCTION public.nlc_require_legal_rule_version_snapshot() FROM PUBLIC")
    # The version-snapshot trigger is installed by the merged-head migration
    # after all historical rule-correction branches have completed.

    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_reject_legal_rule_delete()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $function$
        BEGIN
            RAISE EXCEPTION 'legal rules must be deactivated, not deleted'
                USING ERRCODE = '55000';
        END
        $function$
    """)
    op.execute("REVOKE ALL ON FUNCTION public.nlc_reject_legal_rule_delete() FROM PUBLIC")
    op.execute("DROP TRIGGER IF EXISTS legal_rules_reject_delete ON public.legal_rules")
    op.execute("""
        CREATE TRIGGER legal_rules_reject_delete
        BEFORE DELETE ON public.legal_rules
        FOR EACH ROW EXECUTE FUNCTION public.nlc_reject_legal_rule_delete()
    """)
    op.execute("DROP TRIGGER IF EXISTS legal_rules_reject_truncate ON public.legal_rules")
    op.execute("""
        CREATE TRIGGER legal_rules_reject_truncate
        BEFORE TRUNCATE ON public.legal_rules
        FOR EACH STATEMENT EXECUTE FUNCTION public.nlc_reject_legal_rule_delete()
    """)


def downgrade() -> None:
    # SUPPRESSED is a forward-only operational state. Do not requeue old
    # legal alerts on downgrade; that could send unapproved conclusions.
    pass
