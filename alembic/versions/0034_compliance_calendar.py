"""compliance_calendar_events and regulatory_rules

Revision ID: 0034_compliance_calendar
Revises: 0033_company_orm

Idempotent: Neon already holds these tables (created by hand before this
migration existed), so existing tables/indexes/enums are left untouched.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
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


def _tables() -> set:
    return set(inspect(op.get_bind()).get_table_names())


def _ensure_index(name: str, table: str, cols: list) -> None:
    existing = {i["name"] for i in inspect(op.get_bind()).get_indexes(table)}
    if name not in existing:
        op.create_index(name, table, cols)


def upgrade() -> None:
    bind = op.get_bind()
    type_enum = postgresql.ENUM(*EVENT_TYPES, name="calendar_event_type", create_type=False)
    status_enum = postgresql.ENUM(*EVENT_STATUSES, name="calendar_event_status", create_type=False)
    type_enum.create(bind, checkfirst=True)
    status_enum.create(bind, checkfirst=True)

    if "compliance_calendar_events" not in _tables():
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
    for name, col in (
        ("ix_compliance_calendar_events_company_id", "company_id"),
        ("ix_compliance_calendar_events_event_type", "event_type"),
        ("ix_compliance_calendar_events_due_date", "due_date"),
        ("ix_compliance_calendar_events_status", "status"),
    ):
        _ensure_index(name, "compliance_calendar_events", [col])

    if "regulatory_rules" not in _tables():
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
    _ensure_index("ix_regulatory_rules_jurisdiction", "regulatory_rules", ["jurisdiction"])
    _ensure_index("ix_regulatory_rules_id", "regulatory_rules", ["id"])


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS regulatory_rules")
    op.execute("DROP TABLE IF EXISTS compliance_calendar_events")
    bind = op.get_bind()
    postgresql.ENUM(name="calendar_event_status").drop(bind, checkfirst=True)
    postgresql.ENUM(name="calendar_event_type").drop(bind, checkfirst=True)
