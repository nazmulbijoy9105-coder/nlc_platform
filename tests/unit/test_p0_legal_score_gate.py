"""P0 regressions: product scoring and independent legal verification stay separate."""
from datetime import date, datetime, timezone
from types import SimpleNamespace

import app.rule_engine.engine as engine_module
import app.services.pdf_report_service as report_module
from app.rule_engine.engine import (
    CompanyProfile,
    ComplianceFlag as EngineFlag,
    NLCRuleEngine,
    RevenueTier,
    RuleState,
    Severity,
)
from app.services.compliance_service import _applied_score_impacts
from app.services.pdf_report_service import _verified_flag_score, build_compliance_report_html


def _engine_flag(rule_id="AUD-003", severity=Severity.BLACK, black=True):
    return EngineFlag(
        rule_id=rule_id,
        flag_code=rule_id,
        severity=severity,
        score_impact=25,
        revenue_tier=RevenueTier.CORPORATE_RESCUE,
        description="test",
        statutory_basis="test source",
        is_black_override=black,
        state=RuleState.NON_COMPLIANT,
        eval_state="VIOLATION",
    )


def test_rule_outside_product_scoring_allowlist_cannot_force_zero(monkeypatch):
    monkeypatch.setattr(engine_module, "PRODUCT_SCORING_RULE_IDS", frozenset())
    result = NLCRuleEngine(today=date(2026, 11, 5))._calculate_score(
        [_engine_flag()], CompanyProfile(company_id="x", company_name="Test")
    )
    assert result.override_applied is False
    assert result.black_flag_count == 0
    assert result.final_score == 100
    assert result.risk_band == Severity.NOT_EVALUATED


