"""Add 6 new rules: BNK-001-003 (Bankruptcy) + LBR-001-003 (Labour)

Revision ID: 0013_add_bankruptcy_labour_rules
Revises: 0012_remove_extra_rules
"""
from alembic import op

revision = '0013_add_bankruptcy_labour_rules'
down_revision = '0012_remove_extra_rules'
branch_labels = None
depends_on = None


def upgrade():
    rules = [
        ("BNK-001", "Winding Up Petition Filed", "CONDITIONAL",
         "Bankruptcy Act 1997 (Bangladesh), Section 12",
         "Winding up petition filed against company. Company under court supervision.",
         "BLACK", 25, "CORPORATE_RESCUE", True),
        ("BNK-002", "Liquidator Appointed", "CONDITIONAL",
         "Bankruptcy Act 1997 (Bangladesh), Section 14",
         "Liquidator appointed. Company under liquidation proceedings.",
         "BLACK", 25, "CORPORATE_RESCUE", True),
        ("BNK-003", "Court-Ordered Winding Up", "CONDITIONAL",
         "Bankruptcy Act 1997 (Bangladesh), Section 18",
         "Court-ordered winding up. Company being wound up by court order.",
         "BLACK", 35, "CORPORATE_RESCUE", True),
        ("LBR-001", "Factory License Missing", "THRESHOLD",
         "Labour Act 2006 (Bangladesh), Section 35",
         "Factory license not obtained. Mandatory for manufacturing entities.",
         "RED", 10, "STRUCTURED_REGULARIZATION", False),
        ("LBR-002", "Factory License Expired", "DEADLINE",
         "Labour Act 2006 (Bangladesh), Section 35",
         "Factory license expired. Renewal required.",
         "YELLOW", 5, "COMPLIANCE_PACKAGE", False),
        ("LBR-003", "Labour Court Order Pending", "CONDITIONAL",
         "Labour Act 2006 (Bangladesh), Section 209",
         "Labour court order pending. Compliance with court orders mandatory.",
         "RED", 15, "STRUCTURED_REGULARIZATION", False),
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

    # Add columns to companies table for insolvency + labour fields
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS winding_up_petition_filed BOOLEAN NOT NULL DEFAULT false")
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS winding_up_petition_date DATE")
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS liquidator_appointed BOOLEAN NOT NULL DEFAULT false")
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS court_ordered_winding_up BOOLEAN NOT NULL DEFAULT false")
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS factory_license_obtained BOOLEAN NOT NULL DEFAULT true")
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS factory_license_expiry DATE")
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS worker_compensation_filed BOOLEAN NOT NULL DEFAULT true")
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS labour_court_order_pending BOOLEAN NOT NULL DEFAULT false")


def downgrade():
    op.execute("DELETE FROM legal_rules WHERE rule_id IN ('BNK-001','BNK-002','BNK-003','LBR-001','LBR-002','LBR-003');")
    op.execute("ALTER TABLE companies DROP COLUMN IF EXISTS winding_up_petition_filed")
    op.execute("ALTER TABLE companies DROP COLUMN IF EXISTS winding_up_petition_date")
    op.execute("ALTER TABLE companies DROP COLUMN IF EXISTS liquidator_appointed")
    op.execute("ALTER TABLE companies DROP COLUMN IF EXISTS court_ordered_winding_up")
    op.execute("ALTER TABLE companies DROP COLUMN IF EXISTS factory_license_obtained")
    op.execute("ALTER TABLE companies DROP COLUMN IF EXISTS factory_license_expiry")
    op.execute("ALTER TABLE companies DROP COLUMN IF EXISTS worker_compensation_filed")
    op.execute("ALTER TABLE companies DROP COLUMN IF EXISTS labour_court_order_pending")
