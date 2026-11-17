"""PostgreSQL policy and privilege checks for finding-level evidence bindings."""
import uuid
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.models.company import Company
from app.models.compliance import ComplianceEvaluationRun, ComplianceFlag
from app.models.database import set_rls_context
from app.models.enums import CompanyType, RevenueTier, RiskBand, SeverityLevel, FlagStatus
from app.models.finding_evidence import ComplianceFindingBinding

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

        triggers = await db.execute(
            text(
                "SELECT tgname FROM pg_trigger t "
                "JOIN pg_class c ON c.oid=t.tgrelid "
                "JOIN pg_namespace n ON n.oid=c.relnamespace "
                "WHERE n.nspname='public' AND c.relname=:table AND NOT t.tgisinternal"
            ),
            {"table": table},
        )
        trigger_names = {row[0] for row in triggers.fetchall()}
        assert f"trg_{table}_append_only" in trigger_names
        expected_guard = (
            "trg_finding_binding_insert_guard"
            if table == "compliance_finding_bindings"
            else "trg_finding_evidence_insert_guard"
        )
        assert expected_guard in trigger_names

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

        if table == "compliance_finding_bindings":
            constraint = await db.execute(
                text(
                    "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
                    "WHERE conrelid='public.compliance_finding_bindings'::regclass "
                    "AND conname='ck_finding_binding_attribution_status'"
                )
            )
            definition = constraint.scalar_one()
            assert "'ATTRIBUTED'" not in definition

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
async def test_unassigned_user_cannot_read_existing_finding_binding(db):
    """Exercise tenant RLS against a real row, not an empty relation."""
    company_id = uuid.uuid4()
    flag_id = uuid.uuid4()
    run_id = uuid.uuid4()
    db.add(Company(
        id=company_id,
        registration_number=f"RLS-{company_id.hex[:20]}",
        company_name="RLS isolation test company",
        company_type=CompanyType.PRIVATE_LIMITED,
        incorporation_date=date(2020, 1, 1),
        financial_year_end=date(2025, 12, 31),
    ))
    await db.flush()
    # Use a seeded catalogue key to satisfy the real compliance_flags FK.
    # The fixture's finding remains explicitly unresolved; this is not a legal assertion.
    rule_result = await db.execute(text("SELECT rule_id FROM legal_rules ORDER BY rule_id LIMIT 1"))
    fixture_rule_id = rule_result.scalar_one_or_none()
    assert fixture_rule_id is not None, "integration DB must contain seeded legal_rules"

    db.add(ComplianceFlag(
        id=flag_id, company_id=company_id, rule_id=fixture_rule_id,
        rule_version="test", flag_code="TEST-UNRESOLVED",
        statutory_basis="Not a statutory conclusion",
        severity=SeverityLevel.NOT_EVALUATED, score_impact=0,
        revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
        evaluation_state="NOT_EVALUATED", flag_status=FlagStatus.ACTIVE,
        triggered_date=date.today(),
        description="Integration fixture only; not a legal finding.",
    ))
    db.add(ComplianceEvaluationRun(
        id=run_id, company_id=company_id, risk_band=RiskBand.NOT_EVALUATED,
        calculated_at=datetime.now(timezone.utc), engine_version="test",
        score_hash="a" * 64, evaluation_status="NOT_RELEASED",
        trigger_source="TEST", active_flags_count=1, black_flags_count=0,
        flags_snapshot=[], fact_provenance_snapshot=[],
    ))
    await db.flush()
    db.add(ComplianceFindingBinding(
        company_id=company_id, compliance_flag_id=flag_id,
        evaluation_run_id=run_id, jurisdiction="BD",
        source_namespace="test-fixture", historical_rule_id=fixture_rule_id,
        resolution_status="UNRESOLVED", attribution_status="CURRENT_EVALUATION",
        effective_date=date.today(), evidence_status="MISSING",
        evidence_manifest_hash="b" * 64, finding_snapshot={},
        finding_snapshot_hash="c" * 64,
    ))
    await db.flush()

    await set_rls_context(db, "00000000-0000-0000-0000-000000000001")
    result = await db.execute(text("SELECT count(*) FROM public.compliance_finding_bindings"))
    assert result.scalar_one() == 0
    result = await db.execute(text("SELECT count(*) FROM public.compliance_finding_evidence"))
    assert result.scalar_one() == 0
    await db.rollback()


@pytest.mark.asyncio
async def test_runtime_role_cannot_update_or_delete_finding_audit_rows(db):
    """Privilege checks apply even when the target relation currently has no rows."""
    for table in ("compliance_finding_bindings", "compliance_finding_evidence"):
        for statement in (
            f"UPDATE public.{table} SET created_at = created_at WHERE false",
            f"DELETE FROM public.{table} WHERE false",
        ):
            with pytest.raises(DBAPIError):
                async with db.begin_nested():
                    await db.execute(text("SET LOCAL ROLE nlc_app_role"))
                    await db.execute(text(statement))
