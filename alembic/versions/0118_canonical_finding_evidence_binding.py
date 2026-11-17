"""Bind each compliance finding to immutable canonical rule and evidence snapshots.

Revision ID: 0118_canonical_finding_evidence_binding
Revises: 0117_canonical_registry_runtime_read

No legacy finding is backfilled. New binding rows are append-only and
tenant-scoped. Identity resolution is distinct from legal approval,
evidence sufficiency, historical attribution, and scoring eligibility.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB

revision = "0118_canonical_finding_evidence_binding"
down_revision = "0117_canonical_registry_runtime_read"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "compliance_finding_bindings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("company_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("compliance_flag_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("compliance_flags.id", ondelete="RESTRICT"),
                  nullable=False),
        sa.Column("evaluation_run_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("compliance_evaluation_runs.id", ondelete="RESTRICT"),
                  nullable=False),
        sa.Column("jurisdiction", sa.String(32), nullable=False),
        sa.Column("source_namespace", sa.String(255), nullable=False),
        sa.Column("historical_rule_id", sa.String(100), nullable=False),
        sa.Column("resolution_status", sa.String(40), nullable=False),
        sa.Column("attribution_status", sa.String(24), nullable=False,
                  server_default="CURRENT_EVALUATION"),
        sa.Column("attribution_basis", sa.Text(), nullable=True),
        sa.Column("attribution_evidence_hash", sa.String(64), nullable=True),
        sa.Column("attribution_reviewed_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("attribution_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("canonical_rule_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("legal_rule_identities.id", ondelete="RESTRICT"),
                  nullable=True),
        sa.Column("alias_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("legal_rule_aliases.id", ondelete="RESTRICT"),
                  nullable=True),
        sa.Column("revision_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("legal_rule_revisions.id", ondelete="RESTRICT"),
                  nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=True),
        sa.Column("definition_hash", sa.String(64), nullable=True),
        sa.Column("evaluator_name", sa.String(255), nullable=True),
        sa.Column("evaluator_version", sa.String(100), nullable=True),
        sa.Column("evaluator_artifact_hash", sa.String(64), nullable=True),
        sa.Column("evidence_status", sa.String(20), nullable=False,
                  server_default="MISSING"),
        sa.Column("evidence_manifest_hash", sa.String(64), nullable=False),
        sa.Column("finding_snapshot", JSONB(), nullable=False),
        sa.Column("finding_snapshot_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("compliance_flag_id", "evaluation_run_id",
                            name="uq_finding_binding_flag_run"),
        sa.CheckConstraint(
            "length(btrim(jurisdiction)) > 0 AND length(btrim(source_namespace)) > 0 AND length(btrim(historical_rule_id)) > 0",
            name="ck_finding_binding_lookup_key_nonempty"),
        sa.CheckConstraint(
            "resolution_status IN ('RESOLVED','AMBIGUOUS','RETIRED','UNRESOLVED',"
            "'INVALID_LOOKUP_KEY','INVALID_EFFECTIVE_DATE','INVALID_ALIAS_INTERVAL','INVALID_ALIAS_METADATA',"
            "'ALIAS_OUT_OF_DATE','IDENTITY_MISSING','IDENTITY_QUARANTINED',"
            "'INVALID_REVISION_INTERVAL','NO_EFFECTIVE_REVISION','AMBIGUOUS_REVISION',"
            "'INVALID_REVISION_HASH','INVALID_REVISION_METADATA','JURISDICTION_MISMATCH',"
            "'REGISTRY_UNAVAILABLE')",
            name="ck_finding_binding_resolution_status"),
        sa.CheckConstraint(
            "attribution_status IN ('CURRENT_EVALUATION','ATTRIBUTED',"
            "'UNATTRIBUTED','AMBIGUOUS','QUARANTINED')",
            name="ck_finding_binding_attribution_status"),
        sa.CheckConstraint(
            "evidence_status IN ('COMPLETE','PARTIAL','MISSING','INVALID',"
            "'CONFLICT','UNVERIFIED')",
            name="ck_finding_binding_evidence_status"),
        sa.CheckConstraint(
            "(resolution_status = 'RESOLVED' AND canonical_rule_id IS NOT NULL "
            "AND alias_id IS NOT NULL AND revision_id IS NOT NULL "
            "AND revision_number > 0 AND definition_hash ~ '^[0-9a-f]{64}$') "
            "OR (resolution_status <> 'RESOLVED' AND revision_id IS NULL "
            "AND revision_number IS NULL AND definition_hash IS NULL)",
            name="ck_finding_binding_resolved_metadata"),
        sa.CheckConstraint("evidence_manifest_hash ~ '^[0-9a-f]{64}$'",
                           name="ck_finding_binding_evidence_hash"),
        sa.CheckConstraint("finding_snapshot_hash ~ '^[0-9a-f]{64}$'",
                           name="ck_finding_binding_snapshot_hash"),
        sa.CheckConstraint(
            "evaluator_artifact_hash IS NULL OR evaluator_artifact_hash ~ '^[0-9a-f]{64}$'",
            name="ck_finding_binding_evaluator_hash"),
        sa.CheckConstraint(
            "attribution_evidence_hash IS NULL OR attribution_evidence_hash ~ '^[0-9a-f]{64}$'",
            name="ck_finding_binding_attribution_evidence_hash"),
        sa.CheckConstraint(
            "(attribution_status = 'ATTRIBUTED' AND attribution_basis IS NOT NULL "
            "AND btrim(attribution_basis) <> '' AND attribution_evidence_hash IS NOT NULL "
            "AND attribution_reviewed_by IS NOT NULL AND attribution_reviewed_at IS NOT NULL) "
            "OR (attribution_status <> 'ATTRIBUTED' AND attribution_basis IS NULL "
            "AND attribution_evidence_hash IS NULL AND attribution_reviewed_by IS NULL "
            "AND attribution_reviewed_at IS NULL)",
            name="ck_finding_binding_attribution_review_gate"),
        sa.CheckConstraint(
            "attribution_status <> 'ATTRIBUTED' OR "
            "(resolution_status = 'RESOLVED' AND evidence_status = 'COMPLETE')",
            name="ck_finding_binding_attribution_requires_identity_evidence"),
    )
    op.create_index(
        "ix_finding_binding_company_created",
        "compliance_finding_bindings", ["company_id", "created_at"])
    op.create_index(
        "ix_finding_binding_canonical_revision",
        "compliance_finding_bindings", ["canonical_rule_id", "revision_id"])

    op.create_table(
        "compliance_finding_evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("binding_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("compliance_finding_bindings.id", ondelete="RESTRICT"),
                  nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("company_fact_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("company_facts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("evidence_role", sa.String(80), nullable=False),
        sa.Column("fact_key", sa.String(120), nullable=False),
        sa.Column("fact_value_snapshot", JSONB(), nullable=False),
        sa.Column("fact_value_hash", sa.String(64), nullable=False),
        sa.Column("trust_level", sa.String(40), nullable=False),
        sa.Column("verification_status", sa.String(20), nullable=False),
        sa.Column("observed_on", sa.Date(), nullable=False),
        sa.Column("source_reference", sa.Text(), nullable=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("documents.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("document_sha256", sa.String(64), nullable=True),
        sa.Column("asserted_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("authorized_uploader_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("evidence_hash", sa.String(64), nullable=False),
        sa.UniqueConstraint("binding_id", "company_fact_id",
                            name="uq_finding_evidence_fact"),
        sa.CheckConstraint("length(btrim(evidence_role)) > 0",
                           name="ck_finding_evidence_role_nonempty"),
        sa.CheckConstraint(
            "trust_level IN ('USER_ASSERTED','AUTHORIZED_DOCUMENT_BACKED')",
            name="ck_finding_evidence_trust_level"),
        sa.CheckConstraint(
            "verification_status IN ('UNVERIFIED','VERIFIED','REJECTED','SUPERSEDED')",
            name="ck_finding_evidence_verification_status"),
        sa.CheckConstraint("fact_value_hash ~ '^[0-9a-f]{64}$'",
                           name="ck_finding_evidence_fact_value_hash"),
        sa.CheckConstraint("evidence_hash ~ '^[0-9a-f]{64}$'",
                           name="ck_finding_evidence_hash"),
        sa.CheckConstraint(
            "document_sha256 IS NULL OR document_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_finding_evidence_document_hash"),
        sa.CheckConstraint(
            "(trust_level = 'USER_ASSERTED' AND document_id IS NULL "
            "AND authorized_uploader_id IS NULL AND uploaded_at IS NULL) OR "
            "(trust_level = 'AUTHORIZED_DOCUMENT_BACKED' AND document_id IS NOT NULL "
            "AND authorized_uploader_id IS NOT NULL AND uploaded_at IS NOT NULL "
            "AND source_reference IS NOT NULL AND btrim(source_reference) <> '')",
            name="ck_finding_evidence_source_provenance"),
        sa.CheckConstraint(
            "(verification_status = 'VERIFIED' AND verified_by IS NOT NULL "
            "AND verified_at IS NOT NULL AND trust_level = 'AUTHORIZED_DOCUMENT_BACKED') "
            "OR (verification_status <> 'VERIFIED' AND verified_by IS NULL "
            "AND verified_at IS NULL)",
            name="ck_finding_evidence_verification_actor"),
    )
    op.create_index(
        "ix_finding_evidence_company_binding",
        "compliance_finding_evidence", ["company_id", "binding_id"])

    # Validate all redundant tenant and source snapshots against their parents.
    op.execute("""
        CREATE FUNCTION public.nlc_validate_finding_binding_insert()
        RETURNS trigger LANGUAGE plpgsql
        SET search_path = pg_catalog, public
        AS $function$
        DECLARE flag_company uuid; run_company uuid;
                alias_canonical uuid; alias_namespace text; alias_rule text;
                alias_start date; alias_end date; identity_jurisdiction text; identity_state text;
                revision_canonical uuid; revision_number_value integer;
                revision_start date; revision_end date; revision_hash text;
                revision_evaluator_name text; revision_evaluator_version text;
                revision_evaluator_hash text;
        BEGIN
            SELECT company_id INTO flag_company
              FROM public.compliance_flags WHERE id = NEW.compliance_flag_id;
            IF flag_company IS NULL OR flag_company IS DISTINCT FROM NEW.company_id THEN
                RAISE EXCEPTION 'Finding binding company must match its compliance flag';
            END IF;
            IF NEW.evaluation_run_id IS NOT NULL THEN
                SELECT company_id INTO run_company
                  FROM public.compliance_evaluation_runs WHERE id = NEW.evaluation_run_id;
                IF run_company IS NULL OR run_company IS DISTINCT FROM NEW.company_id THEN
                    RAISE EXCEPTION 'Finding binding evaluation run belongs to another company';
                END IF;
            END IF;
            IF NEW.resolution_status = 'RESOLVED' THEN
                SELECT canonical_rule_id, source_namespace, historical_rule_id, valid_from, valid_to
                  INTO alias_canonical, alias_namespace, alias_rule, alias_start, alias_end
                  FROM public.legal_rule_aliases WHERE id = NEW.alias_id;
                SELECT jurisdiction, identity_status
                  INTO identity_jurisdiction, identity_state
                  FROM public.legal_rule_identities WHERE id = NEW.canonical_rule_id;
                SELECT canonical_rule_id, revision_number, effective_from, effective_to,
                       definition_hash, evaluator_name, evaluator_version, evaluator_artifact_hash
                  INTO revision_canonical, revision_number_value, revision_start, revision_end,
                       revision_hash, revision_evaluator_name, revision_evaluator_version,
                       revision_evaluator_hash
                  FROM public.legal_rule_revisions WHERE id = NEW.revision_id;
                IF alias_canonical IS DISTINCT FROM NEW.canonical_rule_id
                   OR revision_canonical IS DISTINCT FROM NEW.canonical_rule_id
                   OR alias_namespace IS DISTINCT FROM NEW.source_namespace
                   OR alias_rule IS DISTINCT FROM NEW.historical_rule_id
                   OR revision_number_value IS DISTINCT FROM NEW.revision_number
                   OR identity_jurisdiction IS DISTINCT FROM NEW.jurisdiction
                   OR identity_state IS DISTINCT FROM 'ACTIVE'
                   OR alias_start IS NULL OR alias_start > NEW.effective_date
                   OR (alias_end IS NOT NULL AND NEW.effective_date >= alias_end)
                   OR revision_start IS NULL OR revision_start > NEW.effective_date
                   OR (revision_end IS NOT NULL AND NEW.effective_date >= revision_end)
                   OR revision_hash IS DISTINCT FROM NEW.definition_hash
                   OR revision_evaluator_name IS DISTINCT FROM NEW.evaluator_name
                   OR revision_evaluator_version IS DISTINCT FROM NEW.evaluator_version
                   OR revision_evaluator_hash IS DISTINCT FROM NEW.evaluator_artifact_hash THEN
                    RAISE EXCEPTION 'Finding binding canonical identity, jurisdiction, alias, revision and evaluator snapshot do not reconcile';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $function$
    """)
    op.execute("""
        CREATE TRIGGER trg_finding_binding_insert_guard
        BEFORE INSERT ON public.compliance_finding_bindings
        FOR EACH ROW EXECUTE FUNCTION public.nlc_validate_finding_binding_insert()
    """)

    op.execute("""
        CREATE FUNCTION public.nlc_validate_finding_evidence_insert()
        RETURNS trigger LANGUAGE plpgsql
        SET search_path = pg_catalog, public
        AS $function$
        DECLARE binding_company uuid; fact_company uuid; fact_document uuid;
                fact_key_value text; fact_value_value jsonb; fact_trust text; fact_status text;
                fact_observed date; fact_source text; fact_asserted uuid;
                fact_uploader uuid; fact_uploaded timestamptz;
                fact_verified_by uuid; fact_verified_at timestamptz;
                document_company uuid; document_hash text;
        BEGIN
            SELECT company_id INTO binding_company
              FROM public.compliance_finding_bindings WHERE id = NEW.binding_id;
            SELECT company_id, document_id, fact_key, fact_value, trust_level,
                   verification_status, observed_on, source_reference, asserted_by,
                   authorized_uploader_id, uploaded_at, verified_by, verified_at
              INTO fact_company, fact_document, fact_key_value, fact_value_value, fact_trust,
                   fact_status, fact_observed, fact_source, fact_asserted,
                   fact_uploader, fact_uploaded, fact_verified_by, fact_verified_at
              FROM public.company_facts WHERE id = NEW.company_fact_id;
            IF binding_company IS NULL OR fact_company IS DISTINCT FROM NEW.company_id
               OR binding_company IS DISTINCT FROM NEW.company_id THEN
                RAISE EXCEPTION 'Finding evidence, fact and binding must share one company';
            END IF;
            IF NEW.fact_value_snapshot IS DISTINCT FROM fact_value_value
               OR NEW.document_id IS DISTINCT FROM fact_document
               OR NEW.fact_key IS DISTINCT FROM fact_key_value
               OR NEW.trust_level IS DISTINCT FROM fact_trust
               OR NEW.verification_status IS DISTINCT FROM fact_status
               OR NEW.observed_on IS DISTINCT FROM fact_observed
               OR NEW.source_reference IS DISTINCT FROM fact_source
               OR NEW.asserted_by IS DISTINCT FROM fact_asserted
               OR NEW.authorized_uploader_id IS DISTINCT FROM fact_uploader
               OR NEW.uploaded_at IS DISTINCT FROM fact_uploaded
               OR NEW.verified_by IS DISTINCT FROM fact_verified_by
               OR NEW.verified_at IS DISTINCT FROM fact_verified_at THEN
                RAISE EXCEPTION 'Finding evidence snapshot does not match its immutable company fact';
            END IF;
            IF NEW.document_id IS NOT NULL THEN
                SELECT company_id, checksum_sha256 INTO document_company, document_hash
                  FROM public.documents WHERE id = NEW.document_id;
                IF document_company IS DISTINCT FROM NEW.company_id
                   OR document_hash IS DISTINCT FROM NEW.document_sha256 THEN
                    RAISE EXCEPTION 'Finding evidence document snapshot does not match the company vault';
                END IF;
            ELSIF NEW.document_sha256 IS NOT NULL THEN
                RAISE EXCEPTION 'Document hash cannot exist without a document reference';
            END IF;
            RETURN NEW;
        END;
        $function$
    """)
    op.execute("""
        CREATE TRIGGER trg_finding_evidence_insert_guard
        BEFORE INSERT ON public.compliance_finding_evidence
        FOR EACH ROW EXECUTE FUNCTION public.nlc_validate_finding_evidence_insert()
    """)

    for table in ("compliance_finding_bindings", "compliance_finding_evidence"):
        op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE public.{table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {table}_tenant_read ON public.{table} "
            "FOR SELECT USING (public.nlc_can_access_company(company_id))"
        )
        op.execute(
            f"CREATE POLICY {table}_actor_insert ON public.{table} "
            "FOR INSERT WITH CHECK (public.nlc_can_edit_company(company_id) "
            "AND public.nlc_can_access_company(company_id))"
        )
        op.execute(f"GRANT SELECT, INSERT ON TABLE public.{table} TO nlc_app_role")
        op.execute(
            f"REVOKE UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER "
            f"ON TABLE public.{table} FROM nlc_app_role"
        )
        op.execute(
            f"REVOKE ALL PRIVILEGES ON TABLE public.{table} "
            "FROM PUBLIC, nlc_ci_audit_role"
        )

    for function_name in (
        "public.nlc_validate_finding_binding_insert()",
        "public.nlc_validate_finding_evidence_insert()",
    ):
        op.execute(f"REVOKE ALL ON FUNCTION {function_name} FROM PUBLIC")
        op.execute(f"GRANT EXECUTE ON FUNCTION {function_name} TO nlc_app_role")

    for table in ("compliance_finding_bindings", "compliance_finding_evidence"):
        function_name = f"prevent_{table}_mutation"
        op.execute(f"""
            CREATE FUNCTION public.{function_name}()
            RETURNS trigger LANGUAGE plpgsql
            SET search_path = pg_catalog, public
            AS $function$
            BEGIN
                RAISE EXCEPTION '{table} is append-only: % is forbidden',
                    TG_OP USING ERRCODE = '55000';
            END;
            $function$
        """)
        op.execute(f"""
            CREATE TRIGGER trg_{table}_append_only
            BEFORE UPDATE OR DELETE ON public.{table}
            FOR EACH ROW EXECUTE FUNCTION public.{function_name}()
        """)
        op.execute(f"REVOKE ALL ON FUNCTION public.{function_name}() FROM PUBLIC, nlc_app_role, nlc_ci_audit_role")


def downgrade() -> None:
    raise RuntimeError(
        "0118 is forward-only: finding identity and evidence snapshots are "
        "audit records and must not be removed by an Alembic downgrade."
    )
