"""Remove 3 rules not in engine: INC-007, REG-004, VAT-001

INC-007: renamed to TL-001 in engine (migration 0007)
REG-004: engine uses REG-002 for core registers
VAT-001: covered by TAX-002 in engine (VAT registration)

Revision ID: 0012_remove_extra_rules
Revises: 0011_add_missing_rules
"""
from alembic import op

revision = '0012_remove_extra_rules'
down_revision = '0011_add_missing_rules'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("DELETE FROM legal_rules WHERE rule_id IN ('INC-007', 'REG-004', 'VAT-001');")


def downgrade():
    pass
