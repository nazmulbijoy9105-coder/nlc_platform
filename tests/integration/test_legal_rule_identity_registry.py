"""Database-level invariants for the canonical legal-rule identity registry."""
from __future__ import annotations

import pytest
from sqlalchemy import text

pytestmark = [pytest.mark.integration]


@pytest.mark.asyncio
async def test_alias_registry_is_forced_rls_and_has_overlap_guard(db):
    relation = await db.execute(
        text(
            "SELECT c.relrowsecurity, c.relforcerowsecurity "
            "FROM pg_class c "
            "JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = 'public' AND c.relname = 'legal_rule_aliases'"
        )
    )
    assert relation.one() == (True, True)

    trigger = await db.execute(
        text(
            "SELECT t.tgname, pg_get_triggerdef(t.oid), p.prosrc "
            "FROM pg_trigger t "
            "JOIN pg_class c ON c.oid = t.tgrelid "
            "JOIN pg_namespace n ON n.oid = c.relnamespace "
            "JOIN pg_proc p ON p.oid = t.tgfoid "
            "WHERE n.nspname = 'public' "
            "AND c.relname = 'legal_rule_aliases' "
            "AND t.tgname = 'trg_legal_rule_alias_no_overlap' "
            "AND NOT t.tgisinternal"
        )
    )
    trigger_row = trigger.one()
    assert "BEFORE INSERT" in trigger_row[1]
    assert "NEW.resolution_status <> 'RESOLVED'" in trigger_row[2]
    assert "existing.resolution_status = 'RESOLVED'" in trigger_row[2]
    assert "source_namespace" in trigger_row[2]
    assert "historical_rule_id" in trigger_row[2]
    assert "daterange(" in trigger_row[2]
    assert "pg_advisory_xact_lock(" in trigger_row[2]

    for role in ("nlc_app_role", "nlc_ci_audit_role"):
        privileges = await db.execute(
            text(
                "SELECT has_table_privilege(:role, "
                "'public.legal_rule_aliases', 'SELECT') "
                "OR has_table_privilege(:role, "
                "'public.legal_rule_aliases', 'INSERT') "
                "OR has_table_privilege(:role, "
                "'public.legal_rule_aliases', 'UPDATE') "
                "OR has_table_privilege(:role, "
                "'public.legal_rule_aliases', 'DELETE')"
            ),
            {"role": role},
        )
        assert privileges.scalar_one() is False
