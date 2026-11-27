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

    # The mock returns a configured predecessor hash, so also pin the query
    # contract: same company, strictly earlier timestamp, newest predecessor.
    sql = str(db.statement.compile(compile_kwargs={"literal_binds": True})).lower()
    assert "company_id" in sql and "=" in sql
    assert "calculated_at" in sql and "<" in sql
    assert "order by" in sql and "desc" in sql
    assert "limit" in sql


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
        evaluation_status="NOT_RELEASED",
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
        lambda snapshot: snapshot.update(snapshot_schema_version=True),
        lambda snapshot: snapshot.update(snapshot_schema_version=1.0),
        lambda snapshot: snapshot.update(snapshot_schema_version="1"),
        lambda snapshot: snapshot.update(snapshot_schema_version=2),
        lambda snapshot: snapshot.update(reason=""),
        lambda snapshot: snapshot.update(reason="   "),
        lambda snapshot: snapshot.update(reason="FABRICATED_REASON"),
        lambda snapshot: snapshot.update(reason=["INSUFFICIENT_EVIDENCE_FOR_SCORE"]),
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
@pytest.mark.parametrize(
    ("assessment_source", "findings", "conflicts", "expected_problem"),
    [
        (
            "ENGINE_FINDING",
            [{"flag_code": "INC-001"}],
            [{
                "flag_code": "INC-001",
                "flag_statutory_basis": "Section 23",
                "engine_statutory_basis": "Section 23",
                "catalogue_statutory_basis": "Section 9",
                "binding_reason": "STATUTORY_BASIS_MISMATCH",
                "resolution_status": "UNRESOLVED_STATUTORY_IDENTITY_MISMATCH",
            }],
            "RULE_OUTCOME_SOURCE_CONFLICT_CONTRADICTION",
        ),
        (
            "ENGINE_FINDING_WITH_IDENTITY_CONFLICT",
            [],
            [{
                "flag_code": "INC-001",
                "flag_statutory_basis": "Section 23",
                "engine_statutory_basis": "Section 23",
                "catalogue_statutory_basis": "Section 9",
                "binding_reason": "STATUTORY_BASIS_MISMATCH",
                "resolution_status": "UNRESOLVED_STATUTORY_IDENTITY_MISMATCH",
            }],
            "RULE_OUTCOME_IDENTITY_CONFLICT_SHAPE_INVALID",
        ),
    ],
)
def test_integrity_rejects_contradictory_identity_conflict_shapes(
    assessment_source, findings, conflicts, expected_problem
):
    outcomes = [{
        "rule_id": "INC-001",
        "assessment_source": assessment_source,
        "findings": findings,
        "identity_conflicts": conflicts,
    }]
    run = SimpleNamespace(
        rule_outcomes_snapshot=outcomes,
        rule_outcomes_hash=hash_rule_outcomes_snapshot(outcomes),
        score_hash="a" * 64,
        previous_hash=None,
        rule_catalogue_count=1,
        flags_snapshot=[],
        fact_provenance_snapshot=[],
        score_breakdown_snapshot={},
        calculated_at=datetime(2026, 11, 24, tzinfo=timezone.utc),
        engine_version="2.3",
        trigger_source="TEST",
        company_id=uuid4(),
        score=None,
        risk_band="NOT_EVALUATED",
    )

    problems = evaluation_run_integrity_problems(run)
    assert expected_problem in problems



