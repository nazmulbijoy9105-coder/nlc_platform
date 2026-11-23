from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.compliance.evaluation_integrity import (
    calculate_evaluation_score_hash,
    evaluation_run_chain_problem,
    evaluation_run_integrity_problems,
)
from app.compliance.rule_outcome_ledger import hash_rule_outcomes_snapshot


class _Result:
    def __init__(self, value):
        self.value = value

    def one_or_none(self):
        if self.value is None:
            return None
        return SimpleNamespace(score_hash=self.value)


class _DB:
    def __init__(self, predecessor_hash):
        self.predecessor_hash = predecessor_hash
        self.statement = None

    async def execute(self, statement):
        self.statement = statement
        return _Result(self.predecessor_hash)


@pytest.mark.asyncio
async def test_chain_accepts_exact_previous_run_hash():
    previous_hash = "a" * 64
    db = _DB(previous_hash)
    run = SimpleNamespace(
        company_id=uuid4(),
        calculated_at=datetime(2026, 11, 13, tzinfo=timezone.utc),
        previous_hash=previous_hash,
    )
    assert await evaluation_run_chain_problem(db, run) is None
    assert db.statement is not None


@pytest.mark.asyncio
async def test_chain_rejects_wrong_previous_run_hash():
    db = _DB("a" * 64)
    run = SimpleNamespace(
        company_id=uuid4(),
        calculated_at=datetime(2026, 11, 13, tzinfo=timezone.utc),
        previous_hash="b" * 64,
    )
    assert await evaluation_run_chain_problem(db, run) == "PREVIOUS_HASH_CHAIN_MISMATCH"


@pytest.mark.asyncio
async def test_chain_requires_genesis_run_to_have_no_previous_hash():
    db = _DB(None)
    run = SimpleNamespace(
        company_id=uuid4(),
        calculated_at=datetime(2026, 11, 13, tzinfo=timezone.utc),
        previous_hash=None,
    )
    assert await evaluation_run_chain_problem(db, run) is None


@pytest.mark.asyncio
async def test_chain_rejects_non_genesis_run_with_missing_previous_hash():
    db = _DB("a" * 64)
    run = SimpleNamespace(
        company_id=uuid4(),
        calculated_at=datetime(2026, 11, 13, tzinfo=timezone.utc),
        previous_hash=None,
    )
    assert await evaluation_run_chain_problem(db, run) == "PREVIOUS_HASH_CHAIN_MISMATCH"


@pytest.mark.asyncio
async def test_chain_rejects_missing_run_context():
    db = _DB(None)
    run = SimpleNamespace(company_id=None, calculated_at=None, previous_hash=None)
    assert await evaluation_run_chain_problem(db, run) == "PREVIOUS_HASH_CHAIN_CONTEXT_MISSING"



def _valid_not_released_run():
    company_id = uuid4()
    calculated_at = datetime(2026, 11, 24, tzinfo=timezone.utc)
    outcomes = [{
        "rule_id": "AGM-001",
        "assessment_source": "NO_FINDING_EMITTED_NOT_PROOF_OF_COMPLIANCE",
        "findings": [],
        "identity_conflicts": [],
    }]
    outcomes_hash = hash_rule_outcomes_snapshot(outcomes)
    snapshot = {
        "snapshot_schema_version": 1,
        "status": "NOT_RELEASED",
        "reason": "INSUFFICIENT_EVIDENCE_FOR_SCORE",
        "score": None,
        "risk_band": "NOT_EVALUATED",
        "scoring_data": "WITHHELD",
    }
    run = SimpleNamespace(
        company_id=company_id,
        calculated_at=calculated_at,
        previous_hash=None,
        score=None,
        risk_band="NOT_EVALUATED",
        engine_version="2.3",
        trigger_source="MANUAL",
        evaluation_status="NOT_RELEASED",
        flags_snapshot=[],
        fact_provenance_snapshot=[],
        score_breakdown_snapshot=snapshot,
        rule_outcomes_snapshot=outcomes,
        rule_outcomes_hash=outcomes_hash,
        rule_catalogue_count=1,
        score_hash=None,
    )
    run.score_hash = calculate_evaluation_score_hash(
        previous_hash=None,
        company_id=company_id,
        score=None,
        risk_band="NOT_EVALUATED",
        calculated_at=calculated_at,
        engine_version="2.3",
        trigger_source="MANUAL",
        flags_snapshot=[],
        fact_provenance_snapshot=[],
        score_breakdown_snapshot=snapshot,
        rule_outcomes_hash=outcomes_hash,
        rule_outcomes_snapshot=outcomes,
    )
    return run


def test_not_released_snapshot_is_integrity_valid_without_score_data():
    run = _valid_not_released_run()
    assert evaluation_run_integrity_problems(run) == []


@pytest.mark.parametrize(
    "mutation",
    [
        lambda snapshot: snapshot.update(score=75),
        lambda snapshot: snapshot.update(raw_total=25),
        lambda snapshot: snapshot.update(category_deductions={"AGM": 5}),
        lambda snapshot: snapshot.update(risk_band="GREEN"),
        lambda snapshot: snapshot.update(reason=""),
    ],
)
def test_not_released_snapshot_rejects_invented_or_invalid_score_data(mutation):
    run = _valid_not_released_run()
    mutation(run.score_breakdown_snapshot)
    run.score_hash = calculate_evaluation_score_hash(
        previous_hash=None,
        company_id=run.company_id,
        score=None,
        risk_band="NOT_EVALUATED",
        calculated_at=run.calculated_at,
        engine_version=run.engine_version,
        trigger_source=run.trigger_source,
        flags_snapshot=run.flags_snapshot,
        fact_provenance_snapshot=run.fact_provenance_snapshot,
        score_breakdown_snapshot=run.score_breakdown_snapshot,
        rule_outcomes_hash=run.rule_outcomes_hash,
        rule_outcomes_snapshot=run.rule_outcomes_snapshot,
    )
    assert "UNRELEASED_SCORE_BREAKDOWN_INVALID" in evaluation_run_integrity_problems(run)
