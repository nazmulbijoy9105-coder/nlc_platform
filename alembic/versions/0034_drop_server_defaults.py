"""drop server defaults on unknown-able compliance facts

Revision ID: 0034_drop_defaults
Revises: 0033_reconcile_company_orm_columns
Create Date: 2026-10-11

"""
from alembic import op
import sqlalchemy as sa

revision = '0034_drop_defaults'
down_revision = '0033_reconcile_company_orm_columns'
branch_labels = None
depends_on = None

COLUMNS_TO_ALTER = [
    "moa_aoa_filed", "bsec_listed", "bsec_quarterly_report_filed", "cg_certificate_obtained",
    "board_independent_director", "audit_committee_established", "factory_license_obtained",
    "labour_court_order_pending", "winding_up_petition_filed", "liquidator_appointed",
    "court_ordered_winding_up", "voluntary_winding_up", "on_rjsc_strike_off_list",
    "investigation_order", "foreign_exchange_violation", "agm_adjourned_without_notice",
    "name_change_pending", "object_clause_change_pending", "aoa_alteration_pending",
    "special_resolution_filed", "register_of_contracts", "register_of_directors_interests",
    "capital_reduction_pending", "first_agm_held", "first_auditor_appointed",
    "trade_license_obtained", "tax_return_filed_for_current_fy", "vat_annual_return_filed_for_fy"
]

def upgrade() -> None:
    for col in COLUMNS_TO_ALTER:
        op.alter_column('companies', col,
                        existing_type=sa.Boolean(),
                        nullable=True,
                        server_default=None)

def downgrade() -> None:
    for col in COLUMNS_TO_ALTER:
        op.alter_column('companies', col,
                        existing_type=sa.Boolean(),
                        nullable=False,
                        server_default=sa.text('false'))
