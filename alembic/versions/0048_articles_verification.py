"""Articles of Association verification workflow.

Revision ID: 0048_articles_verification
Revises: 0047_aud003_review_state
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "0048_articles_verification"
down_revision = "0047_aud003_review_state"
branch_labels = None
depends_on = None


def upgrade():
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE document_type ADD VALUE IF NOT EXISTS 'ARTICLES_OF_ASSOCIATION'")

    op.create_table(
        "articles_verifications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("source_checksum_sha256", sa.String(64), nullable=False),
        sa.Column("source_document_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("submitted_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("quorum_variation_exists", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("quorum_required", sa.Integer(), nullable=True),
        sa.Column("clause_reference", sa.String(255), nullable=False),
        sa.Column("reviewer_note", sa.Text(), nullable=True),
        sa.Column("revoked_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revocation_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('PENDING', 'VERIFIED', 'REJECTED', 'REVOKED', 'SUPERSEDED')", name="ck_articles_verifications_status"),
        sa.CheckConstraint("source_checksum_sha256 ~ '^[0-9a-f]{64}
        sa.CheckConstraint("quorum_required IS NULL OR quorum_required BETWEEN 1 AND 100", name="ck_articles_verifications_quorum"),
        sa.CheckConstraint("quorum_variation_exists = FALSE OR quorum_required IS NOT NULL", name="ck_articles_verifications_variation_quorum"),
        sa.CheckConstraint(
            "(status = 'PENDING' AND reviewed_by IS NULL AND reviewed_at IS NULL) OR "
            "(status IN ('VERIFIED', 'REJECTED', 'REVOKED', 'SUPERSEDED') AND reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)",
            name="ck_articles_verifications_review_metadata",
        ),
        sa.CheckConstraint(
            "(status = 'REVOKED' AND revoked_by IS NOT NULL AND revoked_at IS NOT NULL AND revocation_reason IS NOT NULL) OR "
            "(status <> 'REVOKED' AND revoked_by IS NULL AND revoked_at IS NULL AND revocation_reason IS NULL)",
            name="ck_articles_verifications_revocation_metadata",
        ),
    )
    op.create_index("ix_articles_verifications_company_id", "articles_verifications", ["company_id"])
    op.create_index("ix_articles_verifications_document_id", "articles_verifications", ["document_id"])
    op.create_index("ix_articles_verifications_status", "articles_verifications", ["status"])
    op.create_index(
        "uq_articles_verifications_pending", "articles_verifications", ["company_id"],
        unique=True, postgresql_where=sa.text("status = 'PENDING'"),
    )
    op.create_index(
        "uq_articles_verifications_verified", "articles_verifications", ["company_id"],
        unique=True, postgresql_where=sa.text("status = 'VERIFIED'"),
    )

    op.create_table(
        "articles_verification_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("verification_id", UUID(as_uuid=True), sa.ForeignKey("articles_verifications.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("actor_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("previous_status", sa.String(20), nullable=True),
        sa.Column("new_status", sa.String(20), nullable=False),
        sa.Column("source_checksum_sha256", sa.String(64), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("action IN ('SUBMITTED', 'VERIFIED', 'REJECTED', 'REVOKED', 'SUPERSEDED')", name="ck_articles_verification_events_action"),
    )
    op.create_index("ix_articles_verification_events_company_id", "articles_verification_events", ["company_id"])
    op.create_index("ix_articles_verification_events_verification_id", "articles_verification_events", ["verification_id"])

    for table in ("articles_verifications", "articles_verification_events"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY {table}_company_policy ON {table}
            USING (
                current_setting('app.current_user_id', TRUE) = 'ADMIN'
                OR (
                    current_setting('app.current_user_id', TRUE)
                        ~* '^[0-9a-f]{{8}}-[0-9a-f]{{4}}-[0-9a-f]{{4}}-[0-9a-f]{{4}}-[0-9a-f]{{12}}$'
                    AND company_id IN (
                        SELECT company_id FROM company_user_access
                        WHERE user_id = current_setting('app.current_user_id', TRUE)::uuid
                          AND is_active = TRUE
                    )
                )
            )
            WITH CHECK (
                current_setting('app.current_user_id', TRUE) = 'ADMIN'
                OR (
                    current_setting('app.current_user_id', TRUE)
                        ~* '^[0-9a-f]{{8}}-[0-9a-f]{{4}}-[0-9a-f]{{4}}-[0-9a-f]{{4}}-[0-9a-f]{{12}}$'
                    AND company_id IN (
                        SELECT company_id FROM company_user_access
                        WHERE user_id = current_setting('app.current_user_id', TRUE)::uuid
                          AND is_active = TRUE
                    )
                )
            )
        """)

    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_articles_event_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'Articles verification events are append-only';
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER articles_verification_events_append_only
        BEFORE UPDATE OR DELETE ON articles_verification_events
        FOR EACH ROW EXECUTE FUNCTION prevent_articles_event_mutation()
    """)
    op.execute("""
        CREATE OR REPLACE FUNCTION protect_articles_verification_source()
        RETURNS trigger AS $$
        BEGIN
            IF NEW.company_id IS DISTINCT FROM OLD.company_id
               OR NEW.document_id IS DISTINCT FROM OLD.document_id
               OR NEW.source_checksum_sha256 IS DISTINCT FROM OLD.source_checksum_sha256
               OR NEW.source_document_version IS DISTINCT FROM OLD.source_document_version
               OR NEW.submitted_by IS DISTINCT FROM OLD.submitted_by
               OR NEW.submitted_at IS DISTINCT FROM OLD.submitted_at THEN
                RAISE EXCEPTION 'Articles verification source identity is immutable';
            END IF;

            IF OLD.status <> 'PENDING' AND (
                NEW.reviewed_by IS DISTINCT FROM OLD.reviewed_by
                OR NEW.reviewed_at IS DISTINCT FROM OLD.reviewed_at
                OR NEW.effective_from IS DISTINCT FROM OLD.effective_from
                OR NEW.quorum_variation_exists IS DISTINCT FROM OLD.quorum_variation_exists
                OR NEW.quorum_required IS DISTINCT FROM OLD.quorum_required
                OR NEW.clause_reference IS DISTINCT FROM OLD.clause_reference
                OR NEW.reviewer_note IS DISTINCT FROM OLD.reviewer_note
            ) THEN
                RAISE EXCEPTION 'Articles reviewer decision is immutable after review';
            END IF;

            IF OLD.status = 'PENDING' AND NEW.status NOT IN ('PENDING', 'VERIFIED', 'REJECTED') THEN
                RAISE EXCEPTION 'Invalid Articles verification transition';
            ELSIF OLD.status = 'VERIFIED' AND NEW.status NOT IN ('VERIFIED', 'REVOKED', 'SUPERSEDED') THEN
                RAISE EXCEPTION 'Invalid Articles verification transition';
            ELSIF OLD.status IN ('REJECTED', 'REVOKED', 'SUPERSEDED') AND NEW.status <> OLD.status THEN
                RAISE EXCEPTION 'Terminal Articles verification state cannot be reopened';
            END IF;

            IF OLD.status IN ('REJECTED', 'REVOKED', 'SUPERSEDED') AND (
                NEW.revoked_by IS DISTINCT FROM OLD.revoked_by
                OR NEW.revoked_at IS DISTINCT FROM OLD.revoked_at
                OR NEW.revocation_reason IS DISTINCT FROM OLD.revocation_reason
            ) THEN
                RAISE EXCEPTION 'Terminal Articles verification metadata is immutable';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER articles_verification_source_immutable
        BEFORE UPDATE ON articles_verifications
        FOR EACH ROW EXECUTE FUNCTION protect_articles_verification_source()
    """)
    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_articles_verification_delete()
        RETURNS trigger AS $
        BEGIN
            RAISE EXCEPTION 'Articles verification records are retained as legal evidence';
        END;
        $ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER articles_verifications_no_delete
        BEFORE DELETE ON articles_verifications
        FOR EACH ROW EXECUTE FUNCTION prevent_articles_verification_delete()
    """)


