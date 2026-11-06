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


def downgrade() -> None:
    # SUPPRESSED is a forward-only operational state. Do not requeue old
    # legal alerts on downgrade; that could send unapproved conclusions.
    pass
