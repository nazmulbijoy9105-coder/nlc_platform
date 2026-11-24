"""Allow score-independent rescue review plans.

Revision ID: 0126_score_independent_rescue_workflow
Revises: 0125_reconcile_agm001_statutory_basis
"""
from alembic import op
import sqlalchemy as sa

revision = "0126_score_independent_rescue_workflow"
down_revision = "0125_reconcile_agm001_statutory_basis"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("rescue_plans", "initial_score", existing_type=sa.Integer(), nullable=True)
    op.add_column(
        "rescue_plans",
        sa.Column(
            "workflow_mode",
            sa.String(length=32),
            nullable=False,
            server_default="STATUTORY_ACTION_AUTHORIZED",
            comment="REVIEW_ONLY or STATUTORY_ACTION; review work is not a score or legal conclusion",
        ),
    )


def downgrade() -> None:
    bind = op.get_bind()
    scoreless_plans = bind.execute(
        sa.text("SELECT count(*) FROM rescue_plans WHERE initial_score IS NULL")
    ).scalar_one()
    if scoreless_plans:
        raise RuntimeError(
            f"0126 refuses to downgrade: {scoreless_plans} rescue_plans rows have "
            "no initial_score. They are score-independent NOT_EVALUATED plans; "
            "restoring NOT NULL would require fabricating a score (0 denotes BLACK)."
        )
    op.drop_column("rescue_plans", "workflow_mode")
    op.alter_column("rescue_plans", "initial_score", existing_type=sa.Integer(), nullable=False)