def downgrade():
    # Forward-only: retain legal verification and audit evidence.
    pass
", name="ck_articles_verifications_checksum"),
        sa.CheckConstraint("source_document_version >= 1", name="ck_articles_verifications_document_version"),
        sa.CheckConstraint("quorum_required IS NULL OR quorum_required BETWEEN 1 AND 100", name="ck_articles_verifications_quorum"),
        sa.CheckConstraint("quorum_variation_exists = FALSE OR quorum_required IS NOT NULL", name="ck_articles_verifications_variation_quorum"),
        sa.CheckConstraint(
            "(status = 'PENDING' AND reviewed_by IS NULL AND reviewed_at IS NULL) OR "
            "(status IN ('VERIFIED', 'REJECTED', 'REVOKED', 'SUPERSEDED') AND reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)",
            name="ck_articles_verifications_review_metadata",
        ),
        sa.CheckConstraint(
            "(status = 'REVOKED' AND revoked_by IS NOT NULL AND revoked_at IS NOT NULL AND revocation_reason IS NOT NULL) OR "
            "(status <> 'REVOKED' AND revoked_by IS NULL AND revoked_at IS NULL AND revocation_reason IS NULL)",
            name="ck_articles_verifications_revocation_metadata",
        ),
    )
    op.create_index("ix_articles_verifications_company_id", "articles_verifications", ["company_id"])
    op.create_index("ix_articles_verifications_document_id", "articles_verifications", ["document_id"])
    op.create_index("ix_articles_verifications_status", "articles_verifications", ["status"])
    op.create_index(
        "uq_articles_verifications_pending", "articles_verifications", ["company_id"],
        unique=True, postgresql_where=sa.text("status = 'PENDING'"),
    )
    op.create_index(
        "uq_articles_verifications_verified", "articles_verifications", ["company_id"],
        unique=True, postgresql_where=sa.text("status = 'VERIFIED'"),
    )

    op.create_table(
        "articles_verification_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("verification_id", UUID(as_uuid=True), sa.ForeignKey("articles_verifications.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("actor_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("previous_status", sa.String(20), nullable=True),
        sa.Column("new_status", sa.String(20), nullable=False),
        sa.Column("source_checksum_sha256", sa.String(64), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("action IN ('SUBMITTED', 'VERIFIED', 'REJECTED', 'REVOKED', 'SUPERSEDED')", name="ck_articles_verification_events_action"),
    )
    op.create_index("ix_articles_verification_events_company_id", "articles_verification_events", ["company_id"])
    op.create_index("ix_articles_verification_events_verification_id", "articles_verification_events", ["verification_id"])

    for table in ("articles_verifications", "articles_verification_events"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"""
            CREATE POLICY {table}_company_policy ON {table}
            USING (
                current_setting('app.current_user_id', TRUE) = 'ADMIN'
                OR (
                    current_setting('app.current_user_id', TRUE)
                        ~* '^[0-9a-f]{{8}}-[0-9a-f]{{4}}-[0-9a-f]{{4}}-[0-9a-f]{{4}}-[0-9a-f]{{12}}$'
                    AND company_id IN (
                        SELECT company_id FROM company_user_access
                        WHERE user_id = current_setting('app.current_user_id', TRUE)::uuid
                          AND is_active = TRUE
                    )
                )
            )
            WITH CHECK (
                current_setting('app.current_user_id', TRUE) = 'ADMIN'
                OR (
                    current_setting('app.current_user_id', TRUE)
                        ~* '^[0-9a-f]{{8}}-[0-9a-f]{{4}}-[0-9a-f]{{4}}-[0-9a-f]{{4}}-[0-9a-f]{{12}}$'
                    AND company_id IN (
                        SELECT company_id FROM company_user_access
                        WHERE user_id = current_setting('app.current_user_id', TRUE)::uuid
                          AND is_active = TRUE
                    )
                )
            )
        """)

    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_articles_event_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'Articles verification events are append-only';
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER articles_verification_events_append_only
        BEFORE UPDATE OR DELETE ON articles_verification_events
        FOR EACH ROW EXECUTE FUNCTION prevent_articles_event_mutation()
    """)
    op.execute("""
        CREATE OR REPLACE FUNCTION protect_articles_verification_source()
        RETURNS trigger AS $$
        BEGIN
            IF NEW.company_id IS DISTINCT FROM OLD.company_id
               OR NEW.document_id IS DISTINCT FROM OLD.document_id
               OR NEW.source_checksum_sha256 IS DISTINCT FROM OLD.source_checksum_sha256
               OR NEW.source_document_version IS DISTINCT FROM OLD.source_document_version
               OR NEW.submitted_by IS DISTINCT FROM OLD.submitted_by
               OR NEW.submitted_at IS DISTINCT FROM OLD.submitted_at THEN
                RAISE EXCEPTION 'Articles verification source identity is immutable';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER articles_verification_source_immutable
        BEFORE UPDATE ON articles_verifications
        FOR EACH ROW EXECUTE FUNCTION protect_articles_verification_source()
    """)


def downgrade():
    # Forward-only: retain legal verification and audit evidence.
    pass
