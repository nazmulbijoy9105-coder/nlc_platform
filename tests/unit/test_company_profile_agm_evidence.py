import pytest
from datetime import date
from types import SimpleNamespace

import app.rule_engine.engine as engine_module

from app.services.company_service import _agm_profile_evidence
from app.services.compliance_service import _applied_score_impacts, _is_rescue_required
from app.rule_engine.engine import RuleState, _input_coverage
from app.rule_engine.engine import CompanyProfile, NLCRuleEngine


def test_missing_agm_record_keeps_attendance_and_auditor_status_unknown():
    evidence = _agm_profile_evidence(None)

    assert evidence["members_present_at_agm"] is None
    assert evidence["agm_attendance_verified"] is False
    assert evidence["agm_quorum_required"] is None
    assert evidence["agm_quorum_basis_verified"] is False
    assert evidence["agm_quorum_met"] is None
    assert evidence["auditor_reappointed_at_agm"] is None
    assert evidence["auditor_reappointment_verified"] is False
    assert evidence["agm_minutes_prepared"] is None
    assert evidence["agm_notice_verified_absent"] is None


def test_agm_profile_evidence_comes_from_the_latest_agm_record():
    meeting = SimpleNamespace(
        members_present=3,
        auditor_reappointed=False,
        minutes_prepared=True,
        minutes_document_id="AGM-MINUTES-DOC-001",
        notice_sent_date=date(2026, 1, 1),
        members_present_verified=True,
        members_present_evidence_ref="AGM-MINUTES-001",
        members_present_verified_at=date(2026, 1, 2),
        members_present_verified_by="reviewer-001",
        quorum_required=2,
        quorum_required_verified=True,
        quorum_evidence_ref="AOA-QUORUM-001",
        quorum_verified_at=date(2026, 1, 2),
        quorum_verified_by="reviewer-001",
        quorum_met=True,
        auditor_reappointment_verified=True,
        auditor_reappointment_evidence_ref="AGM-MINUTES-001",
        auditor_reappointment_verified_at=date(2026, 1, 2),
        auditor_reappointment_verified_by="reviewer-001",
    )

    evidence = _agm_profile_evidence(meeting)

    assert evidence["members_present_at_agm"] == 3
    assert evidence["agm_attendance_verified"] is True
    assert evidence["agm_quorum_required"] == 2
    assert evidence["agm_quorum_basis_verified"] is True
    assert evidence["agm_quorum_met"] is True
    assert evidence["auditor_reappointed_at_agm"] is False
    # A stored boolean/document ID is still not a reviewer-verified
    # minute-book finding; the engine must remain fail-closed.
    assert evidence["agm_minutes_prepared"] is None
    assert evidence["notice_sent_date"] == date(2026, 1, 1)
    assert evidence["agm_notice_verified_absent"] is None


def test_default_zero_attendance_is_not_treated_as_verified_quorum_breach():
    meeting = SimpleNamespace(
        members_present=0,
        auditor_reappointed=True,
        minutes_prepared=False,
        notice_sent_date=None,
    )

    evidence = _agm_profile_evidence(meeting)

    assert evidence["members_present_at_agm"] is None
    assert evidence["auditor_reappointed_at_agm"] is None
    assert evidence["agm_minutes_prepared"] is None




def test_unverified_raw_agm_values_are_not_promoted_to_legal_facts():
    meeting = SimpleNamespace(
        members_present=4,
        quorum_required=2,
        quorum_met=False,
        auditor_reappointed=False,
        minutes_prepared=False,
        notice_missing=True,
        accounts_adopted=False,
        agm_held_without_audit=True,
    )

    evidence = _agm_profile_evidence(meeting)

    assert evidence["members_present_at_agm"] is None
    assert evidence["agm_quorum_required"] is None
    assert evidence["agm_quorum_met"] is None
    assert evidence["auditor_reappointed_at_agm"] is None
    assert evidence["agm_minutes_prepared"] is None
    assert evidence["agm_notice_verified_absent"] is None
    assert evidence["accounts_adopted_at_agm"] is None
    assert evidence["agm_held_without_audit"] is None


