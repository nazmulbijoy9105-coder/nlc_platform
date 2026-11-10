"""persist company fact provenance and finding snapshots

Revision ID: 0104_company_fact_provenance
Revises: 0093_verified_rule_audit_view, b10c91ac6860
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0104_company_fact_provenance"
down_revision = ("0093_verified_rule_audit_view", "b10c91ac6860")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "company_facts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("fact_key", sa.String(120), nullable=False),
        sa.Column("fact_value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("trust_level", sa.String(40), nullable=False),
        sa.Column("asserted_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("observed_on", sa.Date(), nullable=False),
        sa.Column("source_reference", sa.Text(), nullable=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("authorized_uploader_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verification_status", sa.String(20), nullable=False, server_default="UNVERIFIED"),
        sa.Column("verified_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verification_note", sa.Text(), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("supersedes_fact_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("company_facts.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "(trust_level = 'USER_ASSERTED' AND document_id IS NULL AND authorized_uploader_id IS NULL AND uploaded_at IS NULL) OR "
            "(trust_level = 'AUTHORIZED_DOCUMENT_BACKED' AND document_id IS NOT NULL AND authorized_uploader_id IS NOT NULL AND uploaded_at IS NOT NULL)",
            name="ck_company_fact_trust_source",
        ),
        sa.CheckConstraint(
            "(verification_status = 'VERIFIED' AND verified_by IS NOT NULL AND verified_at IS NOT NULL) OR "
            "(verification_status <> 'VERIFIED' AND verified_by IS NULL AND verified_at IS NULL)",
            name="ck_company_fact_verification_actor",
        ),
    )
    op.create_index("ix_company_facts_company_id", "company_facts", ["company_id"])
    op.create_index("ix_company_facts_fact_key", "company_facts", ["fact_key"])
    op.create_index("ix_company_facts_company_key_current", "company_facts", ["company_id", "fact_key", "is_current"])

    # Legacy findings have no reconstructable provenance; [] means unknown, not verified.
    op.add_column(
        "compliance_flags",
        sa.Column("fact_provenance_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
    )
    op.add_column(
        "compliance_evaluation_runs",
        sa.Column("fact_provenance_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
    )


def downgrade() -> None:
    op.drop_column("compliance_evaluation_runs", "fact_provenance_snapshot")
    op.drop_column("compliance_flags", "fact_provenance_snapshot")
    op.drop_index("ix_company_facts_company_key_current", table_name="company_facts")
    op.drop_index("ix_company_facts_fact_key", table_name="company_facts")
    op.drop_index("ix_company_facts_company_id", table_name="company_facts")
    op.drop_table("company_facts")
