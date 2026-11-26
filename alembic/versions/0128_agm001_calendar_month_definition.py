"""Replace the fixed-day AGM-001 catalogue rule with its calendar-month rule.

Revision ID: 0128_agm001_calendar_month_definition
Revises: 0127_one_active_rescue_plan_per_company

0125 reconciled the statutory citation but preserved the old 548-day rule
definition. This forward-only migration accepts only the exact 0125-produced
state, proves that state through its immutable migration history, then records
a complete before-image and installs the canonical 18-calendar-month rule.
"""
import json

from alembic import op
import sqlalchemy as sa

revision = "0128_agm001_calendar_month_definition"
down_revision = "0127_one_active_rescue_plan_per_company"
branch_labels = None
depends_on = None

RULE_ID = "AGM-001"
LEGACY_BASIS = "Section 81, Companies Act 1994 (Bangladesh)"
CANONICAL_BASIS = "Section 81(1), Companies Act 1994 (Bangladesh)"
PREVIOUS_REVISION = "0125_reconcile_agm001_statutory_basis"
PREVIOUS_CHANGE_REASON = (
    "Reconcile the exact known legacy AGM-001 citation to the canonical "
    "Section 81(1) registry identity; preserve the complete prior catalogue "
    "definition and advance its rule version for auditability."
)



LEGACY_DESCRIPTION = (
    "First AGM not held within 18 months (548 days) of incorporation. "
    "Section 81 is mandatory; no waiver for private companies. "
    "Default counts from day after deadline."
)
LEGACY_CONDITION = {
    "check_fn": "check_agm_001",
    "data_points": ["incorporation_date", "first_agm_held", "agm_count"],
    "trigger": "first_agm_held == False AND days_since_incorporation > 548",
}
CANONICAL_DESCRIPTION = (
    "First AGM must be held within 18 calendar months of incorporation. "
    "Calculate with calendar-month arithmetic; do not use a fixed-day approximation."
)
CANONICAL_CONDITION = {
    "check_fn": "check_agm_001",
    "trigger": (
        "agm_history_verified == True AND agm_count == 0 AND "
        "today > add_calendar_months(incorporation_date, 18)"
    ),
    "data_points": [
        "agm_history_verified",
        "incorporation_date",
        "agm_count",
    ],
}
CHANGE_REASON = (
    "Replace the obsolete fixed 548-day AGM-001 catalogue approximation with "
    "the canonical 18-calendar-month rule used by the statutory registry, "
    "seed corpus and evaluator; preserve the complete prior row and migration "
    "provenance in legal_rule_versions."
)


def _next_version(previous_version: str) -> str:
    if not previous_version:
        raise RuntimeError("0128 refuses an empty AGM-001 rule_version")
    parts = previous_version.split(".")
    if any(not part.isdigit() for part in parts):
        raise RuntimeError(
            "0128 refuses to advance non-numeric AGM-001 rule_version: "
            f"{previous_version!r}"
        )
    parts[-1] = str(int(parts[-1]) + 1)
    return ".".join(parts)


def _as_object(value, label):
    if isinstance(value, str):
        value = json.loads(value)
    if not isinstance(value, dict):
        raise RuntimeError(f"0128 {label} is not a JSON object")
    return value


def _validate_0125_history(bind):
    rows = bind.execute(
        sa.text(
            """
            SELECT version, change_reason, changed_by, actor_type,
                   migration_revision, previous_definition
              FROM public.legal_rule_versions
             WHERE rule_id = :rule_id
               AND migration_revision = :migration_revision
            """
        ),
        {"rule_id": RULE_ID, "migration_revision": PREVIOUS_REVISION},
    ).mappings().all()
    if len(rows) != 1:
        raise RuntimeError(
            "0128 requires exactly one 0125 AGM-001 migration history row; "
            f"found {len(rows)}"
        )
    record = rows[0]
    if (
        record["actor_type"] != "MIGRATION"
        or record["changed_by"] is not None
        or record["migration_revision"] != PREVIOUS_REVISION
        or record["change_reason"] != PREVIOUS_CHANGE_REASON
        or not record["version"]
    ):
        raise RuntimeError("0128 found invalid 0125 AGM-001 migration provenance")

    before = _as_object(record["previous_definition"], "0125 before-image")
    expected_legacy = {
        "rule_name": "First AGM Default",
        "rule_type": "DEADLINE",
        "description": LEGACY_DESCRIPTION,
        "rule_condition": LEGACY_CONDITION,
        "is_active": True,
    }
    if (
        before.get("rule_id") != RULE_ID
        or before.get("statutory_basis") != LEGACY_BASIS
        or before.get("rule_version") != record["version"]
        or {key: before.get(key) for key in expected_legacy} != expected_legacy
    ):
        raise RuntimeError(
            "0128 refuses: 0125 history does not prove the exact known "
            "legacy AGM-001 definition"
        )
    return before


