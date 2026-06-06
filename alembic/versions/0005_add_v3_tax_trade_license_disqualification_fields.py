"""add_v3_tax_trade_license_disqualification_fields

Revision ID: 0005_add_v3_tax_trade_license_disqualification_fields
Revises: 0004_add_v2_compliance_fields
"""
from alembic import op
import sqlalchemy as sa

revision = '0005_add_v3_tax_trade_license_disqualification_fields'
down_revision = '0004_add_v2_compliance_fields'


def upgrade():
    # Trade License
    op.add_column('companies', sa.Column('trade_license_obtained', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('companies', sa.Column('trade_license_expiry', sa.Date(), nullable=True))
    
    # Tax Return Tracking
    op.add_column('companies', sa.Column('tax_return_filed_for_current_fy', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('companies', sa.Column('last_tax_return_filed', sa.Date(), nullable=True))
    
    # Advance Tax
    op.add_column('companies', sa.Column('advance_tax_q1_paid', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('companies', sa.Column('advance_tax_q2_paid', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('companies', sa.Column('advance_tax_q3_paid', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('companies', sa.Column('advance_tax_q4_paid', sa.Boolean(), nullable=False, server_default='false'))
    
    # TDS
    op.add_column('companies', sa.Column('tds_deposited_up_to_date', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('companies', sa.Column('last_tds_deposit_date', sa.Date(), nullable=True))
    
    # VAT Returns
    op.add_column('companies', sa.Column('last_vat_return_filed', sa.Date(), nullable=True))
    op.add_column('companies', sa.Column('vat_annual_return_filed_for_fy', sa.Boolean(), nullable=False, server_default='false'))
    
    # Minimum Tax & Clearance
    op.add_column('companies', sa.Column('minimum_tax_paid', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('companies', sa.Column('tax_clearance_obtained', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('companies', sa.Column('tax_return_deadline_extended', sa.Boolean(), nullable=False, server_default='false'))
    
    # Director Disqualification
    op.add_column('companies', sa.Column('any_director_disqualified', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('companies', sa.Column('disqualification_details', sa.ARRAY(sa.String()), nullable=True))
    
    # Penalty History
    op.add_column('companies', sa.Column('penalty_notices_received', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('companies', sa.Column('penalty_notices_resolved', sa.Integer(), nullable=False, server_default='0'))


def downgrade():
    cols = [
        'trade_license_obtained', 'trade_license_expiry',
        'tax_return_filed_for_current_fy', 'last_tax_return_filed',
        'advance_tax_q1_paid', 'advance_tax_q2_paid', 'advance_tax_q3_paid', 'advance_tax_q4_paid',
        'tds_deposited_up_to_date', 'last_tds_deposit_date',
        'last_vat_return_filed', 'vat_annual_return_filed_for_fy',
        'minimum_tax_paid', 'tax_clearance_obtained', 'tax_return_deadline_extended',
        'any_director_disqualified', 'disqualification_details',
        'penalty_notices_received', 'penalty_notices_resolved',
    ]
    for col in cols:
        op.drop_column('companies', col)