def test_integrity_rejects_conflict_rows_missing_explicit_conflict_identity_fields():
    outcomes = [{
        "rule_id": "INC-001",
        "scope_version": "RJSC_SCOPE_2026-11-24.1",
        "scope_class": "IN_SCOPE_RJSC",
        "assessment_source": "IDENTITY_MISMATCH_NOT_ATTRIBUTED",
        "findings": [],
        "identity_conflicts": [{
            "resolution_status": "UNRESOLVED_STATUTORY_IDENTITY_MISMATCH",
            "binding_reason": "STATUTORY_BASIS_MISMATCH",
            "engine_statutory_basis": "Section 23",
            "catalogue_statutory_basis": "Section 9",
        }],
    }]
    run = SimpleNamespace(
        rule_outcomes_snapshot=outcomes,
        rule_outcomes_hash=hash_rule_outcomes_snapshot(outcomes),
        score_hash="a" * 64,
        previous_hash=None,
        rule_catalogue_count=1,
        flags_snapshot=[],
        fact_provenance_snapshot=[],
        score_breakdown_snapshot={},
        calculated_at=datetime(2026, 11, 24, tzinfo=timezone.utc),
        engine_version="2.3",
        trigger_source="TEST",
        company_id=uuid4(),
        score=None,
        risk_band="NOT_EVALUATED",
    )
    problems = evaluation_run_integrity_problems(run)
    assert "RULE_OUTCOME_IDENTITY_CONFLICTS_MALFORMED" in problems
    assert "RJSC_RULE_OUTCOME_SCOPE_COVERAGE_MISMATCH" in problems


@pytest.mark.parametrize(
    "run_status",
    ["COMPLETED", "PENDING"],
)
def test_not_released_snapshot_status_must_match_run_status(run_status):
    run = _valid_not_released_run()
    run.evaluation_status = run_status

    problems = evaluation_run_integrity_problems(run)

    assert "EVALUATION_STATUS_SNAPSHOT_MISMATCH" in problems
    assert "SCORE_HASH_MISMATCH" in problems


def test_not_released_run_rejects_snapshot_with_completed_status():
    run = _valid_not_released_run()
    run.score_breakdown_snapshot["status"] = "COMPLETED"

    problems = evaluation_run_integrity_problems(run)

    assert "EVALUATION_STATUS_SNAPSHOT_MISMATCH" in problems
    assert "UNRELEASED_SCORE_BREAKDOWN_INVALID" in problems


def _rehash_versioned_run(run):
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
        evaluation_status=run.evaluation_status,
    )


@pytest.mark.parametrize(
    ("run_status", "snapshot_status"),
    [
        ("COMPLETED", "FAILED"),
        ("FAILED", "COMPLETED"),
    ],
)
def test_versioned_snapshot_status_must_match_for_all_statuses(
    run_status, snapshot_status
):
    run = _valid_not_released_run()
    run.evaluation_status = run_status
    run.score_breakdown_snapshot["status"] = snapshot_status
    _rehash_versioned_run(run)

    problems = evaluation_run_integrity_problems(run)

    assert "EVALUATION_STATUS_SNAPSHOT_MISMATCH" in problems
    # A valid recomputed hash must not hide the status contradiction.
    assert "SCORE_HASH_MISMATCH" not in problems


def test_matching_completed_versioned_status_is_integrity_valid():
    run = _valid_not_released_run()
    run.evaluation_status = "COMPLETED"
    run.score_breakdown_snapshot["status"] = "COMPLETED"
    _rehash_versioned_run(run)

    assert evaluation_run_integrity_problems(run) == []


def test_legacy_not_released_null_snapshot_is_accepted_during_rollout():
    run = _valid_not_released_run()
    run.score_breakdown_snapshot = None
    run.score_hash = calculate_evaluation_score_hash(
        previous_hash=run.previous_hash,
        company_id=run.company_id,
        score=None,
        risk_band="NOT_EVALUATED",
        calculated_at=run.calculated_at,
        engine_version=run.engine_version,
        trigger_source=run.trigger_source,
        flags_snapshot=run.flags_snapshot,
        fact_provenance_snapshot=run.fact_provenance_snapshot,
        score_breakdown_snapshot=None,
        rule_outcomes_hash=run.rule_outcomes_hash,
        rule_outcomes_snapshot=run.rule_outcomes_snapshot,
    )

    assert evaluation_run_integrity_problems(run) == []
