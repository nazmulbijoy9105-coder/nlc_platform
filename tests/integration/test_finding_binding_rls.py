"""PostgreSQL policy and privilege checks for finding-level evidence bindings."""
import pytest
from sqlalchemy import text

from app.models.database import set_rls_context

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_finding_binding_tables_are_forced_tenant_scoped_append_only(db):
    tables = ("compliance_finding_bindings", "compliance_finding_evidence")
    for table in tables:
        flags = await db.execute(
            text(
                "SELECT c.relrowsecurity, c.relforcerowsecurity "
                "FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                "WHERE n.nspname='public' AND c.relname=:table"
            ),
            {"table": table},
        )
        assert flags.one() == (True, True)

        policies = await db.execute(
            text(
                "SELECT policyname, cmd, qual, with_check FROM pg_policies "
                "WHERE schemaname='public' AND tablename=:table ORDER BY policyname"
            ),
            {"table": table},
        )
        rows = policies.fetchall()
        assert len(rows) == 2
        by_command = {row[1]: row for row in rows}
        assert set(by_command) == {"SELECT", "INSERT"}
        assert "nlc_can_access_company" in (by_command["SELECT"][2] or "")
        assert "nlc_can_edit_company" in (by_command["INSERT"][3] or "")
        assert "nlc_can_access_company" in (by_command["INSERT"][3] or "")

        for privilege in ("SELECT", "INSERT"):
            result = await db.execute(
                text("SELECT has_table_privilege('nlc_app_role', :table, :privilege)"),
                {"table": f"public.{table}", "privilege": privilege},
            )
            assert result.scalar_one() is True
        for privilege in ("UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER"):
            result = await db.execute(
                text("SELECT has_table_privilege('nlc_app_role', :table, :privilege)"),
                {"table": f"public.{table}", "privilege": privilege},
            )
            assert result.scalar_one() is False
        audit = await db.execute(
            text("SELECT has_table_privilege('nlc_ci_audit_role', :table, 'SELECT')"),
            {"table": f"public.{table}"},
        )
        assert audit.scalar_one() is False


@pytest.mark.asyncio
async def test_unsigned_or_unassigned_user_cannot_read_finding_bindings(db):
    await set_rls_context(db, "00000000-0000-0000-0000-000000000001")
    for table in ("compliance_finding_bindings", "compliance_finding_evidence"):
        result = await db.execute(text(f"SELECT count(*) FROM public.{table}"))
        assert result.scalar_one() == 0
    await db.rollback()
