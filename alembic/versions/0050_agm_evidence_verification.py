"""Version-pinned, independently reviewed AGM member and attendance evidence.

Revision ID: 0050_agm_evidence_verification
Revises: 0049_tenant_rls_hardening
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0050_agm_evidence_verification"
down_revision = "0049_tenant_rls_hardening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agm_evidence_verifications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agm_id", UUID(as_uuid=True), sa.ForeignKey("agms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("meeting_date", sa.Date(), nullable=False),
        sa.Column("evidence_kind", sa.String(32), nullable=False),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("source_checksum_sha256", sa.String(64), nullable=False),
        sa.Column("source_document_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("submitted_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_count", sa.Integer(), nullable=True),
        sa.Column("reviewer_note", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("evidence_kind IN ('MEMBERS_REGISTER', 'ATTENDANCE_REGISTER')", name="ck_agm_evidence_kind"),
        sa.CheckConstraint("status IN ('PENDING', 'VERIFIED', 'REJECTED', 'SUPERSEDED')", name="ck_agm_evidence_status"),
        sa.CheckConstraint("source_checksum_sha256 ~ '^[0-9a-f]{64}$'", name="ck_agm_evidence_checksum"),
        sa.CheckConstraint("source_document_version >= 1", name="ck_agm_evidence_version"),
        sa.CheckConstraint("verified_count IS NULL OR verified_count >= 0", name="ck_agm_evidence_count"),
        sa.CheckConstraint(
            "(status = 'PENDING' AND reviewed_by IS NULL AND reviewed_at IS NULL AND verified_count IS NULL) OR "
            "(status = 'VERIFIED' AND reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL AND verified_count IS NOT NULL) OR "
            "(status IN ('REJECTED', 'SUPERSEDED') AND reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)",
            name="ck_agm_evidence_review_metadata",
        ),
        sa.CheckConstraint(
            "status <> 'VERIFIED' OR evidence_kind <> 'MEMBERS_REGISTER' OR verified_count >= 1",
            name="ck_agm_evidence_member_count_positive",
        ),
    )
    for name, column in (
        ("ix_agm_evidence_verifications_company_id", "company_id"),
        ("ix_agm_evidence_verifications_agm_id", "agm_id"),
        ("ix_agm_evidence_verifications_document_id", "document_id"),
    ):
        op.create_index(name, "agm_evidence_verifications", [column])
    op.create_index(
        "uq_agm_evidence_pending_kind", "agm_evidence_verifications",
        ["agm_id", "evidence_kind"], unique=True,
        postgresql_where=sa.text("status = 'PENDING'"),
    )
    op.create_index(
        "uq_agm_evidence_verified_kind", "agm_evidence_verifications",
        ["agm_id", "evidence_kind"], unique=True,
        postgresql_where=sa.text("status = 'VERIFIED'"),
    )

    op.create_table(
        "agm_evidence_verification_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("verification_id", UUID(as_uuid=True), sa.ForeignKey("agm_evidence_verifications.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("actor_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("previous_status", sa.String(20), nullable=True),
        sa.Column("new_status", sa.String(20), nullable=False),
        sa.Column("source_checksum_sha256", sa.String(64), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("action IN ('SUBMITTED', 'VERIFIED', 'REJECTED', 'SUPERSEDED')", name="ck_agm_evidence_event_action"),
    )
    op.create_index("ix_agm_evidence_events_company_id", "agm_evidence_verification_events", ["company_id"])
    op.create_index("ix_agm_evidence_events_verification_id", "agm_evidence_verification_events", ["verification_id"])

    for table in ("agm_evidence_verifications", "agm_evidence_verification_events"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY {table}_tenant_access ON {table}
            FOR ALL USING (public.nlc_can_access_company(company_id))
            WITH CHECK (public.nlc_can_access_company(company_id))
        """)

    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_prevent_agm_evidence_event_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'AGM evidence verification events are append-only';
        END;
        $$;
    """)
    op.execute("""
        CREATE TRIGGER agm_evidence_events_append_only
        BEFORE UPDATE OR DELETE ON public.agm_evidence_verification_events
        FOR EACH ROW EXECUTE FUNCTION public.nlc_prevent_agm_evidence_event_mutation()
    """)
    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_protect_agm_evidence_verification()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.company_id IS DISTINCT FROM OLD.company_id
               OR NEW.agm_id IS DISTINCT FROM OLD.agm_id
               OR NEW.meeting_date IS DISTINCT FROM OLD.meeting_date
               OR NEW.evidence_kind IS DISTINCT FROM OLD.evidence_kind
               OR NEW.document_id IS DISTINCT FROM OLD.document_id
               OR NEW.source_checksum_sha256 IS DISTINCT FROM OLD.source_checksum_sha256
               OR NEW.source_document_version IS DISTINCT FROM OLD.source_document_version
               OR NEW.submitted_by IS DISTINCT FROM OLD.submitted_by
               OR NEW.submitted_at IS DISTINCT FROM OLD.submitted_at THEN
                RAISE EXCEPTION 'AGM evidence source identity is immutable';
            END IF;
            IF OLD.status <> 'PENDING' AND (
                NEW.reviewed_by IS DISTINCT FROM OLD.reviewed_by
                OR NEW.reviewed_at IS DISTINCT FROM OLD.reviewed_at
                OR NEW.verified_count IS DISTINCT FROM OLD.verified_count
                OR NEW.reviewer_note IS DISTINCT FROM OLD.reviewer_note
            ) THEN
                RAISE EXCEPTION 'AGM evidence review decision is immutable';
            END IF;
            IF OLD.status = 'PENDING' AND NEW.status NOT IN ('PENDING', 'VERIFIED', 'REJECTED') THEN
                RAISE EXCEPTION 'Invalid AGM evidence transition';
            ELSIF OLD.status = 'VERIFIED' AND NEW.status NOT IN ('VERIFIED', 'SUPERSEDED') THEN
                RAISE EXCEPTION 'Invalid AGM evidence transition';
            ELSIF OLD.status IN ('REJECTED', 'SUPERSEDED') AND NEW.status <> OLD.status THEN
                RAISE EXCEPTION 'Terminal AGM evidence state cannot be reopened';
            END IF;
            RETURN NEW;
        END;
        $$;
        CREATE TRIGGER agm_evidence_source_immutable
        BEFORE UPDATE ON public.agm_evidence_verifications
        FOR EACH ROW EXECUTE FUNCTION public.nlc_protect_agm_evidence_verification();
    """)
    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_prevent_agm_evidence_delete()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION 'AGM evidence verification records are retained as legal evidence';
        END;
        $$;
    """)
    op.execute("""
        CREATE TRIGGER agm_evidence_no_delete
        BEFORE DELETE ON public.agm_evidence_verifications
        FOR EACH ROW EXECUTE FUNCTION public.nlc_prevent_agm_evidence_delete()
    """)
    op.execute("""
        DO $grant$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'nlc_app_role') THEN
                GRANT SELECT, INSERT, UPDATE ON public.agm_evidence_verifications TO nlc_app_role;
                GRANT SELECT, INSERT ON public.agm_evidence_verification_events TO nlc_app_role;
                REVOKE UPDATE, DELETE, TRUNCATE ON public.agm_evidence_verification_events FROM nlc_app_role;
            END IF;
        END
        $grant$;
    """)


def downgrade() -> None:
    # Forward-only: reviewed legal evidence and its event history are retained.
    pass
