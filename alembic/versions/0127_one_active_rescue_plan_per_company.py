"""Enforce one active rescue plan per company.

Revision ID: 0127_one_active_rescue_plan_per_company
Revises: 0126_score_independent_rescue_workflow
"""
from alembic import op
import sqlalchemy as sa

revision = "0127_one_active_rescue_plan_per_company"
down_revision = "0126_score_independent_rescue_workflow"
branch_labels = None
depends_on = None

_INDEX_NAME = "uq_rescue_plans_one_active_per_company"


def upgrade() -> None:
    bind = op.get_bind()
    # SHARE ROW EXCLUSIVE conflicts with the ROW EXCLUSIVE lock taken by INSERT/UPDATE/DELETE.
    # Acquire it before the duplicate preflight and retain it until the migration transaction
    # commits, so legacy workers cannot insert a duplicate between the check and index build.
    bind.execute(sa.text("LOCK TABLE rescue_plans IN SHARE ROW EXCLUSIVE MODE"))

    duplicates = bind.execute(
        sa.text(
            """
            SELECT company_id, count(*) AS active_count
            FROM rescue_plans
            WHERE is_active IS TRUE
            GROUP BY company_id
            HAVING count(*) > 1
            ORDER BY company_id
            """
        )
    ).all()
    if duplicates:
        summary = ", ".join(
            f"{company_id}:{active_count}"
            for company_id, active_count in duplicates
        )
        raise RuntimeError(
            "Cannot enforce one active rescue plan per company; resolve existing "
            f"duplicate active plans before retrying migration: {summary}"
        )

    op.create_index(
        _INDEX_NAME,
        "rescue_plans",
        ["company_id"],
        unique=True,
        postgresql_where=sa.text("is_active IS TRUE"),
    )


def downgrade() -> None:
    op.drop_index(_INDEX_NAME, table_name="rescue_plans")