def test_quorum_result_requires_both_verified_attendance_and_verified_basis():
    meeting = SimpleNamespace(
        members_present=1,
        members_present_verified=True,
        members_present_evidence_ref="AGM-MINUTES-002",
        members_present_verified_at=date(2026, 1, 2),
        members_present_verified_by="reviewer-001",
        quorum_required=2,
        quorum_required_verified=False,
        quorum_evidence_ref=None,
        quorum_verified_at=None,
        quorum_verified_by=None,
        quorum_met=False,
    )

    evidence = _agm_profile_evidence(meeting)

    assert evidence["members_present_at_agm"] == 1
    assert evidence["agm_attendance_verified"] is True
    assert evidence["agm_quorum_required"] is None
    assert evidence["agm_quorum_met"] is None

def test_missing_agm_evidence_does_not_create_quorum_or_reappointment_flags():
    today = date.today()
    profile = CompanyProfile(
        company_id="agm-evidence-test",
        company_name="AGM Evidence Test Ltd",
        incorporation_date=date(today.year - 3, 1, 1),
        agm_count=1,
        last_agm_date=today.replace(day=1),
        agm_held_this_cycle=True,
        members_present_at_agm=None,
        auditor_reappointed_at_agm=None,
        agm_minutes_prepared=None,
        first_auditor_appointed=True,
        audit_complete=True,
        annual_return_filed=True,
    )

    result = NLCRuleEngine().evaluate(profile)
    fired_rule_ids = {flag.rule_id for flag in result.flags}

    assert "AGM-005" not in fired_rule_ids
    assert "AGM-006" not in fired_rule_ids
    assert "AUD-004" not in fired_rule_ids


def test_director_count_from_local_records_is_not_rjsc_verified():
    today = date.today()
    profile = CompanyProfile(
        company_id="director-verification-test",
        company_name="Director Verification Test Ltd",
        incorporation_date=date(today.year - 2, 1, 1),
        current_director_count=0,
        directors_verified=False,
        agm_count=1,
        annual_return_filed=True,
        first_auditor_appointed=True,
        audit_complete=True,
    )

    result = NLCRuleEngine().evaluate(profile)
    assert "INC-003" not in {flag.rule_id for flag in result.flags}


def test_verified_zero_directors_triggers_minimum_director_rule():
    today = date.today()
    profile = CompanyProfile(
        company_id="verified-director-test",
        company_name="Verified Director Test Ltd",
        incorporation_date=date(today.year - 2, 1, 1),
        current_director_count=0,
        directors_verified=True,
        directors_verification_evidence_ref="RJSC-DIRECTORS-001",
        directors_verified_at=today,
        directors_verified_by="reviewer-001",
        agm_count=1,
        annual_return_filed=True,
        first_auditor_appointed=True,
        audit_complete=True,
    )

    result = NLCRuleEngine().evaluate(profile)
    assert "INC-003" in {flag.rule_id for flag in result.flags}


def test_score_impact_reporting_respects_verified_rule_gate_and_category_caps(monkeypatch):
    # Simulate an internally source-checked rule while the release gate is closed.
    monkeypatch.setattr(engine_module, "VERIFIED_RULE_IDS", frozenset({"AGM-001"}))
    monkeypatch.setattr(engine_module, "LEGAL_SCORE_RELEASED", False)
    flags = [
        SimpleNamespace(
            rule_id="AGM-001", score_impact=20, state=RuleState.NON_COMPLIANT,
            eval_state="VIOLATION", resolved=False, conditional_applies=True,
        ),
        SimpleNamespace(
            rule_id="AGM-001", score_impact=20, state=RuleState.NON_COMPLIANT,
            eval_state="VIOLATION", resolved=False, conditional_applies=True,
        ),
        SimpleNamespace(
            rule_id="TAX-001", score_impact=10, state=RuleState.NON_COMPLIANT,
            eval_state="VIOLATION", resolved=False, conditional_applies=True,
        ),
    ]

    applied = _applied_score_impacts(flags)

    # AGM-001 is internally source-checked, but the global statutory release
    # gate is still closed; TAX-001 is not in the internal allowlist.
    assert applied[0] == {"applied": 0, "status": "LEGAL_SCORE_NOT_RELEASED"}
    assert applied[1] == {"applied": 0, "status": "LEGAL_SCORE_NOT_RELEASED"}
    assert applied[2] == {"applied": 0, "status": "EXCLUDED_UNVERIFIED_RULE"}


def test_unknown_flags_are_not_reported_as_applied_deductions():
    flag = SimpleNamespace(
        rule_id="AGM-001", score_impact=15, state=RuleState.UNKNOWN,
        eval_state="UNKNOWN", resolved=False, conditional_applies=True,
    )

    assert _applied_score_impacts([flag])[0]["applied"] == 0


