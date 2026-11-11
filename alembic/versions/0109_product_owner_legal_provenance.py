"""Add product-owner legal provenance and deadline definitions.

Revision ID: 0109_product_owner_legal_provenance
Revises: 0108_audit_legal_rule_registry_inventory

Product-owner release decisions are recorded independently of statutory/legal
verification. No legal_rules.verification_status is changed by this migration.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0109_product_owner_legal_provenance"
down_revision = "0108_audit_legal_rule_registry_inventory"
branch_labels = None
depends_on = None


def _apply_rls(table: str, select_policy: str, insert_policy: str) -> None:
    op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE public.{table} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY {table}_read_policy ON public.{table} "
        f"FOR SELECT USING ({select_policy})"
    )
    op.execute(
        f"CREATE POLICY {table}_insert_policy ON public.{table} "
        f"FOR INSERT WITH CHECK ({insert_policy})"
    )
    op.execute(f"REVOKE ALL ON TABLE public.{table} FROM PUBLIC")
    op.execute(f"GRANT SELECT, INSERT ON TABLE public.{table} TO nlc_app_role")


def upgrade() -> None:
    op.create_table(
        "legal_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
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
        sa.Column("created_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
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
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("rule_id", sa.String(50),
                  sa.ForeignKey("legal_rules.rule_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("legal_sources.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("mapping_kind", sa.String(40), nullable=False),
        sa.Column("provision_citation", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "mapping_kind IN ('RULE_BASIS', 'DEADLINE_BASIS', 'PENALTY_BASIS')",
            name="ck_legal_mapping_kind",
        ),
        sa.CheckConstraint("length(btrim(provision_citation)) > 0",
                           name="ck_legal_mapping_citation"),
        sa.CheckConstraint("length(btrim(rationale)) >= 10",
                           name="ck_legal_mapping_rationale"),
        sa.UniqueConstraint(
            "rule_id", "source_id", "mapping_kind", "provision_citation",
            name="uq_legal_rule_source_mapping",
        ),
    )
    op.create_index("ix_legal_mapping_rule_id", "legal_rule_source_mappings", ["rule_id"])
    op.create_index("ix_legal_mapping_source_id", "legal_rule_source_mappings", ["source_id"])

    op.create_table(
        "legal_deadline_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("rule_id", sa.String(50),
                  sa.ForeignKey("legal_rules.rule_id", ondelete="RESTRICT"), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("legal_sources.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("mapping_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("legal_rule_source_mappings.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("trigger_fact_key", sa.String(120), nullable=False),
        sa.Column("period_label", sa.String(100), nullable=False),
        sa.Column("offset", sa.Integer(), nullable=False),
        sa.Column("unit", sa.String(20), nullable=False),
        sa.Column("adjustment", sa.String(20), nullable=False, server_default="NONE"),
        sa.Column("exclude_trigger_day", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("holiday_calendar_version", sa.String(100), nullable=True),
        sa.Column("holiday_source_citation", sa.Text(), nullable=True),
        sa.Column("holidays", postgresql.JSONB(astext_type=sa.Text()),
                  nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "event_type IN ('FIRST_AGM','SUBSEQUENT_AGM','ANNUAL_RETURN',"
            "'AUDITOR_APPOINTMENT','FORM_XII','BOARD_MEETING','FINANCIAL_STATEMENTS',"
            "'TRADE_LICENSE','TAX_RETURN','OTHER')",
            name="ck_legal_deadline_event_type",
        ),
        sa.CheckConstraint("offset >= 0", name="ck_legal_deadline_offset"),
        sa.CheckConstraint("unit IN ('DAYS','CLEAR_DAYS','MONTHS','YEARS')",
                           name="ck_legal_deadline_unit"),
        sa.CheckConstraint("adjustment IN ('NONE','FOLLOWING','PRECEDING')",
                           name="ck_legal_deadline_adjustment"),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="ck_legal_deadline_effective_interval",
        ),
        sa.CheckConstraint("length(btrim(trigger_fact_key)) > 0",
                           name="ck_legal_deadline_trigger_fact_key"),
        sa.CheckConstraint("length(btrim(period_label)) > 0",
                           name="ck_legal_deadline_period_label"),
    )
    op.create_index("ix_legal_deadline_rule_id", "legal_deadline_definitions", ["rule_id"])
    op.create_index("ix_legal_deadline_mapping_id", "legal_deadline_definitions", ["mapping_id"])

    op.create_table(
        "legal_rule_release_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("release_scope", sa.String(20), nullable=True),
        sa.Column("decision", sa.String(20), nullable=True),
        sa.Column("rule_id", sa.String(50),
                  sa.ForeignKey("legal_rules.rule_id", ondelete="RESTRICT"), nullable=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("legal_sources.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("mapping_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("legal_rule_source_mappings.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("deadline_definition_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("legal_deadline_definitions.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("event_metadata", postgresql.JSONB(astext_type=sa.Text()),
                  nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("previous_event_hash", sa.String(64), nullable=True),
        sa.Column("event_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  nullable=False, server_default=sa.func.now()),
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
        sa.CheckConstraint("length(btrim(reason)) >= 10", name="ck_legal_release_reason"),
        sa.CheckConstraint("event_hash ~ '^[0-9a-f]{64}$'", name="ck_legal_release_hash"),
        sa.CheckConstraint(
            "previous_event_hash IS NULL OR previous_event_hash ~ '^[0-9a-f]{64}$'",
            name="ck_legal_release_previous_hash",
        ),
    )
    op.create_index(
        "ix_legal_release_events_rule_scope_created",
        "legal_rule_release_events", ["rule_id", "release_scope", "created_at"],
    )

    # All four registries are immutable after insertion. Corrections are new
    # versions/events, never UPDATE or DELETE.
    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_reject_legal_provenance_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path TO 'pg_catalog', 'public'
        AS $function$
        BEGIN
            RAISE EXCEPTION 'legal provenance records are append-only; create a correction/version event'
                USING ERRCODE = '55000';
        END
        $function$
    """)
    op.execute("REVOKE ALL ON FUNCTION public.nlc_reject_legal_provenance_mutation() FROM PUBLIC")
    for table in (
        "legal_sources",
        "legal_rule_source_mappings",
        "legal_deadline_definitions",
        "legal_rule_release_events",
    ):
        op.execute(
            f"CREATE TRIGGER {table}_reject_mutation "
            f"BEFORE UPDATE OR DELETE ON public.{table} "
            "FOR EACH ROW EXECUTE FUNCTION public.nlc_reject_legal_provenance_mutation()"
        )
        op.execute(
            f"CREATE TRIGGER {table}_reject_truncate "
            f"BEFORE TRUNCATE ON public.{table} "
            "FOR EACH STATEMENT EXECUTE FUNCTION public.nlc_reject_legal_provenance_mutation()"
        )

    read_sources = (
        "public.nlc_current_user_context_valid() AND "
        "(public.nlc_current_user_principal() IN ('AUTH','CATALOG') "
        "OR public.nlc_current_user_is_rule_admin())"
    )
    read_admin = "public.nlc_current_user_is_rule_admin()"
    insert_admin = "public.nlc_current_user_is_super_admin()"
    _apply_rls("legal_sources", read_sources, insert_admin)
    _apply_rls("legal_rule_source_mappings", read_admin, insert_admin)
    _apply_rls("legal_deadline_definitions", read_admin, insert_admin)
    _apply_rls("legal_rule_release_events", read_admin, insert_admin)


def downgrade() -> None:
    # Forward-only: this records governance and release decisions. Removing it
    # would destroy audit provenance.
    pass
