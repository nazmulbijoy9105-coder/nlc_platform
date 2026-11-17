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

    # 0117 intentionally grants the application role SELECT only; signed
    # RLS context controls which registry rows it can read. The audit role
    # must have no table access, and the application role must never write.
    for role in ("nlc_app_role", "nlc_ci_audit_role"):
        privileges = await db.execute(
            text(
                "SELECT "
                "has_table_privilege(:role, "
                "'public.legal_rule_aliases', 'SELECT'), "
                "has_table_privilege(:role, "
                "'public.legal_rule_aliases', 'INSERT'), "
                "has_table_privilege(:role, "
                "'public.legal_rule_aliases', 'UPDATE'), "
                "has_table_privilege(:role, "
                "'public.legal_rule_aliases', 'DELETE')"
            ),
            {"role": role},
        )
        can_select, can_insert, can_update, can_delete = privileges.one()
        if role == "nlc_app_role":
            assert can_select is True
            assert (can_insert, can_update, can_delete) == (False, False, False)
        else:
            assert (can_select, can_insert, can_update, can_delete) == (
                False, False, False, False
            )
