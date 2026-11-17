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
from app.rule_engine.canonical_identity import canonical_definition_json, canonical_definition_hash

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
        if table == "compliance_finding_bindings":
            assert "trg_finding_binding_payload_digest" in trigger_names
        else:
            assert "trg_finding_evidence_payload_digest" in trigger_names

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
async def test_database_manifest_verifier_reconstructs_exact_python_evidence_shape(db):
    """The deferred DB comparison must include every key in the Python manifest row."""
    result = await db.execute(text(
        "SELECT pg_get_functiondef("
        "'public.nlc_verify_finding_manifest_children()'::regprocedure)"
    ))
    definition = result.scalar_one()
    assert "e.evidence_canonical::jsonb" in definition
    assert "'evidence_canonical'" in definition
    assert "'fact_value_canonical'" in definition
    assert "'evidence_hash'" in definition


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
    finding_payload = {"finding": {}}
    manifest_payload = {"evidence": []}
    finding_canonical = canonical_definition_json(finding_payload)
    manifest_canonical = canonical_definition_json(manifest_payload)
    db.add(ComplianceFindingBinding(
        company_id=company_id, compliance_flag_id=flag_id,
        evaluation_run_id=run_id, jurisdiction="BD",
        source_namespace="test-fixture", historical_rule_id=fixture_rule_id,
        resolution_status="UNRESOLVED", attribution_status="CURRENT_EVALUATION",
        effective_date=date.today(), evidence_status="MISSING",
        evidence_manifest_hash=canonical_definition_hash(manifest_payload),
        evidence_manifest_canonical=manifest_canonical,
        finding_snapshot={}, finding_snapshot_canonical=finding_canonical,
        finding_snapshot_hash=canonical_definition_hash(finding_payload),
    ))
    await db.flush()

    # A syntactically valid but deliberately incorrect digest must be rejected
    # by PostgreSQL itself, not merely by the Python persistence helper.
    with pytest.raises(DBAPIError):
        async with db.begin_nested():
            await db.execute(text("""
                INSERT INTO public.compliance_finding_bindings (
                    company_id, compliance_flag_id, evaluation_run_id,
                    jurisdiction, source_namespace, historical_rule_id,
                    resolution_status, attribution_status, effective_date,
                    evidence_status, evidence_manifest_hash, evidence_manifest_canonical,
                    finding_snapshot, finding_snapshot_canonical, finding_snapshot_hash
                ) VALUES (
                    :company_id, :flag_id, :run_id, 'BD', 'test-fixture',
                    'TEST-TAMPER', 'UNRESOLVED', 'CURRENT_EVALUATION', CURRENT_DATE,
                    'MISSING', :manifest_hash, :manifest_canonical,
                    '{}'::jsonb, :finding_canonical, :bad_hash
                )
            """), {
                "company_id": company_id, "flag_id": flag_id, "run_id": run_id,
                "manifest_hash": canonical_definition_hash(manifest_payload),
                "manifest_canonical": manifest_canonical,
                "finding_canonical": finding_canonical,
                "bad_hash": "0" * 64,
            })

    # Exercise the append-only triggers against an existing row using the
    # privileged integration connection; runtime-role privilege checks alone
    # do not prove that the database triggers themselves reject mutation.
    for statement in (
        "UPDATE public.compliance_finding_bindings SET finding_snapshot = '{}'::jsonb WHERE compliance_flag_id = :flag_id",
        "DELETE FROM public.compliance_finding_bindings WHERE compliance_flag_id = :flag_id",
    ):
        with pytest.raises(DBAPIError):
            async with db.begin_nested():
                await db.execute(text(statement), {"flag_id": flag_id})

    # Create a second valid flag/run pair before switching to an unassigned
    # actor. This ensures the attempted INSERT cannot fail merely because of
    # a missing FK parent; the expected rejection is the tenant INSERT policy.
    denied_company_id = uuid.uuid4()
    denied_flag_id = uuid.uuid4()
    denied_run_id = uuid.uuid4()
    db.add(Company(
        id=denied_company_id,
        registration_number=f"RLS-DENIED-{denied_company_id.hex[:16]}",
        company_name="RLS denied-insert fixture company",
        company_type=CompanyType.PRIVATE_LIMITED,
        incorporation_date=date(2020, 1, 1),
        financial_year_end=date(2025, 12, 31),
    ))
    await db.flush()
    db.add(ComplianceFlag(
        id=denied_flag_id, company_id=denied_company_id, rule_id=fixture_rule_id,
        rule_version="test", flag_code="TEST-RLS-INSERT",
        statutory_basis="Not a statutory conclusion",
        severity=SeverityLevel.NOT_EVALUATED, score_impact=0,
        revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
        evaluation_state="NOT_EVALUATED", flag_status=FlagStatus.ACTIVE,
        triggered_date=date.today(),
        description="Integration fixture only; not a legal finding.",
    ))
    db.add(ComplianceEvaluationRun(
        id=denied_run_id, company_id=denied_company_id, risk_band=RiskBand.NOT_EVALUATED,
        calculated_at=datetime.now(timezone.utc), engine_version="test",
        score_hash="d" * 64, evaluation_status="NOT_RELEASED",
        trigger_source="TEST", active_flags_count=1, black_flags_count=0,
        flags_snapshot=[], fact_provenance_snapshot=[],
    ))
    await db.flush()

    await set_rls_context(db, "00000000-0000-0000-0000-000000000001")
    result = await db.execute(text("SELECT count(*) FROM public.compliance_finding_bindings"))
    assert result.scalar_one() == 0
    result = await db.execute(text("SELECT count(*) FROM public.compliance_finding_evidence"))
    assert result.scalar_one() == 0
    with pytest.raises(DBAPIError):
        async with db.begin_nested():
            await db.execute(text("""
                INSERT INTO public.compliance_finding_bindings (
                    company_id, compliance_flag_id, evaluation_run_id,
                    jurisdiction, source_namespace, historical_rule_id,
                    resolution_status, attribution_status, effective_date,
                    evidence_status, evidence_manifest_hash, evidence_manifest_canonical,
                    finding_snapshot, finding_snapshot_canonical, finding_snapshot_hash
                ) VALUES (
                    :company_id, :flag_id, :run_id,
                    'BD', 'test-fixture', 'TEST-RLS-INSERT',
                    'UNRESOLVED', 'CURRENT_EVALUATION', CURRENT_DATE,
                    'MISSING', :manifest_hash, :manifest_canonical,
                    '{}'::jsonb, :finding_canonical, :snapshot_hash
                )
            """), {
                "company_id": denied_company_id, "flag_id": denied_flag_id,
                "run_id": denied_run_id,
                "manifest_hash": canonical_definition_hash(manifest_payload),
                "manifest_canonical": manifest_canonical,
                "finding_canonical": finding_canonical,
                "snapshot_hash": canonical_definition_hash(finding_payload),
            })
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


