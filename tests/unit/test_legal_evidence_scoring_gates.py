import pytest
from datetime import date
from types import SimpleNamespace

import app.rule_engine.engine as engine_module

from app.rule_engine.engine import (
    CompanyProfile,
    ComplianceFlag,
    NLCRuleEngine,
    RevenueTier,
    RuleState,
    Severity,
    VERIFIED_RULE_IDS,
)
from app.services.compliance_service import _applied_score_impacts
from app.services.pdf_report_service import _render_score_reconciliation


def _profile(**overrides):
    values = {
        "company_id": "legal-gate-test",
        "company_name": "Legal Gate Test Ltd",
        "company_type": "PRIVATE_LIMITED",
        "incorporation_date": date(2020, 1, 31),
        "agm_count": 1,
        "agm_history_verified": True,
        "agm_history_evidence_ref": "AGM-HISTORY-TEST",
        "agm_history_verified_at": date(2026, 11, 1),
        "agm_history_verified_by": "reviewer-001",
        "last_agm_date": date(2025, 6, 1),
        "agm_held_this_cycle": True,
        "first_auditor_appointed": True,
        "audit_complete": True,
        "annual_return_filed": True,
        "moa_aoa_filed": True,
        "moa_aoa_verified": False,
        "moa_aoa_evidence_ref": None,
        "moa_aoa_verified_at": None,
        "moa_aoa_verified_by": None,
    }
    values.update(overrides)
    return CompanyProfile(**values)


def _flag(result, rule_id):
    return next(flag for flag in result.flags if flag.rule_id == rule_id)


def test_unapproved_black_override_is_excluded_before_override_semantics():
    flag = SimpleNamespace(
        rule_id="UNAPPROVED-TEST-ONLY",
        resolved=False,
        conditional_applies=True,
        state=RuleState.NON_COMPLIANT,
        eval_state="VIOLATION",
        severity=Severity.BLACK,
        is_black_override=True,
        score_impact=100,
    )

    result = _applied_score_impacts([flag])

    assert result == [{"applied": 0, "status": "EXCLUDED_UNVERIFIED_RULE"}]


def test_unapproved_black_rule_cannot_force_black_score_band():
    profile = _profile()
    unapproved_black = ComplianceFlag(
        rule_id="UNAPPROVED-TEST-ONLY",
        flag_code="UNAPPROVED-BLACK",
        severity=Severity.BLACK,
        score_impact=100,
        revenue_tier=RevenueTier.CORPORATE_RESCUE,
        description="Unapproved test finding.",
        statutory_basis="Test only; not a legal rule.",
        state=RuleState.NON_COMPLIANT,
        eval_state="VIOLATION",
        is_black_override=True,
    )

    result = NLCRuleEngine()._calculate_score([unapproved_black], profile)

    assert result.override_applied is False
    assert result.black_flag_count == 0
    assert result.risk_band == Severity.NOT_EVALUATED


def test_counsel_approved_black_override_is_honoured_by_engine(monkeypatch):
    # Simulate a separately approved rule and an explicitly authorised release.
    # The production default remains LEGAL_SCORE_RELEASED=False.
    monkeypatch.setattr(engine_module, "VERIFIED_RULE_IDS", frozenset({"AUD-003"}))
    monkeypatch.setattr(
        engine_module, "AUTHORIZED_BLACK_OVERRIDE_RULE_IDS", frozenset({"AUD-003"})
    )
    monkeypatch.setattr(engine_module, "LEGAL_SCORE_RELEASED", True)
    approved_black = ComplianceFlag(
        rule_id="AUD-003",
        flag_code="AUD-003",
        severity=Severity.BLACK,
        score_impact=25,
        revenue_tier=RevenueTier.CORPORATE_RESCUE,
        description="Approved test override.",
        statutory_basis="Test only.",
        state=RuleState.NON_COMPLIANT,
        eval_state="VIOLATION",
        is_black_override=True,
    )

    result = NLCRuleEngine()._calculate_score([approved_black], _profile())

    assert result.override_applied is True
    assert result.black_flag_count == 1
    assert result.final_score == 0


def test_pdf_reconciliation_ignores_unapproved_black_flag():
    unapproved_black = SimpleNamespace(
        rule_id="AUD-003",
        severity="BLACK",
        score_impact=25,
        score_impact_applied=0,
    )

    assert _render_score_reconciliation([unapproved_black], 100, "GREEN") == ""


