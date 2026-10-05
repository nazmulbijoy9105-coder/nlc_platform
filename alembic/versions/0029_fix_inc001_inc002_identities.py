"""Fix INC-001 and INC-002 identities to match engine

Revision: 0029_fix_inc001_inc002_identities
Revises: 0028_add_remaining_compliance_fields

0026 wrote the seed's values for INC-001 and INC-002 to the DB,
but the seed disagreed with the engine on these rules:
- INC-001: seed said "Certificate of Incorporation/Section 9" but engine
  fires "MoA/AoA Not Filed/Section 11"
- INC-002: seed said BLACK/25/override=True but engine fires
  YELLOW/5/non-override

This migration corrects the DB to match the engine's runtime behavior.
"""
from alembic import op

revision = '0029_fix_inc001_inc002_identities'
down_revision = '0028_add_remaining_compliance_fields'
branch_labels = None
depends_on = None


def upgrade():
    # INC-001: "Certificate of Incorporation Not Obtained" (Sec 9) → "MoA/AoA Not Filed" (Sec 11)
    op.execute("""
        UPDATE legal_rules SET
            rule_name = 'Memorandum and Articles Not Filed',
            statutory_basis = 'Section 11, Companies Act 1994 (Bangladesh)',
            description = 'Memorandum and Articles of Association not filed with RJSC. Section 11: constitutional documents required.',
            rule_condition = '{"check_fn": "check_inc_001", "trigger": "moa_aoa_filed == False", "data_points": ["moa_aoa_filed"]}'::jsonb
        WHERE rule_id = 'INC-001';
    """)

    # INC-002: BLACK/25/override → YELLOW/5/non-override
    op.execute("""
        UPDATE legal_rules SET
            rule_name = 'Form III Not Filed',
            statutory_basis = 'Section 11, Companies Act 1994 (Bangladesh)',
            description = 'Company has paid-up capital but Form III not filed within 28 days of incorporation.',
            default_severity = 'YELLOW',
            score_impact = 5,
            is_black_override = false,
            rule_condition = '{"check_fn": "check_inc_002", "trigger": "paid_up_capital_bdt > 0 AND form_iii_filed == False AND days_since_incorporation > 28", "data_points": ["paid_up_capital_bdt", "form_iii_filed", "incorporation_date"]}'::jsonb
        WHERE rule_id = 'INC-002';
    """)


def downgrade():
    pass
