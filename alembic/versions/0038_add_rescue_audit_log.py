"""add rescue_audit_log table (RES-017)

Revision ID: 0038_add_rescue_audit_log
Revises: 0037_add_webhook_tables
"""
from alembic import op
import sqlalchemy as sa

revision = "0038_add_rescue_audit_log"
down_revision = "0037_add_webhook_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "rescue_audit_log",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("rescue_plan_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("rescue_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("finding_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("compliance_flags.id", ondelete="SET NULL"), nullable=True),
        sa.Column("rule_id", sa.String(50), nullable=False),
        sa.Column("rule_version", sa.String(20), nullable=False),
        sa.Column("action_performed", sa.String(200), nullable=False),
        sa.Column("actor_user_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("evidence_ref", sa.String(500), nullable=True),
        sa.Column("outcome", sa.String(50), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_rescue_audit_log_plan_id", "rescue_audit_log", ["rescue_plan_id"])
    op.create_index("ix_rescue_audit_log_actor_id", "rescue_audit_log", ["actor_user_id"])
    op.create_index("ix_rescue_audit_log_finding_id", "rescue_audit_log", ["finding_id"])
    op.create_index("ix_rescue_audit_log_created_at", "rescue_audit_log", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_rescue_audit_log_created_at", table_name="rescue_audit_log")
    op.drop_index("ix_rescue_audit_log_finding_id", table_name="rescue_audit_log")
    op.drop_index("ix_rescue_audit_log_actor_id", table_name="rescue_audit_log")
    op.drop_index("ix_rescue_audit_log_plan_id", table_name="rescue_audit_log")
    op.drop_table("rescue_audit_log")
