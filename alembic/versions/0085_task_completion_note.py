"""Persist the completion note on company tasks.

Revision ID: 0085_task_completion_note
Revises: 0084_install_legal_rule_version_guard
"""
from alembic import op
import sqlalchemy as sa

revision = "0085_task_completion_note"
down_revision = "0084_install_legal_rule_version_guard"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column("completion_note", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tasks", "completion_note")
