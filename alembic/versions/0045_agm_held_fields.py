"""Reconcile AGM held-record fields and member-count input.

Revision ID: 0045_agm_held_fields
Revises: 0044_webhook_schema_reconcile

This is a forward-only, additive reconciliation. Existing company member counts
are initialized to 0 (unknown sentinel); the application must not treat 0 as
verified membership evidence.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0045_agm_held_fields"
down_revision = "0044_webhook_schema_reconcile"
branch_labels = None
depends_on = None


def _add_if_missing(table_name: str, column: sa.Column) -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table(table_name):
        raise RuntimeError(f"Cannot reconcile AGM fields: missing table {table_name}")
    existing = {item["name"] for item in inspect(bind).get_columns(table_name)}
    if column.name not in existing:
        op.add_column(table_name, column)


def upgrade() -> None:
    # Required for Section 85(2)(b) statutory-default quorum calculation.
    _add_if_missing(
        "companies",
        sa.Column("member_count", sa.Integer(), nullable=True, server_default=sa.text("0")),
    )

    # Fields accepted by the existing PATCH /agm/{id}/held contract but
    # previously not represented on the AGM persistence model.
    _add_if_missing("agms", sa.Column("venue", sa.String(length=255), nullable=True))
    _add_if_missing("agms", sa.Column("accounts_adopted", sa.Boolean(), nullable=True))
    _add_if_missing("agms", sa.Column("agm_held_without_audit", sa.Boolean(), nullable=True))
    _add_if_missing("agms", sa.Column("quorum_basis", sa.String(length=64), nullable=True))


def downgrade() -> None:
    # Forward-only: retain recorded compliance evidence and avoid data loss.
    pass