def test_calendar_month_and_18_month_deadline_are_not_fixed_day_approximations():
    assert NLCRuleEngine._add_months(date(2024, 1, 31), 1) == date(2024, 2, 29)
    assert NLCRuleEngine._add_months(date(2023, 1, 31), 1) == date(2023, 2, 28)
    assert NLCRuleEngine._add_months(date(2024, 1, 31), 18) == date(2025, 7, 31)


def test_unverified_legacy_moa_false_is_unknown_not_a_breach():
    result = NLCRuleEngine().evaluate(
        _profile(moa_aoa_filed=False, moa_aoa_verified=False),
        today=date(2026, 11, 3),
    )
    flag = _flag(result, "INC-001")
    assert flag.state == RuleState.UNKNOWN
    assert flag.eval_state == "UNKNOWN"
    assert flag.score_impact == 0


def test_verified_moa_absence_can_be_evaluated_as_a_breach():
    result = NLCRuleEngine().evaluate(
        _profile(
            moa_aoa_filed=False,
            moa_aoa_verified=True,
            moa_aoa_evidence_ref="RJSC-CERT-REF-001",
            moa_aoa_verified_at=date(2026, 11, 1),
            moa_aoa_verified_by="reviewer-001",
        ),
        today=date(2026, 11, 3),
    )
    flag = _flag(result, "INC-001")
    assert flag.state == RuleState.NON_COMPLIANT
    assert flag.score_impact == 15


def test_two_verified_directors_with_unknown_subsidiary_status_are_not_black():
    result = NLCRuleEngine().evaluate(
        _profile(
            current_director_count=2,
            directors_verified=True,
            directors_verification_evidence_ref="RJSC-DIRECTORS-001",
            directors_verified_at=date(2026, 11, 1),
            directors_verified_by="reviewer-001",
            is_private_subsidiary_of_public_company=None,
            subsidiary_status_verified=False,
            subsidiary_status_verified_at=None,
            subsidiary_status_verified_by=None,
        ),
        today=date(2026, 11, 3),
    )
    flag = _flag(result, "INC-003")
    assert flag.state == RuleState.UNKNOWN
    assert flag.is_black_override is False


def test_private_subsidiary_of_public_company_requires_three_verified_directors():
    result = NLCRuleEngine().evaluate(
        _profile(
            current_director_count=2,
            directors_verified=True,
            directors_verification_evidence_ref="RJSC-DIRECTORS-002",
            directors_verified_at=date(2026, 11, 1),
            directors_verified_by="reviewer-001",
            is_private_subsidiary_of_public_company=True,
            subsidiary_status_verified=True,
            subsidiary_status_evidence_ref="GROUP-STRUCTURE-002",
            subsidiary_status_verified_at=date(2026, 11, 1),
            subsidiary_status_verified_by="reviewer-001",
        ),
        today=date(2026, 11, 3),
    )
    flag = _flag(result, "INC-003")
    assert flag.state == RuleState.NON_COMPLIANT
    assert flag.is_black_override is True
    assert flag.detail["required"] == 3


def test_agm_quorum_without_verified_attendance_or_basis_is_unknown():
    result = NLCRuleEngine().evaluate(
        _profile(
            members_present_at_agm=2,
            agm_attendance_verified=False,
            agm_attendance_evidence_ref=None,
            agm_quorum_required=3,
            agm_quorum_basis_verified=True,
            agm_quorum_evidence_ref="AOA-QUORUM-001",
        ),
        today=date(2026, 11, 3),
    )
    # Unverified attendance/quorum is not emitted as a confirmed compliance finding.
    assert "AGM-005" not in {flag.rule_id for flag in result.flags}


def test_agm_quorum_requires_verified_attendance_and_quorum_basis():
    result = NLCRuleEngine().evaluate(
        _profile(
            members_present_at_agm=2,
            agm_attendance_verified=True,
            agm_attendance_evidence_ref="AGM-MINUTES-001",
            agm_quorum_required=3,
            agm_quorum_basis_verified=True,
            agm_quorum_evidence_ref="AOA-QUORUM-001",
        ),
        today=date(2026, 11, 3),
    )
    flag = _flag(result, "AGM-005")
    assert flag.state == RuleState.NON_COMPLIANT
    # Section 85 quorum rule remains outside the production scoring allowlist
    # until the Articles-specific interpretation has independent legal approval.
    assert "AGM-005" not in VERIFIED_RULE_IDS


