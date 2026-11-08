"""Add evidence-gated AGM cycle records and share statutory event ledger.

Revision ID: 0082_agm_share_event_provenance
Revises: 0081_merge_release_and_articles_wallet_heads

The migration is intentionally additive. Existing boolean/profile values are
not promoted to verified facts. New event writes are tenant-scoped; only a
verified signed staff principal may set verification metadata.
"""
from alembic import op
import sqlalchemy as sa

revision = "0082_agm_share_event_provenance"
down_revision = "0081_merge_release_and_articles_wallet_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agms",
        sa.Column("agm_held_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("agms", sa.Column("agm_held_evidence_ref", sa.Text(), nullable=True))
    op.add_column("agms", sa.Column("agm_held_verified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "agms",
        sa.Column("agm_held_verified_by", sa.UUID(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
    )
    op.add_column(
        "agms",
        sa.Column("member_register_snapshot_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("agms", sa.Column("member_register_evidence_ref", sa.Text(), nullable=True))
    op.add_column("agms", sa.Column("member_register_verified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "agms",
        sa.Column("member_register_verified_by", sa.UUID(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
    )
    op.add_column("agms", sa.Column("entitled_members_count", sa.Integer(), nullable=True))
    op.create_check_constraint(
        "ck_agms_held_verification_provenance",
        "agms",
        "NOT agm_held_verified OR "
        "(agm_held_evidence_ref IS NOT NULL AND btrim(agm_held_evidence_ref) <> '' "
        "AND agm_held_verified_at IS NOT NULL AND agm_held_verified_by IS NOT NULL)",
    )
    op.create_check_constraint(
        "ck_agms_member_register_provenance",
        "agms",
        "NOT member_register_snapshot_verified OR "
        "(member_register_evidence_ref IS NOT NULL AND btrim(member_register_evidence_ref) <> '' "
        "AND member_register_verified_at IS NOT NULL AND member_register_verified_by IS NOT NULL "
        "AND entitled_members_count IS NOT NULL AND entitled_members_count >= 1)",
    )

    op.create_table(
        "agm_notice_evidence",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("company_id", sa.UUID(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agm_id", sa.UUID(), sa.ForeignKey("agms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("shareholder_id", sa.UUID(), sa.ForeignKey("shareholders.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("recipient_key", sa.String(160), nullable=False),
        sa.Column("recipient_name", sa.String(300), nullable=False),
        sa.Column("entitled_member_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("entitlement_evidence_ref", sa.Text(), nullable=True),
        sa.Column("entitlement_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("entitlement_verified_by", sa.UUID(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("notice_delivery_status", sa.String(24), nullable=False, server_default="UNKNOWN"),
        sa.Column("notice_sent_date", sa.Date(), nullable=True),
        sa.Column("notice_evidence_ref", sa.Text(), nullable=True),
        sa.Column("notice_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("notice_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notice_verified_by", sa.UUID(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("consent_given", sa.Boolean(), nullable=True),
        sa.Column("consent_received_date", sa.Date(), nullable=True),
        sa.Column("consent_evidence_ref", sa.Text(), nullable=True),
        sa.Column("consent_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("consent_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consent_verified_by", sa.UUID(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("omission_accidental", sa.Boolean(), nullable=True),
        sa.Column("omission_evidence_ref", sa.Text(), nullable=True),
        sa.Column("omission_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("omission_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("omission_verified_by", sa.UUID(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("agm_id", "recipient_key", name="uq_agm_notice_recipient"),
        sa.CheckConstraint("notice_delivery_status IN ('SERVED','NOT_SERVED','NOT_RECEIVED','UNKNOWN')", name="ck_agm_notice_delivery_status"),
        sa.CheckConstraint(
            "NOT entitled_member_verified OR "
            "(entitlement_evidence_ref IS NOT NULL AND btrim(entitlement_evidence_ref) <> '' "
            "AND entitlement_verified_at IS NOT NULL AND entitled_member_verified IS TRUE "
            "AND entitlement_verified_by IS NOT NULL)",
            name="ck_agm_notice_entitlement_provenance",
        ),
        sa.CheckConstraint(
            "NOT notice_verified OR "
            "(notice_evidence_ref IS NOT NULL AND btrim(notice_evidence_ref) <> '' "
            "AND notice_delivery_status <> 'UNKNOWN' AND notice_verified_at IS NOT NULL "
            "AND notice_verified_by IS NOT NULL)",
            name="ck_agm_notice_service_provenance",
        ),
        sa.CheckConstraint(
            "NOT consent_verified OR "
            "(consent_given IS NOT NULL AND consent_evidence_ref IS NOT NULL "
            "AND btrim(consent_evidence_ref) <> '' AND consent_verified_at IS NOT NULL "
            "AND consent_verified_by IS NOT NULL)",
            name="ck_agm_notice_consent_provenance",
        ),
        sa.CheckConstraint(
            "NOT omission_verified OR "
            "(omission_accidental IS NOT NULL AND omission_evidence_ref IS NOT NULL "
            "AND btrim(omission_evidence_ref) <> '' AND omission_verified_at IS NOT NULL "
            "AND omission_verified_by IS NOT NULL)",
            name="ck_agm_notice_omission_provenance",
        ),
    )
    op.create_index("ix_agm_notice_evidence_company_id", "agm_notice_evidence", ["company_id"])
    op.create_index("ix_agm_notice_evidence_agm_id", "agm_notice_evidence", ["agm_id"])

    op.create_table(
        "share_compliance_events",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("company_id", sa.UUID(), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("share_transfer_id", sa.UUID(), sa.ForeignKey("share_transfers.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("shareholder_id", sa.UUID(), sa.ForeignKey("shareholders.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("event_reference", sa.String(160), nullable=False),
        sa.Column("submitted_by", sa.UUID(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("shares_affected", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("event_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("event_evidence_ref", sa.Text(), nullable=False),
        sa.Column("event_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("event_verified_by", sa.UUID(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("filing_form", sa.String(16), nullable=True),
        sa.Column("filing_status", sa.Boolean(), nullable=True),
        sa.Column("filing_status_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("filing_evidence_ref", sa.Text(), nullable=True),
        sa.Column("filing_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("filing_verified_by", sa.UUID(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("filing_date", sa.Date(), nullable=True),
        sa.Column("certificate_issued", sa.Boolean(), nullable=True),
        sa.Column("certificate_status_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("certificate_evidence_ref", sa.Text(), nullable=True),
        sa.Column("certificate_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("certificate_verified_by", sa.UUID(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("certificate_issue_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("company_id", "event_type", "event_reference", name="uq_share_event_company_reference"),
        sa.CheckConstraint("event_type IN ('ALLOTMENT','CAPITAL_INCREASE_RESOLUTION','TRANSFER_REGISTERED')", name="ck_share_event_type"),
        sa.CheckConstraint("(share_transfer_id IS NOT NULL) = (event_type = 'TRANSFER_REGISTERED')", name="ck_share_event_transfer_link"),
        sa.CheckConstraint(
            "(event_type = 'ALLOTMENT' AND (filing_form IS NULL OR filing_form = 'FORM_XV')) OR "
            "(event_type = 'CAPITAL_INCREASE_RESOLUTION' AND (filing_form IS NULL OR filing_form = 'FORM_IV')) OR "
            "(event_type = 'TRANSFER_REGISTERED' AND filing_form IS NULL)",
            name="ck_share_event_form_matches_trigger",
        ),
        sa.CheckConstraint("shares_affected IS NULL OR shares_affected > 0", name="ck_share_event_shares_positive"),
        sa.CheckConstraint("btrim(event_reference) <> '' AND btrim(event_evidence_ref) <> ''", name="ck_share_event_source_required"),
        sa.CheckConstraint(
            "NOT event_verified OR (event_verified_at IS NOT NULL AND event_verified_by IS NOT NULL AND event_verified_by <> submitted_by)",
            name="ck_share_event_verification_provenance",
        ),
        sa.CheckConstraint(
            "NOT filing_status_verified OR (filing_status IS NOT NULL AND filing_evidence_ref IS NOT NULL "
            "AND btrim(filing_evidence_ref) <> '' AND filing_verified_at IS NOT NULL AND filing_verified_by IS NOT NULL)",
            name="ck_share_event_filing_provenance",
        ),
        sa.CheckConstraint(
            "NOT certificate_status_verified OR (certificate_issued IS NOT NULL AND certificate_evidence_ref IS NOT NULL "
            "AND btrim(certificate_evidence_ref) <> '' AND certificate_verified_at IS NOT NULL AND certificate_verified_by IS NOT NULL)",
            name="ck_share_event_certificate_provenance",
        ),
        sa.CheckConstraint("certificate_issued IS DISTINCT FROM TRUE OR certificate_issue_date IS NOT NULL", name="ck_share_event_certificate_date"),
        sa.CheckConstraint("filing_status IS DISTINCT FROM TRUE OR filing_date IS NOT NULL", name="ck_share_event_filing_date"),
    )
    op.create_index("ix_share_compliance_events_company_id", "share_compliance_events", ["company_id"])
    op.create_index("ix_share_compliance_events_company_event_date", "share_compliance_events", ["company_id", "event_type", "event_date"])

    for table in ("agm_notice_evidence", "share_compliance_events"):
        op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE public.{table} FORCE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY {table}_tenant_select ON public.{table}
            FOR SELECT USING (public.nlc_can_access_company(company_id))
        """)
        op.execute(f"""
            CREATE POLICY {table}_member_submit ON public.{table}
            FOR INSERT WITH CHECK (
                public.nlc_can_edit_company(company_id)
                AND event_verified IS FALSE
                AND filing_status_verified IS FALSE
                AND certificate_status_verified IS FALSE
                AND submitted_by = public.nlc_current_user_id()
                AND submitted_at IS NOT NULL
            )
        """ if table == "share_compliance_events" else f"""
            CREATE POLICY {table}_member_submit ON public.{table}
            FOR INSERT WITH CHECK (
                public.nlc_can_edit_company(company_id)
                AND entitled_member_verified IS FALSE
                AND notice_verified IS FALSE
                AND consent_verified IS FALSE
                AND omission_verified IS FALSE
            )
        """)
        op.execute(f"""
            CREATE POLICY {table}_staff_verify ON public.{table}
            FOR UPDATE
            USING (public.nlc_current_user_is_staff() AND public.nlc_can_access_company(company_id))
            WITH CHECK (public.nlc_current_user_is_staff() AND public.nlc_can_access_company(company_id))
        """)


def downgrade() -> None:
    # Forward-only: these tables are legal evidence records. Dropping them
    # would destroy provenance and verification history.
    pass
