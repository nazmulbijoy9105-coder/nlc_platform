"""seed_v3_tax_enforcement_structural_rules

Revision ID: 0006_seed_v3_rules
Revises: 0005_add_v3_tax_trade_license_disqualification_fields
"""
from alembic import op

revision = '0006_seed_v3_rules'
down_revision = '0005_add_v3_tax_trade_license_disqualification_fields'


def upgrade():
    rules = [
        ('TAX-003', 'Annual Tax Return Overdue', 'DEADLINE', 'Income Tax Act 2023, Section 75', 
         'Annual tax return not filed by deadline. Penalty: Tk 1,000-5,000 + 2%/month.', 
         'YELLOW', 3, 'COMPLIANCE_PACKAGE', False),
        ('TAX-004', 'Advance Tax Payment Missed', 'THRESHOLD', 'Income Tax Act 2023, Section 74',
         'Quarterly advance tax not paid.',
         'YELLOW', 2, 'COMPLIANCE_PACKAGE', False),
        ('DEF-001', 'Director Disqualification Risk', 'CONDITIONAL', 'Companies Act 1994, Section 297',
         'Director disqualification proceedings active.',
         'BLACK', 15, 'CORPORATE_RESCUE', True),
        ('DEF-002', 'Penalty Prosecution Risk', 'THRESHOLD', 'Companies Act 1994, Section 447',
         'Unresolved penalty notices. Fine up to Tk 10,000.',
         'RED', 8, 'STRUCTURED_REGULARIZATION', False),
        ('CHG-001', 'Charge Satisfaction Not Filed', 'DEADLINE', 'Companies Act 1994, Section 87',
         'Charge satisfaction not filed via Form XIX within 30 days.',
         'YELLOW', 3, 'COMPLIANCE_PACKAGE', False),
        ('STR-001', 'Name Change Not Filed', 'DEADLINE', 'Companies Act 1994, Section 20',
         'Name change not filed with RJSC.',
         'YELLOW', 3, 'COMPLIANCE_PACKAGE', False),
        ('STR-002', 'Object Clause Change Not Filed', 'DEADLINE', 'Companies Act 1994, Section 17',
         'MoA amendment not filed.',
         'YELLOW', 3, 'COMPLIANCE_PACKAGE', False),
        ('STR-003', 'AoA Alteration Not Filed', 'DEADLINE', 'Companies Act 1994, Section 17',
         'AoA alteration not filed with RJSC.',
         'YELLOW', 3, 'COMPLIANCE_PACKAGE', False),
        ('CAP-003', 'Capital Reduction Without Court Order', 'CONDITIONAL', 'Companies Act 1994, Section 100',
         'Capital reduction without court confirmation.',
         'BLACK', 15, 'CORPORATE_RESCUE', True),
        ('INC-007', 'Trade License Not Obtained', 'DEADLINE', 'City Corporation Trade License Act',
         'Trade License not obtained or expired.',
         'RED', 10, 'COMPLIANCE_PACKAGE', False),
    ]
    
    for rule in rules:
        op.execute(f"""
        INSERT INTO ilrmf_rules (rule_id, rule_name, rule_type, statutory_basis, description, 
                                  default_severity, score_impact, revenue_tier, is_black_override, created_at)
        VALUES ('{rule[0]}', '{rule[1]}', '{rule[2]}', '{rule[3]}', '{rule[4]}',
                '{rule[5]}', {rule[6]}, '{rule[7]}', {str(rule[8]).lower()}, NOW())
        ON CONFLICT (rule_id) DO NOTHING;
        """)


def downgrade():
    op.execute("""
    DELETE FROM ilrmf_rules WHERE rule_id IN 
    ('TAX-003', 'TAX-004', 'DEF-001', 'DEF-002', 'CHG-001', 
     'STR-001', 'STR-002', 'STR-003', 'CAP-003', 'INC-007');
    """)
