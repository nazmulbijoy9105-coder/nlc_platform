"""Add remaining compliance fields for CompanyProfile coverage

Revision: 0028_add_remaining_compliance_fields
Revises: 0027_add_compliance_data_columns

Adds 26 more columns to companies table for CompanyProfile fields
that still had no DB backing after 0027. Uses IF NOT EXISTS to be
idempotent (some columns may already exist from partial runs).

Feeds: AR-004 (annual return attachments), INC-005/006 (FDI),
SH-003 (form IV), DEF-001/002 (disqualification/penalties),
ESC-002 (strike-off), CAP-003 (capital reduction court order),
BNK-001 (winding up date).
"""
from alembic import op

revision = '0028_add_remaining_compliance_fields'
down_revision = '0027_add_compliance_data_columns'
branch_labels = None
depends_on = None


def upgrade():
    # ── AR-004: Annual Return attachments ──
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS balance_sheet_attached BOOLEAN DEFAULT false")
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS directors_list_attached BOOLEAN DEFAULT false")
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS profit_loss_attached BOOLEAN DEFAULT false")
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS schedule_x_attached BOOLEAN DEFAULT false")
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS shareholders_list_attached BOOLEAN DEFAULT false")

    # ── INC-005/006: FDI / Foreign Shareholding ──
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS has_foreign_shareholder BOOLEAN DEFAULT false")
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS foreign_shareholding_pct NUMERIC(5,2) DEFAULT 0")
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS encashment_certificate_uploaded BOOLEAN DEFAULT false")
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS encashment_certificate_date DATE")
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS bida_registered BOOLEAN DEFAULT false")
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS is_fdi_registered BOOLEAN DEFAULT false")
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS fdi_registration_date DATE")
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS remittance_amount_usd NUMERIC(15,2) DEFAULT 0")

    # ── INC-002/SH-003: Form filing status ──
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS form_iii_filed BOOLEAN DEFAULT true")
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS form_iv_filed BOOLEAN DEFAULT true")

    # ── ESC-002: RJSC Strike-off ──
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS rjsc_status VARCHAR(50) DEFAULT 'ACTIVE'")
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS rjsc_strike_off_notice_date DATE")
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS last_rjsc_compliance_date DATE")

    # ── DEF-001/002: Director disqualification + Penalties ──
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS any_director_disqualified BOOLEAN DEFAULT false")
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS disqualification_details JSONB")
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS penalty_notices_received INTEGER DEFAULT 0")
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS penalty_notices_resolved INTEGER DEFAULT 0")

    # ── CAP-003: Capital Reduction ──
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS capital_reduction_date DATE")
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS capital_reduction_court_order_obtained BOOLEAN DEFAULT false")

    # ── BNK-001: Winding Up ──
    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS winding_up_petition_date DATE")


def downgrade():
    columns = [
        'balance_sheet_attached', 'directors_list_attached', 'profit_loss_attached',
        'schedule_x_attached', 'shareholders_list_attached',
        'has_foreign_shareholder', 'foreign_shareholding_pct',
        'encashment_certificate_uploaded', 'encashment_certificate_date',
        'bida_registered', 'is_fdi_registered', 'fdi_registration_date',
        'remittance_amount_usd', 'form_iii_filed', 'form_iv_filed',
        'rjsc_status', 'rjsc_strike_off_notice_date', 'last_rjsc_compliance_date',
        'any_director_disqualified', 'disqualification_details',
        'penalty_notices_received', 'penalty_notices_resolved',
        'capital_reduction_date', 'capital_reduction_court_order_obtained',
        'winding_up_petition_date',
    ]
    for col in reversed(columns):
        op.execute(f"ALTER TABLE companies DROP COLUMN IF EXISTS {col}")
