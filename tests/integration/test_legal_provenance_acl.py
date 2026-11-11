"""PostgreSQL ACL and RLS checks for append-only legal provenance tables."""
from __future__ import annotations

import pytest
from sqlalchemy import text

pytestmark = [pytest.mark.integration]

_TABLES = (
    "legal_sources",
    "legal_rule_source_mappings",
    "legal_deadline_definitions",
    "legal_rule_release_events",
)


@pytest.mark.asyncio
async def test_legal_provenance_tables_are_append_only_and_least_privilege(db):
    expected_policies = {
        "legal_sources": {"legal_sources_read_policy", "legal_sources_insert_policy"},
        "legal_rule_source_mappings": {
            "legal_rule_source_mappings_read_policy",
            "legal_rule_source_mappings_insert_policy",
        },
        "legal_deadline_definitions": {
            "legal_deadline_definitions_read_policy",
            "legal_deadline_definitions_insert_policy",
        },
        "legal_rule_release_events": {
            "legal_rule_release_events_read_policy",
            "legal_rule_release_events_insert_policy",
        },
    }
    for table in _TABLES:
        flags = await db.execute(
            text(
                "SELECT c.relrowsecurity, c.relforcerowsecurity "
                "FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                "WHERE n.nspname='public' AND c.relname=:table"
            ),
            {"table": table},
        )
        row = flags.one()
        assert row[0] is True
        assert row[1] is True

        policies_result = await db.execute(
            text(
                "SELECT policyname, cmd, qual, with_check FROM pg_policies "
                "WHERE schemaname='public' AND tablename=:table"
            ),
            {"table": table},
        )
        policies = {r[0]: r for r in policies_result.fetchall()}
        assert set(policies) == expected_policies[table]
        assert policies[f"{table}_read_policy"][1] == "SELECT"
        assert "nlc_current_user_context_valid" in (
            policies[f"{table}_read_policy"][2] or ""
        )
        assert policies[f"{table}_insert_policy"][1] == "INSERT"
        assert "nlc_current_user_is_super_admin" in (
            policies[f"{table}_insert_policy"][3] or ""
        )

        for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER"):
            allowed = await db.execute(
                text(
                    "SELECT has_table_privilege('nlc_app_role', "
                    "CAST(:table AS text), :privilege)"
                ),
                {"table": f"public.{table}", "privilege": privilege},
            )
            expected = privilege in {"SELECT", "INSERT"}
            assert allowed.scalar_one() is expected, (
                f"unexpected {privilege} privilege on public.{table}"
            )

        trigger_result = await db.execute(
            text(
                "SELECT tgname FROM pg_trigger "
                "WHERE NOT tgisinternal AND tgrelid=CAST(:table AS regclass)"
            ),
            {"table": f"public.{table}"},
        )
        triggers = {r[0] for r in trigger_result.fetchall()}
        assert f"{table}_actor_guard" in triggers
        assert f"{table}_reject_mutation" in triggers
        assert f"{table}_reject_truncate" in triggers


@pytest.mark.asyncio
async def test_legal_release_event_chain_has_database_guard(db):
    result = await db.execute(
        text(
            "SELECT tgname FROM pg_trigger WHERE NOT tgisinternal "
            "AND tgrelid='public.legal_rule_release_events'::regclass"
        )
    )
    triggers = {row[0] for row in result.fetchall()}
    assert "legal_rule_release_events_chain_guard" in triggers


@pytest.mark.asyncio
async def test_bulk_mapping_endpoint_rejects_unknown_rule_and_source_atomically(
    api_client, super_admin_headers, db
):
    """Exercise the signed admin route and ensure invalid IDs produce no writes."""
    from uuid import uuid4

    response = await api_client.post(
        "/api/v1/legal-provenance/mappings/bulk",
        headers=super_admin_headers,
        json={
            "mappings": [
                {
                    "rule_id": "UNKNOWN-RULE-DO-NOT-INSERT",
                    "source_id": str(uuid4()),
                    "mapping_kind": "RULE_BASIS",
                    "provision_citation": "Companies Act 1994, section 1",
                    "rationale": "Integration fixture intentionally references missing records.",
                }
            ]
        },
    )
    assert response.status_code == 422
    payload = response.json()["detail"]
    assert payload["missing_rule_ids"] == ["UNKNOWN-RULE-DO-NOT-INSERT"]
    assert len(payload["missing_source_ids"]) == 1

    count = await db.execute(
        text("SELECT count(*) FROM legal_rule_source_mappings")
    )
    assert count.scalar_one() == 0


@pytest.mark.asyncio
async def test_customer_calendar_generator_uses_database_registry_without_false_no_due_claim(
    db, db_company
):
    """The customer generation route reports an empty registry explicitly."""
    from types import SimpleNamespace

    from app.api.calendar import generate_calendar

    result = await generate_calendar(
        company_id=db_company.id,
        years_ahead=2,
        db=db,
        current_user=SimpleNamespace(role="CLIENT_DIRECTOR"),
    )

    assert result["processed"] == 0
    assert result["count"] == 0
    assert result["results"] == []
    assert result["events"] == []
    assert result["no_obligation_inference"] is True
