"""Add product-owner controlled legal provenance and deadline registry.

Revision ID: 0109_product_owner_legal_provenance
Revises: 0108_audit_legal_rule_registry_inventory

Product-owner release is deliberately separate from statutory legal verification.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0109_product_owner_legal_provenance"
down_revision = "0108_audit_legal_rule_registry_inventory"
branch_labels = None
depends_on = None


def _apply_registry_rls(table: str) -> None:
    """Jurisdiction-wide catalog: signed users read; authenticated SUPER_ADMIN writes."""
    op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE public.{table} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY {table}_read_policy ON public.{table} "
        "FOR SELECT USING ("
        "public.nlc_current_user_context_valid() "
        "AND public.nlc_current_user_id() IS NOT NULL)"
    )
    op.execute(
        f"CREATE POLICY {table}_insert_policy ON public.{table} "
        "FOR INSERT WITH CHECK ("
        "public.nlc_current_user_context_valid() "
        "AND public.nlc_current_user_is_super_admin())"
    )
    op.execute(f"REVOKE ALL ON TABLE public.{table} FROM PUBLIC")
    op.execute(f"GRANT SELECT, INSERT ON TABLE public.{table} TO nlc_app_role")


def upgrade() -> None:
    op.create_table(
        "legal_sources",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("source_key", sa.String(120), nullable=False),
        sa.Column("jurisdiction", sa.String(20), nullable=False, server_default="BD"),
        sa.Column("instrument_title", sa.String(500), nullable=False),
        sa.Column("issuing_authority", sa.String(250), nullable=False),
        sa.Column("instrument_type", sa.String(80), nullable=False),
        sa.Column("official_url", sa.Text(), nullable=False),
        sa.Column("citation", sa.Text(), nullable=False),
        sa.Column("version_label", sa.String(120), nullable=False),
        sa.Column("publication_date", sa.Date(), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("artifact_sha256", sa.String(64), nullable=True),
        sa.Column("artifact_uri", sa.Text(), nullable=True),
        sa.Column(
            "created_by", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.func.now(),
        ),
        sa.CheckConstraint("length(btrim(source_key)) > 0", name="ck_legal_sources_key"),
        sa.CheckConstraint("length(btrim(official_url)) > 0", name="ck_legal_sources_url"),
        sa.CheckConstraint("length(btrim(citation)) > 0", name="ck_legal_sources_citation"),
        sa.CheckConstraint("length(btrim(version_label)) > 0", name="ck_legal_sources_version"),
        sa.CheckConstraint(
            "(artifact_sha256 IS NULL AND artifact_uri IS NULL) OR "
            "(artifact_sha256 ~ '^[0-9a-f]{64}$' AND artifact_uri IS NOT NULL "
            "AND length(btrim(artifact_uri)) > 0)",
            name="ck_legal_sources_artifact_pair",
        ),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from",
            name="ck_legal_sources_effective_interval",
        ),
        sa.UniqueConstraint("source_key", "version_label", name="uq_legal_sources_key_version"),
    )
    op.create_index("ix_legal_sources_jurisdiction", "legal_sources", ["jurisdiction"])
    op.create_index("ix_legal_sources_authority", "legal_sources", ["issuing_authority"])

    op.create_table(
        "legal_rule_source_mappings",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "rule_id", sa.String(50),
            sa.ForeignKey("legal_rules.rule_id", ondelete="RESTRICT"), nullable=False,
        ),
        sa.Column(
            "source_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("legal_sources.id", ondelete="RESTRICT"), nullable=False,
        ),
        sa.Column("mapping_kind", sa.String(40), nullable=False),
        sa.Column("provision_citation", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column(
            "created_by", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "mapping_kind IN ('RULE_BASIS','DEADLINE_BASIS','PENALTY_BASIS')",
            name="ck_legal_mapping_kind",
        ),
        sa.CheckConstraint(
            "length(btrim(provision_citation)) > 0",
            name="ck_legal_mapping_citation",
        ),
        sa.CheckConstraint(
            "length(btrim(rationale)) >= 10",
            name="ck_legal_mapping_rationale",
        ),
        sa.UniqueConstraint(
            "rule_id", "source_id", "mapping_kind", "provision_citation",
            name="uq_legal_rule_source_mapping",
        ),
    )
    op.create_index("ix_legal_mapping_rule_id", "legal_rule_source_mappings", ["rule_id"])
    op.create_index("ix_legal_mapping_source_id", "legal_rule_source_mappings", ["source_id"])

    op.create_table(
        "legal_deadline_definitions",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "rule_id", sa.String(50),
            sa.ForeignKey("legal_rules.rule_id", ondelete="RESTRICT"), nullable=False,
        ),
        sa.Column(
            "source_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("legal_sources.id", ondelete="RESTRICT"), nullable=False,
        ),
        sa.Column(
            "mapping_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("legal_rule_source_mappings.id", ondelete="RESTRICT"), nullable=False,
        ),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("trigger_fact_key", sa.String(120), nullable=False),
        sa.Column("period_label", sa.String(100), nullable=False),
        sa.Column("offset", sa.Integer(), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("adjustment", sa.String(20), nullable=False, server_default="NONE"),
        sa.Column(
            "exclude_trigger_day", sa.Boolean(), nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("holiday_calendar_version", sa.String(100), nullable=True),
        sa.Column("holiday_source_citation", sa.Text(), nullable=True),
        sa.Column(
            "holidays", postgresql.JSONB(astext_type=sa.Text()),
            nullable=False, server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "created_by", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "event_type IN ('FIRST_AGM','SUBSEQUENT_AGM','ANNUAL_RETURN',"
            "'AUDITOR_APPOINTMENT','FORM_XII','BOARD_MEETING','FINANCIAL_STATEMENTS',"
            "'TRADE_LICENSE','TAX_RETURN','OTHER')",
            name="ck_legal_deadline_event_type",
        ),
        sa.CheckConstraint('"offset" >= 0', name="ck_legal_deadline_offset"),
        sa.CheckConstraint(
            "unit IN ('DAYS','CLEAR_DAYS','MONTHS','YEARS')",
            name="ck_legal_deadline_unit",
        ),
        sa.CheckConstraint(
            "adjustment IN ('NONE','FOLLOWING','PRECEDING')",
            name="ck_legal_deadline_adjustment",
        ),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="ck_legal_deadline_effective_interval",
        ),
        sa.CheckConstraint(
            "length(btrim(trigger_fact_key)) > 0",
            name="ck_legal_deadline_trigger_fact_key",
        ),
        sa.CheckConstraint(
            "length(btrim(period_label)) > 0",
            name="ck_legal_deadline_period_label",
        ),
        sa.CheckConstraint(
            "holidays = '[]'::jsonb OR "
            "(holiday_calendar_version IS NOT NULL AND holiday_source_citation IS NOT NULL)",
            name="ck_legal_deadline_holiday_provenance",
        ),
    )
    op.create_index("ix_legal_deadline_rule_id", "legal_deadline_definitions", ["rule_id"])
    op.create_index(
        "ix_legal_deadline_mapping_id", "legal_deadline_definitions", ["mapping_id"]
    )

    op.create_table(
        "legal_rule_release_events",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("release_scope", sa.String(20), nullable=True),
        sa.Column("decision", sa.String(20), nullable=True),
        sa.Column(
            "rule_id", sa.String(50),
            sa.ForeignKey("legal_rules.rule_id", ondelete="RESTRICT"), nullable=True,
        ),
        sa.Column(
            "source_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("legal_sources.id", ondelete="RESTRICT"), nullable=True,
        ),
        sa.Column(
            "mapping_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("legal_rule_source_mappings.id", ondelete="RESTRICT"), nullable=True,
        ),
        sa.Column(
            "deadline_definition_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("legal_deadline_definitions.id", ondelete="RESTRICT"), nullable=True,
        ),
        sa.Column(
            "actor_id", postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False,
        ),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "event_metadata", postgresql.JSONB(astext_type=sa.Text()),
            nullable=False, server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("previous_event_hash", sa.String(64), nullable=True),
        sa.Column("event_hash", sa.String(64), nullable=False),
        sa.Column("sequence_no", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True),
            nullable=False, server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "event_type IN ('SOURCE_REGISTERED','RULE_SOURCE_MAPPED',"
            "'DEADLINE_RULE_REGISTERED','PRODUCT_OWNER_APPROVED','PRODUCT_OWNER_REVOKED')",
            name="ck_legal_release_event_type",
        ),
        sa.CheckConstraint(
            "release_scope IS NULL OR release_scope IN ('SCORING','DEADLINE')",
            name="ck_legal_release_scope",
        ),
        sa.CheckConstraint(
            "decision IS NULL OR decision IN ('APPROVED','REVOKED')",
            name="ck_legal_release_decision",
        ),
        sa.CheckConstraint(
            "length(btrim(reason)) >= 10",
            name="ck_legal_release_reason",
        ),
        sa.CheckConstraint(
            "event_hash ~ '^[0-9a-f]{64}$'",
            name="ck_legal_release_hash",
        ),
        sa.CheckConstraint(
            "previous_event_hash IS NULL OR previous_event_hash ~ '^[0-9a-f]{64}$'",
            name="ck_legal_release_previous_hash",
        ),
        sa.CheckConstraint(
            "(event_type = 'SOURCE_REGISTERED' AND source_id IS NOT NULL) OR "
            "(event_type = 'RULE_SOURCE_MAPPED' AND rule_id IS NOT NULL "
            "AND source_id IS NOT NULL AND mapping_id IS NOT NULL) OR "
            "(event_type = 'DEADLINE_RULE_REGISTERED' AND rule_id IS NOT NULL "
            "AND source_id IS NOT NULL AND mapping_id IS NOT NULL "
            "AND deadline_definition_id IS NOT NULL) OR "
            "(event_type IN ('PRODUCT_OWNER_APPROVED','PRODUCT_OWNER_REVOKED') "
            "AND rule_id IS NOT NULL AND source_id IS NOT NULL "
            "AND mapping_id IS NOT NULL AND release_scope IS NOT NULL "
            "AND decision IS NOT NULL)",
            name="ck_legal_release_event_shape",
        ),
        sa.UniqueConstraint("event_hash", name="uq_legal_release_event_hash"),
        sa.UniqueConstraint("sequence_no", name="uq_legal_release_sequence"),
    )
    op.create_index(
        "ix_legal_release_events_rule_scope_sequence",
        "legal_rule_release_events", ["rule_id", "release_scope", "sequence_no"],
    )

    # Bind audit actor columns to the authenticated signed user identity.
    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_enforce_legal_provenance_actor()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path TO 'pg_catalog', 'public'
        AS $function$
        DECLARE
            supplied_actor uuid;
        BEGIN
            supplied_actor := NULLIF(to_jsonb(NEW)->>TG_ARGV[0], '')::uuid;
            IF supplied_actor IS NULL
               OR supplied_actor IS DISTINCT FROM public.nlc_current_user_id()
               OR NOT public.nlc_current_user_is_super_admin() THEN
                RAISE EXCEPTION 'legal provenance insert requires actor-bound SUPER_ADMIN identity'
                    USING ERRCODE = '42501';
            END IF;
            RETURN NEW;
        END
        $function$
    """)
    op.execute(
        "REVOKE ALL ON FUNCTION public.nlc_enforce_legal_provenance_actor() FROM PUBLIC"
    )

    for table, actor_column in (
        ("legal_sources", "created_by"),
        ("legal_rule_source_mappings", "created_by"),
        ("legal_deadline_definitions", "created_by"),
        ("legal_rule_release_events", "actor_id"),
    ):
        op.execute(
            f"CREATE TRIGGER {table}_actor_guard BEFORE INSERT ON public.{table} "
            f"FOR EACH ROW EXECUTE FUNCTION "
            f"public.nlc_enforce_legal_provenance_actor('{actor_column}')"
        )

    # The event predecessor is checked in PostgreSQL as well as serialized by
    # the API advisory lock, preventing a privileged direct insert from forking the chain.
    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_validate_legal_release_chain()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path TO 'pg_catalog', 'public'
        AS $function$
        DECLARE
            expected_previous text;
        BEGIN
            PERFORM pg_advisory_xact_lock(741113, 1);
            SELECT event_hash
              INTO expected_previous
              FROM public.legal_rule_release_events
             ORDER BY sequence_no DESC
             LIMIT 1;
            IF NEW.previous_event_hash IS DISTINCT FROM expected_previous THEN
                RAISE EXCEPTION 'legal release event predecessor hash mismatch'
                    USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END
        $function$
    """)
    op.execute(
        "REVOKE ALL ON FUNCTION public.nlc_validate_legal_release_chain() FROM PUBLIC"
    )
    op.execute("""
        CREATE TRIGGER legal_rule_release_events_chain_guard
        BEFORE INSERT ON public.legal_rule_release_events
        FOR EACH ROW
        EXECUTE FUNCTION public.nlc_validate_legal_release_chain()
    """)

    # Every provenance row is append-only. Corrections create new versions/events.
    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_reject_legal_provenance_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path TO 'pg_catalog', 'public'
        AS $function$
        BEGIN
            RAISE EXCEPTION 'legal provenance is append-only; record a correction or new version'
                USING ERRCODE = '55000';
        END
        $function$
    """)
    op.execute(
        "REVOKE ALL ON FUNCTION public.nlc_reject_legal_provenance_mutation() FROM PUBLIC"
    )
    for table in (
        "legal_sources",
        "legal_rule_source_mappings",
        "legal_deadline_definitions",
        "legal_rule_release_events",
    ):
        op.execute(
            f"CREATE TRIGGER {table}_reject_mutation BEFORE UPDATE OR DELETE "
            f"ON public.{table} FOR EACH ROW "
            "EXECUTE FUNCTION public.nlc_reject_legal_provenance_mutation()"
        )
        op.execute(
            f"CREATE TRIGGER {table}_reject_truncate BEFORE TRUNCATE "
            f"ON public.{table} FOR EACH STATEMENT "
            "EXECUTE FUNCTION public.nlc_reject_legal_provenance_mutation()"
        )

    for table in (
        "legal_sources",
        "legal_rule_source_mappings",
        "legal_deadline_definitions",
        "legal_rule_release_events",
    ):
        _apply_registry_rls(table)


def downgrade() -> None:
    # Forward-only: the release ledger is audit evidence and is not destructively downgraded.
    pass
