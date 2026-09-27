"""Add 10 extended legal rules

Revision ID: 0015_add_extended_legal_rules
Revises: 0014_add_performance_indexes
"""
from alembic import op

revision = '0015_add_extended_legal_rules'
down_revision = '0014_add_performance_indexes'
branch_labels = None
depends_on = None

def upgrade():
    rules = [
        ("AGM-007", "AGM Adjourned Without Notice", "THRESHOLD", "Companies Act 1994, Section 84", "AGM adjourned without proper notice.", "YELLOW", 5, "COMPLIANCE_PACKAGE", False),
        ("DIR-005", "Register of Directors Interests Missing", "THRESHOLD", "Companies Act 1994, Section 97", "Register of directors interests not maintained.", "YELLOW", 5, "COMPLIANCE_PACKAGE", False),
        ("DIR-006", "Register of Contracts Missing", "THRESHOLD", "Companies Act 1994, Section 98", "Register of contracts not maintained.", "YELLOW", 5, "COMPLIANCE_PACKAGE", False),
        ("ESC-004", "Voluntary Winding Up", "CONDITIONAL", "Companies Act 1994, Section 196", "Voluntary winding up resolution passed.", "BLACK", 30, "CORPORATE_RESCUE", True),
        ("ESC-005", "Investigation Order Pending", "CONDITIONAL", "Companies Act 1994, Section 199", "Investigation order pending.", "RED", 20, "STRUCTURED_REGULARIZATION", False),
        ("BSEC-001", "Quarterly Report Not Filed", "DEADLINE", "BSEC Corporate Governance Code 2023, Para 8", "BSEC quarterly report not filed.", "RED", 10, "STRUCTURED_REGULARIZATION", False),
        ("BSEC-002", "CG Certificate Not Obtained", "DEADLINE", "BSEC Corporate Governance Code 2023, Para 9", "CG certificate not obtained.", "RED", 10, "STRUCTURED_REGULARIZATION", False),
        ("BSEC-003", "Board Composition Non-Compliant", "THRESHOLD", "BSEC Corporate Governance Code 2023, Para 5", "Board composition non-compliant.", "YELLOW", 8, "COMPLIANCE_PACKAGE", False),
        ("BSEC-004", "Audit Committee Not Established", "THRESHOLD", "BSEC Corporate Governance Code 2023, Para 6", "Audit committee not established.", "YELLOW", 5, "COMPLIANCE_PACKAGE", False),
        ("FX-001", "Foreign Exchange Violation", "CONDITIONAL", "Foreign Exchange Regulation Act 1947 (Bangladesh)", "Foreign exchange violation.", "RED", 15, "STRUCTURED_REGULARIZATION", False),
    ]
    for r in rules:
        op.execute(f"INSERT INTO legal_rules (id, rule_id, rule_name, rule_type, statutory_basis, description, rule_condition, default_severity, score_impact, revenue_tier, is_black_override, rule_version, is_active, created_at, updated_at) VALUES (gen_random_uuid(), '{r[0]}', '{r[1]}', '{r[2]}', '{r[3]}', '{r[4]}', NULL, '{r[5]}', {r[6]}, '{r[7]}', {str(r[8]).lower()}, 1, true, NOW(), NOW()) ON CONFLICT (rule_id) DO NOTHING;")
    for col in ["agm_adjourned_without_notice BOOLEAN NOT NULL DEFAULT false", "register_of_directors_interests BOOLEAN NOT NULL DEFAULT true", "register_of_contracts BOOLEAN NOT NULL DEFAULT true", "voluntary_winding_up BOOLEAN NOT NULL DEFAULT false", "investigation_order BOOLEAN NOT NULL DEFAULT false", "bsec_listed BOOLEAN NOT NULL DEFAULT false", "bsec_quarterly_report_filed BOOLEAN NOT NULL DEFAULT true", "cg_certificate_obtained BOOLEAN NOT NULL DEFAULT true", "board_independent_director BOOLEAN NOT NULL DEFAULT true", "audit_committee_established BOOLEAN NOT NULL DEFAULT true", "foreign_exchange_violation BOOLEAN NOT NULL DEFAULT false"]:
        col_name = col.split()[0]
        op.execute(f"ALTER TABLE companies ADD COLUMN IF NOT EXISTS {col}")

def downgrade():
    op.execute("DELETE FROM legal_rules WHERE rule_id IN ('AGM-007','DIR-005','DIR-006','ESC-004','ESC-005','BSEC-001','BSEC-002','BSEC-003','BSEC-004','FX-001');")
