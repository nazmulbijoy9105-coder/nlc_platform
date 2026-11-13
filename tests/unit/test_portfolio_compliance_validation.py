from datetime import datetime, timezone
from types import SimpleNamespace

from app.api.portfolio_compliance import _validation
from app.rule_engine.engine import RULE_ENGINE_VERSION
from canonical_architecture.scoring_spec import SCORING_SPEC_VERSION


def _records():
    run = SimpleNamespace(
        id="run-1",
        evaluation_status="COMPLETED",
        score_hash="a" * 64,
        engine_version=RULE_ENGINE_VERSION,
        score=82,
        risk_band="YELLOW",
        calculated_at=datetime(2026, 11, 13, tzinfo=timezone.utc),
        score_breakdown_snapshot={
            "scoring_spec_version": SCORING_SPEC_VERSION,
            "score_reconciles": True,
            "final_score": 82,
        },
    )
    company = SimpleNamespace(
        current_compliance_score=82,
        current_risk_band="YELLOW",
        last_evaluated_at=datetime(2026, 11, 13, tzinfo=timezone.utc),
    )
    return run, company


def test_portfolio_validation_accepts_completed_reconciled_authoritative_run():
    run, company = _records()
    result = _validation(run, company)
    assert result["valid"] is True
    assert result["pdf_eligible"] is True
    assert result["score_hash"] == "a" * 64


def test_portfolio_validation_withholds_pdf_when_reconciliation_fails():
    run, company = _records()
    run.score_breakdown_snapshot["score_reconciles"] = False
    result = _validation(run, company)
    assert result["valid"] is False
    assert result["pdf_eligible"] is False
    assert "SCORE_RECONCILIATION_FAILED" in result["problems"]


def test_portfolio_validation_withholds_pdf_when_company_state_does_not_match_run():
    run, company = _records()
    company.current_compliance_score = 100
    result = _validation(run, company)
    assert result["valid"] is False
    assert result["pdf_eligible"] is False
    assert "COMPANY_SCORE_MISMATCH" in result["problems"]