def test_product_allowlisted_black_override_requires_explicit_override_authorisation(monkeypatch):
    monkeypatch.setattr(engine_module, "PRODUCT_SCORING_RULE_IDS", frozenset({"AUD-003"}))
    monkeypatch.setattr(
        engine_module, "AUTHORIZED_BLACK_OVERRIDE_RULE_IDS", frozenset({"AUD-003"})
    )
    monkeypatch.setattr(engine_module, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(engine_module, "VERIFIED_RULE_IDS", frozenset({"AUD-003"}))
    result = NLCRuleEngine(today=date(2026, 11, 5))._calculate_score(
        [_engine_flag()], CompanyProfile(company_id="x", company_name="Test")
    )
    assert result.override_applied is True
    assert result.black_flag_count == 1
    assert result.final_score == 0


def test_rule_outside_product_allowlist_is_excluded_from_score_reconciliation(monkeypatch):
    monkeypatch.setattr(engine_module, "PRODUCT_SCORING_RULE_IDS", frozenset())
    flag = SimpleNamespace(
        rule_id="AUD-003", severity="BLACK", score_impact=25,
        state=RuleState.NON_COMPLIANT, resolved=False,
        conditional_applies=True, eval_state="VIOLATION",
        is_black_override=True,
    )
    assert _applied_score_impacts([flag]) == [
        {"applied": 0, "status": "LEGAL_SCORE_NOT_RELEASED"}
    ]


def test_pdf_score_reconciliation_ignores_rule_outside_product_allowlist(monkeypatch):
    monkeypatch.setattr(report_module, "PRODUCT_SCORING_RULE_IDS", frozenset())
    flag = SimpleNamespace(rule_id="AUD-003", severity="BLACK", score_impact=25)
    assert _verified_flag_score([flag]) == (0, False)


def test_pdf_score_reconciliation_counts_product_allowlisted_rules_without_counsel_allowlist(monkeypatch):
    monkeypatch.setattr(report_module, "PRODUCT_SCORING_RULE_IDS", frozenset({"AGM-001"}))
    monkeypatch.setattr(report_module, "SCORE_DEDUCTION_RULE_IDS", frozenset({"AGM-001"}))
    monkeypatch.setattr(report_module, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(report_module, "VERIFIED_RULE_IDS", frozenset())
    approved = SimpleNamespace(rule_id="AGM-001", severity="RED", score_impact=15)
    unapproved = SimpleNamespace(rule_id="AUD-003", severity="BLACK", score_impact=25)
    assert _verified_flag_score([approved, unapproved]) == (85, False)


def test_release_switch_without_product_rules_does_not_release_a_score(monkeypatch):
    monkeypatch.setattr(engine_module, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(engine_module, "PRODUCT_SCORING_RULE_IDS", frozenset())
    result = NLCRuleEngine(today=date(2026, 11, 5))._calculate_score(
        [_engine_flag()], CompanyProfile(company_id="x", company_name="Test")
    )
    assert engine_module.legal_score_is_released() is False
    assert result.final_score == 100  # non-authoritative arithmetic placeholder
    assert result.risk_band == Severity.NOT_EVALUATED
    assert result.override_applied is False
    assert _applied_score_impacts([_engine_flag()]) == [
        {"applied": 0, "status": "LEGAL_SCORE_NOT_RELEASED"}
    ]


def test_pdf_requires_explicit_authorisation_for_black_override(monkeypatch):
    monkeypatch.setattr(report_module, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(report_module, "PRODUCT_SCORING_RULE_IDS", frozenset({"AGM-001"}))
    monkeypatch.setattr(report_module, "VERIFIED_RULE_IDS", frozenset({"AGM-001"}))
    monkeypatch.setattr(report_module, "AUTHORIZED_BLACK_OVERRIDE_RULE_IDS", frozenset())
    flag = SimpleNamespace(
        rule_id="AGM-001",
        severity="BLACK",
        score_impact=25,
        is_black_override=True,
    )
    score, override = _verified_flag_score([flag])
    assert score == 75  # AGM category cap applies; no forced-zero override
    assert override is False

    monkeypatch.setattr(
        report_module, "AUTHORIZED_BLACK_OVERRIDE_RULE_IDS", frozenset({"AGM-001"})
    )
    score, override = _verified_flag_score([flag])
    assert score == 0
    assert override is True


def test_product_scoring_can_run_with_empty_counsel_allowlist(monkeypatch):
    monkeypatch.setattr(engine_module, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(engine_module, "VERIFIED_RULE_IDS", frozenset())
    monkeypatch.setattr(engine_module, "PRODUCT_SCORING_RULE_IDS", frozenset({"AUD-003"}))
    result = NLCRuleEngine(today=date(2026, 11, 5))._calculate_score(
        [_engine_flag(severity=Severity.RED, black=False)],
        CompanyProfile(company_id="x", company_name="Test"),
    )
    assert engine_module.legal_score_is_released() is True
    assert engine_module.VERIFIED_RULE_IDS == frozenset()
    # Product scoring is released independently of counsel verification;
    # the confirmed RED finding applies its ordinary category deduction.
    assert result.final_score == 75
    assert result.override_applied is False
    assert result.risk_band == Severity.RED


def test_verified_director_minimum_violation_emits_one_candidate_black_override(monkeypatch, build_profile):
    monkeypatch.setattr(engine_module, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(engine_module, "PRODUCT_SCORING_RULE_IDS", frozenset({"INC-003"}))
    monkeypatch.setattr(engine_module, "VERIFIED_RULE_IDS", frozenset({"INC-003"}))
    # This test exercises candidate generation only: explicit product-owner
    # override authority is intentionally absent.
    monkeypatch.setattr(engine_module, "AUTHORIZED_BLACK_OVERRIDE_RULE_IDS", frozenset())
    profile = build_profile(
        company_type="PRIVATE_LIMITED",
        current_director_count=1,
        directors_verified=True,
        directors_verification_evidence_ref="rjsc://company/directors/current",
        directors_verified_at=date(2026, 11, 5),
        directors_verified_by="super-admin-1",
    )

    output = NLCRuleEngine(today=date(2026, 11, 5)).evaluate(profile)
    director_findings = [flag for flag in output.flags if flag.rule_id == "INC-003"]

    assert len(director_findings) == 1
    assert director_findings[0].is_black_override is True
    assert director_findings[0].state == RuleState.NON_COMPLIANT
    assert director_findings[0].eval_state == "VIOLATION"
    assert output.score_breakdown.override_applied is False
    # Other profile-completeness inputs can affect the ordinary score. The
    # safety invariant is that an unauthorised candidate never forces BLACK/0.
    assert output.score_breakdown.final_score > 0
    assert output.score_breakdown.risk_band != Severity.BLACK


def test_product_owner_black_override_does_not_require_counsel_allowlist(monkeypatch):
    monkeypatch.setattr(engine_module, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(engine_module, "VERIFIED_RULE_IDS", frozenset())
    monkeypatch.setattr(engine_module, "PRODUCT_SCORING_RULE_IDS", frozenset({"INC-003"}))
    flag = _engine_flag(rule_id="INC-003", severity=Severity.BLACK, black=True)

    result = NLCRuleEngine(today=date(2026, 11, 5))._calculate_score(
        [flag], CompanyProfile(company_id="x", company_name="Test")
    )

    assert engine_module.legal_score_is_released() is True
    assert engine_module.VERIFIED_RULE_IDS == frozenset()
    assert engine_module.AUTHORIZED_BLACK_OVERRIDE_RULE_IDS == frozenset({"INC-003"})
    # The product owner has explicitly authorised this override. Counsel
    # status remains empty and is not consulted for this separate control.
    assert result.override_applied is True
    assert result.black_flag_count == 1
    assert result.final_score == 0
    assert result.risk_band == Severity.BLACK


def test_pdf_html_is_unsigned_and_discloses_counsel_review_even_when_product_scoring_is_released(monkeypatch):
    monkeypatch.setattr(report_module, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(report_module, "PRODUCT_SCORING_RULE_IDS", frozenset({"AGM-001"}))
    monkeypatch.setattr(report_module, "VERIFIED_RULE_IDS", frozenset())
    company = SimpleNamespace(
        company_name="Test Company",
        registration_number="TEST-001",
        current_compliance_score=88,
        current_risk_band="GREEN",
    )

    html = build_compliance_report_html(
        company=company,
        flags=[],
        generated_at=datetime(2026, 11, 13, tzinfo=timezone.utc),
    )

    assert "UNSIGNED — FOR COUNSEL REVIEW ONLY — NO NLC LIABILITY WITHOUT SIGNATURE" in html
    assert "LIABILITY AND RELIANCE NOTICE" in html
    assert "Lawyer Review &amp; Signature" in html
    assert "Approval status:</strong> UNSIGNED" in html
    assert "<strong>Status: UNSIGNED</strong>" in html
    assert "Product risk score:" in html



def test_pdf_reconciliation_fails_closed_for_unknown_persisted_finding(monkeypatch):
    monkeypatch.setattr(report_module, "PRODUCT_SCORING_RULE_IDS", frozenset({"AGM-001"}))
    monkeypatch.setattr(report_module, "SCORE_DEDUCTION_RULE_IDS", frozenset({"AGM-001"}))
    monkeypatch.setattr(report_module, "LEGAL_SCORE_RELEASED", True)
    unknown = SimpleNamespace(
        rule_id="AGM-001",
        evaluation_state="UNKNOWN",
        flag_status="ACTIVE",
        resolved_date=None,
        score_impact=15,
        detail={},
    )

    assert _verified_flag_score([unknown]) == (100, False)
    assert report_module._render_score_reconciliation([unknown], 100, "GREEN") == ""


def test_pdf_reconciliation_requires_active_explicit_violation(monkeypatch):
    monkeypatch.setattr(report_module, "PRODUCT_SCORING_RULE_IDS", frozenset({"AGM-001"}))
    monkeypatch.setattr(report_module, "SCORE_DEDUCTION_RULE_IDS", frozenset({"AGM-001"}))
    monkeypatch.setattr(report_module, "LEGAL_SCORE_RELEASED", True)
    confirmed = SimpleNamespace(
        rule_id="AGM-001",
        evaluation_state="VIOLATION",
        flag_status="ACTIVE",
        resolved_date=None,
        score_impact=15,
        detail={},
    )

    assert _verified_flag_score([confirmed]) == (85, False)
    assert "Score reconciliation" in report_module._render_score_reconciliation(
        [confirmed], 85, "YELLOW"
    )
