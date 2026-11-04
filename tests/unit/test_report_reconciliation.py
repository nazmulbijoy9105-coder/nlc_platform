"""P0: Reports must not present a numerical compliance score before legal release."""
from datetime import datetime
from types import SimpleNamespace

from app.services.pdf_report_service import build_compliance_report_html

WHEN = datetime(2026, 10, 30, 12, 0, 0)


def _company(name="Test Co"):
    return SimpleNamespace(
        company_name=name,
        registration_number="TEST-FE8A8D55",
        current_compliance_score=None,
        current_risk_band="NOT_EVALUATED",
    )


def _flag(rid, sev, imp):
    return SimpleNamespace(rule_id=rid, severity=sev, description="d", score_impact=imp)


def test_unreleased_score_is_not_rendered_as_zero_or_one_hundred():
    page = build_compliance_report_html(
        _company(),
        [_flag("REG-002", "BLACK", 12), _flag("AUD-001", "BLACK", 10)],
        WHEN,
    )
    assert "NOT RELEASED" in page
    assert "Score reconciliation" not in page
    assert "No authoritative compliance score is released" in page


def test_unapproved_flags_are_labelled_provisional():
    page = build_compliance_report_html(
        _company(),
        [_flag("AUD-001", "BLACK", 10)],
        WHEN,
    )
    assert "Not scored — pending independent legal approval" in page


def test_missing_company_name_placeholder():
    page = build_compliance_report_html(_company(name=None), [], WHEN)
    assert "[COMPANY NAME NOT ON FILE]" in page
