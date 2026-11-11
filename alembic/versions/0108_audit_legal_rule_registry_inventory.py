"""Expose a safe, read-only legal-rule inventory to the parity audit role.

Revision ID: 0108_audit_legal_rule_registry_inventory
Revises: 0107_merge_legacy_agm_and_domain_event_heads

This view is deliberately separate from audit.active_legal_rule_ids:
the latter represents independently VERIFIED rules, while this view
represents the complete product catalogue for migration/API parity audits.
It omits legacy verification timestamps and statutory_effective_date because
those fields are not trusted proof of legal verification.
"""

from alembic import op

revision = "0108_audit_legal_rule_registry_inventory"
down_revision = "0107_merge_legacy_agm_and_domain_event_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS audit")
    op.execute(
        """
        CREATE OR REPLACE VIEW audit.legal_rule_registry_inventory
        WITH (security_barrier = true)
        AS
        SELECT
            rule_id,
            rule_name,
            rule_type::text AS rule_type,
            statutory_basis,
            description,
            rule_condition,
            default_severity::text AS default_severity,
            score_impact,
            revenue_tier::text AS revenue_tier,
            is_black_override,
            rule_version,
            is_active,
            verification_status
        FROM public.legal_rules
        """
    )
    op.execute(
        """
        COMMENT ON VIEW audit.legal_rule_registry_inventory IS
        'Read-only audit projection of the complete legal-rule catalogue. '
        'This is not a legal-verification or scoring authority. '
        'Legacy verified_at, verified_by, verification_notes, and '
        'statutory_effective_date are intentionally omitted.'
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_roles WHERE rolname = 'nlc_ci_audit_role'
            ) THEN
                EXECUTE 'GRANT USAGE ON SCHEMA audit TO nlc_ci_audit_role';
                EXECUTE
                    'GRANT SELECT ON audit.legal_rule_registry_inventory '
                    'TO nlc_ci_audit_role';
            END IF;
        END
        $$
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS audit.legal_rule_registry_inventory")
