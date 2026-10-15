"""compliance_calendar_events and regulatory_rules

Revision ID: 0034_compliance_calendar
Revises: 0033_company_orm
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0034_compliance_calendar"
down_revision = "0033_company_orm"
branch_labels = None
depends_on = None

EVENT_TYPES = (
    "FIRST_AGM", "SUBSEQUENT_AGM", "ANNUAL_RETURN", "AUDITOR_APPOINTMENT",
    "FORM_XII", "BOARD_MEETING", "FINANCIAL_STATEMENTS", "TRADE_LICENSE",
    "TAX_RETURN", "OTHER",
)
EVENT_STATUSES = ("UPCOMING", "DUE_SOON", "OVERDUE", "COMPLETED", "WAIVED")


def upgrade() -> None:
    bind = op.get_bind()
    type_enum = postgresql.ENUM(*EVENT_TYPES, name="calendar_event_type", create_type=False)
    status_enum = postgresql.ENUM(*EVENT_STATUSES, name="calendar_event_status", create_type=False)
    type_enum.create(bind, checkfirst=True)
    status_enum.create(bind, checkfirst=True)

    op.create_table(
        "compliance_calendar_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()"), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", type_enum, nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("reminder_30_days", sa.Date(), nullable=True),
        sa.Column("reminder_14_days", sa.Date(), nullable=True),
        sa.Column("reminder_7_days", sa.Date(), nullable=True),
        sa.Column("period_label", sa.String(100), nullable=False),
        sa.Column("status", status_enum, nullable=False),
        sa.Column("is_statutory", sa.Boolean(), nullable=False),
        sa.Column("statutory_basis", sa.String(200), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("evidence_document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("company_id", "event_type", "period_label", name="uq_company_event_period"),
    )
    op.create_index("ix_compliance_calendar_events_company_id", "compliance_calendar_events", ["company_id"])
    op.create_index("ix_compliance_calendar_events_event_type", "compliance_calendar_events", ["event_type"])
    op.create_index("ix_compliance_calendar_events_due_date", "compliance_calendar_events", ["due_date"])
    op.create_index("ix_compliance_calendar_events_status", "compliance_calendar_events", ["status"])

    op.create_table(
        "regulatory_rules",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("jurisdiction", sa.String(10), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("frequency", sa.String(50), nullable=False),
        sa.Column("governing_body", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_regulatory_rules_jurisdiction", "regulatory_rules", ["jurisdiction"])
    op.create_index("ix_regulatory_rules_id", "regulatory_rules", ["id"])


def downgrade() -> None:
    op.drop_index("ix_regulatory_rules_id", table_name="regulatory_rules")
    op.drop_index("ix_regulatory_rules_jurisdiction", table_name="regulatory_rules")
    op.drop_table("regulatory_rules")
    op.drop_table("compliance_calendar_events")
    bind = op.get_bind()
    postgresql.ENUM(name="calendar_event_status").drop(bind, checkfirst=True)
    postgresql.ENUM(name="calendar_event_type").drop(bind, checkfirst=True)
