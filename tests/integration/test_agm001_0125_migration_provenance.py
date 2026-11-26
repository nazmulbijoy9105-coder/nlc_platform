"""Integration contract for the 0125 AGM-001 reconciliation.

The CI PostgreSQL job applies Alembic from an empty database before running
integration tests. These assertions inspect the persisted migration result,
not source-code snippets.
"""
from __future__ import annotations

from sqlalchemy import text


LEGACY_BASIS = "Section 81, Companies Act 1994 (Bangladesh)"
CANONICAL_BASIS = "Section 81(1), Companies Act 1994 (Bangladesh)"
MIGRATION_REVISION = "0125_reconcile_agm001_statutory_basis"


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
    before = history["previous_definition"]
    if isinstance(before, str):
        import json
        before = json.loads(before)

    assert history["actor_type"] == "MIGRATION"
    assert history["changed_by"] is None
    assert history["migration_revision"] == MIGRATION_REVISION
    assert history["change_reason"]
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

    current = (
        await db.execute(
            text(
                """
                SELECT statutory_basis, rule_version, rule_name, rule_type,
                       description, rule_condition, is_active
                  FROM public.legal_rules
                 WHERE rule_id = 'AGM-001'
                """
            )
        )
    ).mappings().one()

    version_parts = str(history["version"]).split(".")
    assert all(part.isdigit() for part in version_parts)
    version_parts[-1] = str(int(version_parts[-1]) + 1)
    assert current["rule_version"] == ".".join(version_parts)
    assert current["statutory_basis"] == CANONICAL_BASIS
    assert current["rule_name"] == before["rule_name"]
    assert current["rule_type"] == before["rule_type"]
    assert current["description"] == before["description"]
    assert current["rule_condition"] == before["rule_condition"]
    assert current["is_active"] is True
