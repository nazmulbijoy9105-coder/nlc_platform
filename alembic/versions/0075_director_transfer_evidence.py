"""Add evidence-bound director and share-transfer facts.

Revision ID: 0075_director_transfer_evidence
Revises: 0074_legal_release_quarantine

Legacy share-transfer booleans defaulted to True without evidence provenance.
Snapshot them, then clear them to NULL. New verified fields require evidence
references and reviewer identity/timestamps.
"""
from alembic import op
import sqlalchemy as sa

revision = "0075_director_transfer_evidence"
down_revision = "0061_legal_release_quarantine"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS audit")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS audit.share_transfer_legacy_status_snapshot (
            id BIGSERIAL PRIMARY KEY,
            share_transfer_id UUID NOT NULL,
            company_id UUID NOT NULL,
            captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            has_transfer_instrument BOOLEAN,
            stamp_duty_paid BOOLEAN,
            board_approval_obtained BOOLEAN,
            register_updated BOOLEAN,
            aoa_restriction_violated BOOLEAN,
            transfer_status TEXT,
            is_irregular BOOLEAN
        )
        """
    )
    op.execute(
        """
        INSERT INTO audit.share_transfer_legacy_status_snapshot (
            share_transfer_id, company_id, has_transfer_instrument,
            stamp_duty_paid, board_approval_obtained, register_updated,
            aoa_restriction_violated, transfer_status, is_irregular
        )
        SELECT id, company_id, has_transfer_instrument, stamp_duty_paid,
               board_approval_obtained, register_updated,
               aoa_restriction_violated, transfer_status::text, is_irregular
          FROM public.share_transfers
        """
    )

    # Legacy values/defaults have no source identity, verification timestamp
    # or evidence reference. Preserve them in audit, then mark current state unknown.
    for column in (
        "has_transfer_instrument",
        "stamp_duty_paid",
        "board_approval_obtained",
        "register_updated",
        "aoa_restriction_violated",
    ):
        op.alter_column(
            "share_transfers",
            column,
            existing_type=sa.Boolean(),
            nullable=True,
            schema="public",
        )
    op.execute(
        """
        UPDATE public.share_transfers
           SET has_transfer_instrument = NULL,
               stamp_duty_paid = NULL,
               board_approval_obtained = NULL,
               register_updated = NULL,
               aoa_restriction_violated = NULL
        """
    )

    # Director Form XII status and section 93(2) consent are separate facts.
    director_columns = [
        sa.Column("form_xii_filed", sa.Boolean(), nullable=True),
        sa.Column("form_xii_status_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("form_xii_evidence_ref", sa.Text(), nullable=True),
        sa.Column("form_xii_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("form_xii_verified_by", sa.UUID(), nullable=True),
        sa.Column("consent_filed", sa.Boolean(), nullable=True),
        sa.Column("consent_filed_date", sa.Date(), nullable=True),
        sa.Column("consent_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("consent_evidence_ref", sa.Text(), nullable=True),
        sa.Column("consent_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consent_verified_by", sa.UUID(), nullable=True),
    ]
    for column in director_columns:
        op.add_column("directors", column, schema="public")
    op.create_foreign_key(
        "fk_directors_form_xii_verified_by_users",
        "directors", "users", ["form_xii_verified_by"], ["id"],
        source_schema="public", referent_schema="public",
    )
    op.create_foreign_key(
        "fk_directors_consent_verified_by_users",
        "directors", "users", ["consent_verified_by"], ["id"],
        source_schema="public", referent_schema="public",
    )
    op.create_check_constraint(
        "ck_directors_form_xii_verified_has_provenance",
        "directors",
        "NOT form_xii_status_verified OR "
        "(form_xii_filed IS NOT NULL AND form_xii_evidence_ref IS NOT NULL "
        "AND form_xii_verified_at IS NOT NULL AND form_xii_verified_by IS NOT NULL)",
        schema="public",
    )
    op.create_check_constraint(
        "ck_directors_consent_verified_has_provenance",
        "directors",
        "NOT consent_verified OR "
        "(consent_filed IS NOT NULL AND consent_evidence_ref IS NOT NULL "
        "AND consent_verified_at IS NOT NULL AND consent_verified_by IS NOT NULL)",
        schema="public",
    )

    transfer_columns = [
        sa.Column("transfer_instrument_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("transfer_instrument_evidence_ref", sa.Text(), nullable=True),
        sa.Column("form_117_filed", sa.Boolean(), nullable=True),
        sa.Column("form_117_evidence_ref", sa.Text(), nullable=True),
        sa.Column("stamp_duty_applicability_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("stamp_duty_evidence_ref", sa.Text(), nullable=True),
        sa.Column("board_approval_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("board_approval_evidence_ref", sa.Text(), nullable=True),
        sa.Column("aoa_restriction_apply", sa.Boolean(), nullable=True),
        sa.Column("articles_clause_evidence_ref", sa.Text(), nullable=True),
        sa.Column("transfer_registered", sa.Boolean(), nullable=True),
        sa.Column("transfer_registration_evidence_ref", sa.Text(), nullable=True),
        sa.Column("registration_refused", sa.Boolean(), nullable=True),
        sa.Column("registration_refusal_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("refusal_decision_evidence_ref", sa.Text(), nullable=True),
        sa.Column("refusal_notice_sent", sa.Boolean(), nullable=True),
        sa.Column("refusal_notice_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("refusal_notice_evidence_ref", sa.Text(), nullable=True),
        sa.Column("instrument_lodged_date", sa.Date(), nullable=True),
        sa.Column("instrument_lodgement_evidence_ref", sa.Text(), nullable=True),
        sa.Column("register_update_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("register_update_evidence_ref", sa.Text(), nullable=True),
    ]
    for column in transfer_columns:
        op.add_column("share_transfers", column, schema="public")

    constraints = [
        ("ck_share_transfer_instrument_verified_has_evidence",
         "NOT transfer_instrument_verified OR transfer_instrument_evidence_ref IS NOT NULL"),
        ("ck_share_transfer_form117_status_has_evidence",
         "form_117_filed IS NULL OR form_117_evidence_ref IS NOT NULL"),
        ("ck_share_transfer_instrument_status_has_evidence",
         "has_transfer_instrument IS NULL OR (transfer_instrument_verified AND transfer_instrument_evidence_ref IS NOT NULL)"),
        ("ck_share_transfer_stamp_status_has_evidence",
         "stamp_duty_paid IS NULL OR (stamp_duty_applicability_verified AND stamp_duty_evidence_ref IS NOT NULL)"),
        ("ck_share_transfer_board_status_has_evidence",
         "board_approval_obtained IS NULL OR (board_approval_verified AND board_approval_evidence_ref IS NOT NULL)"),
        ("ck_share_transfer_register_status_has_evidence",
         "register_updated IS NULL OR (register_update_verified AND register_update_evidence_ref IS NOT NULL)"),
        ("ck_share_transfer_stamp_duty_verified_has_evidence",
         "NOT stamp_duty_applicability_verified OR stamp_duty_evidence_ref IS NOT NULL"),
        ("ck_share_transfer_board_approval_verified_has_evidence",
         "NOT board_approval_verified OR board_approval_evidence_ref IS NOT NULL"),
        ("ck_share_transfer_articles_restriction_has_clause",
         "aoa_restriction_apply IS NULL OR articles_clause_evidence_ref IS NOT NULL"),
        ("ck_share_transfer_registered_has_evidence",
         "transfer_registered IS NULL OR transfer_registration_evidence_ref IS NOT NULL"),
        ("ck_share_transfer_refusal_verified_has_evidence",
         "NOT registration_refusal_verified OR refusal_decision_evidence_ref IS NOT NULL"),
        ("ck_share_transfer_refusal_notice_verified_has_evidence",
         "NOT refusal_notice_verified OR refusal_notice_evidence_ref IS NOT NULL"),
        ("ck_share_transfer_lodgement_date_has_evidence",
         "instrument_lodged_date IS NULL OR instrument_lodgement_evidence_ref IS NOT NULL"),
        ("ck_share_transfer_register_update_verified_has_evidence",
         "NOT register_update_verified OR register_update_evidence_ref IS NOT NULL"),
    ]
    for name, expression in constraints:
        op.create_check_constraint(name, "share_transfers", expression, schema="public")

    # Form XII filing date is distinct from the appointment/cessation event date.
    op.add_column("directors", sa.Column("form_xii_filed_date", sa.Date(), nullable=True), schema="public")

    # Section 150 applicability and declaration status are not universal. Snapshot
    # legacy company boolean values before clearing them because they had no
    # evidence/reviewer provenance and defaulted to True.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS audit.section150_legacy_status_snapshot (
            id BIGSERIAL PRIMARY KEY,
            company_id UUID NOT NULL,
            captured_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            business_commencement_declaration_filed BOOLEAN
        )
        """
    )
    op.execute(
        """
        INSERT INTO audit.section150_legacy_status_snapshot (
            company_id, business_commencement_declaration_filed
        )
        SELECT id, business_commencement_declaration_filed
          FROM public.companies
        """
    )
    op.alter_column(
        "companies",
        "business_commencement_declaration_filed",
        existing_type=sa.Boolean(),
        nullable=True,
        server_default=None,
        schema="public",
    )
    op.execute(
        "UPDATE public.companies SET business_commencement_declaration_filed = NULL"
    )
    company_columns = [
        sa.Column("business_commencement_declaration_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("business_commencement_declaration_evidence_ref", sa.Text(), nullable=True),
        sa.Column("business_commencement_declaration_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("business_commencement_declaration_verified_by", sa.UUID(), nullable=True),
        sa.Column("section150_prospectus_issued", sa.Boolean(), nullable=True),
        sa.Column("section150_applicability_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("section150_applicability_evidence_ref", sa.Text(), nullable=True),
        sa.Column("section150_applicability_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("section150_applicability_verified_by", sa.UUID(), nullable=True),
    ]
    for column in company_columns:
        op.add_column("companies", column, schema="public")
    op.create_foreign_key(
        "fk_companies_section150_verified_by_users",
        "companies", "users", ["section150_applicability_verified_by"], ["id"],
        source_schema="public", referent_schema="public",
    )
    op.create_foreign_key(
        "fk_companies_commencement_verified_by_users",
        "companies", "users", ["business_commencement_declaration_verified_by"], ["id"],
        source_schema="public", referent_schema="public",
    )
    op.create_check_constraint(
        "ck_companies_section150_applicability_verified_has_provenance",
        "companies",
        "NOT section150_applicability_verified OR "
        "(section150_prospectus_issued IS NOT NULL AND section150_applicability_evidence_ref IS NOT NULL "
        "AND section150_applicability_verified_at IS NOT NULL AND section150_applicability_verified_by IS NOT NULL)",
        schema="public",
    )
    op.create_check_constraint(
        "ck_companies_commencement_status_verified_has_provenance",
        "companies",
        "NOT business_commencement_declaration_verified OR "
        "(business_commencement_declaration_filed IS NOT NULL AND business_commencement_declaration_evidence_ref IS NOT NULL "
        "AND business_commencement_declaration_verified_at IS NOT NULL AND business_commencement_declaration_verified_by IS NOT NULL)",
        schema="public",
    )

    # Keep defaults in the ORM only; DB rows must explicitly set verified fields.
    for table, columns in (
        ("directors", ("form_xii_status_verified", "consent_verified")),
        ("share_transfers", (
            "transfer_instrument_verified", "stamp_duty_applicability_verified",
            "board_approval_verified", "registration_refusal_verified",
            "refusal_notice_verified", "register_update_verified",
        )),
        ("companies", (
            "business_commencement_declaration_verified",
            "section150_applicability_verified",
        )),
    ):
        for column in columns:
            op.alter_column(table, column, server_default=None, schema="public")


def downgrade() -> None:
    raise RuntimeError(
        "0062 is forward-only: downgrading would discard evidence provenance "
        "or restore unverified legacy share-transfer booleans."
    )
