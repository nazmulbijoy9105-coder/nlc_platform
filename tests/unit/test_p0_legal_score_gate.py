import pytest
"""P0 regressions: unapproved rules must never affect authoritative scores or reports."""
from datetime import date
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
from app.services.pdf_report_service import _verified_flag_score


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


def test_pdf_score_reconciliation_counts_product_allowlisted_rules(monkeypatch):
    monkeypatch.setattr(report_module, "PRODUCT_SCORING_RULE_IDS", frozenset({"AGM-001"}))
    monkeypatch.setattr(report_module, "LEGAL_SCORE_RELEASED", True)
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


def test_product_scoring_is_released_without_legal_verification_allowlist(monkeypatch):
    monkeypatch.setattr(engine_module, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(engine_module, "VERIFIED_RULE_IDS", frozenset())
    monkeypatch.setattr(engine_module, "PRODUCT_SCORING_RULE_IDS", frozenset({"AUD-003"}))
    result = NLCRuleEngine(today=date(2026, 11, 5))._calculate_score(
        [_engine_flag(severity=Severity.RED, black=False)],
        CompanyProfile(company_id="x", company_name="Test"),
    )
    assert engine_module.legal_score_is_released() is True
    assert engine_module.VERIFIED_RULE_IDS == frozenset()
    assert result.final_score == 75
    assert result.risk_band != Severity.NOT_EVALUATED
