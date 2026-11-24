"""Reconcile the exact AGM-001 legacy citation through the rule-version ledger.

Revision ID: 0125_reconcile_agm001_statutory_basis
Revises: 0124_restore_85_rule_catalogue_parity

Only the known 0026 AGM-001 definition may be normalized. The complete
before-image is recorded as MIGRATION provenance in legal_rule_versions.
Conflicting catalogue definitions are rejected without mutation.
"""
import json

from alembic import op
import sqlalchemy as sa

revision = "0125_reconcile_agm001_statutory_basis"
down_revision = "0124_restore_85_rule_catalogue_parity"
branch_labels = None
depends_on = None

RULE_ID = "AGM-001"
LEGACY_BASIS = "Section 81, Companies Act 1994 (Bangladesh)"
CANONICAL_BASIS = "Section 81(1), Companies Act 1994 (Bangladesh)"
LEGACY_DEFINITION = {
    "rule_name": "First AGM Default",
    "rule_type": "DEADLINE",
    "description": (
        "First AGM not held within 18 months (548 days) of incorporation. "
        "Section 81 is mandatory; no waiver for private companies. "
        "Default counts from day after deadline."
    ),
    "rule_condition": {
        "check_fn": "check_agm_001",
        "data_points": ["incorporation_date", "first_agm_held", "agm_count"],
        "trigger": "first_agm_held == False AND days_since_incorporation > 548",
    },
    "is_active": True,
}
CHANGE_REASON = (
    "Reconcile the exact known legacy AGM-001 citation to the canonical "
    "Section 81(1) registry identity; preserve the complete prior catalogue "
    "definition and advance its rule version for auditability."
)


def _next_version(previous_version: str) -> str:
    if not previous_version:
        raise RuntimeError("0125 refuses an empty AGM-001 rule_version")
    parts = previous_version.split(".")
    if any(not part.isdigit() for part in parts):
        raise RuntimeError(
            "0125 refuses to advance non-numeric AGM-001 rule_version: "
            f"{previous_version!r}"
        )
    parts[-1] = str(int(parts[-1]) + 1)
    return ".".join(parts)


def _definition(row) -> dict:
    return {
        "rule_name": row["rule_name"],
        "rule_type": row["rule_type"],
        "description": row["description"],
        "rule_condition": row["rule_condition"],
        "is_active": row["is_active"],
    }


def _validate_migration_history(bind, current_row, expected_previous=None):
    history = bind.execute(
        sa.text(
            """
            SELECT version, change_reason, changed_by, actor_type,
                   migration_revision, previous_definition
              FROM public.legal_rule_versions
             WHERE rule_id = :rule_id
               AND migration_revision = :migration_revision
            """
        ),
        {"rule_id": RULE_ID, "migration_revision": revision},
    ).mappings().all()

    if len(history) != 1:
        raise RuntimeError(
            "0125 requires exactly one auditable AGM-001 migration history row; "
            f"found {len(history)}"
        )

    record = history[0]
    if (
        record["actor_type"] != "MIGRATION"
        or record["changed_by"] is not None
        or record["migration_revision"] != revision
        or record["change_reason"] != CHANGE_REASON
        or not record["version"]
    ):
        raise RuntimeError(
            f"0125 AGM-001 migration provenance is invalid: {dict(record)!r}"
        )

    previous = record["previous_definition"]
    if isinstance(previous, str):
        previous = json.loads(previous)
    if not isinstance(previous, dict):
        raise RuntimeError("0125 AGM-001 previous_definition is not a JSON object")
    if previous.get("rule_id") != RULE_ID:
        raise RuntimeError("0125 AGM-001 history row references another rule ID")
    if previous.get("statutory_basis") != LEGACY_BASIS:
        raise RuntimeError(
            "0125 AGM-001 history row does not preserve the exact legacy citation"
        )
    if previous.get("rule_version") != record["version"]:
        raise RuntimeError(
            "0125 AGM-001 history version does not match its before-image"
        )
    if _definition(
        {
            "rule_name": previous.get("rule_name"),
            "rule_type": previous.get("rule_type"),
            "description": previous.get("description"),
            "rule_condition": previous.get("rule_condition"),
            "is_active": previous.get("is_active"),
        }
    ) != LEGACY_DEFINITION:
        raise RuntimeError(
            "0125 AGM-001 history row does not preserve the exact known legacy definition"
        )

    expected_version = _next_version(str(record["version"]))
    if current_row["rule_version"] != expected_version:
        raise RuntimeError(
            "0125 AGM-001 current version does not follow its migration history: "
            f"expected={expected_version!r}, actual={current_row['rule_version']!r}"
        )
    if expected_previous is not None:
        if isinstance(expected_previous, str):
            expected_previous = json.loads(expected_previous)
        if previous != expected_previous:
            raise RuntimeError(
                "0125 AGM-001 migration history differs from the locked before-image"
            )


