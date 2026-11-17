from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.compliance.evaluation_integrity import evaluation_run_chain_problem


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
