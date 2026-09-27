"""Add 14 missing rules to reach 59 total

Revision ID: 0011_add_missing_rules
Revises: 0010_fix_rule_identities
"""
from alembic import op

revision = '0011_add_missing_rules'
down_revision = '0010_fix_rule_identities'
branch_labels = None
depends_on = None


def upgrade():
    rules = [
        ("INC-001", "Memorandum and Articles Not Filed", "DEADLINE",
         "Companies Act 1994, Section 11",
         "MoA and AoA not filed with RJSC. Section 11: constitutional documents required.",
         "RED", 15, "STRUCTURED_REGULARIZATION", False),

        ("INC-002", "Form III Not Filed", "DEADLINE",
         "Companies Act 1994, Section 81",
         "Form III not filed. Section 81: filing required.",
         "BLACK", 5, "CORPORATE_RESCUE", True),

        ("INC-003", "Minimum Directors Not Appointed", "THRESHOLD",
         "Companies Act 1994, Section 90(2)",
         "Private company has fewer than 2 directors. Section 90(2): minimum 2 required.",
         "BLACK", 15, "CORPORATE_RESCUE", True),

        ("INC-004", "Paid-Up Capital Exceeds Authorized", "THRESHOLD",
         "Companies Act 1994, Section 150",
         "Paid-up capital exceeds authorized capital. Section 150: all excess allotments void.",
         "BLACK", 20, "CORPORATE_RESCUE", True),

        ("INC-005", "Encashment Certificate Missing", "CONDITIONAL",
         "BIDA Foreign Investment Act 1980; Bangladesh Bank FDI Circular",
         "Foreign shareholding but Encashment Certificate from AD bank not uploaded.",
         "YELLOW", 8, "COMPLIANCE_PACKAGE", False),

        ("INC-006", "Remittance Below Work Permit Threshold", "CONDITIONAL",
         "BIDA Foreign Investment Act 1980",
         "Foreign remittance below USD 50,000 threshold for work permit sponsorship.",
         "YELLOW", 5, "COMPLIANCE_PACKAGE", False),

        ("SH-002", "Share Certificates Not Issued", "DEADLINE",
         "Companies Act 1994, Section 46",
         "Share certificates not issued within 60 days of allotment.",
         "YELLOW", 5, "COMPLIANCE_PACKAGE", False),

        ("SH-003", "Capital Increase Not Filed", "DEADLINE",
         "Companies Act 1994, Section 52",
         "Capital increase not filed via Form IV within 30 days.",
         "YELLOW", 8, "COMPLIANCE_PACKAGE", False),

        ("TAX-001", "TIN Not Obtained", "THRESHOLD",
         "Income Tax Act 2023 (Bangladesh)",
         "No TIN from NBR. Income Tax Act 2023: TIN mandatory for all companies.",
         "RED", 10, "STRUCTURED_REGULARIZATION", False),

        ("TAX-002", "VAT Registration Required", "CONDITIONAL",
         "Value Added Tax Act 2012 (Bangladesh)",
         "Company exceeds VAT threshold but not registered. VAT Act 2012: registration required.",
         "YELLOW", 5, "COMPLIANCE_PACKAGE", False),

        ("REG-003", "Registers Not at Registered Office", "THRESHOLD",
         "Companies Act 1994, Section 34(2)",
         "Statutory registers not at registered office. Section 34(2): must be at registered office.",
         "YELLOW", 3, "COMPLIANCE_PACKAGE", False),

        ("CAP-004", "Special Resolution Not Filed", "DEADLINE",
         "Companies Act 1994, Section 87",
         "Special resolution passed but not filed within 30 days. Section 87: must be filed.",
         "YELLOW", 8, "COMPLIANCE_PACKAGE", False),

        ("VAT-002", "Monthly VAT Return Overdue", "DEADLINE",
         "Value Added Tax Act 2012 (Bangladesh)",
         "Monthly/Bi-monthly VAT return overdue. VAT Act 2012.",
         "YELLOW", 8, "COMPLIANCE_PACKAGE", False),

        ("VAT-003", "Annual VAT Return Overdue", "DEADLINE",
         "Value Added Tax Act 2012 (Bangladesh)",
         "VAT Annual Return overdue for current FY. VAT Act 2012.",
         "YELLOW", 5, "COMPLIANCE_PACKAGE", False),
    ]

    for rule_id, rule_name, rule_type, statutory_basis, description, severity, score, tier, black_override in rules:
        op.execute(f"""
            INSERT INTO legal_rules (
                id, rule_id, rule_name, rule_type, statutory_basis,
                description, rule_condition, default_severity, score_impact,
                revenue_tier, is_black_override, rule_version, is_active,
                created_at, updated_at
            )
            VALUES (
                gen_random_uuid(), '{rule_id}', '{rule_name}', '{rule_type}',
                '{statutory_basis}', '{description}', NULL, '{severity}', {score},
                '{tier}', {str(black_override).lower()}, 1, true, NOW(), NOW()
            )
            ON CONFLICT (rule_id) DO NOTHING;
        """)


def downgrade():
    rule_ids = [r[0] for r in [
        ("INC-001",), ("INC-002",), ("INC-003",), ("INC-004",),
        ("INC-005",), ("INC-006",), ("SH-002",), ("SH-003",),
        ("TAX-001",), ("TAX-002",), ("REG-003",), ("CAP-004",),
        ("VAT-002",), ("VAT-003",),
    ]]
    for (rule_id,) in rule_ids:
        op.execute(f"DELETE FROM legal_rules WHERE rule_id = '{rule_id}';")
