"""Add ON DELETE CASCADE, CHECK constraints, and additional indexes

Revision ID: 0016_add_constraints_indexes
Revises: 0015_add_extended_legal_rules
"""
from alembic import op

revision = '0016_add_constraints_indexes'
down_revision = '0015_add_extended_legal_rules'
branch_labels = None
depends_on = None

def upgrade():
    # ── 1. Add ON DELETE CASCADE to FKs missing it ──
    # compliance_flags → companies
    op.execute("ALTER TABLE compliance_flags DROP CONSTRAINT IF EXISTS compliance_flags_company_id_fkey")
    op.execute("ALTER TABLE compliance_flags ADD CONSTRAINT compliance_flags_company_id_fkey FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE")
    
    # compliance_flags → legal_rules (RESTRICT — don't delete flags when rule deleted)
    op.execute("ALTER TABLE compliance_flags DROP CONSTRAINT IF EXISTS compliance_flags_rule_id_fkey")
    op.execute("ALTER TABLE compliance_flags ADD CONSTRAINT compliance_flags_rule_id_fkey FOREIGN KEY (rule_id) REFERENCES legal_rules(rule_id) ON DELETE RESTRICT")
    
    # compliance_score_history → companies
    op.execute("ALTER TABLE compliance_score_history DROP CONSTRAINT IF EXISTS compliance_score_history_company_id_fkey")
    op.execute("ALTER TABLE compliance_score_history ADD CONSTRAINT compliance_score_history_company_id_fkey FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE")
    
    # compliance_events → companies
    op.execute("ALTER TABLE compliance_events DROP CONSTRAINT IF EXISTS compliance_events_company_id_fkey")
    op.execute("ALTER TABLE compliance_events ADD CONSTRAINT compliance_events_company_id_fkey FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE")
    
    # agms → companies
    op.execute("ALTER TABLE agms DROP CONSTRAINT IF EXISTS agms_company_id_fkey")
    op.execute("ALTER TABLE agms ADD CONSTRAINT agms_company_id_fkey FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE")
    
    # directors → companies
    op.execute("ALTER TABLE directors DROP CONSTRAINT IF EXISTS directors_company_id_fkey")
    op.execute("ALTER TABLE directors ADD CONSTRAINT directors_company_id_fkey FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE")
    
    # shareholders → companies
    op.execute("ALTER TABLE shareholders DROP CONSTRAINT IF EXISTS shareholders_company_id_fkey")
    op.execute("ALTER TABLE shareholders ADD CONSTRAINT shareholders_company_id_fkey FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE")
    
    # share_transfers → companies
    op.execute("ALTER TABLE share_transfers DROP CONSTRAINT IF EXISTS share_transfers_company_id_fkey")
    op.execute("ALTER TABLE share_transfers ADD CONSTRAINT share_transfers_company_id_fkey FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE")
    
    # annual_returns → companies
    op.execute("ALTER TABLE annual_returns DROP CONSTRAINT IF EXISTS annual_returns_company_id_fkey")
    op.execute("ALTER TABLE annual_returns ADD CONSTRAINT annual_returns_company_id_fkey FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE")
    
    # audits → companies
    op.execute("ALTER TABLE audits DROP CONSTRAINT IF EXISTS audits_company_id_fkey")
    op.execute("ALTER TABLE audits ADD CONSTRAINT audits_company_id_fkey FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE")
    
    # documents → companies
    op.execute("ALTER TABLE documents DROP CONSTRAINT IF EXISTS documents_company_id_fkey")
    op.execute("ALTER TABLE documents ADD CONSTRAINT documents_company_id_fkey FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE")
    
    # statutory_registers → companies
    op.execute("ALTER TABLE statutory_registers DROP CONSTRAINT IF EXISTS statutory_registers_company_id_fkey")
    op.execute("ALTER TABLE statutory_registers ADD CONSTRAINT statutory_registers_company_id_fkey FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE")
    
    # registered_office_history → companies
    op.execute("ALTER TABLE registered_office_history DROP CONSTRAINT IF EXISTS registered_office_history_company_id_fkey")
    op.execute("ALTER TABLE registered_office_history ADD CONSTRAINT registered_office_history_company_id_fkey FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE")
    
    # company_user_access → companies + users
    op.execute("ALTER TABLE company_user_access DROP CONSTRAINT IF EXISTS company_user_access_company_id_fkey")
    op.execute("ALTER TABLE company_user_access ADD CONSTRAINT company_user_access_company_id_fkey FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE")
    
    # tasks → engagements
    op.execute("ALTER TABLE tasks DROP CONSTRAINT IF EXISTS tasks_engagement_id_fkey")
    op.execute("ALTER TABLE tasks ADD CONSTRAINT tasks_engagement_id_fkey FOREIGN KEY (engagement_id) REFERENCES engagements(id) ON DELETE CASCADE")
    
    # quotations → engagements
    op.execute("ALTER TABLE quotations DROP CONSTRAINT IF EXISTS quotations_engagement_id_fkey")
    op.execute("ALTER TABLE quotations ADD CONSTRAINT quotations_engagement_id_fkey FOREIGN KEY (engagement_id) REFERENCES engagements(id) ON DELETE CASCADE")
    
    # rescue_steps → rescue_plans
    op.execute("ALTER TABLE rescue_steps DROP CONSTRAINT IF EXISTS rescue_steps_rescue_plan_id_fkey")
    op.execute("ALTER TABLE rescue_steps ADD CONSTRAINT rescue_steps_rescue_plan_id_fkey FOREIGN KEY (rescue_plan_id) REFERENCES rescue_plans(id) ON DELETE CASCADE")
    
    # notifications → companies + users
    op.execute("ALTER TABLE notifications DROP CONSTRAINT IF EXISTS notifications_company_id_fkey")
    op.execute("ALTER TABLE notifications ADD CONSTRAINT notifications_company_id_fkey FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE")
    op.execute("ALTER TABLE notifications DROP CONSTRAINT IF EXISTS notifications_user_id_fkey")
    op.execute("ALTER TABLE notifications ADD CONSTRAINT notifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE")

    # ── 2. CHECK constraints for data integrity ──
    op.execute("ALTER TABLE companies ADD CONSTRAINT IF NOT EXISTS check_compliance_score_range CHECK (current_compliance_score >= 0 AND current_compliance_score <= 100)")
    op.execute("ALTER TABLE compliance_score_history ADD CONSTRAINT IF NOT EXISTS check_score_history_range CHECK (score >= 0 AND score <= 100)")
    op.execute("ALTER TABLE compliance_flags ADD CONSTRAINT IF NOT EXISTS check_score_impact_nonneg CHECK (score_impact >= 0)")
    op.execute("ALTER TABLE legal_rules ADD CONSTRAINT IF NOT EXISTS check_rule_score_impact CHECK (score_impact >= 0 AND score_impact <= 100)")
    op.execute("ALTER TABLE companies ADD CONSTRAINT IF NOT EXISTS check_unfiled_returns CHECK (agm_default_count >= 0)")

    # ── 3. Additional indexes for enterprise query patterns ──
    op.execute("CREATE INDEX IF NOT EXISTS idx_compliance_events_company_type ON compliance_events(company_id, event_type)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_documents_company_status ON documents(company_id, status) WHERE is_active = true")
    op.execute("CREATE INDEX IF NOT EXISTS idx_directors_company_status ON directors(company_id, director_status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_shareholders_company ON shareholders(company_id) WHERE is_active = true")
    op.execute("CREATE INDEX IF NOT EXISTS idx_rescue_plans_company_active ON rescue_plans(company_id) WHERE is_active = true")
    op.execute("CREATE INDEX IF NOT EXISTS idx_engagements_company_active ON engagements(company_id) WHERE is_active = true")
    op.execute("CREATE INDEX IF NOT EXISTS idx_companies_type_active ON companies(company_type) WHERE is_active = true")
    op.execute("CREATE INDEX IF NOT EXISTS idx_compliance_flags_triggered ON compliance_flags(triggered_date) WHERE flag_status = 'ACTIVE'")
    op.execute("CREATE INDEX IF NOT EXISTS idx_notifications_user_unread ON notifications(user_id) WHERE read_at IS NULL")
    op.execute("CREATE INDEX IF NOT EXISTS idx_legal_rule_versions_rule ON legal_rule_versions(rule_id)")

def downgrade():
    # CHECK constraints
    op.execute("ALTER TABLE companies DROP CONSTRAINT IF EXISTS check_compliance_score_range")
    op.execute("ALTER TABLE compliance_score_history DROP CONSTRAINT IF EXISTS check_score_history_range")
    op.execute("ALTER TABLE compliance_flags DROP CONSTRAINT IF EXISTS check_score_impact_nonneg")
    op.execute("ALTER TABLE legal_rules DROP CONSTRAINT IF EXISTS check_rule_score_impact")
    op.execute("ALTER TABLE companies DROP CONSTRAINT IF EXISTS check_unfiled_returns")
    # Indexes
    for idx in ["idx_compliance_events_company_type", "idx_documents_company_status", "idx_directors_company_status",
                "idx_shareholders_company", "idx_rescue_plans_company_active", "idx_engagements_company_active",
                "idx_companies_type_active", "idx_compliance_flags_triggered", "idx_notifications_user_unread",
                "idx_legal_rule_versions_rule"]:
        op.execute(f"DROP INDEX IF EXISTS {idx}")
