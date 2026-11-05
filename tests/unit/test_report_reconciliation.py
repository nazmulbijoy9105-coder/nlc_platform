"""F1/F2a/F3 regression tests: cap reconciliation, target derivation, placeholder."""
from datetime import date, datetime
from types import SimpleNamespace

import pytest

from app.services.pdf_report_service import ScoreReconciliationError, build_compliance_report_html
from app.services.rescue_service import _derive_plan_target

WHEN = datetime(2026, 10, 30, 12, 0, 0)


def _company(score=75, band="RED", name="Test Co"):
    return SimpleNamespace(
        company_name=name,
        registration_number="TEST-FE8A8D55",
        current_compliance_score=score,
        current_risk_band=band,
    )


def _flag(rid, sev, imp):
    return SimpleNamespace(rule_id=rid, severity=sev, description="d", score_impact=imp)




def _enable_authorized_score_for_report_test(monkeypatch, rule_ids):
    # Arithmetic/report rendering tests opt into an isolated approved-rule
    # fixture. Production defaults remain unreleased and fail closed.
    monkeypatch.setattr("app.services.pdf_report_service.LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(
        "app.services.pdf_report_service.VERIFIED_RULE_IDS",
        frozenset(rule_ids),
    )


FLAGS = [
    _flag("REG-002", "BLACK", 12),
    _flag("INC-001", "RED", 0),
    _flag("AGM-001", "YELLOW", 0),
    _flag("AUD-001", "YELLOW", 10),
    _flag("TL-001", "YELLOW", 5),
]


def test_cap_adjustment_row_rendered(monkeypatch):
    _enable_authorized_score_for_report_test(monkeypatch, {"REG-002", "AUD-001", "TL-001"})
    page = build_compliance_report_html(_company(), FLAGS, WHEN)
    assert "Category cap applied (REG)" in page
    assert "raw deduction 12 pts capped to 10 pts" in page


def test_reconciliation_line_matches_score(monkeypatch):
    _enable_authorized_score_for_report_test(monkeypatch, {"REG-002", "AUD-001", "TL-001"})
    page = build_compliance_report_html(_company(score=75), FLAGS, WHEN)
    assert "effective deductions -25 pts" in page
    assert "indicated score 75/100" in page


def test_no_caps_no_adjustment_rows(monkeypatch):
    _enable_authorized_score_for_report_test(monkeypatch, {"OFF-001"})
    page = build_compliance_report_html(_company(score=95), [_flag("OFF-001", "YELLOW", 5)], WHEN)
    assert "Category cap applied" not in page
    assert "effective deductions -5 pts" in page


def test_black_band_suppresses_reconciliation():
    page = build_compliance_report_html(_company(score=0, band="BLACK"), FLAGS, WHEN)
    assert "Score reconciliation" not in page


def test_missing_company_name_placeholder():
    page = build_compliance_report_html(_company(name=None), FLAGS, WHEN)
    assert "[COMPANY NAME NOT ON FILE]" in page


def test_derive_plan_target_explicit_wins():
    steps = [SimpleNamespace(target_completion_date=date(2026, 11, 28))]
    assert _derive_plan_target(date(2026, 12, 1), steps) == date(2026, 12, 1)


def test_derive_plan_target_from_steps():
    steps = [
        SimpleNamespace(target_completion_date=date(2026, 11, 28)),
        SimpleNamespace(target_completion_date=date(2026, 11, 10)),
    ]
    assert _derive_plan_target(None, steps) == date(2026, 11, 28)


def test_derive_plan_target_empty():
    assert _derive_plan_target(None, []) is None


def test_reconciliation_mismatch_is_rejected(monkeypatch):
    _enable_authorized_score_for_report_test(monkeypatch, {"REG-002", "AUD-001", "TL-001"})
    with pytest.raises(ScoreReconciliationError):
        build_compliance_report_html(_company(score=74), FLAGS, WHEN)


def test_unreleased_provisional_findings_are_not_shown_as_score_deductions():
    page = build_compliance_report_html(
        _company(score=100, band="NOT_EVALUATED"),
        [_flag("AGM-001", "RED", 20)],
        WHEN,
    )
    assert "Not scored" in page
    assert "pending independent legal approval" in page
    assert "-20 pts" not in page
    assert "Score reconciliation" not in page
