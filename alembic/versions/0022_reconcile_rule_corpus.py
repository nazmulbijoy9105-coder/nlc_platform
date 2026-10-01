"""reconcile_rule_corpus — align DB with engine (75 rules)

Removes 5 ghost rules (TAX-005 through TAX-009) not in engine.
Adds 6 missing rules (CHG-001, DEF-002, STR-001-003, TL-002).
"""
from alembic import op

revision = "0022_reconcile_rule_corpus"
down_revision = "0021_risk_band_not_evaluated"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Delete ghost rules
    op.execute("DELETE FROM legal_rules WHERE rule_id IN ('TAX-005', 'TAX-006', 'TAX-007', 'TAX-008', 'TAX-009')")

    # Insert missing rules
    missing = [
        ("CHG-001", "Charge Satisfaction Not Filed", "DEADLINE", "Section 87, Companies Act 1994 (Bangladesh)", "Charge satisfaction not filed via Form XIX. Section 87.", "YELLOW", 3, "COMPLIANCE_PACKAGE", False),
        ("DEF-002", "Unresolved Penalty Notices", "ESCALATION", "Section 447, Companies Act 1994 (Bangladesh)", "Unresolved penalty notices. Section 447: fine up to Tk 10,000 per offence.", "YELLOW", 5, "STRUCTURED_REGULARIZATION", False),
        ("STR-001", "Name Change Not Filed", "DEADLINE", "Section 20, Companies Act 1994 (Bangladesh)", "Name change special resolution not filed with RJSC.", "YELLOW", 3, "COMPLIANCE_PACKAGE", False),
        ("STR-002", "Object Clause Change Not Filed", "DEADLINE", "Section 17, Companies Act 1994 (Bangladesh)", "MoA object clause change not filed with RJSC.", "YELLOW", 3, "COMPLIANCE_PACKAGE", False),
        ("STR-003", "AoA Alteration Not Filed", "DEADLINE", "Section 18, Companies Act 1994 (Bangladesh)", "Articles of Association alteration not filed with RJSC.", "YELLOW", 3, "COMPLIANCE_PACKAGE", False),
        ("TL-002", "Trade License Expired", "DEADLINE", "City Corporation Ordinance 1983 / Pourashava Act 2009", "Trade License expired. Must renew by 31 March annually.", "YELLOW", 5, "COMPLIANCE_PACKAGE", False),
    ]
    for r in missing:
        op.execute(f"""
            INSERT INTO legal_rules (id, rule_id, rule_name, rule_type, statutory_basis,
                description, rule_condition, default_severity, score_impact,
                revenue_tier, is_black_override, rule_version, is_active, created_at, updated_at)
            VALUES (gen_random_uuid(), '{r[0]}', '{r[1]}', '{r[2]}', '{r[3]}', '{r[4]}',
                    NULL, '{r[5]}', {r[6]}, '{r[7]}', {str(r[8]).lower()}, '2.1', true, NOW(), NOW())
            ON CONFLICT (rule_id) DO NOTHING
        """)


def downgrade() -> None:
    pass
