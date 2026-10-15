"""add missing rjsc columns

Revision ID: 0032_rjsc_cols
Revises: 0031_add_board_accounts_rules
Create Date: 2024-01-01

"""
from alembic import op
import sqlalchemy as sa

revision = '0032_rjsc_cols'
down_revision = '0031_add_board_accounts_rules'
branch_labels = None
depends_on = None

def _add_column_if_not_exists(table_name, column, inspector):
    existing = [col['name'] for col in inspector.get_columns(table_name)]
    if column.name not in existing:
        op.add_column(table_name, column)

def upgrade():
    inspector = sa.inspect(op.get_bind())
    
    _add_column_if_not_exists('companies', sa.Column('on_rjsc_strike_off_list', sa.Boolean(), server_default='false', nullable=True), inspector)
    _add_column_if_not_exists('companies', sa.Column('rjsc_strike_off_notice_date', sa.Date(), nullable=True), inspector)
    _add_column_if_not_exists('companies', sa.Column('rjsc_status', sa.String(50), nullable=True), inspector)
    _add_column_if_not_exists('companies', sa.Column('last_rjsc_compliance_date', sa.Date(), nullable=True), inspector)

def downgrade():
    pass
