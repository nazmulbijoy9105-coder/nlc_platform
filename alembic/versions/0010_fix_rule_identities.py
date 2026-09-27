"""Fix rule identities: align legal_rules with engine

Revision ID: 0010_fix_rule_identities
Revises: 0009_add_template_cols
"""
from alembic import op
import sqlalchemy as sa

revision = '0010_fix_rule_identities'
down_revision = '0009_add_template_cols'
branch_labels = None
depends_on = None


def upgrade():
    # ── 1. If ilrmf_rules table exists (from broken 0006/0007), migrate data ──
    op.execute("""
        DO $$         BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'ilrmf_rules'
            ) THEN
                INSERT INTO legal_rules (
                    id, rule_id, rule_name, rule_type, statutory_basis,
                    description, rule_condition, default_severity, score_impact,
                    revenue_tier, is_black_override, rule_version, is_active,
                    created_at, updated_at
                )
                SELECT
                    gen_random_uuid(), rule_id, rule_name, rule_type,
                    statutory_basis, description, rule_condition,
                    default_severity, score_impact, revenue_tier,
                    is_black_override, rule_version, is_active,
                    created_at, updated_at
                FROM ilrmf_rules
                ON CONFLICT (rule_id) DO UPDATE SET
                    rule_name = EXCLUDED.rule_name,
                    statutory_basis = EXCLUDED.statutory_basis,
                    description = EXCLUDED.description,
                    score_impact = EXCLUDED.score_impact,
                    revenue_tier = EXCLUDED.revenue_tier,
                    is_black_override = EXCLUDED.is_black_override,
                    updated_at = NOW();
                DROP TABLE ilrmf_rules;
            END IF;
        END $$;
    """)

    # ── 2. AGM-006: was "Auditor Not Reappointed", engine = "AGM Minutes Not Prepared" ──
    op.execute("""
        UPDATE legal_rules SET
            rule_name = 'AGM Minutes Not Prepared',
            statutory_basis = 'Companies Act 1994, Section 83',
            description = 'AGM held but minutes not prepared or signed by chairman. Section 83: minutes are prima facie evidence of proceedings.'
        WHERE rule_id = 'AGM-006';
    """)

    # ── 3. AUD-001: swap to match engine ("First Auditor Not Appointed Within 30 Days") ──
    op.execute("""
        UPDATE legal_rules SET
            rule_name = 'First Auditor Not Appointed Within 30 Days',
            statutory_basis = 'Companies Act 1994, Section 210(1)',
            description = 'First auditor not appointed by Board within 30 days of incorporation. Section 210(1): Board must appoint first auditor.'
        WHERE rule_id = 'AUD-001';
    """)

    # ── 4. AUD-002: swap to match engine ("Audit Not Completed Before AGM") ──
    op.execute("""
        UPDATE legal_rules SET
            rule_name = 'Audit Not Completed Before AGM',
            statutory_basis = 'Companies Act 1994, Section 151',
            description = 'Annual audit not completed before AGM. Section 151: directors must lay audited accounts at AGM.'
        WHERE rule_id = 'AUD-002';
    """)

    # ── 5. AUD-004: add if missing ("Auditor Not Reappointed at AGM") ──
    op.execute("""
        INSERT INTO legal_rules (
            id, rule_id, rule_name, rule_type, statutory_basis,
            description, rule_condition, default_severity, score_impact,
            revenue_tier, is_black_override, rule_version, is_active,
            created_at, updated_at
        )
        VALUES (
            gen_random_uuid(), 'AUD-004', 'Auditor Not Reappointed at AGM',
            'DEPENDENCY', 'Companies Act 1994, Section 210(2)',
            'Auditor not reappointed at AGM. Section 210(2): mandatory at every AGM where accounts presented.',
            NULL, 'YELLOW', 5, 'COMPLIANCE_PACKAGE', false, 1, true, NOW(), NOW()
        )
        ON CONFLICT (rule_id) DO UPDATE SET
            rule_name = EXCLUDED.rule_name,
            statutory_basis = EXCLUDED.statutory_basis,
            description = EXCLUDED.description,
            score_impact = EXCLUDED.score_impact;
    """)

    # ── 6. AUD-005: add if missing ("No Auditor Appointed for Current FY") ──
    op.execute("""
        INSERT INTO legal_rules (
            id, rule_id, rule_name, rule_type, statutory_basis,
            description, rule_condition, default_severity, score_impact,
            revenue_tier, is_black_override, rule_version, is_active,
            created_at, updated_at
        )
        VALUES (
            gen_random_uuid(), 'AUD-005', 'No Auditor Appointed for Current FY',
            'DEPENDENCY', 'Companies Act 1994, Section 210(2)',
            'No auditor appointed for current FY. Section 210(2): mandatory at every AGM.',
            NULL, 'YELLOW', 10, 'COMPLIANCE_PACKAGE', false, 1, true, NOW(), NOW()
        )
        ON CONFLICT (rule_id) DO UPDATE SET
            rule_name = EXCLUDED.rule_name,
            statutory_basis = EXCLUDED.statutory_basis,
            description = EXCLUDED.description,
            score_impact = EXCLUDED.score_impact;
    """)

    # ── 7. REG-002: update to match engine ("Core Statutory Registers Missing") ──
    op.execute("""
        UPDATE legal_rules SET
            rule_name = 'Core Statutory Registers Missing',
            statutory_basis = 'Companies Act 1994, Sections 34, 83, 87, 90',
            description = 'Core registers missing: Members (Sec 34), Directors (Sec 90), Charges (Sec 87), or AGM Minutes (Sec 83).'
        WHERE rule_id = 'REG-002';
    """)

    # ── 8. AGM-003/004: Section 86 → 85 ──
    op.execute("""
        UPDATE legal_rules SET
            statutory_basis = 'Companies Act 1994, Section 85'
        WHERE rule_id IN ('AGM-003', 'AGM-004') AND statutory_basis ILIKE '%Section 86%';
    """)

    # ── 9. AR-001 to AR-004: Section 190 → 119 ──
    op.execute("UPDATE legal_rules SET statutory_basis = 'Companies Act 1994, Section 119' WHERE rule_id = 'AR-001';")
    op.execute("UPDATE legal_rules SET statutory_basis = 'Companies Act 1994, Sections 119, 304' WHERE rule_id = 'AR-002';")
    op.execute("UPDATE legal_rules SET statutory_basis = 'Companies Act 1994, Sections 119, 304' WHERE rule_id = 'AR-003';")
    op.execute("UPDATE legal_rules SET statutory_basis = 'Companies Act 1994, Section 119' WHERE rule_id = 'AR-004';")

    # ── 10. DIR-001 to DIR-004: Section 115 → 92 ──
    op.execute("UPDATE legal_rules SET statutory_basis = 'Companies Act 1994, Section 92' WHERE rule_id IN ('DIR-001', 'DIR-002', 'DIR-003', 'DIR-004');")

    # ── 11. ESC-001/002: Section 396 → 304 ──
    op.execute("UPDATE legal_rules SET statutory_basis = 'Companies Act 1994, Section 304' WHERE rule_id IN ('ESC-001', 'ESC-002');")

    # ── 12. OFF-001: Section 77 → 81 ──
    op.execute("UPDATE legal_rules SET statutory_basis = 'Companies Act 1994, Section 81' WHERE rule_id = 'OFF-001';")

    # ── 13. TR-001: Section 82 → 108, TR-004: Section 82 → 34 ──
    op.execute("UPDATE legal_rules SET statutory_basis = 'Companies Act 1994, Section 108' WHERE rule_id = 'TR-001';")
    op.execute("UPDATE legal_rules SET statutory_basis = 'Companies Act 1994, Section 34' WHERE rule_id = 'TR-004';")

    # ── 14. VAT-001: add placeholder (VAT registration covered by TAX-002 in engine) ──
    op.execute("""
        INSERT INTO legal_rules (
            id, rule_id, rule_name, rule_type, statutory_basis,
            description, rule_condition, default_severity, score_impact,
            revenue_tier, is_black_override, rule_version, is_active,
            created_at, updated_at
        )
        VALUES (
            gen_random_uuid(), 'VAT-001', 'VAT Registration Required But Not Obtained',
            'CONDITIONAL', 'Value Added Tax Act 2012 (Bangladesh)',
            'Company exceeds VAT threshold but not registered. NOTE: Engine fires TAX-002 for this condition. VAT-001 is a catalog placeholder for numbering consistency.',
            NULL, 'YELLOW', 5, 'COMPLIANCE_PACKAGE', false, 1, true, NOW(), NOW()
        )
        ON CONFLICT (rule_id) DO NOTHING;
    """)


def downgrade():
    # No downgrade — this is a data correctness fix.
    # The previous state had incorrect rule_ids and statutory_basis strings.
    pass