@pytest.mark.asyncio
async def test_nonempty_evidence_manifest_matches_database_rows_at_commit(db):
    """A real child evidence row must match the canonical parent manifest."""
    from app.models.company_fact import CompanyFact
    from app.models.user import User
    from app.models.enums import UserRole
    from app.rule_engine.canonical_identity import RuleResolution
    from app.rule_engine.finding_binding import (
        build_finding_binding_snapshot,
        persist_finding_binding,
    )

    today = date.today()
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    flag_id = uuid.uuid4()
    run_id = uuid.uuid4()
    db.add(User(
        id=user_id,
        email=f"finding-evidence-{user_id.hex[:12]}@nlctest.com",
        full_name="Finding Evidence Integration Actor",
        password_hash="!integration-only-no-login",
        role=UserRole.ADMIN_STAFF,
        is_active=True,
        totp_enabled=False,
    ))
    db.add(Company(
        id=company_id,
        registration_number=f"FINDING-{company_id.hex[:16]}",
        company_name="Finding Evidence Integration Ltd",
        company_type=CompanyType.PRIVATE_LIMITED,
        incorporation_date=date(2020, 1, 1),
        financial_year_end=date(2025, 12, 31),
    ))
    await db.flush()

    rule_result = await db.execute(
        text("SELECT rule_id FROM legal_rules ORDER BY rule_id LIMIT 1")
    )
    rule_id = rule_result.scalar_one()
    db.add(ComplianceFlag(
        id=flag_id,
        company_id=company_id,
        rule_id=rule_id,
        rule_version="integration",
        flag_code="TEST-EVIDENCE-MANIFEST",
        statutory_basis="Integration fixture only; not a legal conclusion.",
        severity=SeverityLevel.NOT_EVALUATED,
        score_impact=0,
        revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
        evaluation_state="NOT_EVALUATED",
        flag_status=FlagStatus.ACTIVE,
        triggered_date=today,
        description="Integration fixture only; not a legal finding.",
    ))
    db.add(ComplianceEvaluationRun(
        id=run_id,
        company_id=company_id,
        risk_band=RiskBand.NOT_EVALUATED,
        calculated_at=datetime.now(timezone.utc),
        engine_version="integration",
        score_hash="e" * 64,
        evaluation_status="NOT_RELEASED",
        trigger_source="TEST",
        active_flags_count=1,
        black_flags_count=0,
        flags_snapshot=[],
        fact_provenance_snapshot=[],
    ))
    fact = CompanyFact(
        id=uuid.uuid4(),
        company_id=company_id,
        fact_key="integration_evidence_fact",
        fact_value=False,
        trust_level="USER_ASSERTED",
        asserted_by=user_id,
        observed_on=today,
        verification_status="UNVERIFIED",
    )
    db.add(fact)
    await db.flush()

    source_namespace = "integration-test:manifest"
    resolution = RuleResolution(
        status="UNRESOLVED",
        source_namespace=source_namespace,
        historical_rule_id=rule_id,
        effective_date=today,
    )
    snapshot = build_finding_binding_snapshot(
        company_id=str(company_id),
        compliance_flag_id=str(flag_id),
        evaluation_run_id=str(run_id),
        source_namespace=source_namespace,
        historical_rule_id=rule_id,
        jurisdiction="BD",
        effective_date=today,
        resolution=resolution,
        finding_snapshot={"evaluation_state": "NOT_EVALUATED", "score_impact": 0},
        evidence_facts=[{
            "fact_id": str(fact.id),
            "fact_key": fact.fact_key,
            "fact_value": fact.fact_value,
            "trust_level": fact.trust_level,
            "verification_status": fact.verification_status,
            "observed_on": today.isoformat(),
            "asserted_by": str(user_id),
        }],
        required_fact_keys=[fact.fact_key],
    )
    binding = await persist_finding_binding(db, snapshot)

    # Force deferred constraint triggers now, so a mismatch fails this test
    # rather than being hidden by the fixture's transaction rollback.
    await db.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    result = await db.execute(
        text("SELECT count(*) FROM compliance_finding_evidence WHERE company_fact_id=:fact_id"),
        {"fact_id": fact.id},
    )
    assert result.scalar_one() == 1

 
    # Exercise database-side SHA-256 checks for both evidence payload layers.
    # The Python helper is used only to construct a valid baseline; each
    # mutation below is submitted directly to PostgreSQL.
    for suffix, tampered_column in (
        ("FACT-HASH", "fact_value_canonical"),
        ("EVIDENCE-HASH", "evidence_canonical"),
    ):
        tamper_fact = CompanyFact(
            id=uuid.uuid4(),
            company_id=company_id,
            fact_key=f"integration_{suffix.lower()}",
            fact_value=False,
            trust_level="USER_ASSERTED",
            asserted_by=user_id,
            observed_on=today,
            verification_status="UNVERIFIED",
        )
        db.add(tamper_fact)
        await db.flush()
        candidate = build_finding_binding_snapshot(
            company_id=str(company_id),
            compliance_flag_id=str(flag_id),
            evaluation_run_id=str(run_id),
            source_namespace=source_namespace,
            historical_rule_id=rule_id,
            jurisdiction="BD",
            effective_date=today,
            resolution=resolution,
            finding_snapshot={"evaluation_state": "NOT_EVALUATED", "score_impact": 0},
            evidence_facts=[{
                "fact_id": str(tamper_fact.id),
                "fact_key": tamper_fact.fact_key,
                "fact_value": tamper_fact.fact_value,
                "trust_level": tamper_fact.trust_level,
                "verification_status": tamper_fact.verification_status,
                "observed_on": today.isoformat(),
                "asserted_by": str(user_id),
            }],
        )["evidence"][0]
        candidate[tampered_column] += " "
        with pytest.raises(DBAPIError):
            async with db.begin_nested():
                await db.execute(text("""
                    INSERT INTO public.compliance_finding_evidence (
                        binding_id, company_id, company_fact_id, evidence_role,
                        fact_key, fact_value_snapshot, fact_value_canonical,
                        evidence_canonical, fact_value_hash, trust_level,
                        verification_status, observed_on, source_reference,
                        document_id, document_sha256, asserted_by,
                        authorized_uploader_id, uploaded_at, verified_by,
                        verified_at, evidence_hash
                    ) VALUES (
                        :binding_id, :company_id, :company_fact_id, :evidence_role,
                        :fact_key, :fact_value_snapshot, :fact_value_canonical,
                        :evidence_canonical, :fact_value_hash, :trust_level,
                        :verification_status, :observed_on, :source_reference,
                        :document_id, :document_sha256, :asserted_by,
                        :authorized_uploader_id, :uploaded_at, :verified_by,
                        :verified_at, :evidence_hash
                    )
                """), {"binding_id": binding.id, **candidate})

    # A valid child row whose digest is correct but which is absent from the
    # immutable parent manifest must fail at the deferred manifest constraint.
    extra_fact = CompanyFact(
        id=uuid.uuid4(),
        company_id=company_id,
        fact_key="integration_manifest_extra",
        fact_value=False,
        trust_level="USER_ASSERTED",
        asserted_by=user_id,
        observed_on=today,
        verification_status="UNVERIFIED",
    )
    db.add(extra_fact)
    await db.flush()
    extra_evidence = build_finding_binding_snapshot(
        company_id=str(company_id),
        compliance_flag_id=str(flag_id),
        evaluation_run_id=str(run_id),
        source_namespace=source_namespace,
        historical_rule_id=rule_id,
        jurisdiction="BD",
        effective_date=today,
        resolution=resolution,
        finding_snapshot={"evaluation_state": "NOT_EVALUATED", "score_impact": 0},
        evidence_facts=[{
            "fact_id": str(extra_fact.id),
            "fact_key": extra_fact.fact_key,
            "fact_value": extra_fact.fact_value,
            "trust_level": extra_fact.trust_level,
            "verification_status": extra_fact.verification_status,
            "observed_on": today.isoformat(),
            "asserted_by": str(user_id),
        }],
    )["evidence"][0]
    with pytest.raises(DBAPIError):
        async with db.begin_nested():
            await db.execute(text("SET CONSTRAINTS ALL DEFERRED"))
            await db.execute(text("""
                INSERT INTO public.compliance_finding_evidence (
                    binding_id, company_id, company_fact_id, evidence_role,
                    fact_key, fact_value_snapshot, fact_value_canonical,
                    evidence_canonical, fact_value_hash, trust_level,
                    verification_status, observed_on, source_reference,
                    document_id, document_sha256, asserted_by,
                    authorized_uploader_id, uploaded_at, verified_by,
                    verified_at, evidence_hash
                ) VALUES (
                    :binding_id, :company_id, :company_fact_id, :evidence_role,
                    :fact_key, :fact_value_snapshot, :fact_value_canonical,
                    :evidence_canonical, :fact_value_hash, :trust_level,
                    :verification_status, :observed_on, :source_reference,
                    :document_id, :document_sha256, :asserted_by,
                    :authorized_uploader_id, :uploaded_at, :verified_by,
                    :verified_at, :evidence_hash
                )
            """), {"binding_id": binding.id, **extra_evidence})
            await db.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