def test_unverified_red_finding_does_not_force_red_risk_band():
    profile = _profile()
    unknown_red = ComplianceFlag(
        rule_id="AGM-005",
        flag_code="AGM_QUORUM_UNVERIFIED",
        severity=Severity.RED,
        score_impact=15,
        revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
        description="Quorum basis is unknown.",
        statutory_basis="Section 85(2)(b), Companies Act 1994 (Bangladesh)",
        state=RuleState.UNKNOWN,
        eval_state="UNKNOWN",
    )
    score = NLCRuleEngine()._calculate_score([unknown_red], profile)
    assert score.risk_band == Severity.NOT_EVALUATED
    assert score.final_score == 100



def test_unverified_first_auditor_absence_is_not_a_confirmed_violation():
    result = NLCRuleEngine().evaluate(
        _profile(
            first_auditor_appointed=False,
            first_auditor_appointment_verified=False,
        ),
        today=date(2026, 11, 3),
    )
    flag = _flag(result, "AUD-001")
    assert flag.state == RuleState.UNKNOWN
    assert flag.score_impact == 0


def test_verified_audit_missing_at_agm_requires_lawyer_judgment_not_black():
    result = NLCRuleEngine().evaluate(
        _profile(
            audit_complete=False,
            audit_completion_verified=True,
            audit_completion_evidence_ref="AUDIT-REVIEW-001",
            audit_completion_verified_at=date(2026, 11, 1),
            audit_completion_verified_by="reviewer-001",
        ),
        today=date(2026, 11, 3),
    )
    flag = _flag(result, "AUD-003")
    assert flag.state == RuleState.REQUIRES_LAWYER_JUDGMENT
    assert flag.is_black_override is False
    assert flag.score_impact == 0


def test_public_company_requires_three_verified_directors():
    result = NLCRuleEngine().evaluate(
        _profile(
            company_type="PUBLIC_LIMITED",
            current_director_count=2,
            directors_verified=True,
            directors_verification_evidence_ref="RJSC-DIRECTORS-PUBLIC-001",
            directors_verified_at=date(2026, 11, 1),
            directors_verified_by="reviewer-001",
        ),
        today=date(2026, 11, 3),
    )
    flag = _flag(result, "INC-003")
    assert flag.state == RuleState.NON_COMPLIANT
    assert flag.detail["required"] == 3



def test_section_94_unverified_disqualification_allegation_is_unknown():
    result = NLCRuleEngine().evaluate(
        _profile(
            disqualification_grounds=[{
                "ground_type": "UNPAID_CALL",
                "director_name": "Director A",
                "evidence_ref": "NOTICE-001",
                "effective_date": "2026-01-01",
                "continuing_status": True,
                "days_since_payment_due": 120,
            }]
        ),
        today=date(2026, 11, 3),
    )
    flag = _flag(result, "DEF-001")
    assert flag.state == RuleState.UNKNOWN
    assert flag.score_impact == 0
    assert flag.is_black_override is False


def test_section_94_verified_disqualification_is_not_automatic_black():
    result = NLCRuleEngine().evaluate(
        _profile(
            disqualification_grounds=[{
                "ground_type": "UNPAID_CALL",
                "director_name": "Director A",
                "evidence_ref": "NOTICE-002",
                "authority": "RJSC",
                "effective_date": "2026-01-01",
                "continuing_status": True,
                "days_since_payment_due": 180,
            }]
        ),
        today=date(2026, 11, 3),
    )
    flag = _flag(result, "DEF-001")
    assert flag.state == RuleState.DISPUTED
    assert flag.severity == Severity.NOT_EVALUATED
    assert flag.is_black_override is False
    assert "DEF-001" not in VERIFIED_RULE_IDS

