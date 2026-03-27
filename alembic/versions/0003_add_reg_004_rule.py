"""Add REG-004 statutory register core maintenance rule

NEUM LEX COUNSEL 	6 Database Migration
Revision:  0003
Previous:  0002

Adds REG-004 to the legal_rules seed set.
"""
from datetime import date

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO legal_rules (
            id, created_at, updated_at, rule_id, rule_name, rule_type,
            statutory_basis, description, rule_condition,
            default_severity, score_impact, revenue_tier, is_black_override,
            rule_version, is_active
        )
        VALUES (
            gen_random_uuid(), now(), now(), 'REG-004',
            'Statutory Register Core Maintenance', 'REGISTER',
            'Section 26, Companies Act 1994 (Bangladesh)',
            'Core statutory registers for Members, Directors and Charges must be maintained.',
            NULL, 'RED', 15, 'STRUCTURED_REGULARIZATION', FALSE,
            '1.0', TRUE
        )
        ON CONFLICT (rule_id) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute("DELETE FROM legal_rules WHERE rule_id = 'REG-004';")