def upgrade() -> None:
    bind = op.get_bind()
    current = bind.execute(
        sa.text(
            """
            SELECT to_jsonb(rule) AS previous_definition
              FROM public.legal_rules AS rule
             WHERE rule.rule_id = :rule_id
             FOR UPDATE
            """
        ),
        {"rule_id": RULE_ID},
    ).mappings().one_or_none()
    if current is None:
        raise RuntimeError("0128 refuses to update a missing AGM-001 catalogue row")

    previous = _as_object(current["previous_definition"], "locked before-image")
    history_before = _validate_0125_history(bind)
    expected_previous_version = _next_version(history_before["rule_version"])
    expected_next_version = _next_version(expected_previous_version)
    if (
        previous.get("statutory_basis") != CANONICAL_BASIS
        or previous.get("rule_version") != expected_previous_version
        or previous.get("rule_name") != "First AGM Default"
        or previous.get("rule_type") != "DEADLINE"
        or previous.get("description") != LEGACY_DESCRIPTION
        or previous.get("rule_condition") != LEGACY_CONDITION
        or previous.get("is_active") is not True
    ):
        raise RuntimeError(
            "0128 refuses unexpected AGM-001 catalogue drift; "
            "only the exact 0125-produced 548-day state is eligible"
        )
    if (
        history_before.get("rule_name") != previous.get("rule_name")
        or history_before.get("rule_type") != previous.get("rule_type")
        or history_before.get("is_active") != previous.get("is_active")
    ):
        raise RuntimeError("0128 0125 history does not match the current AGM-001 identity")

    existing = bind.execute(
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
    if existing:
        raise RuntimeError(
            "0128 found pre-existing AGM-001 migration history while the "
            "catalogue still has the legacy definition; refusing inconsistent replay"
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
            "previous_version": expected_previous_version,
            "change_reason": CHANGE_REASON,
            "previous_definition": json.dumps(
                previous, sort_keys=True, separators=(",", ":"), default=str
            ),
            "migration_revision": revision,
        },
    )

    result = bind.execute(
        sa.text(
            """
            UPDATE public.legal_rules
               SET description = :canonical_description,
                   rule_condition = CAST(:canonical_condition AS jsonb),
                   rule_version = :next_version,
                   last_modified_at = now(),
                   updated_at = now()
             WHERE rule_id = :rule_id
               AND statutory_basis = :canonical_basis
               AND rule_version = :previous_version
               AND rule_name = :rule_name
               AND rule_type::text = 'DEADLINE'
               AND description = :legacy_description
               AND rule_condition = CAST(:legacy_condition AS jsonb)
               AND is_active IS TRUE
            """
        ),
        {
            "canonical_description": CANONICAL_DESCRIPTION,
            "canonical_condition": json.dumps(
                CANONICAL_CONDITION, sort_keys=True, separators=(",", ":")
            ),
            "next_version": expected_next_version,
            "rule_id": RULE_ID,
            "canonical_basis": CANONICAL_BASIS,
            "previous_version": expected_previous_version,
            "rule_name": "First AGM Default",
            "legacy_description": LEGACY_DESCRIPTION,
            "legacy_condition": json.dumps(
                LEGACY_CONDITION, sort_keys=True, separators=(",", ":")
            ),
        },
    )
    if result.rowcount != 1:
        raise RuntimeError(
            "0128 expected exactly one conditional AGM-001 definition update; "
            f"updated={result.rowcount}"
        )

    actual = bind.execute(
        sa.text(
            """
            SELECT statutory_basis, description, rule_condition, rule_version,
                   rule_name, rule_type::text AS rule_type, is_active
              FROM public.legal_rules
             WHERE rule_id = :rule_id
            """
        ),
        {"rule_id": RULE_ID},
    ).mappings().one_or_none()
    if (
        actual is None
        or actual["statutory_basis"] != CANONICAL_BASIS
        or actual["description"] != CANONICAL_DESCRIPTION
        or actual["rule_condition"] != CANONICAL_CONDITION
        or actual["rule_version"] != expected_next_version
        or actual["rule_name"] != "First AGM Default"
        or actual["rule_type"] != "DEADLINE"
        or actual["is_active"] is not True
    ):
        raise RuntimeError(
            "0128 AGM-001 post-update verification failed: "
            f"{None if actual is None else dict(actual)!r}"
        )


def downgrade() -> None:
    raise RuntimeError(
        "0128 is forward-only: restoring the fixed 548-day AGM-001 rule would "
        "reintroduce a known mismatch with the calendar-month statutory rule "
        "and evaluator."
    )