def test_rescue_required_is_based_on_findings_not_sequence_generation():
    output = SimpleNamespace(
        score_breakdown=SimpleNamespace(
            black_flag_count=0, red_flag_count=1, override_applied=False,
        ),
        rescue_sequence=[],
    )

    assert _is_rescue_required(output) is True


def test_missing_capital_resolution_evidence_does_not_create_violation():
    today = date.today()
    profile = CompanyProfile(
        company_id="capital-evidence-test",
        company_name="Capital Evidence Test Ltd",
        incorporation_date=date(today.year - 2, 1, 1),
        capital_increase_date=date(today.year - 1, 1, 1),
        capital_increase_resolution=None,
        agm_count=1,
        annual_return_filed=True,
        first_auditor_appointed=True,
        audit_complete=True,
    )

    result = NLCRuleEngine().evaluate(profile)
    assert "CAP-001" not in {flag.rule_id for flag in result.flags}


def test_unverified_director_rows_do_not_inflate_evidence_coverage():
    unverified = CompanyProfile(
        company_id="coverage-unverified",
        company_name="Coverage Test Ltd",
        current_director_count=3,
        directors_verified=False,
    )
    verified = CompanyProfile(
        company_id="coverage-verified",
        company_name="Coverage Test Ltd",
        current_director_count=3,
        directors_verified=True,
    )

    assert _input_coverage(unverified) == 0.0
    assert _input_coverage(verified) > 0.0


def test_black_override_is_reported_separately_from_category_deduction():
    flag = SimpleNamespace(
        rule_id="ESC-003", score_impact=10, state=RuleState.NON_COMPLIANT,
        eval_state="VIOLATION", resolved=False, conditional_applies=True,
        is_black_override=True, severity="BLACK",
    )

    assert _applied_score_impacts([flag])[0] == {
        "applied": 0,
        "status": "EXCLUDED_UNVERIFIED_RULE",
    }


def test_agm_api_response_hides_unverified_raw_values():
    from app.api.filings import _agm_to_response

    meeting = SimpleNamespace(
        id="agm-001",
        company_id="company-001",
        financial_year=2025,
        agm_deadline=date(2026, 6, 30),
        agm_date=date(2026, 5, 1),
        rjsc_filing_date=None,
        quorum_met=False,
        quorum_required=2,
        quorum_basis="SECTION_85_2_B_DEFAULT_ARTICLES_NOT_REVIEWED",
        venue="Dhaka",
        members_present=1,
        auditor_reappointed=False,
        accounts_adopted=False,
        agm_held_without_audit=True,
        minutes_prepared=False,
        minutes_document_id=None,
        is_default=False,
        created_at=None,
        members_present_verified=False,
        members_present_evidence_ref=None,
        members_present_verified_at=None,
        members_present_verified_by=None,
        quorum_required_verified=False,
        quorum_evidence_ref=None,
        quorum_verified_at=None,
        quorum_verified_by=None,
        auditor_reappointment_verified=False,
        auditor_reappointment_evidence_ref=None,
        auditor_reappointment_verified_at=None,
        auditor_reappointment_verified_by=None,
    )

    response = _agm_to_response(meeting)

    assert response.members_present is None
    assert response.quorum_required is None
    assert response.quorum_met is None
    assert response.quorum_basis is None
    assert response.auditor_reappointed is None
    assert response.accounts_adopted is None
    assert response.agm_held_without_audit is None
    assert response.minutes_prepared is None


def test_unverified_quorum_and_auditor_defaults_are_not_exposed_as_facts():
    meeting = SimpleNamespace(
        members_present=0,
        members_present_verified=False,
        members_present_evidence_ref=None,
        members_present_verified_at=None,
        members_present_verified_by=None,
        quorum_required=2,
        quorum_required_verified=False,
        quorum_evidence_ref=None,
        quorum_verified_at=None,
        quorum_verified_by=None,
        quorum_met=True,
        auditor_reappointed=True,
        auditor_reappointment_verified=False,
        auditor_reappointment_evidence_ref=None,
        auditor_reappointment_verified_at=None,
        auditor_reappointment_verified_by=None,
        minutes_prepared=False,
        notice_sent_date=None,
        notice_missing=False,
    )

    evidence = _agm_profile_evidence(meeting)

    assert evidence["members_present_at_agm"] is None
    assert evidence["agm_quorum_required"] is None
    assert evidence["agm_quorum_met"] is None
    assert evidence["auditor_reappointed_at_agm"] is None
    assert evidence["agm_minutes_prepared"] is None
