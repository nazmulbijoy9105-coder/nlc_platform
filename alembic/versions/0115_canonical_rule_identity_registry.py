"""Add canonical legal-rule identity, alias and revision registries.

Revision ID: 0115_canonical_rule_identity_registry
Revises: 0114_annual_return_filing_status_provenance

This is additive only. It intentionally performs no automatic identity
assignment, alias backfill, historical finding update, or score change.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0115_canonical_rule_identity_registry"
down_revision = "0114_annual_return_filing_status_provenance"
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
        "REVOKE ALL ON FUNCTION public.prevent_legal_rule_identity_mutation() FROM PUBLIC"
    )


def downgrade() -> None:
    raise RuntimeError(
         "0115 is forward-only: canonical identity and alias evidence must not "
        "be removed by an Alembic downgrade."
    )
