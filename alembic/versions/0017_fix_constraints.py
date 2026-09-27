"""Re-add constraints that 0016 missed (failed on tasks.engagement_id)

Revision ID: 0017_fix_constraints
Revises: 0016_add_constraints_indexes
"""
from alembic import op

revision = '0017_fix_constraints'
down_revision = '0016_add_constraints_indexes'
branch_labels = None
depends_on = None

def upgrade():
    # Re-add all FKs with CASCADE (idempotent — uses DO blocks)
    fk_sqls = [
        ("compliance_flags", "company_id", "companies", "id"),
        ("compliance_score_history", "company_id", "companies", "id"),
        ("compliance_events", "company_id", "companies", "id"),
        ("agms", "company_id", "companies", "id"),
        ("directors", "company_id", "companies", "id"),
        ("shareholders", "company_id", "companies", "id"),
        ("share_transfers", "company_id", "companies", "id"),
        ("annual_returns", "company_id", "companies", "id"),
        ("audits", "company_id", "companies", "id"),
        ("documents", "company_id", "companies", "id"),
        ("statutory_registers", "company_id", "companies", "id"),
        ("registered_office_history", "company_id", "companies", "id"),
        ("company_user_access", "company_id", "companies", "id"),
        ("notifications", "company_id", "companies", "id"),
        ("notifications", "user_id", "users", "id"),
        ("rescue_steps", "rescue_plan_id", "rescue_plans", "id"),
    ]
    
    for table, col, ref_table, ref_col in fk_sqls:
        constraint_name = f"{table}_{col}_fkey"
        op.execute(f"""
            DO $$ 
            BEGIN
                IF EXISTS (SELECT 1 FROM information_schema.columns 
                           WHERE table_name = '{table}' AND column_name = '{col}') THEN
                    EXECUTE 'ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {constraint_name}';
                    EXECUTE 'ALTER TABLE {table} ADD CONSTRAINT {constraint_name} FOREIGN KEY ({col}) REFERENCES {ref_table}({ref_col}) ON DELETE CASCADE';
                END IF;
            END $$;
        """)
    
    # compliance_flags -> legal_rules (RESTRICT)
    op.execute("""
        DO $$         BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.columns 
                       WHERE table_name = 'compliance_flags' AND column_name = 'rule_id') THEN
                ALTER TABLE compliance_flags DROP CONSTRAINT IF EXISTS compliance_flags_rule_id_fkey;
                ALTER TABLE compliance_flags ADD CONSTRAINT compliance_flags_rule_id_fkey 
                    FOREIGN KEY (rule_id) REFERENCES legal_rules(rule_id) ON DELETE RESTRICT;
            END IF;
        END $$;
    """)
    
    # CHECK constraints (idempotent)
    op.execute("ALTER TABLE companies DROP CONSTRAINT IF EXISTS check_compliance_score_range")
    op.execute("ALTER TABLE companies ADD CONSTRAINT check_compliance_score_range CHECK (current_compliance_score >= 0 AND current_compliance_score <= 100)")
    op.execute("ALTER TABLE compliance_score_history DROP CONSTRAINT IF EXISTS check_score_history_range")
    op.execute("ALTER TABLE compliance_score_history ADD CONSTRAINT check_score_history_range CHECK (score >= 0 AND score <= 100)")
    op.execute("ALTER TABLE compliance_flags DROP CONSTRAINT IF EXISTS check_score_impact_nonneg")
    op.execute("ALTER TABLE compliance_flags ADD CONSTRAINT check_score_impact_nonneg CHECK (score_impact >= 0)")
    
    # Indexes (idempotent)
    for idx_sql in [
        "CREATE INDEX IF NOT EXISTS idx_compliance_events_company_type ON compliance_events(company_id, event_type)",
        "CREATE INDEX IF NOT EXISTS idx_documents_company_status ON documents(company_id, status) WHERE is_active = true",
        "CREATE INDEX IF NOT EXISTS idx_directors_company_status ON directors(company_id, director_status)",
        "CREATE INDEX IF NOT EXISTS idx_shareholders_company ON shareholders(company_id) WHERE is_active = true",
        "CREATE INDEX IF NOT EXISTS idx_rescue_plans_company_active ON rescue_plans(company_id) WHERE is_active = true",
        "CREATE INDEX IF NOT EXISTS idx_engagements_company_active ON engagements(company_id) WHERE is_active = true",
        "CREATE INDEX IF NOT EXISTS idx_companies_type_active ON companies(company_type) WHERE is_active = true",
        "CREATE INDEX IF NOT EXISTS idx_compliance_flags_triggered ON compliance_flags(triggered_date) WHERE flag_status = 'ACTIVE'",
        "CREATE INDEX IF NOT EXISTS idx_notifications_user_unread ON notifications(user_id) WHERE read_at IS NULL",
        "CREATE INDEX IF NOT EXISTS idx_legal_rule_versions_rule ON legal_rule_versions(rule_id)",
    ]:
        op.execute(idx_sql)

def downgrade():
    pass
