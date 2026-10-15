"""Reconcile companies table with the Company ORM.

Revision ID: 0033_company_orm
Revises: 0032_rjsc_cols

Forward-only schema repair: add only columns that are absent.
"""
from alembic import op
import sqlalchemy as sa

revision = "0033_company_orm"
down_revision = "0032_rjsc_cols"
branch_labels = None
depends_on = None


COLUMNS = [
    ("form_iii_filed_date", sa.Date(), True, None),
    ("form_iv_filed_date", sa.Date(), True, None),
    ("form_vi_filed", sa.Boolean(), False, "false"),
    ("form_vi_filed_date", sa.Date(), True, None),
    ("form_xv_filed_date", sa.Date(), True, None),
    ("special_resolution_filed_date", sa.Date(), True, None),
    ("paid_up_ge_authorized", sa.Boolean(), False, "false"),
    ("register_of_members_maintained", sa.Boolean(), False, "true"),
    ("register_of_directors_maintained", sa.Boolean(), False, "true"),
    ("register_of_charges_maintained", sa.Boolean(), False, "true"),
    ("minutes_book_agm_maintained", sa.Boolean(), False, "true"),
    ("minutes_book_board_maintained", sa.Boolean(), False, "true"),
    ("agm_scheduled_date", sa.Date(), True, None),
    ("notice_sent_date", sa.Date(), True, None),
    ("members_present_at_agm", sa.Integer(), False, "0"),
    ("auditor_reappointed_at_agm", sa.Boolean(), False, "false"),
    ("accounts_adopted_at_agm", sa.Boolean(), False, "false"),
    ("audit_in_progress", sa.Boolean(), False, "false"),
    ("first_auditor_appointment_date", sa.Date(), True, None),
    ("auditor_name", sa.String(length=255), True, None),
    ("auditor_firm_reg_no", sa.String(length=100), True, None),
    ("registered_office_address", sa.Text(), True, None),
    ("registered_office_change_date", sa.Date(), True, None),
    ("last_tax_return_filed_year", sa.Integer(), True, None),
    ("share_certificates_issued", sa.Boolean(), False, "false"),
    ("share_certificates_issued_date", sa.Date(), True, None),
    ("last_allotment_date", sa.Date(), True, None),
    ("shareholder_change_date", sa.Date(), True, None),
    ("is_dormant", sa.Boolean(), False, "false"),
    ("aoa_transfer_restriction", sa.Boolean(), False, "false"),
    ("capital_increase_date", sa.Date(), True, None),
    ("capital_increase_special_resolution", sa.Boolean(), False, "false"),
    ("minimum_directors_met", sa.Boolean(), False, "false"),
]


def upgrade():
    bind = op.get_bind()

    for name, column_type, nullable, default in COLUMNS:
        # Re-inspect after each addition; never rely on a stale inspector.
        existing = {
            column["name"]
            for column in sa.inspect(bind).get_columns("companies")
        }

        if name in existing:
            print(f"0033: skip existing companies.{name}")
            continue

        kwargs = {"nullable": nullable}
        if default is not None:
            kwargs["server_default"] = sa.text(default)

        op.add_column(
            "companies",
            sa.Column(name, column_type, **kwargs),
        )
        print(f"0033: added companies.{name}")


def downgrade():
    # Intentionally forward-only: avoid destructive rollback of compliance data.
    pass
