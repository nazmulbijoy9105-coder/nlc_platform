"""Add RJSC form filings table

Revision ID: 0019_add_rjsc_forms
Revises: 0017_fix_constraints
"""
import sqlalchemy as sa
from alembic import op

revision = '0019_add_rjsc_forms'
down_revision = '0017_fix_constraints'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "rjsc_form_filings",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("form_code", sa.String(20), nullable=False),
        sa.Column("form_number", sa.String(20), nullable=False),
        sa.Column("form_name", sa.String(255), nullable=False),
        sa.Column("section_reference", sa.String(100), nullable=False),
        sa.Column("related_rule_id", sa.String(20), nullable=True),
        sa.Column("filing_status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("due_date", sa.Date, nullable=True),
        sa.Column("filed_date", sa.Date, nullable=True),
        sa.Column("rjsc_receipt_number", sa.String(255), nullable=True),
        sa.Column("rjsc_acknowledgment_number", sa.String(255), nullable=True),
        sa.Column("filed_by", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("financial_year", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("idx_rjsc_forms_company", "rjsc_form_filings", ["company_id"])
    op.create_index("idx_rjsc_forms_status", "rjsc_form_filings", ["filing_status"])
    op.create_index("idx_rjsc_forms_due", "rjsc_form_filings", ["due_date"])

def downgrade():
    op.drop_table("rjsc_form_filings")
