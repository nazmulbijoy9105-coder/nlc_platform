"""Make R-008-sensitive boolean columns nullable

Revision ID: 0036_nullable_bools
Revises: 0035_verification_status

These columns currently default to False (NOT NULL), which causes the
rule engine to treat "data not yet assessed" as "confirmed non-compliant".
R-008 requires: missing data → UNKNOWN, never NON_COMPLIANT.

Making these columns nullable allows None = "not assessed" vs False = "confirmed absent".
"""
from alembic import op
import sqlalchemy as sa

revision = "0036_nullable_bools"
down_revision = "0035_verification_status"
branch_labels = None
depends_on = None

# Columns to make nullable (engine CompanyProfile has these as bool | None)
COLUMNS = [
    "first_auditor_appointed",
    "trade_license_obtained",
    "factory_license_obtained",
    "worker_compensation_filed",
    "bsec_quarterly_report_filed",
    "cg_certificate_obtained",
    "board_independent_director",
    "audit_committee_established",
    "moa_aoa_filed",
]


def upgrade():
    for col in COLUMNS:
        op.alter_column(
            "companies",
            col,
            existing_type=sa.Boolean(),
            nullable=True,
            server_default=None,
        )


def downgrade():
    for col in COLUMNS:
        op.alter_column(
            "companies",
            col,
            existing_type=sa.Boolean(),
            nullable=False,
            server_default="false",
        )
