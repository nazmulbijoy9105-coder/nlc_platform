from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.compliance.evaluation_integrity import (\n    evaluation_run_chain_problem,\n    evaluation_run_integrity_problems,\n)\nfrom app.compliance.rule_outcome_ledger import hash_rule_outcomes_snapshot


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
