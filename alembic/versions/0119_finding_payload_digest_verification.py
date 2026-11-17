"""Add database-verifiable canonical payload digests for finding snapshots.

Revision ID: 0119_finding_payload_digest_verification
Revises: 0118_canonical_finding_evidence_binding

Existing rows are not silently re-serialized from JSONB: that would change the
Python canonical-JSON contract. If 0118 already contains rows, migration stops
and requires an explicit controlled backfill using the original serializer.
"""
from alembic import op
import sqlalchemy as sa

revision = "0119_finding_payload_digest_verification"
down_revision = "0118_canonical_finding_evidence_binding"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM public.compliance_finding_bindings)
               OR EXISTS (SELECT 1 FROM public.compliance_finding_evidence) THEN
                RAISE EXCEPTION
                    '0119 requires an explicit canonical-payload backfill before existing 0118 rows can be upgraded';
            END IF;
        END;
        $$;
    """)
    op.add_column("compliance_finding_bindings",
                  sa.Column("finding_snapshot_canonical", sa.Text(), nullable=True))
    op.add_column("compliance_finding_bindings",
                  sa.Column("evidence_manifest_canonical", sa.Text(), nullable=True))
    op.add_column("compliance_finding_evidence",
                  sa.Column("fact_value_canonical", sa.Text(), nullable=True))
    op.add_column("compliance_finding_evidence",
                  sa.Column("evidence_canonical", sa.Text(), nullable=True))
    op.alter_column("compliance_finding_bindings", "finding_snapshot_canonical", nullable=False)
    op.alter_column("compliance_finding_bindings", "evidence_manifest_canonical", nullable=False)
    op.alter_column("compliance_finding_evidence", "fact_value_canonical", nullable=False)
    op.alter_column("compliance_finding_evidence", "evidence_canonical", nullable=False)

    op.execute("""
        CREATE FUNCTION public.nlc_verify_finding_binding_payloads()
        RETURNS trigger LANGUAGE plpgsql
        SET search_path = pg_catalog, public, extensions
        AS $function$
        BEGIN
            IF encode(digest(convert_to(NEW.finding_snapshot_canonical, 'UTF8'), 'sha256'), 'hex')
                   IS DISTINCT FROM NEW.finding_snapshot_hash
               OR (NEW.finding_snapshot_canonical::jsonb -> 'finding')
                   IS DISTINCT FROM NEW.finding_snapshot THEN
                RAISE EXCEPTION 'Finding snapshot canonical payload or SHA-256 digest mismatch';
            END IF;
            IF encode(digest(convert_to(NEW.evidence_manifest_canonical, 'UTF8'), 'sha256'), 'hex')
                   IS DISTINCT FROM NEW.evidence_manifest_hash
               OR jsonb_typeof(NEW.evidence_manifest_canonical::jsonb -> 'evidence') IS DISTINCT FROM 'array' THEN
                RAISE EXCEPTION 'Evidence manifest canonical payload or SHA-256 digest mismatch';
            END IF;
            RETURN NEW;
        END;
        $function$
    """)
    op.execute("""
        CREATE TRIGGER trg_finding_binding_payload_digest
        BEFORE INSERT ON public.compliance_finding_bindings
        FOR EACH ROW EXECUTE FUNCTION public.nlc_verify_finding_binding_payloads()
    """)
    op.execute("""
        CREATE FUNCTION public.nlc_verify_finding_evidence_payloads()
        RETURNS trigger LANGUAGE plpgsql
        SET search_path = pg_catalog, public, extensions
        AS $function$
        BEGIN
            IF encode(digest(convert_to(NEW.fact_value_canonical, 'UTF8'), 'sha256'), 'hex')
                   IS DISTINCT FROM NEW.fact_value_hash
               OR (NEW.fact_value_canonical::jsonb -> 'value')
                   IS DISTINCT FROM NEW.fact_value_snapshot THEN
                RAISE EXCEPTION 'Fact value canonical payload or SHA-256 digest mismatch';
            END IF;
            IF encode(digest(convert_to(NEW.evidence_canonical, 'UTF8'), 'sha256'), 'hex')
                   IS DISTINCT FROM NEW.evidence_hash
               OR (NEW.evidence_canonical::jsonb -> 'fact_value_snapshot')
                   IS DISTINCT FROM NEW.fact_value_snapshot
               OR (NEW.evidence_canonical::jsonb ->> 'fact_key')
                   IS DISTINCT FROM NEW.fact_key
               OR (NEW.evidence_canonical::jsonb ->> 'company_fact_id')
                   IS DISTINCT FROM NEW.company_fact_id::text
               OR (NEW.evidence_canonical::jsonb ->> 'company_id')
                   IS DISTINCT FROM NEW.company_id::text
               OR (NEW.evidence_canonical::jsonb ->> 'evidence_role')
                   IS DISTINCT FROM NEW.evidence_role
               OR (NEW.evidence_canonical::jsonb ->> 'fact_value_hash')
                   IS DISTINCT FROM NEW.fact_value_hash
               OR (NEW.evidence_canonical::jsonb ->> 'trust_level')
                   IS DISTINCT FROM NEW.trust_level
               OR (NEW.evidence_canonical::jsonb ->> 'verification_status')
                   IS DISTINCT FROM NEW.verification_status
               OR (NEW.evidence_canonical::jsonb ->> 'observed_on')
                   IS DISTINCT FROM NEW.observed_on::text
               OR (NEW.evidence_canonical::jsonb ->> 'source_reference')
                   IS DISTINCT FROM NEW.source_reference
               OR (NEW.evidence_canonical::jsonb ->> 'document_id')
                   IS DISTINCT FROM NEW.document_id::text
               OR (NEW.evidence_canonical::jsonb ->> 'document_sha256')
                   IS DISTINCT FROM NEW.document_sha256
               OR (NEW.evidence_canonical::jsonb ->> 'asserted_by')
                   IS DISTINCT FROM NEW.asserted_by::text
               OR (NEW.evidence_canonical::jsonb ->> 'authorized_uploader_id')
                   IS DISTINCT FROM NEW.authorized_uploader_id::text
               OR (NEW.evidence_canonical::jsonb ->> 'uploaded_at')
                   IS DISTINCT FROM to_char(NEW.uploaded_at AT TIME ZONE 'UTC',
                           'YYYY-MM-DD"T"HH24:MI:SS.US"+00:00"')
               OR (NEW.evidence_canonical::jsonb ->> 'verified_by')
                   IS DISTINCT FROM NEW.verified_by::text
               OR (NEW.evidence_canonical::jsonb ->> 'verified_at')
                   IS DISTINCT FROM to_char(NEW.verified_at AT TIME ZONE 'UTC',
                           'YYYY-MM-DD"T"HH24:MI:SS.US"+00:00"') THEN
                RAISE EXCEPTION 'Evidence canonical payload or SHA-256 digest mismatch';
            END IF;
            RETURN NEW;
        END;
        $function$
    """)
    op.execute("""
        CREATE TRIGGER trg_finding_evidence_payload_digest
        BEFORE INSERT ON public.compliance_finding_evidence
        FOR EACH ROW EXECUTE FUNCTION public.nlc_verify_finding_evidence_payloads()
    """)

    # Reconstruct the exact Python manifest shape, including the canonical
    # evidence JSON string itself. Without that key, every non-empty manifest
    # would differ from the DB aggregate and the deferred trigger would reject
    # an otherwise valid transaction at COMMIT.
    op.execute("""
        CREATE FUNCTION public.nlc_verify_finding_manifest_children()
        RETURNS trigger LANGUAGE plpgsql
        SET search_path = pg_catalog, public, extensions
        AS $function$
        DECLARE target_binding uuid; expected_manifest jsonb; actual_manifest jsonb;
        BEGIN
            IF TG_TABLE_NAME = 'compliance_finding_bindings' THEN
                target_binding := NEW.id;
            ELSE
                target_binding := NEW.binding_id;
            END IF;
            SELECT evidence_manifest_canonical::jsonb -> 'evidence'
              INTO expected_manifest
              FROM public.compliance_finding_bindings WHERE id = target_binding;
            IF expected_manifest IS NULL THEN
                RAISE EXCEPTION 'Finding evidence manifest parent is missing';
            END IF;
            SELECT COALESCE(
                jsonb_agg(
                    e.evidence_canonical::jsonb ||
                    jsonb_build_object(
                        'evidence_canonical', e.evidence_canonical,
                        'fact_value_canonical', e.fact_value_canonical,
                        'evidence_hash', e.evidence_hash
                    )
                    ORDER BY e.fact_key, e.company_fact_id
                ),
                '[]'::jsonb
            )
              INTO actual_manifest
              FROM public.compliance_finding_evidence e
             WHERE e.binding_id = target_binding;
            IF actual_manifest IS DISTINCT FROM expected_manifest THEN
                RAISE EXCEPTION 'Evidence manifest does not match persisted evidence rows';
            END IF;
            RETURN NULL;
        END;
        $function$
    """)
    op.execute("""
        CREATE CONSTRAINT TRIGGER trg_finding_binding_manifest_children
        AFTER INSERT ON public.compliance_finding_bindings
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION public.nlc_verify_finding_manifest_children()
    """)
    op.execute("""
        CREATE CONSTRAINT TRIGGER trg_finding_evidence_manifest_children
        AFTER INSERT ON public.compliance_finding_evidence
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION public.nlc_verify_finding_manifest_children()
    """)
    for function_name in (
        "public.nlc_verify_finding_binding_payloads()",
        "public.nlc_verify_finding_evidence_payloads()",
        "public.nlc_verify_finding_manifest_children()",
    ):
        op.execute(f"REVOKE ALL ON FUNCTION {function_name} FROM PUBLIC")
        op.execute(f"GRANT EXECUTE ON FUNCTION {function_name} TO nlc_app_role")


def downgrade() -> None:
    raise RuntimeError(
        "0119 is forward-only: canonical digest verification is part of the "
        "finding audit record and must not be removed."
    )
