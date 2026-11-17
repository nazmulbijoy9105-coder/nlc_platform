"""Database governance controls for the global finding-context catalogue."""
import pytest
from sqlalchemy import text

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_governed_context_tables_are_forced_rls_and_append_only(db):
    tables = (
        "legal_rule_finding_contexts",
        "legal_rule_finding_context_reviews",
    )
    for table in tables:
        flags = await db.execute(text(
            "SELECT c.relrowsecurity, c.relforcerowsecurity "
            "FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
            "WHERE n.nspname='public' AND c.relname=:table"
        ), {"table": table})
        assert flags.one() == (True, True)

        triggers = await db.execute(text(
            "SELECT tgname FROM pg_trigger t "
            "JOIN pg_class c ON c.oid=t.tgrelid "
            "JOIN pg_namespace n ON n.oid=c.relnamespace "
            "WHERE n.nspname='public' AND c.relname=:table AND NOT t.tgisinternal"
        ), {"table": table})
        names = {row[0] for row in triggers.fetchall()}
        assert f"trg_{table}_append_only" in names

        policies = await db.execute(text(
            "SELECT policyname, cmd, qual, with_check FROM pg_policies "
            "WHERE schemaname='public' AND tablename=:table"
        ), {"table": table})
        by_command = {row[1]: row for row in policies.fetchall()}
        assert set(by_command) == {"SELECT", "INSERT"}
        assert "nlc_current_user_context_valid" in (by_command["SELECT"][2] or "")
        assert "nlc_current_user_principal" in (by_command["INSERT"][3] or "")
        assert "'ADMIN'" in by_command["INSERT"][3]
        assert "'CATALOG'" in by_command["INSERT"][3]

        for privilege in ("SELECT", "INSERT"):
            result = await db.execute(text(
                "SELECT has_table_privilege('nlc_app_role', :table, :privilege)"
            ), {"table": f"public.{table}", "privilege": privilege})
            assert result.scalar_one() is True
        for privilege in ("UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER"):
            result = await db.execute(text(
                "SELECT has_table_privilege('nlc_app_role', :table, :privilege)"
            ), {"table": f"public.{table}", "privilege": privilege})
            assert result.scalar_one() is False
        audit = await db.execute(text(
            "SELECT has_table_privilege('nlc_ci_audit_role', :table, 'SELECT')"
        ), {"table": f"public.{table}"})
        assert audit.scalar_one() is False


@pytest.mark.asyncio
async def test_context_database_triggers_bind_digest_and_reviewer_to_exact_version(db):
    context_fn = await db.execute(text(
        "SELECT pg_get_functiondef("
        "'public.nlc_verify_legal_finding_context()'::regprocedure)"
    ))
    context_definition = context_fn.scalar_one()
    assert "context_canonical" in context_definition
    assert "context_sha256" in context_definition
    assert "context_snapshot" in context_definition
    assert "effective_date_source_ref" in context_definition

    review_fn = await db.execute(text(
        "SELECT pg_get_functiondef("
        "'public.nlc_verify_legal_finding_context_review()'::regprocedure)"
    ))
    review_definition = review_fn.scalar_one()
    assert "reviewed_by = context_author" in review_definition
    assert "reviewed_context_sha256" in review_definition
    assert "context_authored_at" in review_definition
    assert "context_digest" in review_definition


@pytest.mark.asyncio
async def test_context_catalog_has_no_tenant_scope_or_legacy_backfill(db):
    columns = await db.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name='legal_rule_finding_contexts'"
    ))
    names = {row[0] for row in columns.fetchall()}
    assert {
        "historical_rule_id", "catalog_version", "source_namespace",
        "jurisdiction", "source_instrument", "source_provision",
        "effective_date", "effective_date_basis", "effective_date_source_ref",
        "context_snapshot", "context_canonical", "context_sha256",
        "authored_by", "authored_at",
    } <= names
    assert "company_id" not in names
    assert "tenant_id" not in names
