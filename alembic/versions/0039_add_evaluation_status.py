"""add evaluation_status to compliance_score_history (OPS-004)

Revision ID: 0039_add_evaluation_status
Revises: 0038_add_rescue_audit_log
"""
from alembic import op
import sqlalchemy as sa

revision = "0039_add_evaluation_status"
down_revision = "0038_add_rescue_audit_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "compliance_score_history",
        sa.Column(
            "evaluation_status",
            sa.String(20),
            nullable=False,
            server_default="COMPLETED",
            comment="PENDING | IN_PROGRESS | COMPLETED | FAILED",
        ),
    )
    op.create_index(
        "ix_compliance_score_history_eval_status",
        "compliance_score_history",
        ["evaluation_status"],
    )


def downgrade() -> None:
    op.drop_index("ix_compliance_score_history_eval_status", table_name="compliance_score_history")
    op.drop_column("compliance_score_history", "evaluation_status")
