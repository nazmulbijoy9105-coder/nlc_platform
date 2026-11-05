"""Preserve legacy AGM minutes values but stop treating default False as evidence.

Revision ID: 0053_agm_minutes_unknown_default
Revises: 0052_invalidate_unreleased_legacy_scores
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "0053_agm_minutes_unknown_default"
down_revision: Union[str, Sequence[str], None] = "0052_invalidate_unreleased_legacy_scores"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table("agms"):
        raise RuntimeError("Cannot harden AGM minutes evidence: agms table is missing")

    columns = {column["name"] for column in inspector.get_columns("agms")}
    if "minutes_prepared_legacy" not in columns:
        op.add_column(
            "agms",
            sa.Column("minutes_prepared_legacy", sa.Boolean(), nullable=True),
        )

    # Retain the exact previous value for audit/rollback, then invalidate only
    # the legacy False default where no minutes document was attached.
    op.execute("""
        UPDATE agms
        SET minutes_prepared_legacy = COALESCE(
            minutes_prepared_legacy,
            minutes_prepared
        )
    """)
    op.execute("""
        UPDATE agms
        SET minutes_prepared = NULL
        WHERE minutes_prepared IS FALSE
          AND minutes_document_id IS NULL
    """)
    op.alter_column(
        "agms",
        "minutes_prepared",
        existing_type=sa.Boolean(),
        nullable=True,
        server_default=None,
    )


def downgrade() -> None:
    # Restore the exact pre-migration value where available. Rows created
    # after upgrade with NULL receive FALSE only because the old schema
    # required a non-null boolean.
    op.execute("""
        UPDATE agms
        SET minutes_prepared = COALESCE(
            minutes_prepared_legacy,
            minutes_prepared,
            FALSE
        )
    """)
    op.drop_column("agms", "minutes_prepared_legacy")
    op.alter_column(
        "agms",
        "minutes_prepared",
        existing_type=sa.Boolean(),
        nullable=False,
        server_default=None,
    )
