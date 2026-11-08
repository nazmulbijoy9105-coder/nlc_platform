"""Require reviewer provenance for AGM held/not-held facts.

Revision ID: 0079_agm_held_evidence
Revises: 0078_share_compliance_events

Legacy agm_held booleans have no meeting-specific evidence metadata. Preserve
the legacy values in audit, then require explicit verification before the
company profile can pass a held/not-held fact to the legal engine.
"""
from alembic import op
import sqlalchemy as sa

revision = "0079_agm_held_evidence"
down_revision = "0078_share_compliance_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS audit")
    op.execute("""
        CREATE TABLE IF NOT EXISTS audit.agm_held_legacy_status_snapshot (
            id BIGSERIAL PRIMARY KEY,
            agm_id UUID NOT NULL,
            company_id UUID NOT NULL,
            agm_held BOOLEAN NOT NULL,
            agm_date DATE,
            captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute("""
        INSERT INTO audit.agm_held_legacy_status_snapshot
            (agm_id, company_id, agm_held, agm_date)
        SELECT id, company_id, agm_held, agm_date FROM public.agms
    """)
    op.add_column(
        "agms",
        sa.Column("agm_held_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        schema="public",
    )
    op.add_column(
        "agms",
        sa.Column("agm_held_evidence_ref", sa.Text(), nullable=True),
        schema="public",
    )
    op.add_column(
        "agms",
        sa.Column("agm_held_verified_at", sa.DateTime(timezone=True), nullable=True),
        schema="public",
    )
    op.add_column(
        "agms",
        sa.Column("agm_held_verified_by", sa.UUID(), nullable=True),
        schema="public",
    )
    op.create_foreign_key(
        "fk_agms_held_verified_by_users",
        "agms", "users", ["agm_held_verified_by"], ["id"],
        source_schema="public", referent_schema="public", ondelete="SET NULL",
    )
    op.create_check_constraint(
        "ck_agms_held_verified_has_provenance",
        "agms",
        "NOT agm_held_verified OR "
        "(agm_held_evidence_ref IS NOT NULL AND agm_held_verified_at IS NOT NULL "
        "AND agm_held_verified_by IS NOT NULL AND agm_date IS NOT NULL)",
        schema="public",
    )
    # Database default is explicitly FALSE: legacy rows remain unverified.


def downgrade() -> None:
    raise RuntimeError(
        "0079 is forward-only: downgrade could re-expose unverified historical AGM facts."
    )
