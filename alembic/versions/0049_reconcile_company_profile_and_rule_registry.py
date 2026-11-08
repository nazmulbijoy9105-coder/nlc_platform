"""Reconcile company profile columns and canonical legal-rule registry.

Production is marked at 0042 but catalog inspection found that several
0031/0035 objects were absent. Add missing columns with UNKNOWN-safe NULL
defaults, restore the 11 canonical rules omitted from production, and retire
the legacy INC-002 registry row from the active set without deleting it.

Revision ID: 0049_reconcile_company_profile_and_rule_registry
Revises: 0048_merge_legal_evidence_and_agm_defaults
"""
import json

import sqlalchemy as sa
from alembic import op

revision = "0049_reconcile_company_profile_and_rule_registry"
down_revision = "0048_merge_legal_evidence_and_agm_defaults"
branch_labels = None
depends_on = None


COMPANY_COLUMNS = (
    ("last_board_meeting_date", sa.Date(), True),
    ("board_meeting_notice_given", sa.Boolean(), True),
    ("board_minutes_prepared", sa.Boolean(), True),
    ("financial_statements_presented", sa.Boolean(), True),
    ("financial_statements_filed", sa.Boolean(), True),
    ("books_of_account_kept", sa.Boolean(), True),
    ("director_consent_filed", sa.Boolean(), True),
    ("director_office_of_profit", sa.Boolean(), True),
    ("managing_director_appointment_date", sa.Date(), True),
    ("business_commencement_declaration_filed", sa.Boolean(), True),
)

RULES = (
    ("BOD-001", "Board Meeting Not Held Within Quarter", "DEADLINE",
     "Section 96, Companies Act 1994 (Bangladesh)",
     "Board meeting not held within 3 months. Section 96: minimum 4 board meetings per year.",
     {"check_fn": "check_bod_001", "trigger": "last_board_meeting_date IS NULL OR days_since_board_meeting > 90", "data_points": ["last_board_meeting_date"]},
     "YELLOW", 5, "COMPLIANCE_PACKAGE"),
    ("BOD-002", "Board Meeting Notice Not Given", "CONDITIONAL",
     "Section 95, Companies Act 1994 (Bangladesh)",
     "Board meeting notice not given to all directors. Section 95 requires written notice.",
     {"check_fn": "check_bod_002", "trigger": "board_meeting_notice_given == False", "data_points": ["board_meeting_notice_given"]},
     "YELLOW", 3, "COMPLIANCE_PACKAGE"),
    ("BOD-003", "Board Meeting Minutes Not Prepared", "CONDITIONAL",
     "Section 89, Companies Act 1994 (Bangladesh)",
     "Board meeting minutes not prepared. Section 89: minutes of all proceedings must be entered.",
     {"check_fn": "check_bod_003", "trigger": "board_minutes_prepared == False", "data_points": ["board_minutes_prepared"]},
     "YELLOW", 5, "COMPLIANCE_PACKAGE"),
    ("ACC-001", "Financial Statements Not Presented at AGM", "DEPENDENCY",
     "Section 183, Companies Act 1994 (Bangladesh)",
     "AGM held but balance sheet and P&L not presented. Section 183.",
     {"check_fn": "check_acc_001", "trigger": "financial_statements_presented == False", "data_points": ["financial_statements_presented"]},
     "RED", 15, "STRUCTURED_REGULARIZATION"),
    ("ACC-002", "Financial Statements Not Filed with Registrar", "DEADLINE",
     "Section 190, Companies Act 1994 (Bangladesh)",
     "Balance sheet not filed within 30 days of AGM. Section 190.",
     {"check_fn": "check_acc_002", "trigger": "financial_statements_filed == False AND days_since_agm > 30", "data_points": ["financial_statements_filed"]},
     "RED", 15, "STRUCTURED_REGULARIZATION"),
    ("ACC-003", "Books of Account Not Kept", "CONDITIONAL",
     "Section 181, Companies Act 1994 (Bangladesh)",
     "Proper books of account not maintained. Section 181.",
     {"check_fn": "check_acc_003", "trigger": "books_of_account_kept == False", "data_points": ["books_of_account_kept"]},
     "RED", 15, "STRUCTURED_REGULARIZATION"),
    ("DIR-007", "Director Consent Not Filed Within 30 Days", "DEADLINE",
     "Section 93, Companies Act 1994 (Bangladesh)",
     "Director consent not filed within 30 days. Section 93(2).",
     {"check_fn": "check_dir_007", "trigger": "director_consent_filed == False", "data_points": ["director_consent_filed"]},
     "YELLOW", 5, "COMPLIANCE_PACKAGE"),
    ("DIR-008", "Director Holding Office of Profit Without Consent", "CONDITIONAL",
     "Section 104, Companies Act 1994 (Bangladesh)",
     "Director holding office of profit without consent. Section 104.",
     {"check_fn": "check_dir_008", "trigger": "director_office_of_profit == True", "data_points": ["director_office_of_profit"]},
     "YELLOW", 8, "COMPLIANCE_PACKAGE"),
    ("DIR-010", "Managing Director Appointed for More Than 5 Years", "THRESHOLD",
     "Section 110, Companies Act 1994 (Bangladesh)",
     "MD term exceeds 5 years. Section 110: max 5 years at a time.",
     {"check_fn": "check_dir_010", "trigger": "years_since_md_appointment > 5", "data_points": ["managing_director_appointment_date"]},
     "YELLOW", 5, "COMPLIANCE_PACKAGE"),
    ("MEM-001", "Company Operating with Fewer than Minimum Members", "THRESHOLD",
     "Section 222, Companies Act 1994 (Bangladesh)",
     "Company below minimum members. Section 222: private < 2, public < 7.",
     {"check_fn": "check_mem_001", "trigger": "member_count < minimum_members", "data_points": ["member_count"]},
     "RED", 10, "STRUCTURED_REGULARIZATION"),
    ("INC-007", "Business Commenced Without Section 150 Declaration", "CONDITIONAL",
     "Section 150, Companies Act 1994 (Bangladesh)",
     "Business commenced without Section 150 declaration.",
     {"check_fn": "check_inc_007", "trigger": "business_commencement_declaration_filed == False", "data_points": ["business_commencement_declaration_filed"]},
     "RED", 10, "STRUCTURED_REGULARIZATION"),
)


