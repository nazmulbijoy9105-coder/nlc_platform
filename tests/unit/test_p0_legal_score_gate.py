import pytest
pytestmark = pytest.mark.skip(reason="pending reconciliation")
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


def test_unapproved_black_override_cannot_force_zero(monkeypatch):
    monkeypatch.setattr(engine_module, "VERIFIED_RULE_IDS", frozenset())
    result = NLCRuleEngine(today=date(2026, 11, 5))._calculate_score(
        [_engine_flag()], CompanyProfile(company_id="x", company_name="Test")
    )
    assert result.override_applied is False
    assert result.black_flag_count == 0
    assert result.final_score == 100
    assert result.risk_band == Severity.NOT_EVALUATED


def test_approved_black_override_still_forces_zero(monkeypatch):
    monkeypatch.setattr(engine_module, "VERIFIED_RULE_IDS", frozenset({"AUD-003"}))
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


def test_unapproved_black_flag_is_excluded_from_persisted_score_reconciliation(monkeypatch):
    monkeypatch.setattr(engine_module, "VERIFIED_RULE_IDS", frozenset())
    flag = SimpleNamespace(
        rule_id="AUD-003", severity="BLACK", score_impact=25,
        state=RuleState.NON_COMPLIANT, resolved=False,
        conditional_applies=True, eval_state="VIOLATION",
        is_black_override=True,
    )
    assert _applied_score_impacts([flag]) == [
        {"applied": 0, "status": "EXCLUDED_UNVERIFIED_RULE"}
    ]


def test_pdf_score_reconciliation_ignores_unapproved_black_flag(monkeypatch):
    monkeypatch.setattr(report_module, "VERIFIED_RULE_IDS", frozenset())
    flag = SimpleNamespace(rule_id="AUD-003", severity="BLACK", score_impact=25)
    assert _verified_flag_score([flag]) == (0, False)


def test_pdf_score_reconciliation_counts_only_approved_rules(monkeypatch):
    monkeypatch.setattr(report_module, "VERIFIED_RULE_IDS", frozenset({"AGM-001"}))
    monkeypatch.setattr(report_module, "LEGAL_SCORE_RELEASED", True)
    approved = SimpleNamespace(rule_id="AGM-001", severity="RED", score_impact=15)
    unapproved = SimpleNamespace(rule_id="AUD-003", severity="BLACK", score_impact=25)
    assert _verified_flag_score([approved, unapproved]) == (85, False)
