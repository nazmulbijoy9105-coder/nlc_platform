"""Integration contract for the 0125 AGM-001 reconciliation.

The CI PostgreSQL job applies Alembic from an empty database before running
integration tests. These assertions inspect the persisted migration result,
not source-code snippets.
"""
from __future__ import annotations

import json

from sqlalchemy import text


LEGACY_BASIS = "Section 81, Companies Act 1994 (Bangladesh)"
CANONICAL_BASIS = "Section 81(1), Companies Act 1994 (Bangladesh)"
MIGRATION_REVISION = "0125_reconcile_agm001_statutory_basis"

# Every legal_rules column at 0125; the before-image is to_jsonb(rule).
BEFORE_IMAGE_FIELDS = frozenset(
    {
        "id",
        "rule_id",
        "rule_name",
        "rule_type",
        "statutory_basis",
        "statutory_effective_date",
        "description",
        "verification_status",
        "verified_by",
        "verified_at",
        "verification_notes",
        "rule_condition",
        "default_severity",
        "score_impact",
        "revenue_tier",
        "is_black_override",
        "rule_version",
        "is_active",
        "created_by",
        "last_modified_by",
        "last_modified_at",
        "created_at",
        "updated_at",
    }
)
MIGRATION_MUTATED_FIELDS = frozenset(
    {
        "statutory_basis",
        "description",
        "rule_condition",
        "rule_version",
        "last_modified_at",
        "updated_at",
    }
)


def _json_object(value):
    return json.loads(value) if isinstance(value, str) else value


async def test_0125_persists_complete_agm001_before_image_and_version(db):
    history_rows = (
        await db.execute(
            text(
                """
                SELECT version, change_reason, changed_by, actor_type,
                       migration_revision, previous_definition
                  FROM public.legal_rule_versions
                 WHERE rule_id = 'AGM-001'
                   AND migration_revision = :revision
                """
            ),
            {"revision": MIGRATION_REVISION},
        )
    ).mappings().all()

    assert len(history_rows) == 1
    history = history_rows[0]
    before = _json_object(history["previous_definition"])

    current = _json_object(
        (
            await db.execute(
                text(
                    """
                    SELECT to_jsonb(rule) AS row_json
                      FROM public.legal_rules AS rule
                     WHERE rule.rule_id = 'AGM-001'
                    """
                )
            )
        ).scalar_one()
    )

    assert history["actor_type"] == "MIGRATION"
    assert history["changed_by"] is None
    assert history["migration_revision"] == MIGRATION_REVISION
    assert history["change_reason"]
    assert set(before) == BEFORE_IMAGE_FIELDS
    assert before["rule_id"] == "AGM-001"
    assert before["statutory_basis"] == LEGACY_BASIS
    assert before["rule_name"] == "First AGM Default"
    assert before["rule_type"] == "DEADLINE"
    assert before["description"] == (
        "First AGM not held within 18 months (548 days) of incorporation. "
        "Section 81 is mandatory; no waiver for private companies. "
        "Default counts from day after deadline."
    )
    assert before["rule_condition"] == {
        "check_fn": "check_agm_001",
        "data_points": ["incorporation_date", "first_agm_held", "agm_count"],
        "trigger": "first_agm_held == False AND days_since_incorporation > 548",
    }
    assert before["is_active"] is True
    assert before["rule_version"] == history["version"]

    for field in sorted(BEFORE_IMAGE_FIELDS - MIGRATION_MUTATED_FIELDS):
        assert before[field] == current[field], field

    version_parts = str(history["version"]).split(".")
    assert all(part.isdigit() for part in version_parts)
    version_parts[-1] = str(int(version_parts[-1]) + 1)
    assert current["rule_version"] == ".".join(version_parts)
    assert current["statutory_basis"] == CANONICAL_BASIS
    assert current["rule_name"] == before["rule_name"]
    assert current["rule_type"] == before["rule_type"]
    assert current["description"] == (
        "First AGM must be held within 18 calendar months of incorporation. "
        "Calculate with calendar-month arithmetic; do not use a fixed-day approximation."
    )
    assert current["rule_condition"] == {
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
    assert current["is_active"] is True
