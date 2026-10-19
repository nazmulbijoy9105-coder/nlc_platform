"""Add verification_status to legal_rules

Revision ID: 0035_verification_status
Revises: 0034_compliance_calendar

Adds verification_status, verified_by, verified_at, verification_notes
columns to legal_rules table. Existing rules default to 'PENDING'.
"""
from alembic import op
import sqlalchemy as sa

revision = "0035_verification_status"
down_revision = "0034_compliance_calendar"
branch_labels = None
depends_on = None


def upgrade():
    # Add verification_status column with default 'PENDING'
    op.add_column(
        "legal_rules",
        sa.Column(
            "verification_status",
            sa.String(20),
            nullable=False,
            server_default="PENDING",
            comment="VERIFIED | PENDING | DISPUTED",
        ),
    )
    # Add audit fields
    op.add_column(
        "legal_rules",
        sa.Column("verified_by", sa.String(100), nullable=True),
    )
    op.add_column(
        "legal_rules",
        sa.Column("verified_at", sa.Date, nullable=True),
    )
    op.add_column(
        "legal_rules",
        sa.Column("verification_notes", sa.Text, nullable=True),
    )


def downgrade():
    op.drop_column("legal_rules", "verification_notes")
    op.drop_column("legal_rules", "verified_at")
    op.drop_column("legal_rules", "verified_by")
    op.drop_column("legal_rules", "verification_status")