def upgrade() -> None:
    bind = op.get_bind()

    # Existing human-authored history remains USER provenance. Migration
    # history is explicit and does not invent a user actor.
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

    # Lock and inspect the whole row before deciding whether it is safe to touch.
    current = bind.execute(
        sa.text(
            """
            SELECT to_jsonb(rule) AS previous_definition,
                   rule.rule_name,
                   rule.rule_type::text AS rule_type,
                   rule.statutory_basis,
                   rule.description,
                   rule.rule_condition,
                   rule.is_active,
                   rule.rule_version
              FROM public.legal_rules AS rule
             WHERE rule.rule_id = :rule_id
             FOR UPDATE
            """
        ),
        {"rule_id": RULE_ID},
    ).mappings().one_or_none()

    if current is None:
        raise RuntimeError("0125 refuses to reconcile a missing AGM-001 catalogue row")
    if _definition(current) != LEGACY_DEFINITION:
        raise RuntimeError(
            "0125 refuses to overwrite a conflicting AGM-001 legal definition: "
            f"{_definition(current)!r}"
        )

    # If an operator changed the citation before this migration, do not silently
    # accept it. A canonical row is accepted only with this migration's own
    # complete, immutable MIGRATION-provenance before-image.
    if current["statutory_basis"] == CANONICAL_BASIS:
        _validate_migration_history(bind, current)
        return
    if current["statutory_basis"] != LEGACY_BASIS:
        raise RuntimeError(
            "0125 refuses unexpected AGM-001 statutory_basis: "
            f"{current['statutory_basis']!r}"
        )

    previous_definition = current["previous_definition"]
    if isinstance(previous_definition, str):
        previous_definition = json.loads(previous_definition)
    if not isinstance(previous_definition, dict):
        raise RuntimeError(
            "0125 AGM-001 locked before-image is not a JSON object"
        )

    previous_version = current["rule_version"]
    next_version = _next_version(previous_version)
    existing_history_count = bind.execute(
        sa.text(
            """
            SELECT count(*)
              FROM public.legal_rule_versions
             WHERE rule_id = :rule_id
               AND migration_revision = :migration_revision
            """
        ),
        {"rule_id": RULE_ID, "migration_revision": revision},
    ).scalar_one()
    if existing_history_count:
        raise RuntimeError(
            "0125 found an AGM-001 migration history row while the catalogue "
            "still has the legacy basis; refusing duplicate/inconsistent history"
        )

    bind.execute(
        sa.text(
            """
            INSERT INTO public.legal_rule_versions
                (rule_id, version, change_reason, changed_by, changed_at,
                 previous_definition, sro_reference, actor_type,
                 migration_revision)
            VALUES
                (:rule_id, :previous_version, :change_reason, NULL,
                 now(), CAST(:previous_definition AS jsonb), NULL,
                 'MIGRATION', :migration_revision)
            """
        ),
        {
            "rule_id": RULE_ID,
            "previous_version": previous_version,
            "change_reason": CHANGE_REASON,
            "migration_revision": revision,
            "previous_definition": json.dumps(
                previous_definition,
                sort_keys=True,
                separators=(",", ":"),
                default=str,
            ),
        },
    )

    result = bind.execute(
        sa.text(
            """
            UPDATE public.legal_rules
               SET statutory_basis = :canonical_basis,
                   rule_version = :next_version,
                   last_modified_at = now(),
                   updated_at = now()
             WHERE rule_id = :rule_id
               AND statutory_basis = :legacy_basis
               AND rule_version = :previous_version
               AND is_active IS TRUE
            """
        ),
        {
            "canonical_basis": CANONICAL_BASIS,
            "next_version": next_version,
            "rule_id": RULE_ID,
            "legacy_basis": LEGACY_BASIS,
            "previous_version": previous_version,
        },
    )
    if result.rowcount != 1:
        raise RuntimeError(
            "0125 expected exactly one conditional AGM-001 basis update; "
            f"updated={result.rowcount}"
        )

    actual = bind.execute(
        sa.text(
            """
            SELECT rule.rule_name,
                   rule.rule_type::text AS rule_type,
                   rule.statutory_basis,
                   rule.description,
                   rule.rule_condition,
                   rule.is_active,
                   rule.rule_version
              FROM public.legal_rules AS rule
             WHERE rule.rule_id = :rule_id
            """
        ),
        {"rule_id": RULE_ID},
    ).mappings().one_or_none()

    if (
        actual is None
        or actual["statutory_basis"] != CANONICAL_BASIS
        or actual["rule_version"] != next_version
        or _definition(actual) != LEGACY_DEFINITION
    ):
        raise RuntimeError(
            "0125 AGM-001 post-update identity/version verification failed: "
            f"{None if actual is None else dict(actual)!r}"
        )

    _validate_migration_history(
        bind,
        actual,
        expected_previous=previous_definition,
    )


def downgrade() -> None:
    raise RuntimeError(
        "0125 is forward-only: reverting the canonical AGM-001 identity "
        "would reintroduce a known statutory-basis mismatch and invalidate "
        "the immutable rule-version history."
    )
