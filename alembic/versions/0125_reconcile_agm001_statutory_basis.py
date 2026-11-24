"""Reconcile AGM-001 citation with a versioned, auditable rule change.

Revision ID: 0125_reconcile_agm001_statutory_basis
Revises: 0124_restore_85_rule_catalogue_parity

The migration records the complete prior catalogue row in the append-only
legal_rule_versions ledger before changing its statutory citation/version.
It only rewrites the one known legacy citation and fails closed on drift.
"""
import json

from alembic import op
import sqlalchemy as sa

revision = "0125_reconcile_agm001_statutory_basis"
down_revision = "0124_restore_85_rule_catalogue_parity"
branch_labels = None
depends_on = None

LEGACY_BASIS = "Section 81, Companies Act 1994 (Bangladesh)"
CANONICAL_BASIS = "Section 81(1), Companies Act 1994 (Bangladesh)"
CHANGE_REASON = (
    "Reconcile the known legacy AGM-001 citation to the canonical "
    "Section 81(1) statutory identity; preserve the prior catalogue "
    "definition and advance its rule version for auditability."
)


def upgrade() -> None:
    bind = op.get_bind()

    # Migration provenance must not depend on an application user existing:
    # first-time setup provisions users only after the schema is migrated.
    # Keep human-authored history rows constrained to real user actors, while
    # representing this schema migration explicitly as MIGRATION provenance.
    op.add_column(
        "legal_rule_versions",
        sa.Column(
            "actor_type", sa.String(20), nullable=False, server_default="USER"
        ),
    )
    op.add_column(
        "legal_rule_versions",
        sa.Column("migration_revision", sa.String(255), nullable=True),
    )
    op.alter_column(
        "legal_rule_versions", "changed_by", existing_type=sa.UUID(), nullable=True
    )
    op.create_check_constraint(
        "ck_legal_rule_versions_actor_provenance",
        "legal_rule_versions",
        """(
            actor_type = 'USER'
            AND changed_by IS NOT NULL
            AND migration_revision IS NULL
        ) OR (
            actor_type = 'MIGRATION'
            AND changed_by IS NULL
            AND migration_revision IS NOT NULL
        )""",
    )

    # Lock the target row and capture its complete pre-change definition.
    prior = bind.execute(
        sa.text(
            """
            SELECT to_jsonb(rule) AS previous_definition,
                   rule.rule_version AS previous_version
              FROM public.legal_rules AS rule
             WHERE rule.rule_id = 'AGM-001'
               AND rule.statutory_basis = :legacy_basis
             FOR UPDATE
            """
        ),
        {"legacy_basis": LEGACY_BASIS},
    ).mappings().one_or_none()

    if prior is not None:
        previous_version = prior["previous_version"]
        # Increment the final numeric component (2.0 -> 2.1; 2.0.0 -> 2.0.1).
        parts = previous_version.split(".")
        if not parts or any(not part.isdigit() for part in parts):
            raise RuntimeError(
                "0125 refuses to advance non-numeric AGM-001 rule_version: "
                f"{previous_version!r}"
            )
        parts[-1] = str(int(parts[-1]) + 1)
        next_version = ".".join(parts)

        bind.execute(
            sa.text(
                """
                INSERT INTO public.legal_rule_versions
                    (rule_id, version, change_reason, changed_by, changed_at,
                     previous_definition, sro_reference, actor_type,
                     migration_revision)
                VALUES
                    ('AGM-001', :previous_version, :change_reason, NULL,
                     now(), CAST(:previous_definition AS jsonb), NULL,
                     'MIGRATION', :migration_revision)
                """
            ),
            {
                "previous_version": previous_version,
                "change_reason": CHANGE_REASON,
                "migration_revision": revision,
                "previous_definition": json.dumps(
                    prior["previous_definition"], default=str
                ),
            },
        )

        bind.execute(
            sa.text(
                """
                UPDATE public.legal_rules
                   SET statutory_basis = :canonical_basis,
                       rule_version = :next_version,
                       last_modified_at = now(),
                       updated_at = now()
                 WHERE rule_id = 'AGM-001'
                   AND statutory_basis = :legacy_basis
                """
            ),
            {
                "canonical_basis": CANONICAL_BASIS,
                "next_version": next_version,
                "legacy_basis": LEGACY_BASIS,
            },
        )

    actual = bind.execute(
        sa.text(
            """
            SELECT rule.statutory_basis,
                   rule.rule_version,
                   (
                       SELECT count(*)
                         FROM public.legal_rule_versions AS history
                        WHERE history.rule_id = 'AGM-001'
                   ) AS history_count
              FROM public.legal_rules AS rule
             WHERE rule.rule_id = 'AGM-001'
            """
        )
    ).mappings().one_or_none()

    if actual is None or actual["statutory_basis"] != CANONICAL_BASIS:
        raise RuntimeError(
            "0125 refuses AGM-001 identity drift: "
            f"expected={CANONICAL_BASIS!r}, actual="
            f"{None if actual is None else actual['statutory_basis']!r}"
        )

    if prior is not None:
        if actual["rule_version"] != next_version:
            raise RuntimeError(
                "0125 failed to advance AGM-001 rule_version: "
                f"expected={next_version!r}, actual={actual['rule_version']!r}"
            )
        if actual["history_count"] < 1:
            raise RuntimeError("0125 failed to record AGM-001 prior definition")


def downgrade() -> None:
    raise RuntimeError(
        "0125 is forward-only: reverting the canonical AGM-001 identity "
        "would reintroduce a known statutory-basis mismatch and invalidate "
        "the immutable rule-version history."
    )
