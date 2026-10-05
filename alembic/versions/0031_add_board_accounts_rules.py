"""Add 11 new rules + 11 DB columns for board meetings, accounts, director extended

Revision: 0031_add_board_accounts_rules
Revises: 0030_fix_citation_errors

Adds rules from verified Companies Act 1994 text:
- BOD-001 (Sec 96): Board meeting quarterly
- BOD-002 (Sec 95): Board meeting notice
- BOD-003 (Sec 89): Board minutes
- ACC-001 (Sec 183): Financial statements at AGM
- ACC-002 (Sec 190): Financial statements filed with Registrar
- ACC-003 (Sec 181): Books of account
- DIR-007 (Sec 93): Director consent filing
- DIR-008 (Sec 104): Office of profit
- DIR-010 (Sec 110): Managing director 5-year term
- MEM-001 (Sec 222): Minimum members
- INC-007 (Sec 150): Business commencement declaration

Also fixes:
- CAP-004 citation: Section 87 → 88 (registration of special resolutions)
"""
from alembic import op
import sqlalchemy as sa

revision = '0031_add_board_accounts_rules'
down_revision = '0030_fix_citation_errors'
branch_labels = None
depends_on = None


def upgrade():
    # ── Add 11 columns to companies table ──
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS last_board_meeting_date DATE")
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS board_meeting_notice_given BOOLEAN DEFAULT true")
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS board_minutes_prepared BOOLEAN DEFAULT true")
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS financial_statements_presented BOOLEAN DEFAULT true")
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS financial_statements_filed BOOLEAN DEFAULT true")
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS books_of_account_kept BOOLEAN DEFAULT true")
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS director_consent_filed BOOLEAN DEFAULT true")
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS director_office_of_profit BOOLEAN DEFAULT false")
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS managing_director_appointment_date DATE")
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS member_count INTEGER DEFAULT 0")
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS business_commencement_declaration_filed BOOLEAN DEFAULT true")

    # ── Fix CAP-004 citation ──
    op.execute("UPDATE legal_rules SET statutory_basis = 'Section 88, Companies Act 1994 (Bangladesh)' WHERE rule_id = 'CAP-004';")

    # ── Insert 11 new rules ──
    rules = [
        ("BOD-001", "Board Meeting Not Held Within Quarter", "DEADLINE", "Section 96, Companies Act 1994 (Bangladesh)", "Board meeting not held within 3 months. Section 96: minimum 4 board meetings per year.", "YELLOW", 5, "COMPLIANCE_PACKAGE"),
        ("BOD-002", "Board Meeting Notice Not Given", "CONDITIONAL", "Section 95, Companies Act 1994 (Bangladesh)", "Board meeting notice not given to all directors. Section 95 requires written notice.", "YELLOW", 3, "COMPLIANCE_PACKAGE"),
        ("BOD-003", "Board Meeting Minutes Not Prepared", "CONDITIONAL", "Section 89, Companies Act 1994 (Bangladesh)", "Board meeting minutes not prepared. Section 89: minutes must be entered.", "YELLOW", 5, "COMPLIANCE_PACKAGE"),
        ("ACC-001", "Financial Statements Not Presented at AGM", "DEPENDENCY", "Section 183, Companies Act 1994 (Bangladesh)", "Balance sheet and P&L not presented at AGM. Section 183.", "RED", 15, "STRUCTURED_REGULARIZATION"),
        ("ACC-002", "Financial Statements Not Filed with Registrar", "DEADLINE", "Section 190, Companies Act 1994 (Bangladesh)", "Balance sheet not filed with Registrar within 30 days. Section 190.", "RED", 15, "STRUCTURED_REGULARIZATION"),
        ("ACC-003", "Books of Account Not Kept", "CONDITIONAL", "Section 181, Companies Act 1994 (Bangladesh)", "Proper books of account not maintained. Section 181.", "RED", 15, "STRUCTURED_REGULARIZATION"),
        ("DIR-007", "Director Consent Not Filed Within 30 Days", "DEADLINE", "Section 93, Companies Act 1994 (Bangladesh)", "Director consent not filed within 30 days. Section 93(2).", "YELLOW", 5, "COMPLIANCE_PACKAGE"),
        ("DIR-008", "Director Holding Office of Profit Without Consent", "CONDITIONAL", "Section 104, Companies Act 1994 (Bangladesh)", "Director holding office of profit without consent. Section 104.", "YELLOW", 8, "COMPLIANCE_PACKAGE"),
        ("DIR-010", "Managing Director Appointed for More Than 5 Years", "THRESHOLD", "Section 110, Companies Act 1994 (Bangladesh)", "Managing director term exceeds 5 years. Section 110: max 5 years.", "YELLOW", 5, "COMPLIANCE_PACKAGE"),
        ("MEM-001", "Company Operating with Fewer than Minimum Members", "THRESHOLD", "Section 222, Companies Act 1994 (Bangladesh)", "Company below minimum members. Section 222: private < 2, public < 7.", "RED", 10, "STRUCTURED_REGULARIZATION"),
        ("INC-007", "Business Commenced Without Section 150 Declaration", "CONDITIONAL", "Section 150, Companies Act 1994 (Bangladesh)", "Business commenced without Section 150 declaration.", "RED", 10, "STRUCTURED_REGULARIZATION"),
    ]

    for rule_id, name, rtype, basis, desc, sev, impact, tier in rules:
        op.execute(f"""
            INSERT INTO legal_rules (id, rule_id, rule_name, rule_type, statutory_basis, description, rule_condition, default_severity, score_impact, revenue_tier, is_black_override, rule_version, is_active, created_at, updated_at)
            VALUES (gen_random_uuid(), '{rule_id}', '{name}', '{rtype}', '{basis}', '{desc}', NULL, '{sev}', {impact}, '{tier}', false, 1, true, NOW(), NOW())
            ON CONFLICT (rule_id) DO NOTHING;
        """)


def downgrade():
    cols = ['last_board_meeting_date', 'board_meeting_notice_given', 'board_minutes_prepared',
            'financial_statements_presented', 'financial_statements_filed', 'books_of_account_kept',
            'director_consent_filed', 'director_office_of_profit', 'managing_director_appointment_date',
            'member_count', 'business_commencement_declaration_filed']
    for col in reversed(cols):
        op.execute(f"ALTER TABLE companies DROP COLUMN IF EXISTS {col}")
    for rid in ['BOD-001','BOD-002','BOD-003','ACC-001','ACC-002','ACC-003','DIR-007','DIR-008','DIR-010','MEM-001','INC-007']:
        op.execute(f"DELETE FROM legal_rules WHERE rule_id = '{rid}';")