def test_pre_score_and_authoritative_raw_score_use_identical_category_caps():
    profile = _profile()
    flags = [
        ComplianceFlag(
            rule_id="AGM-001",
            flag_code="AGM-001-A",
            severity=Severity.RED,
            score_impact=20,
            revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
            description="Verified AGM default.",
            statutory_basis="Section 81, Companies Act 1994 (Bangladesh)",
        ),
        ComplianceFlag(
            rule_id="AGM-002",
            flag_code="AGM-002-B",
            severity=Severity.RED,
            score_impact=20,
            revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
            description="Second verified AGM default.",
            statutory_basis="Section 81, Companies Act 1994 (Bangladesh)",
        ),
        ComplianceFlag(
            rule_id="INC-003",
            flag_code="INC-003-C",
            severity=Severity.RED,
            score_impact=15,
            revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
            description="Verified director count finding.",
            statutory_basis="Section 90, Companies Act 1994 (Bangladesh)",
        ),
    ]
    engine = NLCRuleEngine()
    breakdown = engine._calculate_score(flags, profile)
    assert engine._calculate_raw_score(flags) == breakdown.raw_total
    # Legal approval register is fail-closed: unapproved findings remain visible
    # but none may affect the authoritative compliance score.
    assert breakdown.raw_total == 100




def test_short_agm_notice_with_verified_all_member_consent_is_not_defective():
    result = NLCRuleEngine().evaluate(
        _profile(
            agm_scheduled_date=date(2026, 11, 20),
            notice_sent_date=date(2026, 11, 10),
            short_notice_consent_obtained=True,
            short_notice_consent_verified=True,
            short_notice_consent_evidence_ref="AGM-CONSENTS-001",
        ),
        today=date(2026, 11, 3),
    )
    assert "AGM-003" not in {flag.rule_id for flag in result.flags}


def test_short_agm_notice_without_verified_consent_is_not_a_confirmed_breach():
    result = NLCRuleEngine().evaluate(
        _profile(
            agm_scheduled_date=date(2026, 11, 20),
            notice_sent_date=date(2026, 11, 10),
            short_notice_consent_obtained=None,
            short_notice_consent_verified=False,
        ),
        today=date(2026, 11, 3),
    )
    flag = _flag(result, "AGM-003")
    assert flag.state == RuleState.UNKNOWN
    assert flag.score_impact == 0


def test_short_agm_notice_with_verified_absence_of_consent_is_defective():
    result = NLCRuleEngine().evaluate(
        _profile(
            agm_scheduled_date=date(2026, 11, 20),
            notice_sent_date=date(2026, 11, 10),
            short_notice_consent_obtained=False,
            short_notice_consent_verified=True,
            short_notice_consent_evidence_ref="AGM-CONSENT-REVIEW-002",
        ),
        today=date(2026, 11, 3),
    )
    flag = _flag(result, "AGM-003")
    assert flag.state == RuleState.NON_COMPLIANT



def test_unverified_agm_history_does_not_create_deadline_violation():
    result = NLCRuleEngine().evaluate(
        _profile(
            incorporation_date=date(2020, 1, 1),
            agm_count=0,
            agm_history_verified=False,
            agm_history_evidence_ref=None,
        ),
        today=date(2026, 11, 3),
    )
    assert not {"AGM-001", "AGM-002"} & {flag.rule_id for flag in result.flags}

def test_section_81_first_agm_within_18_months_defers_next_agm_to_second_following_year():
    profile = _profile(
        incorporation_date=date(2025, 1, 1),
        last_agm_date=date(2025, 12, 15),
        agm_count=1,
        agm_held_this_cycle=False,
    )
    result = NLCRuleEngine().evaluate(profile, today=date(2026, 11, 3))
    assert "AGM-002" not in {flag.rule_id for flag in result.flags}


def test_verified_registrar_agm_extension_is_applied_within_section_81_limit():
    profile = _profile(
        agm_count=1,
        last_agm_date=date(2024, 1, 1),
        agm_held_this_cycle=False,
        agm_extension_granted_until=date(2025, 6, 30),
        agm_extension_application_date=date(2025, 4, 15),
        agm_extension_verified=True,
        agm_extension_evidence_ref="RJSC-EXTENSION-001",
        agm_extension_verified_at=date(2025, 4, 16),
        agm_extension_verified_by="reviewer-001",
    )
    result = NLCRuleEngine().evaluate(profile, today=date(2025, 6, 15))
    assert "AGM-002" not in {flag.rule_id for flag in result.flags}


