from __future__ import annotations

from datetime import date

import pytest
from fastapi import HTTPException

from app.rule_engine.engine import (
    CompanyProfile,
    NLCRuleEngine,
    RuleState,
    Severity,
    _input_coverage,
)
from app.services.company_fact_service import CompanyFactService


def test_unattributed_legacy_profile_values_do_not_count_as_verified_coverage():
    profile = CompanyProfile(
        company_id="coverage-test",
        company_name="Coverage Test Ltd",
        last_agm_date=date(2025, 6, 1),
        last_audit_signed_date=date(2025, 12, 31),
        last_return_filed_year=2025,
        first_auditor_appointed=True,
        tin_obtained=True,
        current_director_count=2,
        member_count=5,
        trade_license_obtained=False,
        maintained_registers=[],
        verified_fact_keys=frozenset(),
    )

    assert _input_coverage(profile) == 0.0
    output = NLCRuleEngine(today=date(2026, 11, 21)).evaluate(profile)
    assert output.score_breakdown.risk_band == Severity.NOT_EVALUATED
    assert not any(flag.rule_id in {"TL-001", "REG-001", "REG-002"} for flag in output.flags)


def test_verified_document_facts_count_toward_score_coverage():
    keys = frozenset({
        "last_agm_date",
        "last_audit_signed_date",
        "last_return_filed_year",
        "first_auditor_appointed",
        "tin_obtained",
        "current_director_count",
        "member_count",
    })
    profile = CompanyProfile(
        company_id="coverage-test",
        company_name="Coverage Test Ltd",
        last_agm_date=date(2025, 6, 1),
        last_audit_signed_date=date(2025, 12, 31),
        last_return_filed_year=2025,
        first_auditor_appointed=True,
        tin_obtained=True,
        current_director_count=2,
        member_count=5,
        verified_fact_keys=keys,
    )

    assert _input_coverage(profile) == 1.0


def test_only_verified_trade_license_absence_can_emit_scored_finding():
    engine = NLCRuleEngine(today=date(2026, 11, 21))
    legacy = CompanyProfile(
        company_id="trade-license-test",
        company_name="Trade Licence Test Ltd",
        trade_license_obtained=False,
        verified_fact_keys=frozenset(),
    )
    assert not any(flag.rule_id == "TL-001" for flag in engine.evaluate(legacy).flags)

    verified = CompanyProfile(
        company_id="trade-license-test",
        company_name="Trade Licence Test Ltd",
        trade_license_obtained=False,
        verified_fact_keys=frozenset({"trade_license_obtained"}),
    )
    flag = next(flag for flag in engine.evaluate(verified).flags if flag.rule_id == "TL-001")
    assert flag.state == RuleState.VERIFIED_ABSENT
    assert flag.eval_state == "VIOLATION"
    assert flag.score_impact == 5


def test_internal_trust_metadata_cannot_be_asserted_as_a_company_fact():
    for key in ("verified_fact_keys", "catalogue_rule_active", "catalogue_rule_versions"):
        with pytest.raises(HTTPException) as exc:
            CompanyFactService._normalize_fact_key(key)
        assert exc.value.status_code == 422



def test_legacy_verification_flags_do_not_count_without_fresh_fact_keys():
    profile = CompanyProfile(
        company_id="coverage-test",
        company_name="Coverage Test Ltd",
        last_agm_date=date(2025, 6, 1),
        agm_history_verified=True,
        agm_history_evidence_ref="legacy-evidence-ref",
        audit_completion_verified=True,
        audit_completion_evidence_ref="legacy-audit-ref",
        annual_return_filing_status_verified=True,
        annual_return_filing_status_evidence_ref="legacy-return-ref",
        first_auditor_appointed=True,
        first_auditor_appointment_verified=True,
        first_auditor_appointment_evidence_ref="legacy-appointment-ref",
        current_director_count=2,
        directors_verified=True,
        directors_verification_evidence_ref="legacy-director-ref",
        member_count=5,
        verified_fact_keys=frozenset(),
    )
    assert _input_coverage(profile) == 0.0
