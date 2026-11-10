"""PostgreSQL regression checks for company-fact provenance RLS and immutability."""
from __future__ import annotations

from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text


pytestmark = [pytest.mark.integration]


@pytest.mark.asyncio
async def test_company_facts_use_signed_tenant_rls_and_immutable_source_fields(db):
    result = await db.execute(
        text(
            "SELECT policyname, cmd, qual, with_check FROM pg_policies "
            "WHERE schemaname='public' AND tablename='company_facts'"
        )
    )
    policies = {row[0]: row for row in result.fetchall()}
    assert set(policies) == {
        "company_facts_tenant_read",
        "company_facts_actor_insert",
        "company_facts_staff_verification_update",
    }

    read_policy = policies["company_facts_tenant_read"]
    assert read_policy[1] == "SELECT"
    assert "nlc_can_access_company" in (read_policy[2] or "")

    insert_policy = policies["company_facts_actor_insert"]
    assert insert_policy[1] == "INSERT"
    assert "nlc_current_user_id" in (insert_policy[3] or "")
    assert "nlc_can_edit_company" in (insert_policy[3] or "")

    update_policy = policies["company_facts_staff_verification_update"]
    assert update_policy[1] == "UPDATE"
    assert "nlc_current_user_is_staff" in (update_policy[2] or "")
    assert "nlc_current_user_is_staff" in (update_policy[3] or "")
    assert "nlc_current_user_id" in (update_policy[3] or "")

    flags = await db.execute(
        text(
            "SELECT c.relrowsecurity, c.relforcerowsecurity "
            "FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
            "WHERE n.nspname='public' AND c.relname='company_facts'"
        )
    )
    enabled, forced = flags.one()
    assert enabled is True
    assert forced is True

    for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE"):
        allowed = await db.execute(
            text(
                "SELECT has_table_privilege('nlc_app_role', "
                "CAST(:table AS text), :privilege)"
            ),
            {"table": "public.company_facts", "privilege": privilege},
        )
        assert allowed.scalar_one() is (privilege in {"SELECT", "INSERT", "UPDATE"})

    triggers = await db.execute(
        text(
            "SELECT tgname FROM pg_trigger WHERE NOT tgisinternal "
            "AND tgrelid='public.company_facts'::regclass"
        )
    )
    assert "trg_company_facts_immutable_source" in {
        row[0] for row in triggers.fetchall()
    }


def test_company_fact_migration_merges_to_one_head():
    alembic_ini = Path(__file__).resolve().parents[2] / "alembic.ini"
    script = ScriptDirectory.from_config(Config(str(alembic_ini)))
    heads = script.get_heads()
    assert len(heads) == 1, f"multiple Alembic heads: {heads}"

    ancestors = {
        revision.revision
        for revision in script.walk_revisions(base="base", head=heads[0])
    }
    assert "0104_company_fact_provenance" in ancestors
    assert "0093_verified_rule_audit_view" in ancestors
    assert "b10c91ac6860" in ancestors
