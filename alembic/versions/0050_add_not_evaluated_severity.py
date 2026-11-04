"""Allow evidence-only NOT_EVALUATED severity in persisted findings.

Revision ID: 0050_add_not_evaluated_severity
Revises: 0049_reconcile_company_profile_and_rule_registry
"""
from alembic import op

revision = "0050_add_not_evaluated_severity"
down_revision = "0049_reconcile_company_profile_and_rule_registry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rule engine already emits this state for unknown/evidence-only findings.
    # Persist it explicitly rather than coercing it to GREEN or a risk severity.
    op.execute("ALTER TYPE severity_level ADD VALUE IF NOT EXISTS 'NOT_EVALUATED' AFTER 'BLACK'")


def downgrade() -> None:
    # PostgreSQL enum values cannot safely be removed while rows may reference
    # them. Keep this migration forward-only.
    pass
