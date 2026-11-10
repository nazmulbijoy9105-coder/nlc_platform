"""Limit the legal-rule audit view to citation-verified active rules.

Revision ID: 0093_verified_rule_audit_view
Revises: 0092_rescue_source_rule_ids

The audit view is a database candidate inventory, not a legal release switch.
Rows must have an explicit VERIFIED citation status; application release
allowlists and LEGAL_SCORE_RELEASED remain independent fail-closed controls.
"""
from alembic import op

revision = "0093_verified_rule_audit_view"
down_revision = "0092_rescue_source_rule_ids"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE VIEW audit.active_legal_rule_ids
        WITH (security_barrier = true)
        AS
        SELECT rule_id
        FROM public.legal_rules
        WHERE is_active IS TRUE
          AND verification_status = 'VERIFIED'
    """)


def downgrade() -> None:
    # Forward-only: restoring the old is_active-only view would expose
    # unverified rule IDs to the production audit principal.
    pass
