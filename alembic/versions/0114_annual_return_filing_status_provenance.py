"""Require authenticated RJSC evidence before annual-return default findings.

Revision ID: 0114_annual_return_filing_status_provenance
Revises: 0113_score_history_append_only
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0114_annual_return_filing_status_provenance"
down_revision = "0113_score_history_append_only"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "annual_returns",
        sa.Column("filing_status_submitted_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_annual_returns_filing_status_submitted_by_users",
        "annual_returns", "users",
        ["filing_status_submitted_by"], ["id"],
        ondelete="SET NULL",
    )
    op.add_column(
        "annual_returns",
        sa.Column(
            "filing_status_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "annual_returns",
        sa.Column("filing_status_evidence_ref", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "annual_returns",
        sa.Column(
            "filing_status_verified_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "annual_returns",
        sa.Column(
            "filing_status_verified_by",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_annual_returns_filing_status_verified_by_users",
        "annual_returns", "users",
        ["filing_status_verified_by"], ["id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "ck_annual_returns_filing_status_provenance",
        "annual_returns",
        "NOT filing_status_verified OR "
        "(filing_status_evidence_ref IS NOT NULL "
        "AND btrim(filing_status_evidence_ref) <> '' "
        "AND filing_status_verified_at IS NOT NULL "
        "AND filing_status_verified_by IS NOT NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_annual_returns_filing_status_verified_by_users",
        "annual_returns",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_annual_returns_filing_status_submitted_by_users",
        "annual_returns",
        type_="foreignkey",
    )
    op.drop_constraint(
        "ck_annual_returns_filing_status_provenance",
        "annual_returns",
        type_="check",
    )
    op.drop_column("annual_returns", "filing_status_verified_by")
    op.drop_column("annual_returns", "filing_status_verified_at")
    op.drop_column("annual_returns", "filing_status_evidence_ref")
    op.drop_column("annual_returns", "filing_status_verified")
    op.drop_column("annual_returns", "filing_status_submitted_by")
