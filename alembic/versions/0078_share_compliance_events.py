"""Create evidence-bound share statutory trigger events.

Revision ID: 0078_share_compliance_events
Revises: 0077_merge_0076_release_heads

The event ledger separates allotment, capital-increase and transfer-registration
dates from user-entered shareholder profile fields. A trigger is usable only
when the event and the relevant filing/certificate status have independent
evidence provenance and reviewer identity.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0078_share_compliance_events"
down_revision = "0077_merge_0076_release_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "share_compliance_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("uuid_generate_v4()")),
        sa.Column("company_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("share_transfer_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("share_transfers.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("event_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("event_evidence_ref", sa.Text(), nullable=True),
        sa.Column("event_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("event_verified_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("filing_form", sa.String(16), nullable=True),
        sa.Column("filing_status", sa.Boolean(), nullable=True),
        sa.Column("filing_status_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("filing_evidence_ref", sa.Text(), nullable=True),
        sa.Column("filing_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("filing_verified_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("filing_date", sa.Date(), nullable=True),
        sa.Column("certificate_issued", sa.Boolean(), nullable=True),
        sa.Column("certificate_status_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("certificate_evidence_ref", sa.Text(), nullable=True),
        sa.Column("certificate_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("certificate_verified_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("certificate_issue_date", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("id", "company_id", name="uq_share_compliance_events_id_company"),
        sa.CheckConstraint(
            "event_type IN ('ALLOTMENT','CAPITAL_INCREASE','TRANSFER_REGISTRATION')",
            name="ck_share_compliance_event_type",
        ),
        sa.CheckConstraint(
            "(event_type = 'TRANSFER_REGISTRATION' AND share_transfer_id IS NOT NULL) OR "
            "(event_type IN ('ALLOTMENT','CAPITAL_INCREASE') AND share_transfer_id IS NULL)",
            name="ck_share_compliance_event_transfer_link",
        ),
        sa.CheckConstraint(
            "NOT event_verified OR (event_evidence_ref IS NOT NULL AND "
            "event_verified_at IS NOT NULL AND event_verified_by IS NOT NULL)",
            name="ck_share_compliance_event_verified_provenance",
        ),
        sa.CheckConstraint(
            "NOT filing_status_verified OR (filing_status IS NOT NULL AND "
            "filing_evidence_ref IS NOT NULL AND filing_verified_at IS NOT NULL "
            "AND filing_verified_by IS NOT NULL)",
            name="ck_share_compliance_event_filing_provenance",
        ),
        sa.CheckConstraint(
            "NOT certificate_status_verified OR (certificate_issued IS NOT NULL AND "
            "certificate_evidence_ref IS NOT NULL AND certificate_verified_at IS NOT NULL "
            "AND certificate_verified_by IS NOT NULL)",
            name="ck_share_compliance_event_certificate_provenance",
        ),
        sa.CheckConstraint(
            "filing_form IS NULL OR filing_form IN ('XV','IV')",
            name="ck_share_compliance_event_filing_form",
        ),
        schema="public",
    )
    op.create_index(
        "ix_share_compliance_events_company_type_date",
        "share_compliance_events", ["company_id", "event_type", "event_date"],
        schema="public",
    )
    op.create_index(
        "ix_share_compliance_events_transfer",
        "share_compliance_events", ["share_transfer_id"],
        schema="public",
        postgresql_where=sa.text("share_transfer_id IS NOT NULL"),
    )

    # Match the signed-identity tenant boundary introduced in 0050.
    op.execute("ALTER TABLE public.share_compliance_events ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.share_compliance_events FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY share_compliance_events_tenant_select
        ON public.share_compliance_events
        FOR SELECT USING (public.nlc_can_access_company(company_id))
    """)
    op.execute("""
        CREATE POLICY share_compliance_events_tenant_insert
        ON public.share_compliance_events
        FOR INSERT WITH CHECK (public.nlc_can_edit_company(company_id))
    """)
    # Event rows are immutable evidence. Corrections must be represented by
    # a new event; application roles cannot update or delete the evidence row.
    op.execute("REVOKE UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER ON public.share_compliance_events FROM nlc_app_role")
    op.execute("GRANT SELECT, INSERT ON public.share_compliance_events TO nlc_app_role")
    op.execute("REVOKE ALL ON public.share_compliance_events FROM PUBLIC")


def downgrade() -> None:
    raise RuntimeError(
        "0078 is forward-only: dropping the share event ledger would destroy "
        "statutory trigger and evidence provenance."
    )
