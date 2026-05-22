"""add_v2_compliance_fields

Revision ID: 0004_add_v2_compliance_fields
Revises: 0003_add_reg_004_rule
"""
from alembic import op
import sqlalchemy as sa

revision = '0004_add_v2_compliance_fields'
down_revision = '0003_add_reg_004_rule'


def upgrade():
    # Add conditional rule type values to enum
    op.execute("ALTER TYPE rule_type ADD VALUE 'DEADLINE'")
    op.execute("ALTER TYPE rule_type ADD VALUE 'DEPENDENCY'")
    op.execute("ALTER TYPE rule_type ADD VALUE 'THRESHOLD'")
    op.execute("ALTER TYPE rule_type ADD VALUE 'CONDITIONAL'")

    # Add new columns to companies table
    op.add_column('companies', sa.Column('has_foreign_shareholder', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('companies', sa.Column('foreign_shareholding_pct', sa.Float(), nullable=True))
    op.add_column('companies', sa.Column('bida_registered', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('companies', sa.Column('remittance_amount_usd', sa.Float(), nullable=True))
    op.add_column('companies', sa.Column('encashment_certificate_uploaded', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('companies', sa.Column('tin_obtained', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('companies', sa.Column('vat_registered', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('companies', sa.Column('form_xv_filed', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('companies', sa.Column('form_iv_filed', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('companies', sa.Column('special_resolution_date', sa.Date(), nullable=True))
    op.add_column('companies', sa.Column('maintained_registers', sa.ARRAY(sa.String()), nullable=True))
    op.add_column('companies', sa.Column('register_location', sa.String(), nullable=False, server_default='registered_office'))


def downgrade():
    # Remove columns
    op.drop_column('companies', 'has_foreign_shareholder')
    op.drop_column('companies', 'foreign_shareholding_pct')
    op.drop_column('companies', 'bida_registered')
    op.drop_column('companies', 'remittance_amount_usd')
    op.drop_column('companies', 'encashment_certificate_uploaded')
    op.drop_column('companies', 'tin_obtained')
    op.drop_column('companies', 'vat_registered')
    op.drop_column('companies', 'form_xv_filed')
    op.drop_column('companies', 'form_iv_filed')
    op.drop_column('companies', 'special_resolution_date')
    op.drop_column('companies', 'maintained_registers')
    op.drop_column('companies', 'register_location')
    # Note: Cannot remove enum values in PostgreSQL