def test_unverified_or_late_agm_extension_never_suppresses_into_false_default():
    profile = _profile(
        agm_count=1,
        last_agm_date=date(2024, 1, 1),
        agm_held_this_cycle=False,
        agm_extension_granted_until=date(2025, 6, 30),
        agm_extension_application_date=date(2025, 6, 1),
        agm_extension_verified=False,
        agm_extension_evidence_ref=None,
    )
    result = NLCRuleEngine().evaluate(profile, today=date(2026, 11, 3))
    flag = _flag(result, "AGM-002")
    assert flag.state == RuleState.REQUIRES_LAWYER_JUDGMENT
    assert flag.score_impact == 0

def test_score_hash_changes_when_evidence_inputs_change():
    engine = NLCRuleEngine()
    first = engine.evaluate(_profile(member_count=2), today=date(2026, 11, 3))
    second = engine.evaluate(_profile(member_count=3), today=date(2026, 11, 3))
    assert first.score_breakdown.final_score == second.score_breakdown.final_score
    assert first.score_breakdown.score_hash != second.score_breakdown.score_hash


def test_verified_absence_is_a_scoring_state_but_unknown_is_not():
    profile = _profile()
    verified_absent = ComplianceFlag(
        rule_id="AGM-001",
        flag_code="FIRST_AGM_VERIFIED_ABSENT",
        severity=Severity.RED,
        score_impact=20,
        revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
        description="Verified statutory absence.",
        statutory_basis="Section 81, Companies Act 1994 (Bangladesh)",
        state=RuleState.VERIFIED_ABSENT,
    )
    score = NLCRuleEngine()._calculate_score([verified_absent], profile)
    assert score.agm_score == 20
    assert score.final_score == 100




def test_labour_section_326_missing_direction_evidence_is_not_a_breach():
    result = NLCRuleEngine().evaluate(
        _profile(
            is_manufacturing=True,
            factory_license_required_by_direction=True,
            factory_license_obtained=False,
        ),
        today=date(2026, 11, 4),
    )
    flag = _flag(result, "LBR-001")
    assert flag.severity == Severity.NOT_EVALUATED
    assert flag.state == RuleState.UNKNOWN
    assert flag.eval_state == "UNKNOWN"
    assert flag.score_impact == 0


def test_labour_section_326_expiry_requires_verified_licence_class_and_direction():
    result = NLCRuleEngine().evaluate(
        _profile(
            is_manufacturing=True,
            factory_license_required_by_direction=True,
            factory_license_obtained=True,
            factory_license_expiry=date(2026, 1, 1),
        ),
        today=date(2026, 11, 4),
    )
    flag = _flag(result, "LBR-002")
    assert flag.severity == Severity.NOT_EVALUATED
    assert flag.state == RuleState.UNKNOWN
    assert flag.eval_state == "UNKNOWN"
    assert flag.score_impact == 0


def test_company_tax_return_deadline_uses_finance_act_2026_section_170():
    # 30 June income-year end: ninth-month date is 15 March, so the
    # statutory floor moves the provisional deadline to 15 September.
    result = NLCRuleEngine().evaluate(
        _profile(
            tin_obtained=True,
            tax_return_filed_for_current_fy=False,
            financial_year_end=date(2025, 6, 30),
        ),
        today=date(2026, 11, 4),
    )
    flag = _flag(result, "TAX-003")
    assert flag.severity == Severity.NOT_EVALUATED
    assert flag.state == RuleState.REQUIRES_LAWYER_JUDGMENT
    assert flag.eval_state == "UNKNOWN"
    assert flag.score_impact == 0
    assert flag.detail["ninth_month_date"] == "2026-03-15"
    assert flag.detail["september_15_floor"] == "2025-09-15"
    assert flag.detail["provisional_deadline"] == "2026-03-15"


def test_company_tax_return_deadline_keeps_later_ninth_month_date():
    result = NLCRuleEngine().evaluate(
        _profile(
            tin_obtained=True,
            tax_return_filed_for_current_fy=False,
            financial_year_end=date(2025, 3, 31),
        ),
        today=date(2026, 11, 4),
    )
    flag = _flag(result, "TAX-003")
    assert flag.detail["ninth_month_date"] == "2025-12-15"
    assert flag.detail["september_15_floor"] == "2025-09-15"
    assert flag.detail["provisional_deadline"] == "2025-12-15"



