"""
Fix INC-007 collision, add TL-001/TL-002, upgrade INC-003 to BLACK

Revision ID: 0007_fix_tl_inc003_rules
Revises: 0006_seed_v3_rules
"""
from alembic import op

revision = '0007_fix_tl_inc003_rules'
down_revision = '0006_seed_v3_rules'


def upgrade():
    # 1. Restore INC-007 to its correct identity:
    #    "Commencement of Business Certificate Missing" — Section 10 CA 1994
    #    The engine was writing trade-license content under this ID (bug).
    op.execute("""
        UPDATE ilrmf_rules
        SET
            rule_name        = 'Commencement of Business Certificate Missing',
            rule_type        = 'DEADLINE',
            statutory_basis  = 'Companies Act 1994, Section 10',
            description      = 'Certificate of commencement of business not obtained. Required before company commences any business activity.',
            default_severity = 'RED',
            score_impact     = 12,
            revenue_tier     = 'COMPLIANCE_PACKAGE',
            is_black_override = false
        WHERE rule_id = 'INC-007';
    """)

    # 2. Add TL-001 — Trade License Not Obtained (was wrongly written as INC-007)
    op.execute("""
        INSERT INTO ilrmf_rules
            (rule_id, rule_name, rule_type, statutory_basis, description,
             default_severity, score_impact, revenue_tier, is_black_override, created_at)
        VALUES
            ('TL-001',
             'Trade License Not Obtained',
             'DEADLINE',
             'City Corporation Ordinance 1983 / Pourashava Act 2009',
             'Trade License not obtained from City Corporation/Municipality. Every business operating within a city corporation area must hold a valid trade license.',
             'YELLOW', 5, 'COMPLIANCE_PACKAGE', false, NOW())
        ON CONFLICT (rule_id) DO NOTHING;
    """)

    # 3. Add TL-002 — Trade License Expired (renewal lapse — more common than TL-001)
    op.execute("""
        INSERT INTO ilrmf_rules
            (rule_id, rule_name, rule_type, statutory_basis, description,
             default_severity, score_impact, revenue_tier, is_black_override, created_at)
        VALUES
            ('TL-002',
             'Trade License Expired — Renewal Not Obtained',
             'DEADLINE',
             'City Corporation Ordinance 1983 / Pourashava Act 2009',
             'Trade license must be renewed annually by 31 March. Expiry means business operation is unlicensed from that date. Escalates to RED after 90 days.',
             'YELLOW', 5, 'COMPLIANCE_PACKAGE', false, NOW())
        ON CONFLICT (rule_id) DO NOTHING;
    """)

    # 4. Upgrade INC-003 to BLACK (zero directors = structural incapacity, not filing irregularity)
    op.execute("""
        UPDATE ilrmf_rules
        SET
            default_severity  = 'BLACK',
            score_impact       = 20,
            is_black_override  = true,
            description        = 'Minimum directors not appointed per Section 90(2). Company cannot legally act, pass resolutions, or execute contracts. Structural incapacity.'
        WHERE rule_id = 'INC-003';
    """)

    # 5. Resolve any existing active compliance_flags that stored TL-001/TL-002
    #    content under INC-007 rule_id (wrong ID from the bug).
    #    Re-assign them to TL-001 or TL-002 based on flag_code.
    op.execute("""
        UPDATE compliance_flags
        SET rule_id = 'TL-001'
        WHERE rule_id = 'INC-007'
          AND flag_code = 'TRADE_LICENSE_NOT_OBTAINED'
          AND flag_status = 'ACTIVE';
    """)

    op.execute("""
        UPDATE compliance_flags
        SET rule_id = 'TL-002'
        WHERE rule_id = 'INC-007'
          AND flag_code = 'TRADE_LICENSE_EXPIRED'
          AND flag_status = 'ACTIVE';
    """)


def downgrade():
    # Reverse INC-007 to the (incorrect) trade license description
    # that was there before — only do this if rolling back is intentional.
    op.execute("""
        UPDATE ilrmf_rules
        SET
            rule_name        = 'Trade License Not Obtained',
            rule_type        = 'DEADLINE',
            statutory_basis  = 'City Corporation Trade License Act',
            description      = 'Trade License not obtained or expired.',
            default_severity = 'RED',
            score_impact     = 10,
            revenue_tier     = 'COMPLIANCE_PACKAGE',
            is_black_override = false
        WHERE rule_id = 'INC-007';
    """)

    op.execute("DELETE FROM ilrmf_rules WHERE rule_id IN ('TL-001', 'TL-002');")

    op.execute("""
        UPDATE ilrmf_rules
        SET
            default_severity  = 'RED',
            score_impact       = 15,
            is_black_override  = false,
            description        = 'Minimum directors not appointed per Section 90(2).'
        WHERE rule_id = 'INC-003';
    """)
