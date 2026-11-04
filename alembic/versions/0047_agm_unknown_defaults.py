"""Make AGM conclusions explicitly unknown until verified evidence exists.

Revision ID: 0047_agm_unknown_defaults
Revises: 0046_legal_evidence_provenance
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0047_agm_unknown_defaults"
down_revision = "0046_legal_evidence_provenance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if not inspect(bind).has_table("agms"):
        raise RuntimeError("Cannot harden AGM evidence: agms table is missing")

    columns = {item["name"]: item for item in inspect(bind).get_columns("agms")}
    if "quorum_required" in columns:
        op.alter_column(
            "agms", "quorum_required",
            existing_type=sa.Integer(), nullable=True,
            server_default=None,
        )
    if "quorum_met" in columns:
        op.alter_column(
            "agms", "quorum_met",
            existing_type=sa.Boolean(), nullable=True,
            server_default=None,
        )
    if "auditor_reappointed" in columns:
        op.alter_column(
            "agms", "auditor_reappointed",
            existing_type=sa.Boolean(), nullable=True,
            server_default=None,
        )


def downgrade() -> None:
    # Deliberately irreversible: restoring TRUE/2 defaults would fabricate
    # statutory compliance evidence for future records.
    pass
