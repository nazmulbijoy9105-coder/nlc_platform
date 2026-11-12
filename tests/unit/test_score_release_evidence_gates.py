from __future__ import annotations

from datetime import date

import app.rule_engine.engine as engine_module
from app.rule_engine.engine import (
    CompanyProfile,
    ComplianceFlag,
    NLCRuleEngine,
    RevenueTier,
    RuleState,
    Severity,
)


TODAY = date(2026, 11, 13)


def _verified_agm_profile() -> CompanyProfile:
    return CompanyProfile(
        company_id="fixture-company-001",
        company_name="Controlled Evidence Fixture Ltd.",
        incorporation_date=date(2024, 1, 1),
        agm_count=0,
        agm_history_verified=True,
        agm_history_evidence_ref="fixture://authenticated-agm-history",
        agm_history_verified_at=date(2026, 11, 12),
        agm_history_verified_by="fixture-reviewer",
    )


def _finding(
    *,
    rule_id: str = "AGM-001",
    severity: Severity = Severity.RED,
    state: RuleState = RuleState.NON_COMPLIANT,
    eval_state: str = "VIOLATION",
    score_impact: int = 10,
    black_override: bool = False,
) -> ComplianceFlag:
    return ComplianceFlag(
        rule_id=rule_id,
        flag_code="CONTROLLED_FIXTURE",
        severity=severity,
        score_impact=score_impact,
        revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
        description="Controlled evaluator test fixture",
        statutory_basis="Controlled fixture only; not a legal conclusion",
        state=state,
        eval_state=eval_state,
        is_black_override=black_override,
        detail={"evidence_ref": "fixture://verified-record"},
    )


def test_verified_applicable_evidence_produces_expected_agm_finding():
    result = NLCRuleEngine(today=TODAY).evaluate(_verified_agm_profile())
    finding = next(flag for flag in result.flags if flag.rule_id == "AGM-001")

    assert finding.flag_code == "FIRST_AGM_DEFAULT"
    assert finding.state == RuleState.NON_COMPLIANT
    assert finding.eval_state == "VIOLATION"
    assert finding.detail["deadline"] == "2025-07-01"


def test_missing_agm_history_is_unknown_not_a_violation():
    company = CompanyProfile(company_id="fixture-unknown", company_name="Unknown Ltd.")
    result = NLCRuleEngine(today=TODAY).evaluate(company)
    finding = next(flag for flag in result.flags if flag.rule_id == "AGM-001")

    assert finding.state == RuleState.UNKNOWN
    assert finding.eval_state == "UNKNOWN"
    assert finding.severity == Severity.NOT_EVALUATED
    assert finding.score_impact == 0


def test_unknown_never_enters_scoring_even_if_impact_was_supplied(monkeypatch):
    monkeypatch.setattr(engine_module, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(engine_module, "VERIFIED_RULE_IDS", frozenset({"AGM-001"}))
    unknown = _finding(
        state=RuleState.UNKNOWN,
        eval_state="UNKNOWN",
        score_impact=25,
    )

    assert unknown.score_impact == 0
    assert NLCRuleEngine(today=TODAY)._eligible_scoring_flags([unknown]) == []


def test_unapproved_rule_cannot_affect_released_score(monkeypatch):
    monkeypatch.setattr(engine_module, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(engine_module, "VERIFIED_RULE_IDS", frozenset({"AGM-001"}))
    flag = _finding(rule_id="AUD-001")
    engine = NLCRuleEngine(today=TODAY)

    assert engine._eligible_scoring_flags([flag]) == []
    assert engine._category_deductions(engine._eligible_scoring_flags([flag]))["AUD"] == 0

    score = engine._calculate_score([flag], CompanyProfile(
        company_id="fixture-score", company_name="Score Fixture Ltd."
    ))
    assert score.category_deductions["AGM"] == 0
    assert score.final_score == 100


def test_explicitly_approved_rule_can_score_in_controlled_release_fixture(monkeypatch):
    monkeypatch.setattr(engine_module, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(engine_module, "VERIFIED_RULE_IDS", frozenset({"AGM-001"}))
    flag = _finding()
    engine = NLCRuleEngine(today=TODAY)

    eligible = engine._eligible_scoring_flags([flag])
    assert eligible == [flag]
    assert engine._category_deductions(eligible)["AGM"] == 10


def test_unverified_black_fact_cannot_activate_black_override(monkeypatch):
    monkeypatch.setattr(engine_module, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(engine_module, "VERIFIED_RULE_IDS", frozenset({"AGM-001"}))
    black = _finding(
        rule_id="INC-003",
        severity=Severity.BLACK,
        black_override=True,
    )
    score = NLCRuleEngine(today=TODAY)._calculate_score(
        [black],
        CompanyProfile(company_id="fixture-black", company_name="Black Fixture Ltd."),
    )

    assert score.override_applied is False
    assert score.override_reason is None
    assert score.final_score == 100


def test_identical_evidence_and_release_versions_produce_identical_score_hashes():
    company = _verified_agm_profile()
    first = NLCRuleEngine(today=TODAY).evaluate(company).score_breakdown
    second = NLCRuleEngine(today=TODAY).evaluate(company).score_breakdown

    assert first.score_hash
    assert first.score_hash == second.score_hash
    assert first.final_score == second.final_score
    assert first.category_deductions == second.category_deductions


def test_default_runtime_release_is_fail_closed_until_counsel_signoff():
    assert engine_module.VERIFIED_RULE_IDS == frozenset()
    assert engine_module.LEGAL_SCORE_RELEASED is False
    assert engine_module.legal_score_is_released() is False
