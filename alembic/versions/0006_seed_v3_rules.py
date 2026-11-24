"""Seed v3 tax, structural, and disqualification rules.

Revision ID: 0006_seed_v3_rules
Revises: 0005_v3_tax_fields
"""
import sqlalchemy as sa
from alembic import op

revision = "0006_seed_v3_rules"
down_revision = "0005_v3_tax_fields"


def upgrade():
    # The v3 rule taxonomy extends the original enum, so store it as VARCHAR.
    op.execute(
        "ALTER TABLE legal_rules "
        "ALTER COLUMN rule_type TYPE VARCHAR(50) USING rule_type::text"
    )
    op.execute("DROP TYPE IF EXISTS rule_type")

    rules = [
        (
            "TAX-003",
            "Annual Tax Return Overdue",
            "DEADLINE",
            "Income Tax Act 2023, Section 75",
            "Annual tax return not filed by deadline. Penalty: Tk 1,000-5,000 + 2%/month.",
            "YELLOW",
            3,
            "COMPLIANCE_PACKAGE",
            False,
        ),
        (
            "TAX-004",
            "Advance Tax Payment Missed",
            "THRESHOLD",
            "Income Tax Act 2023, Section 74",
            "Quarterly advance tax not paid.",
            "YELLOW",
            2,
            "COMPLIANCE_PACKAGE",
            False,
        ),
        (
            "DEF-001",
            "Director Disqualification Risk",
            "CONDITIONAL",
            "Companies Act 1994, Section 297",
            "Director disqualification proceedings active.",
            "BLACK",
            15,
            "CORPORATE_RESCUE",
            True,
        ),
        (
            "DEF-002",
            "Penalty Prosecution Risk",
            "THRESHOLD",
            "Companies Act 1994, Section 447",
            "Unresolved penalty notices. Fine up to Tk 10,000.",
            "RED",
            8,
            "STRUCTURED_REGULARIZATION",
            False,
        ),
        (
            "CHG-001",
            "Charge Satisfaction Not Filed",
            "DEADLINE",
            "Companies Act 1994, Section 87",
            "Charge satisfaction not filed via Form XIX within 30 days.",
            "YELLOW",
            3,
            "COMPLIANCE_PACKAGE",
            False,
        ),
        (
            "STR-001",
            "Name Change Not Filed",
            "DEADLINE",
            "Companies Act 1994, Section 20",
            "Name change not filed with RJSC.",
            "YELLOW",
            3,
            "COMPLIANCE_PACKAGE",
            False,
        ),
        (
            "STR-002",
            "Object Clause Change Not Filed",
            "DEADLINE",
            "Companies Act 1994, Section 17",
            "MoA amendment not filed.",
            "YELLOW",
            3,
            "COMPLIANCE_PACKAGE",
            False,
        ),
        (
            "STR-003",
            "AoA Alteration Not Filed",
            "DEADLINE",
            "Companies Act 1994, Section 17",
            "AoA alteration not filed with RJSC.",
            "YELLOW",
            3,
            "COMPLIANCE_PACKAGE",
            False,
        ),
        (
            "CAP-003",
            "Capital Reduction Without Court Order",
            "CONDITIONAL",
            "Companies Act 1994, Section 100",
            "Capital reduction without court confirmation.",
            "BLACK",
            15,
            "CORPORATE_RESCUE",
            True,
        ),
        (
            "INC-007",
            "Trade License Not Obtained",
            "DEADLINE",
            "City Corporation Trade License Act",
            "Trade License not obtained or expired.",
            "RED",
            10,
            "COMPLIANCE_PACKAGE",
            False,
        ),
    ]

    # Track only rows this migration actually inserted. A conflicting row may
    # predate this migration and must never be deleted by its downgrade.
    op.execute(
        """
        CREATE TABLE _nlc_migration_0006_seeded_rule_ids (
            rule_id VARCHAR(50) PRIMARY KEY
        )
        """
    )
    connection = op.get_bind()
    insert_rule = sa.text(
        """
        INSERT INTO legal_rules (
            rule_id, rule_name, rule_type, statutory_basis, description,
            default_severity, score_impact, revenue_tier, is_black_override, created_at
        )
        VALUES (
            :rule_id, :rule_name, :rule_type, :statutory_basis, :description,
            :default_severity, :score_impact, :revenue_tier, :is_black_override, NOW()
        )
        ON CONFLICT (rule_id) DO NOTHING
        RETURNING rule_id
        """
    )
    track_insert = sa.text(
        """
        INSERT INTO _nlc_migration_0006_seeded_rule_ids (rule_id)
        VALUES (:rule_id)
        """
    )

    for rule in rules:
        params = {
            "rule_id": rule[0],
            "rule_name": rule[1],
            "rule_type": rule[2],
            "statutory_basis": rule[3],
            "description": rule[4],
            "default_severity": rule[5],
            "score_impact": rule[6],
            "revenue_tier": rule[7],
            "is_black_override": rule[8],
        }
        inserted_rule_id = connection.execute(insert_rule, params).scalar_one_or_none()
        if inserted_rule_id is not None:
            connection.execute(track_insert, {"rule_id": inserted_rule_id})


def downgrade():
    connection = op.get_bind()

    # Delete only rows inserted by this revision. Rows that existed before the
    # migration and were skipped by ON CONFLICT are preserved.
    connection.execute(
        sa.text(
            """
            DELETE FROM legal_rules
            WHERE rule_id IN (
                SELECT rule_id FROM _nlc_migration_0006_seeded_rule_ids
            )
            """
        )
    )
    op.drop_table("_nlc_migration_0006_seeded_rule_ids")

    # Restore the original enum only when every remaining value is representable.
    connection.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM legal_rules
                    WHERE rule_type NOT IN (
                        'AGM', 'AUDIT', 'RETURN', 'DIRECTOR',
                        'TRANSFER', 'REGISTER', 'ESCALATION', 'CASCADE'
                    )
                ) THEN
                    RAISE EXCEPTION
                        'Cannot downgrade 0006: legal_rules contains rule_type values outside the original enum';
                END IF;
            END;
            $;
            """
        )
    )
    op.execute(
        """
        CREATE TYPE rule_type AS ENUM (
            'AGM', 'AUDIT', 'RETURN', 'DIRECTOR',
            'TRANSFER', 'REGISTER', 'ESCALATION', 'CASCADE'
        )
        """
    )
    op.execute(
        "ALTER TABLE legal_rules "
        "ALTER COLUMN rule_type TYPE rule_type USING rule_type::text::rule_type"
    )
