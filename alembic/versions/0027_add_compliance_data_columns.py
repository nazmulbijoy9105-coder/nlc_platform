"""Add compliance data columns for DEAD rule inputs

Revision: 0027_add_compliance_data_columns
Revises: 0026_reconcile_rule_law

Adds 29 columns to the companies table for CompanyProfile fields
that had no DB backing. These columns feed the 25 DEAD rules
identified in audit_wiring.txt — rules that could never fire
because the data was never populated from the DB.

Columns default to safe values (True for registers/audits that
should exist, False for violations/defaults that shouldn't).
"""
from alembic import op
import sqlalchemy as sa

revision = '0027_add_compliance_data_columns'
down_revision = '0026_reconcile_rule_law'
branch_labels = None
depends_on = None


def upgrade():
    # ── Incorporation ──
    op.add_column('companies', sa.Column('moa_aoa_filed', sa.Boolean(), server_default='true', nullable=True))

    # ── Capital & Charges ──
    op.add_column('companies', sa.Column('capital_reduction_pending', sa.Boolean(), server_default='false', nullable=True))
    op.add_column('companies', sa.Column('special_resolution_date', sa.Date(), nullable=True))
    op.add_column('companies', sa.Column('special_resolution_filed', sa.Boolean(), server_default='false', nullable=True))

    # ── Registers ──
    op.add_column('companies', sa.Column('register_of_directors_interests', sa.Boolean(), server_default='true', nullable=True))
    op.add_column('companies', sa.Column('register_of_contracts', sa.Boolean(), server_default='true', nullable=True))

    # ── Insolvency ──
    op.add_column('companies', sa.Column('winding_up_petition_filed', sa.Boolean(), server_default='false', nullable=True))
    op.add_column('companies', sa.Column('liquidator_appointed', sa.Boolean(), server_default='false', nullable=True))
    op.add_column('companies', sa.Column('court_ordered_winding_up', sa.Boolean(), server_default='false', nullable=True))
    op.add_column('companies', sa.Column('voluntary_winding_up', sa.Boolean(), server_default='false', nullable=True))
    op.add_column('companies', sa.Column('investigation_order', sa.Boolean(), server_default='false', nullable=True))

    # ── Labour ──
    op.add_column('companies', sa.Column('factory_license_obtained', sa.Boolean(), server_default='false', nullable=True))
    op.add_column('companies', sa.Column('factory_license_expiry', sa.Date(), nullable=True))
    op.add_column('companies', sa.Column('labour_court_order_pending', sa.Boolean(), server_default='false', nullable=True))

    # ── BSEC ──
    op.add_column('companies', sa.Column('bsec_listed', sa.Boolean(), server_default='false', nullable=True))
    op.add_column('companies', sa.Column('bsec_quarterly_report_filed', sa.Boolean(), server_default='true', nullable=True))
    op.add_column('companies', sa.Column('cg_certificate_obtained', sa.Boolean(), server_default='true', nullable=True))
    op.add_column('companies', sa.Column('board_independent_director', sa.Boolean(), server_default='true', nullable=True))
    op.add_column('companies', sa.Column('audit_committee_established', sa.Boolean(), server_default='true', nullable=True))

    # ── AGM Extended ──
    op.add_column('companies', sa.Column('agm_adjourned_without_notice', sa.Boolean(), server_default='false', nullable=True))

    # ── Structural Change ──
    op.add_column('companies', sa.Column('name_change_pending', sa.Boolean(), server_default='false', nullable=True))
    op.add_column('companies', sa.Column('name_change_date', sa.Date(), nullable=True))
    op.add_column('companies', sa.Column('name_change_sr_passed', sa.Boolean(), server_default='false', nullable=True))
    op.add_column('companies', sa.Column('object_clause_change_pending', sa.Boolean(), server_default='false', nullable=True))
    op.add_column('companies', sa.Column('object_clause_change_date', sa.Date(), nullable=True))
    op.add_column('companies', sa.Column('aoa_alteration_pending', sa.Boolean(), server_default='false', nullable=True))
    op.add_column('companies', sa.Column('aoa_alteration_date', sa.Date(), nullable=True))

    # ── Foreign Exchange ──
    op.add_column('companies', sa.Column('foreign_exchange_violation', sa.Boolean(), server_default='false', nullable=True))

    # ── Tax ──
    op.add_column('companies', sa.Column('annual_turnover_bdt', sa.Numeric(20, 2), nullable=True))


def downgrade():
    columns = [
        'moa_aoa_filed', 'capital_reduction_pending', 'special_resolution_date',
        'special_resolution_filed', 'register_of_directors_interests',
        'register_of_contracts', 'winding_up_petition_filed', 'liquidator_appointed',
        'court_ordered_winding_up', 'voluntary_winding_up', 'investigation_order',
        'factory_license_obtained', 'factory_license_expiry', 'labour_court_order_pending',
        'bsec_listed', 'bsec_quarterly_report_filed', 'cg_certificate_obtained',
        'board_independent_director', 'audit_committee_established',
        'agm_adjourned_without_notice', 'name_change_pending', 'name_change_date',
        'name_change_sr_passed', 'object_clause_change_pending',
        'object_clause_change_date', 'aoa_alteration_pending', 'aoa_alteration_date',
        'foreign_exchange_violation', 'annual_turnover_bdt',
    ]
    for col in reversed(columns):
        op.drop_column('companies', col)
