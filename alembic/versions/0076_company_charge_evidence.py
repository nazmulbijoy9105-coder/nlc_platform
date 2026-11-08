"""Persist tenant-scoped charge events with explicit legal evidence provenance.

Revision ID: 0076_company_charge_evidence
Revises: 0075_director_transfer_evidence

Reported charge facts remain nullable/unverified. Verification metadata is
required before any reported fact can enter the deterministic legal engine.
"""
from alembic import op
import sqlalchemy as sa

revision = "0076_company_charge_evidence"
down_revision = "0075_director_transfer_evidence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "company_charges",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("company_id", sa.UUID(), sa.ForeignKey("public.companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("creation_date", sa.Date(), nullable=False),
        sa.Column("charge_type", sa.String(100), nullable=False),
        sa.Column("amount_bdt", sa.Numeric(20, 2), nullable=False),
        sa.Column("charge_holder", sa.String(500), nullable=False),
        sa.Column("charge_reference", sa.String(255), nullable=True),
        sa.Column("form_xviii_filed", sa.Boolean(), nullable=True),
        sa.Column("form_xviii_filed_date", sa.Date(), nullable=True),
        sa.Column("registrable_under_s159", sa.Boolean(), nullable=True),
        sa.Column("satisfied", sa.Boolean(), nullable=True),
        sa.Column("satisfaction_date", sa.Date(), nullable=True),
        sa.Column("satisfaction_filed", sa.Boolean(), nullable=True),
        sa.Column("satisfaction_filed_date", sa.Date(), nullable=True),
        sa.Column("creation_date_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("creation_date_evidence_ref", sa.Text(), nullable=True),
        sa.Column("creation_date_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("creation_date_verified_by", sa.UUID(), sa.ForeignKey("public.users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("form_xviii_filing_status_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("form_xviii_filing_evidence_ref", sa.Text(), nullable=True),
        sa.Column("form_xviii_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("form_xviii_verified_by", sa.UUID(), sa.ForeignKey("public.users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("registrability_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("registrability_evidence_ref", sa.Text(), nullable=True),
        sa.Column("registrability_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("registrability_verified_by", sa.UUID(), sa.ForeignKey("public.users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("satisfaction_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("satisfaction_evidence_ref", sa.Text(), nullable=True),
        sa.Column("satisfaction_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("satisfaction_verified_by", sa.UUID(), sa.ForeignKey("public.users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("satisfaction_filing_status_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("satisfaction_filing_evidence_ref", sa.Text(), nullable=True),
        sa.Column("satisfaction_filing_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("satisfaction_filing_verified_by", sa.UUID(), sa.ForeignKey("public.users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("company_id", "charge_reference", name="uq_company_charge_reference"),
        sa.CheckConstraint("amount_bdt >= 0", name="ck_company_charges_amount_nonnegative"),
        sa.CheckConstraint(
            "NOT creation_date_verified OR (creation_date_evidence_ref IS NOT NULL AND creation_date_verified_at IS NOT NULL AND creation_date_verified_by IS NOT NULL)",
            name="ck_company_charges_creation_provenance",
        ),
        sa.CheckConstraint(
            "NOT form_xviii_filing_status_verified OR (form_xviii_filed IS NOT NULL AND form_xviii_filing_evidence_ref IS NOT NULL AND form_xviii_verified_at IS NOT NULL AND form_xviii_verified_by IS NOT NULL)",
            name="ck_company_charges_form_xviii_provenance",
        ),
        sa.CheckConstraint(
            "NOT registrability_verified OR (registrable_under_s159 IS NOT NULL AND registrability_evidence_ref IS NOT NULL AND registrability_verified_at IS NOT NULL AND registrability_verified_by IS NOT NULL)",
            name="ck_company_charges_registrability_provenance",
        ),
        sa.CheckConstraint(
            "NOT satisfaction_verified OR (satisfied IS NOT NULL AND satisfaction_evidence_ref IS NOT NULL AND satisfaction_verified_at IS NOT NULL AND satisfaction_verified_by IS NOT NULL)",
            name="ck_company_charges_satisfaction_provenance",
        ),
        sa.CheckConstraint(
            "NOT satisfaction_filing_status_verified OR (satisfaction_filed IS NOT NULL AND satisfaction_filing_evidence_ref IS NOT NULL AND satisfaction_filing_verified_at IS NOT NULL AND satisfaction_filing_verified_by IS NOT NULL)",
            name="ck_company_charges_satisfaction_filing_provenance",
        ),
        schema="public",
    )
    op.create_index("ix_company_charges_company_created", "company_charges", ["company_id", "creation_date"], schema="public")
    op.execute("ALTER TABLE public.company_charges ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE public.company_charges FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY company_charges_tenant_select ON public.company_charges
        FOR SELECT USING (public.nlc_can_view_financials_company(company_id))
    """)
    op.execute("""
        CREATE POLICY company_charges_tenant_insert ON public.company_charges
        FOR INSERT WITH CHECK (public.nlc_can_manage_financials_company(company_id))
    """)
    op.execute("""
        CREATE POLICY company_charges_tenant_update ON public.company_charges
        FOR UPDATE USING (public.nlc_can_manage_financials_company(company_id))
        WITH CHECK (public.nlc_can_manage_financials_company(company_id))
    """)
    op.execute("""
        CREATE POLICY company_charges_tenant_delete ON public.company_charges
        FOR DELETE USING (public.nlc_can_manage_financials_company(company_id))
    """)
    op.execute("REVOKE ALL ON TABLE public.company_charges FROM PUBLIC, nlc_app_role")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON public.company_charges TO nlc_app_role")


def downgrade() -> None:
    raise RuntimeError(
        "0076 is forward-only: dropping company_charges would destroy legal charge evidence."
    )
