"""Add append-only, globally governed finding-context catalogue.

Revision ID: 0120_governed_finding_context_catalog
Revises: 0119_finding_payload_digest_verification

Context versions and legal-review decisions are immutable records. Runtime
users may read under signed RLS; only trusted ADMIN/CATALOG service principals
may append catalogue and review records. No statutory scoring is activated.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0120_governed_finding_context_catalog"
down_revision = "0119_finding_payload_digest_verification"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.create_table(
        "legal_rule_finding_contexts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("historical_rule_id", sa.String(100), nullable=False),
        sa.Column("catalog_version", sa.String(100), nullable=False),
        sa.Column("source_namespace", sa.String(255), nullable=False),
        sa.Column("jurisdiction", sa.String(32), nullable=False),
        sa.Column("source_instrument", sa.String(500), nullable=False),
        sa.Column("source_provision", sa.String(255), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("effective_date_basis", sa.Text(), nullable=False),
        sa.Column("effective_date_source_ref", sa.String(1000), nullable=False),
        sa.Column("context_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("context_canonical", sa.Text(), nullable=False),
        sa.Column("context_sha256", sa.String(64), nullable=False),
        sa.Column("authored_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("authored_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("historical_rule_id", "catalog_version",
                            name="uq_legal_finding_context_rule_version"),
        sa.CheckConstraint("length(btrim(historical_rule_id)) > 0 AND "
                           "length(btrim(catalog_version)) > 0 AND "
                           "length(btrim(source_namespace)) > 0 AND "
                           "length(btrim(jurisdiction)) > 0 AND "
                           "length(btrim(source_instrument)) > 0 AND "
                           "length(btrim(source_provision)) > 0 AND "
                           "length(btrim(effective_date_basis)) > 0 AND "
                           "length(btrim(effective_date_source_ref)) > 0",
                           name="ck_legal_finding_context_required_text"),
        sa.CheckConstraint("context_sha256 ~ '^[0-9a-f]{64}$'",
                           name="ck_legal_finding_context_digest"),
    )
    op.create_index(
        "ix_legal_finding_context_lookup",
        "legal_rule_finding_contexts",
        ["historical_rule_id", "source_namespace", "jurisdiction", "catalog_version"],
    )

    op.create_table(
        "legal_rule_finding_context_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("context_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("legal_rule_finding_contexts.id", ondelete="RESTRICT"),
                  nullable=False),
        sa.Column("review_status", sa.String(20), nullable=False),
        sa.Column("reviewed_context_sha256", sa.String(64), nullable=False),
        sa.Column("review_basis", sa.Text(), nullable=False),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.CheckConstraint("review_status IN ('APPROVED','REJECTED','REVOKED')",
                           name="ck_legal_finding_context_review_status"),
        sa.CheckConstraint("reviewed_context_sha256 ~ '^[0-9a-f]{64}$'",
                           name="ck_legal_finding_context_review_digest"),
        sa.CheckConstraint("length(btrim(review_basis)) > 0",
                           name="ck_legal_finding_context_review_basis"),
    )
    op.create_index(
        "ix_legal_finding_context_reviews_latest",
        "legal_rule_finding_context_reviews", ["context_id", "reviewed_at", "id"],
    )

    op.execute("""
        CREATE FUNCTION public.nlc_verify_legal_finding_context()
        RETURNS trigger LANGUAGE plpgsql
        SET search_path = pg_catalog, public, extensions
        AS $function$
        BEGIN
            IF encode(digest(convert_to(NEW.context_canonical, 'UTF8'), 'sha256'), 'hex')
                   IS DISTINCT FROM NEW.context_sha256
               OR NEW.context_canonical::jsonb IS DISTINCT FROM NEW.context_snapshot
               OR NEW.context_snapshot ->> 'historical_rule_id' IS DISTINCT FROM NEW.historical_rule_id
               OR NEW.context_snapshot ->> 'source_namespace' IS DISTINCT FROM NEW.source_namespace
               OR NEW.context_snapshot ->> 'jurisdiction' IS DISTINCT FROM NEW.jurisdiction
               OR NEW.context_snapshot ->> 'effective_date' IS DISTINCT FROM NEW.effective_date::text
               OR NEW.context_snapshot ->> 'effective_date_basis' IS DISTINCT FROM NEW.effective_date_basis
               OR NEW.context_snapshot ->> 'effective_date_source_ref' IS DISTINCT FROM NEW.effective_date_source_ref
               OR NEW.context_snapshot ->> 'source_instrument' IS DISTINCT FROM NEW.source_instrument
               OR NEW.context_snapshot ->> 'source_provision' IS DISTINCT FROM NEW.source_provision THEN
                RAISE EXCEPTION 'Legal finding context payload, metadata or digest mismatch';
            END IF;
            RETURN NEW;
        END;
        $function$
    """)
    op.execute("""
        CREATE TRIGGER trg_legal_finding_context_verify
        BEFORE INSERT ON public.legal_rule_finding_contexts
        FOR EACH ROW EXECUTE FUNCTION public.nlc_verify_legal_finding_context()
    """)
    op.execute("""
        CREATE FUNCTION public.nlc_verify_legal_finding_context_review()
        RETURNS trigger LANGUAGE plpgsql
        SET search_path = pg_catalog, public
        AS $function$
        DECLARE context_author uuid; context_digest text;
        BEGIN
            SELECT authored_by, context_sha256
              INTO context_author, context_digest
              FROM public.legal_rule_finding_contexts
             WHERE id = NEW.context_id;
            IF context_author IS NULL THEN
                RAISE EXCEPTION 'Finding context review references missing context';
            END IF;
            IF NEW.reviewed_by = context_author THEN
                RAISE EXCEPTION 'Finding context author cannot independently review own context';
            END IF;
            IF NEW.reviewed_context_sha256 IS DISTINCT FROM context_digest THEN
                RAISE EXCEPTION 'Finding context review digest does not match exact context version';
            END IF;
            RETURN NEW;
        END;
        $function$
    """)
    op.execute("""
        CREATE TRIGGER trg_legal_finding_context_review_verify
        BEFORE INSERT ON public.legal_rule_finding_context_reviews
        FOR EACH ROW EXECUTE FUNCTION public.nlc_verify_legal_finding_context_review()
    """)
    op.execute("""
        CREATE FUNCTION public.nlc_prevent_finding_context_mutation()
        RETURNS trigger LANGUAGE plpgsql
        AS $function$
        BEGIN
            RAISE EXCEPTION 'Governed finding context records are append-only; create a new version or review event';
        END;
        $function$
    """)
    for table in ("legal_rule_finding_contexts", "legal_rule_finding_context_reviews"):
        op.execute(f"""
            CREATE TRIGGER trg_{table}_append_only
            BEFORE UPDATE OR DELETE ON public.{table}
            FOR EACH ROW EXECUTE FUNCTION public.nlc_prevent_finding_context_mutation()
        """)
        op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE public.{table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {table}_signed_read ON public.{table} "
            "FOR SELECT TO nlc_app_role USING (public.nlc_current_user_context_valid() "
            "AND (public.nlc_current_user_id() IS NOT NULL "
            "OR public.nlc_current_user_principal() IN ('ADMIN','CATALOG')))"
        )
        op.execute(
            f"CREATE POLICY {table}_trusted_insert ON public.{table} "
            "FOR INSERT TO nlc_app_role WITH CHECK (public.nlc_current_user_context_valid() "
            "AND public.nlc_current_user_principal() IN ('ADMIN','CATALOG'))"
        )
        op.execute(
            f"REVOKE ALL PRIVILEGES ON TABLE public.{table} "
            "FROM PUBLIC, nlc_app_role, nlc_ci_audit_role"
        )
        op.execute(f"GRANT SELECT, INSERT ON TABLE public.{table} TO nlc_app_role")

    for function_name in (
        "public.nlc_verify_legal_finding_context()",
        "public.nlc_verify_legal_finding_context_review()",
        "public.nlc_prevent_finding_context_mutation()",
    ):
        op.execute(f"REVOKE ALL ON FUNCTION {function_name} FROM PUBLIC")
        op.execute(f"GRANT EXECUTE ON FUNCTION {function_name} TO nlc_app_role")


def downgrade() -> None:
    raise RuntimeError(
        "0120 is forward-only: governed legal context and review history "
        "must not be destructively removed."
    )
