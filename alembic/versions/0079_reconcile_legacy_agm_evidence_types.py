"""Normalize the AGM evidence reference type across restored migration branches.

Revision ID: 0079_reconcile_legacy_agm_evidence_types
Revises: 0078_articles_evidence_signed_rls

The restored historical 0046_schema_reconcile_agm used VARCHAR(500) for
agms.members_present_evidence_ref, while canonical 0046_legal_evidence_provenance
uses TEXT. Normalize both upgrade paths to the canonical TEXT type.
"""
from alembic import op
import sqlalchemy as sa

revision = "0079_reconcile_legacy_agm_evidence_types"
down_revision = "0078_articles_evidence_signed_rls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    column_type = bind.execute(
        sa.text(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_schema = 'public' "
            "AND table_name = 'agms' "
            "AND column_name = 'members_present_evidence_ref'"
        )
    ).scalar_one_or_none()

    if column_type is None:
        raise RuntimeError(
            "Cannot reconcile AGM evidence reference type: "
            "public.agms.members_present_evidence_ref is missing"
        )

    if column_type != "text":
        # Widening VARCHAR to TEXT preserves every existing value.
        op.execute(
            "ALTER TABLE public.agms "
            "ALTER COLUMN members_present_evidence_ref TYPE TEXT "
            "USING members_present_evidence_ref::text"
        )


def downgrade() -> None:
    # Forward-only: narrowing the column could truncate preserved evidence.
    pass
