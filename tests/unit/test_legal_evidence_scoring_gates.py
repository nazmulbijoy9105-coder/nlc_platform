from datetime import date

from app.rule_engine.engine import (
    CompanyProfile,
    ComplianceFlag,
    NLCRuleEngine,
    RevenueTier,
    RuleState,
    Severity,
    VERIFIED_RULE_IDS,
)


def _profile(**overrides):
    values = {
        "company_id": "legal-gate-test",
        "company_name": "Legal Gate Test Ltd",
        "company_type": "PRIVATE_LIMITED",
        "incorporation_date": date(2020, 1, 31),
        "agm_count": 1,
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
    flag = _flag(result, "AGM-005")
    assert flag.state == RuleState.UNKNOWN
    assert flag.score_impact == 0


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
    assert breakdown.raw_total == 55

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
    assert score.agm_score == 0
    assert score.final_score == 80
