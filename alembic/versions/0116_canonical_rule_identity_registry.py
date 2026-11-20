"""Add canonical legal-rule identity, alias and revision registries.

Revision ID: 0116_canonical_rule_identity_registry
Revises: 0115_rule_identity_collision_reconciliation

This is additive and seeds 85 stable technical identities for the static engine
registry. Source aliases remain UNRESOLVED; no legacy legal_rules row, historical
finding, legal revision, statutory validity, or score is automatically assigned.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0116_canonical_rule_identity_registry"
down_revision = "0115_rule_identity_collision_reconciliation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "legal_rule_identities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("jurisdiction", sa.String(length=8), nullable=False),
        sa.Column("obligation_key", sa.String(length=160), nullable=True),
        sa.Column("identity_status", sa.String(length=20), nullable=False,
                  server_default="QUARANTINED"),
        sa.Column("creation_basis", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(length=160), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.CheckConstraint(
            "identity_status IN ('ACTIVE', 'RETIRED', 'QUARANTINED')",
            name="ck_legal_rule_identity_status",
        ),
        sa.UniqueConstraint("obligation_key", name="uq_legal_rule_identity_obligation_key"),
    )
    op.create_index(
        "ix_legal_rule_identities_jurisdiction_status",
        "legal_rule_identities", ["jurisdiction", "identity_status"],
    )

    op.create_table(
        "legal_rule_aliases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("canonical_rule_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("legal_rule_identities.id", ondelete="RESTRICT"),
                  nullable=False),
        sa.Column("source_namespace", sa.String(length=255), nullable=False),
        sa.Column("historical_rule_id", sa.String(length=100), nullable=False),
        sa.Column("resolution_status", sa.String(length=20), nullable=False,
                  server_default="UNRESOLVED"),
        sa.Column("mapping_basis", sa.Text(), nullable=True),
        sa.Column("evidence_ref", sa.String(length=1000), nullable=True),
        sa.Column("evidence_hash", sa.String(length=128), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("approved_by", sa.String(length=160), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.CheckConstraint(
            "resolution_status IN ('RESOLVED', 'AMBIGUOUS', 'UNRESOLVED', 'RETIRED')",
            name="ck_legal_rule_alias_resolution_status",
        ),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_from IS NULL OR valid_to > valid_from",
            name="ck_legal_rule_alias_validity",
        ),
        sa.UniqueConstraint(
            "source_namespace", "historical_rule_id", "canonical_rule_id",
            name="uq_legal_rule_alias_source_historical_canonical",
        ),
    )
    op.create_index(
        "ix_legal_rule_alias_lookup",
        "legal_rule_aliases", ["source_namespace", "historical_rule_id"],
    )

    op.create_table(
        "legal_rule_revisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("canonical_rule_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("legal_rule_identities.id", ondelete="RESTRICT"),
                  nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("legal_source_revision_id", sa.String(length=255), nullable=True),
        sa.Column("provision_reference", sa.String(length=1000), nullable=True),
        sa.Column("definition_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("definition_hash", sa.String(length=128), nullable=False),
        sa.Column("evaluator_name", sa.String(length=255), nullable=True),
        sa.Column("evaluator_version", sa.String(length=100), nullable=True),
        sa.Column("evaluator_artifact_hash", sa.String(length=128), nullable=True),
        sa.Column("approval_state", sa.String(length=30), nullable=False,
                  server_default="REVIEW_REQUIRED"),
        sa.Column("approval_evidence", postgresql.JSONB(astext_type=sa.Text()),
                  nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_to > effective_from",
            name="ck_legal_rule_revision_effective_interval",
        ),
        sa.CheckConstraint("revision_number > 0", name="ck_legal_rule_revision_positive"),
        sa.UniqueConstraint(
            "canonical_rule_id", "revision_number",
            name="uq_legal_rule_revision_number",
        ),
    )
    op.create_index(
        "ix_legal_rule_revision_effective_lookup",
        "legal_rule_revisions",
        ["canonical_rule_id", "effective_from", "effective_to"],
    )

    # Stable technical identities for the exact 85-key engine registry. These
    # identify source keys only: they do not validate statutory content, dates,
    # scope, or attribute any historical legal_rules row/finding. Aliases stay
    # UNRESOLVED; no legal revisions or historical finding bindings are seeded.
    op.execute("""
        WITH engine_rule_ids(rule_id) AS (
            VALUES
            ('ACC-001'),
            ('ACC-002'),
            ('ACC-003'),
            ('AGM-001'),
            ('AGM-002'),
            ('AGM-003'),
            ('AGM-004'),
            ('AGM-005'),
            ('AGM-006'),
            ('AGM-007'),
            ('AR-001'),
            ('AR-002'),
            ('AR-003'),
            ('AR-004'),
            ('AUD-001'),
            ('AUD-002'),
            ('AUD-003'),
            ('AUD-004'),
            ('AUD-005'),
            ('BNK-001'),
            ('BNK-002'),
            ('BNK-003'),
            ('BOD-001'),
            ('BOD-002'),
            ('BOD-003'),
            ('BSEC-001'),
            ('BSEC-002'),
            ('BSEC-003'),
            ('BSEC-004'),
            ('CAP-001'),
            ('CAP-002'),
            ('CAP-003'),
            ('CAP-004'),
            ('CHG-001'),
            ('DEF-001'),
            ('DEF-002'),
            ('DIR-001'),
            ('DIR-002'),
            ('DIR-003'),
            ('DIR-004'),
            ('DIR-005'),
            ('DIR-006'),
            ('DIR-007'),
            ('DIR-008'),
            ('DIR-010'),
            ('ESC-001'),
            ('ESC-002'),
            ('ESC-003'),
            ('ESC-004'),
            ('ESC-005'),
            ('FX-001'),
            ('INC-001'),
            ('INC-003'),
            ('INC-004'),
            ('INC-005'),
            ('INC-006'),
            ('INC-007'),
            ('LBR-001'),
            ('LBR-002'),
            ('LBR-003'),
            ('MEM-001'),
            ('OFF-001'),
            ('REG-001'),
            ('REG-002'),
            ('REG-003'),
            ('SH-001'),
            ('SH-002'),
            ('SH-003'),
            ('STR-001'),
            ('STR-002'),
            ('STR-003'),
            ('TAX-001'),
            ('TAX-002'),
            ('TAX-003'),
            ('TAX-004'),
            ('TL-001'),
            ('TL-002'),
            ('TR-001'),
            ('TR-002'),
            ('TR-003'),
            ('TR-004'),
            ('TR-005'),
            ('TR-006'),
            ('VAT-002'),
            ('VAT-003')
        )
        INSERT INTO public.legal_rule_identities (
            jurisdiction, obligation_key, identity_status,
            creation_basis, created_by
        )
        SELECT
            'BD',
            'BD:NLC_ENGINE_REGISTRY_V2:' || rule_id,
            'ACTIVE',
            'Stable technical identity from the NLC statutory engine registry v2 key only. '
            'This does not certify legal validity, effective dates, statutory scope, '
            'or attribution of legacy legal_rules rows or historical findings.',
            'migration:0116'
        FROM engine_rule_ids
        ON CONFLICT (obligation_key) DO NOTHING
    """)
    op.execute("""
        INSERT INTO public.legal_rule_aliases (
            canonical_rule_id, source_namespace, historical_rule_id,
            resolution_status, mapping_basis
        )
        SELECT
            id,
            'NLC_ENGINE_REGISTRY_V2',
            split_part(obligation_key, ':', 4),
            'UNRESOLVED',
            'Engine registry source key only. This is not a resolution to any '
            'legacy legal_rules row or historical finding; no legal revision '
            'or statutory validity is asserted.'
        FROM public.legal_rule_identities
        WHERE obligation_key LIKE 'BD:NLC_ENGINE_REGISTRY_V2:%'
        ON CONFLICT (
            source_namespace, historical_rule_id, canonical_rule_id
        ) DO NOTHING
    """)
    op.execute("""
        COMMENT ON TABLE public.legal_rule_identities IS
        'Stable technical rule identities; identity status is not a legal-validity or scoring-release status.'
    """)
    op.execute("""
        COMMENT ON TABLE public.legal_rule_aliases IS
        'Source-key aliases; UNRESOLVED rows do not attribute legacy database rules or historical findings.'
    """)

    # Serialize inserts per canonical identity and reject overlapping
    # half-open effective intervals. This is database-enforced, including
    # concurrent writers; NULL effective_to represents an unbounded end date.
    op.execute("""
        CREATE FUNCTION public.prevent_legal_rule_revision_overlap()
        RETURNS trigger LANGUAGE plpgsql VOLATILE AS $overlap$
        BEGIN
            PERFORM pg_advisory_xact_lock(
                hashtextextended(NEW.canonical_rule_id::text, 0)
            );
            IF EXISTS (
                SELECT 1
                  FROM public.legal_rule_revisions existing
                 WHERE existing.canonical_rule_id = NEW.canonical_rule_id
                   AND daterange(
                       existing.effective_from, existing.effective_to, '[)'
                   ) && daterange(
                       NEW.effective_from, NEW.effective_to, '[)'
                   )
            ) THEN
                RAISE EXCEPTION
                    'Overlapping effective interval for canonical legal rule %',
                    NEW.canonical_rule_id
                    USING ERRCODE = '23P01';
            END IF;
            RETURN NEW;
        END;
        $overlap$
    """)
    op.execute("""
        CREATE TRIGGER trg_legal_rule_revision_no_overlap
        BEFORE INSERT ON public.legal_rule_revisions
        FOR EACH ROW
        EXECUTE FUNCTION public.prevent_legal_rule_revision_overlap()
    """)
    op.execute(
        "REVOKE ALL ON FUNCTION public.prevent_legal_rule_revision_overlap() "
        "FROM PUBLIC, nlc_app_role, nlc_ci_audit_role"
    )

    # These governance tables remain inaccessible to runtime and audit roles
    # until a separately reviewed service/API contract grants scoped access.
    for table in ("legal_rule_identities", "legal_rule_aliases", "legal_rule_revisions"):
        op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE public.{table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"REVOKE ALL PRIVILEGES ON TABLE public.{table} "
            "FROM PUBLIC, nlc_app_role, nlc_ci_audit_role"
        )

    # Evidence and identity mappings are append-only. Corrections are new rows
    # with explicit supersession in a future governed extension, never UPDATE.
    op.execute("""
        CREATE FUNCTION public.prevent_legal_rule_identity_mutation()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION '% is append-only: % is forbidden',
                TG_TABLE_NAME, TG_OP USING ERRCODE = '55000';
        END;
        $$
    """)
    for table in ("legal_rule_identities", "legal_rule_aliases", "legal_rule_revisions"):
        op.execute(
            f"CREATE TRIGGER trg_{table}_append_only "
            f"BEFORE UPDATE OR DELETE ON public.{table} "
            "FOR EACH ROW EXECUTE FUNCTION public.prevent_legal_rule_identity_mutation()"
        )
    op.execute(
        "REVOKE ALL ON FUNCTION public.prevent_legal_rule_identity_mutation() FROM PUBLIC, nlc_app_role, nlc_ci_audit_role"
    )


def downgrade() -> None:
    raise RuntimeError(
        "0116 is forward-only: canonical identity and alias evidence must not "
        "be removed by an Alembic downgrade."
    )
