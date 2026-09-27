"""Add performance indexes for enterprise scale

Revision ID: 0014_add_performance_indexes
Revises: 0013_add_bankruptcy_labour_rules
"""
from alembic import op

revision = '0014_add_performance_indexes'
down_revision = '0013_add_bankruptcy_labour_rules'
branch_labels = None
depends_on = None


def upgrade():
    # Compliance flags — most queried table
    op.execute("CREATE INDEX IF NOT EXISTS idx_flags_company_rule_active ON compliance_flags(company_id, rule_id) WHERE flag_status = 'ACTIVE'")
    op.execute("CREATE INDEX IF NOT EXISTS idx_flags_company_severity ON compliance_flags(company_id, severity) WHERE flag_status = 'ACTIVE'")

    # Companies — dashboard queries
    op.execute("CREATE INDEX IF NOT EXISTS idx_companies_risk_score ON companies(current_risk_band, current_compliance_score) WHERE is_active = true")
    op.execute("CREATE INDEX IF NOT EXISTS idx_companies_last_eval ON companies(last_evaluated_at) WHERE is_active = true")

    # AGMs — deadline queries
    op.execute("CREATE INDEX IF NOT EXISTS idx_agms_deadline_active ON agms(company_id, agm_deadline) WHERE agm_held = false AND agm_deadline IS NOT NULL")

    # Activity logs — audit queries
    op.execute("CREATE INDEX IF NOT EXISTS idx_activity_user_date ON user_activity_logs(user_id, logged_at)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_activity_company_date ON user_activity_logs(company_id, logged_at)")

    # Score history — trend queries
    op.execute("CREATE INDEX IF NOT EXISTS idx_score_history_company_month ON compliance_score_history(company_id, snapshot_month)")

    # Legal rules — API queries
    op.execute("CREATE INDEX IF NOT EXISTS idx_legal_rules_type_active ON legal_rules(rule_type) WHERE is_active = true")


def downgrade():
    op.execute("DROP INDEX IF EXISTS idx_flags_company_rule_active")
    op.execute("DROP INDEX IF EXISTS idx_flags_company_severity")
    op.execute("DROP INDEX IF EXISTS idx_companies_risk_score")
    op.execute("DROP INDEX IF EXISTS idx_companies_last_eval")
    op.execute("DROP INDEX IF EXISTS idx_agms_deadline_active")
    op.execute("DROP INDEX IF EXISTS idx_activity_user_date")
    op.execute("DROP INDEX IF EXISTS idx_activity_company_date")
    op.execute("DROP INDEX IF EXISTS idx_score_history_company_month")
    op.execute("DROP INDEX IF EXISTS idx_legal_rules_type_active")
