"""Preserve duplicate compliance flags and enforce one active row per company/rule.

Revision ID: 0089_unique_active_compliance_flags
Revises: 0088_strict_activity_log_actor_tenant

Duplicate active rows are retained as linked DUPLICATE records for audit.
They are not treated as legally resolved and do not change the legal-release gate.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0089_unique_active_compliance_flags"
down_revision = "0088_strict_activity_log_actor_tenant"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # PostgreSQL requires a newly added enum value to be committed before it
    # can be used in subsequent statements.
    with op.get_context().autocommit_block():
        op.execute(
            "ALTER TYPE public.flag_status "
            "ADD VALUE IF NOT EXISTS 'DUPLICATE'"
        )

    op.add_column(
        "compliance_flags",
        sa.Column(
            "duplicate_of_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_compliance_flags_duplicate_of",
        "compliance_flags",
        "compliance_flags",
        ["duplicate_of_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    # Keep the oldest active row as the canonical record. Preserve every
    # duplicate row, its original detail, and its notification provenance.
    # DUPLICATE explicitly does not mean the underlying matter was resolved.
    op.execute(
        """
        WITH ranked AS (
            SELECT
                id,
                FIRST_VALUE(id) OVER (
                    PARTITION BY company_id, rule_id
                    ORDER BY created_at ASC NULLS LAST, id ASC
                ) AS canonical_id,
                ROW_NUMBER() OVER (
                    PARTITION BY company_id, rule_id
                    ORDER BY created_at ASC NULLS LAST, id ASC
                ) AS row_number
            FROM public.compliance_flags
            WHERE flag_status = 'ACTIVE'
        )
        UPDATE public.compliance_flags AS duplicate
        SET
            flag_status = 'DUPLICATE'::public.flag_status,
            duplicate_of_id = ranked.canonical_id,
            resolution_notes = concat_ws(
                E'\\n',
                NULLIF(duplicate.resolution_notes, ''),
                'Duplicate active record retained for audit. Canonical record: '
                    || ranked.canonical_id::text
                    || '. DUPLICATE does not mean the underlying legal or compliance matter is resolved.'
            )
        FROM ranked
        WHERE duplicate.id = ranked.id
          AND ranked.row_number > 1
        """
    )

    op.create_index(
        "uq_compliance_flags_active_company_rule",
        "compliance_flags",
        ["company_id", "rule_id"],
        unique=True,
        postgresql_where=sa.text("flag_status = 'ACTIVE'"),
    )


def downgrade() -> None:
    # Forward-only: the migration adds an enum value and preserves duplicate
    # evidence. Removing the link or reactivating duplicates could recreate
    # the MultipleResultsFound production failure.
    pass