def upgrade() -> None:
    bind = op.get_bind()

    # Reconcile missing 0031 company fields. NULL means unknown; never recreate
    # the old server defaults of TRUE that could fabricate compliance evidence.
    for name, column_type, nullable in COMPANY_COLUMNS:
        existing = {c["name"] for c in sa.inspect(bind).get_columns("companies")}
        if name not in existing:
            op.add_column("companies", sa.Column(name, column_type, nullable=nullable))

    # Restore the 0035 legal verification metadata as pending by default.
    existing_rule_columns = {c["name"] for c in sa.inspect(bind).get_columns("legal_rules")}
    if "verification_status" not in existing_rule_columns:
        op.add_column(
            "legal_rules",
            sa.Column("verification_status", sa.String(20), nullable=False, server_default="PENDING"),
        )
    if "verified_by" not in existing_rule_columns:
        op.add_column("legal_rules", sa.Column("verified_by", sa.String(100), nullable=True))
    if "verified_at" not in existing_rule_columns:
        op.add_column("legal_rules", sa.Column("verified_at", sa.Date(), nullable=True))
    if "verification_notes" not in existing_rule_columns:
        op.add_column("legal_rules", sa.Column("verification_notes", sa.Text(), nullable=True))

    insert_rule = sa.text("""
        INSERT INTO legal_rules (
            rule_id, rule_name, rule_type, statutory_basis, description,
            rule_condition, default_severity, score_impact, revenue_tier,
            is_black_override, rule_version, is_active, verification_status,
            verification_notes, created_at, updated_at
        ) VALUES (
            :rule_id, :rule_name, :rule_type, :statutory_basis,
            :description, CAST(:rule_condition AS jsonb),
            :default_severity, :score_impact,
            :revenue_tier, false, '1.0', true, 'PENDING',
            'Restored from canonical seed during schema reconciliation; independent legal approval pending.',
            NOW(), NOW()
        ) ON CONFLICT (rule_id) DO NOTHING
    """)
    for rule in RULES:
        (rule_id, rule_name, rule_type, statutory_basis, description,
         condition, severity, impact, tier) = rule
        bind.execute(insert_rule, {
            "rule_id": rule_id,
            "rule_name": rule_name,
            "rule_type": rule_type,
            "statutory_basis": statutory_basis,
            "description": description,
            "rule_condition": json.dumps(condition),
            "default_severity": severity,
            "score_impact": impact,
            "revenue_tier": tier,
        })

    # INC-002 exists only as a legacy DB row and is absent from both canonical
    # engine and seed registries. Preserve it for audit, but remove it from the
    # active API/parity set pending counsel review.
    bind.execute(sa.text("""
        UPDATE legal_rules
        SET is_active = false,
            verification_status = 'PENDING',
            verification_notes = COALESCE(verification_notes, '') ||
                CASE WHEN COALESCE(verification_notes, '') = '' THEN '' ELSE E'\\n' END ||
                'Legacy rule absent from canonical engine/seed registry; inactive pending independent counsel review.',
            updated_at = NOW()
        WHERE rule_id = 'INC-002'
    """))


def downgrade() -> None:
    # Forward-only: do not delete restored legal rules or compliance evidence.
    pass
