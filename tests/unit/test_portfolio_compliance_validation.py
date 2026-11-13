from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.api.portfolio_compliance import _validation
from app.compliance.evaluation_integrity import calculate_evaluation_score_hash
from app.compliance.rule_outcome_ledger import hash_rule_outcomes_snapshot
from app.rule_engine.engine import RULE_ENGINE_VERSION
from canonical_architecture.scoring_spec import SCORING_SPEC_VERSION


def _records():
    company_id = uuid4()
    calculated_at = datetime(2026, 11, 13, tzinfo=timezone.utc)
    outcomes = [
        {
            "rule_id": "AGM-001",
            "rule_version": "2.2",
            "assessment_source": "NO_FINDING_EMITTED_NOT_PROOF_OF_COMPLIANCE",
            "outcome_state": "NOT_EVALUATED",
            "findings": [],
        }
    ]
    score_breakdown = {
        "scoring_spec_version": SCORING_SPEC_VERSION,
        "score_reconciles": True,
        "final_score": 82,
    }
    flags_snapshot = []
    fact_provenance_snapshot = []
    outcomes_hash = hash_rule_outcomes_snapshot(outcomes)
    run = SimpleNamespace(
        id=uuid4(),
        company_id=company_id,
        previous_hash=None,
        evaluation_status="COMPLETED",
        engine_version=RULE_ENGINE_VERSION,
        score=82,
        risk_band="YELLOW",
        calculated_at=calculated_at,
        trigger_source="UNIT_TEST",
        flags_snapshot=flags_snapshot,
        fact_provenance_snapshot=fact_provenance_snapshot,
        score_breakdown_snapshot=score_breakdown,
        rule_outcomes_snapshot=outcomes,
        rule_outcomes_hash=outcomes_hash,
        rule_catalogue_count=1,
    )
    run.score_hash = calculate_evaluation_score_hash(
        previous_hash=run.previous_hash,
        company_id=run.company_id,
        score=run.score,
        risk_band=run.risk_band,
        calculated_at=run.calculated_at,
        engine_version=run.engine_version,
        trigger_source=run.trigger_source,
        flags_snapshot=run.flags_snapshot,
        fact_provenance_snapshot=run.fact_provenance_snapshot,
        score_breakdown_snapshot=run.score_breakdown_snapshot,
        rule_outcomes_hash=run.rule_outcomes_hash,
        rule_outcomes_snapshot=run.rule_outcomes_snapshot,
    )
    company = SimpleNamespace(
        current_compliance_score=82,
        current_risk_band="YELLOW",
        last_evaluated_at=calculated_at,
    )
    return run, company


def test_portfolio_validation_accepts_completed_run_with_verified_evidence_hashes():
    run, company = _records()
    result = _validation(run, company)
    assert result["valid"] is True
    assert result["pdf_eligible"] is True
    assert result["score_hash"] == run.score_hash
    assert result["rule_outcomes_hash"] == run.rule_outcomes_hash
    assert result["rule_catalogue_count"] == 1


def test_portfolio_validation_withholds_pdf_when_rule_outcome_snapshot_is_missing():
    run, company = _records()
    run.rule_outcomes_snapshot = None
    run.rule_outcomes_hash = None
    result = _validation(run, company)
    assert result["valid"] is False
    assert result["pdf_eligible"] is False
    assert "RULE_OUTCOME_SNAPSHOT_MISSING" in result["problems"]
    assert "RULE_OUTCOME_HASH_MISSING" in result["problems"]


def test_portfolio_validation_withholds_pdf_when_rule_outcome_hash_does_not_match():
    run, company = _records()
    run.rule_outcomes_snapshot[0]["outcome_state"] = "NON_COMPLIANT"
    result = _validation(run, company)
    assert result["valid"] is False
    assert result["pdf_eligible"] is False
    assert "RULE_OUTCOME_HASH_MISMATCH" in result["problems"]
    assert "SCORE_HASH_MISMATCH" in result["problems"]


def test_portfolio_validation_withholds_pdf_when_score_hash_does_not_match():
    run, company = _records()
    run.score_hash = "f" * 64
    result = _validation(run, company)
    assert result["valid"] is False
    assert result["pdf_eligible"] is False
    assert "SCORE_HASH_MISMATCH" in result["problems"]


def test_portfolio_validation_withholds_pdf_when_rule_outcome_ids_are_duplicated():
    run, company = _records()
    run.rule_outcomes_snapshot.append(dict(run.rule_outcomes_snapshot[0]))
    run.rule_catalogue_count = 2
    run.rule_outcomes_hash = hash_rule_outcomes_snapshot(run.rule_outcomes_snapshot)
    run.score_hash = calculate_evaluation_score_hash(
        previous_hash=run.previous_hash,
        company_id=run.company_id,
        score=run.score,
        risk_band=run.risk_band,
        calculated_at=run.calculated_at,
        engine_version=run.engine_version,
        trigger_source=run.trigger_source,
        flags_snapshot=run.flags_snapshot,
        fact_provenance_snapshot=run.fact_provenance_snapshot,
        score_breakdown_snapshot=run.score_breakdown_snapshot,
        rule_outcomes_hash=run.rule_outcomes_hash,
        rule_outcomes_snapshot=run.rule_outcomes_snapshot,
    )
    result = _validation(run, company)
    assert result["valid"] is False
    assert result["pdf_eligible"] is False
    assert "RULE_OUTCOME_IDS_DUPLICATED" in result["problems"]


def test_portfolio_validation_withholds_pdf_when_score_reconciliation_fails():
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