def test_vat_registration_threshold_uses_current_50_lakh_value_and_fails_closed():
    below = NLCRuleEngine().evaluate(
        _profile(vat_registered=False, annual_turnover_bdt=2_999_999),
        today=date(2026, 11, 4),
    )
    assert not any(flag.rule_id == "TAX-002" for flag in below.flags)

    above = NLCRuleEngine().evaluate(
        _profile(vat_registered=False, annual_turnover_bdt=5_000_001),
        today=date(2026, 11, 4),
    )
    flag = _flag(above, "TAX-002")
    assert flag.severity == Severity.NOT_EVALUATED
    assert flag.state == RuleState.UNKNOWN
    assert flag.eval_state == "UNKNOWN"
    assert flag.score_impact == 0
    assert flag.detail["registration_threshold_bdt"] == 5_000_000
    assert flag.detail["turnover_tax_enlistment_threshold_bdt"] == 3_000_000


def test_vat_turnover_tax_enlistment_band_is_review_only():
    result = NLCRuleEngine().evaluate(
        _profile(vat_registered=False, annual_turnover_bdt=4_000_000),
        today=date(2026, 11, 4),
    )
    flag = _flag(result, "TAX-002")
    assert flag.severity == Severity.NOT_EVALUATED
    assert flag.state == RuleState.UNKNOWN
    assert flag.eval_state == "UNKNOWN"
    assert flag.score_impact == 0
    assert flag.detail["turnover_tax_enlistment_threshold_bdt"] == 3_000_000
    assert flag.detail["registration_threshold_bdt"] == 5_000_000
    assert flag.detail["turnover_tax_enlistment_application_window_days"] == 30



def test_vat_return_status_without_verified_tax_period_is_not_a_default():
    result = NLCRuleEngine().evaluate(
        _profile(vat_registered=True, last_vat_return_filed=date(2026, 8, 1)),
        today=date(2026, 11, 4),
    )
    flag = _flag(result, "VAT-002")
    assert flag.severity == Severity.NOT_EVALUATED
    assert flag.state == RuleState.UNKNOWN
    assert flag.eval_state == "UNKNOWN"
    assert flag.score_impact == 0


def test_unreleased_legal_corpus_never_reports_green_even_with_full_input_coverage():
    from app.rule_engine.engine import LEGAL_SCORE_RELEASED

    assert LEGAL_SCORE_RELEASED is False
    profile = _profile(
        last_agm_date=date(2025, 6, 1),
        last_audit_signed_date=date(2025, 5, 1),
        last_return_filed_year=2025,
        first_auditor_appointed=True,
        tin_obtained=True,
        current_director_count=2,
        directors_verified=True,
        member_count=2,
    )
    score = NLCRuleEngine()._calculate_score([], profile)
    assert score.final_score == 100  # arithmetic placeholder only
    assert score.risk_band == Severity.NOT_EVALUATED
    assert score.override_applied is False


def test_unapproved_black_override_cannot_force_zero_score():
    profile = _profile()
    unapproved_black = ComplianceFlag(
        rule_id="INC-003",
        flag_code="UNAPPROVED_BLACK_TEST",
        severity=Severity.BLACK,
        score_impact=15,
        revenue_tier=RevenueTier.CORPORATE_RESCUE,
        description="Unapproved legal mapping must not force BLACK.",
        statutory_basis="Section 90, Companies Act 1994 (Bangladesh)",
        state=RuleState.NON_COMPLIANT,
        eval_state="VIOLATION",
        is_black_override=True,
    )
    score = NLCRuleEngine()._calculate_score([unapproved_black], profile)
    assert score.final_score == 100
    assert score.override_applied is False

def test_tin_profile_absence_is_review_only_not_a_confirmed_tax_breach():
    result = NLCRuleEngine().evaluate(
        _profile(tin_obtained=False),
        today=date(2026, 11, 4),
    )
    flag = _flag(result, "TAX-001")
    assert flag.state == RuleState.UNKNOWN
    assert flag.eval_state == "UNKNOWN"
    assert flag.severity == Severity.NOT_EVALUATED
    assert flag.score_impact == 0
