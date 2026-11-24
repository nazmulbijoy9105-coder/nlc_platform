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

    # Lock the target row and capture its complete pre-change definition.
    # changed_by is a real user FK: prefer the rule's existing governance
    # actor, otherwise require an active SUPER_ADMIN. Never invent an actor.
    prior = bind.execute(
        sa.text(
            """
            SELECT to_jsonb(rule) AS previous_definition,
                   rule.rule_version AS previous_version,
                   COALESCE(
                       (
                           SELECT admin.id
                             FROM public.users AS admin
                            WHERE admin.role = 'SUPER_ADMIN'
                              AND admin.is_active IS TRUE
                            ORDER BY admin.created_at, admin.id
                            LIMIT 1
                       ),
                       rule.last_modified_by,
                       rule.created_by
                   ) AS changed_by
              FROM public.legal_rules AS rule
             WHERE rule.rule_id = 'AGM-001'
               AND rule.statutory_basis = :legacy_basis
             FOR UPDATE
            """
        ),
        {"legacy_basis": LEGACY_BASIS},
    ).mappings().one_or_none()

    if prior is not None:
        if prior["changed_by"] is None:
            raise RuntimeError(
                "0125 cannot audit AGM-001 correction: no existing rule "
                "governance actor or active SUPER_ADMIN user is available"
            )

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
                     previous_definition, sro_reference)
                VALUES
                    ('AGM-001', :previous_version, :change_reason, :changed_by,
                     now(), CAST(:previous_definition AS jsonb), NULL)
                """
            ),
            {
                "previous_version": previous_version,
                "change_reason": CHANGE_REASON,
                "changed_by": prior["changed_by"],
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
                       last_modified_by = :changed_by,
                       last_modified_at = now(),
                       updated_at = now()
                 WHERE rule_id = 'AGM-001'
                   AND statutory_basis = :legacy_basis
                """
            ),
            {
                "canonical_basis": CANONICAL_BASIS,
                "next_version": next_version,
                "changed_by": prior["changed_by"],
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
