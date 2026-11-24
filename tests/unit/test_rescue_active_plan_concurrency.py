"""Concurrency and database invariant contract for active rescue plans."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.dialects import postgresql

from app.models.rescue import RescuePlan
from app.services.rescue_service import (
    ActiveRescuePlanExistsError,
    RescueService,
)

ROOT = Path(__file__).resolve().parents[2]


def _result(value):
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


class _Savepoint:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        return False


@pytest.mark.asyncio
async def test_service_locks_company_before_check_and_create():
    company_id = __import__("uuid").uuid4()
    plan = SimpleNamespace(id=__import__("uuid").uuid4())
    db = MagicMock()
    statements = []
    async def execute(statement):
        statements.append(statement)
        return _result(company_id if len(statements) == 1 else None)

    db.execute = AsyncMock(side_effect=execute)
    db.begin_nested.return_value = _Savepoint()
    service = RescueService(db)
    service._generate_rescue_plan = AsyncMock(return_value=plan)

    result = await service.generate_rescue_plan(
        company_id, engine_output=SimpleNamespace(), score_withheld=True
    )

    assert result is plan
    assert len(statements) == 2
    lock_sql = str(statements[0].compile(dialect=postgresql.dialect()))
    assert "FROM companies" in lock_sql
    assert "FOR UPDATE" in lock_sql
    service._generate_rescue_plan.assert_awaited_once()
    assert service._generate_rescue_plan.await_args.args[0] == company_id


@pytest.mark.asyncio
async def test_service_rejects_second_active_plan_after_company_lock():
    company_id = __import__("uuid").uuid4()
    active_plan_id = __import__("uuid").uuid4()
    db = MagicMock()
    statements = []
    async def execute(statement):
        statements.append(statement)
        return _result(company_id if len(statements) == 1 else active_plan_id)

    db.execute = AsyncMock(side_effect=execute)
    service = RescueService(db)
    service._generate_rescue_plan = AsyncMock()

    with pytest.raises(ActiveRescuePlanExistsError, match=str(active_plan_id)):
        await service.generate_rescue_plan(
            company_id, engine_output=SimpleNamespace(), score_withheld=True
        )

    assert len(statements) == 2
    assert "FOR UPDATE" in str(statements[0].compile(dialect=postgresql.dialect()))
    service._generate_rescue_plan.assert_not_awaited()


@pytest.mark.asyncio
async def test_evaluation_can_replace_only_after_its_locked_stale_plan_decision():
    company_id = __import__("uuid").uuid4()
    active_plan_id = __import__("uuid").uuid4()
    plan = SimpleNamespace(id=__import__("uuid").uuid4())
    db = MagicMock()
    statements = []
    async def execute(statement):
        statements.append(statement)
        return _result(company_id if len(statements) == 1 else active_plan_id)

    db.execute = AsyncMock(side_effect=execute)
    db.begin_nested.return_value = _Savepoint()
    service = RescueService(db)
    service._generate_rescue_plan = AsyncMock(return_value=plan)

    result = await service.generate_rescue_plan(
        company_id, engine_output=SimpleNamespace(), score_withheld=True,
        replace_existing=True,
    )

    assert result is plan
    service._generate_rescue_plan.assert_awaited_once()


def test_migration_creates_partial_unique_active_plan_index():
    migration = (
        ROOT / "alembic" / "versions"
        / "0127_one_active_rescue_plan_per_company.py"
    ).read_text(encoding="utf-8")

    assert 'revision = "0127_one_active_rescue_plan_per_company"' in migration
    assert 'down_revision = "0126_score_independent_rescue_workflow"' in migration
    assert "_INDEX_NAME = \"uq_rescue_plans_one_active_per_company\"" in migration
    assert "unique=True" in migration
    assert 'postgresql_where=sa.text("is_active IS TRUE")' in migration
    assert "HAVING count(*) > 1" in migration
    assert "Cannot enforce one active rescue plan per company" in migration


def test_migration_refuses_to_hide_existing_duplicate_active_plans(monkeypatch):
    path = ROOT / "alembic" / "versions" / "0127_one_active_rescue_plan_per_company.py"
    spec = importlib.util.spec_from_file_location("migration_0127", path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    calls = []
    duplicate = (str(__import__("uuid").uuid4()), 2)
    bind = SimpleNamespace(execute=lambda statement: SimpleNamespace(all=lambda: [duplicate]))
    fake_op = SimpleNamespace(
        get_bind=lambda: bind,
        create_index=lambda *args, **kwargs: calls.append((args, kwargs)),
    )
    monkeypatch.setattr(migration, "op", fake_op)

    with pytest.raises(RuntimeError, match="duplicate active plans"):
        migration.upgrade()
    assert calls == []



def test_orm_model_declares_the_same_partial_unique_index():
    indexes = {
        index.name: index
        for index in RescuePlan.__table__.indexes
    }
    index = indexes["uq_rescue_plans_one_active_per_company"]
    assert index.unique is True
    assert [column.name for column in index.columns] == ["company_id"]
    assert "is_active IS TRUE" in str(index.dialect_options["postgresql"]["where"])
    assert "is_active IS TRUE" in str(index.dialect_options["sqlite"]["where"])


def test_migration_creates_index_after_clean_preflight(monkeypatch):
    path = ROOT / "alembic" / "versions" / "0127_one_active_rescue_plan_per_company.py"
    spec = importlib.util.spec_from_file_location("migration_0127_clean", path)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    calls = []
    bind = SimpleNamespace(execute=lambda statement: SimpleNamespace(all=lambda: []))
    fake_op = SimpleNamespace(
        get_bind=lambda: bind,
        create_index=lambda *args, **kwargs: calls.append((args, kwargs)),
    )
    monkeypatch.setattr(migration, "op", fake_op)

    migration.upgrade()

    assert len(calls) == 1
    args, kwargs = calls[0]
    assert args[:3] == (
        "uq_rescue_plans_one_active_per_company",
        "rescue_plans",
        ["company_id"],
    )
    assert kwargs["unique"] is True
    assert "is_active IS TRUE" in str(kwargs["postgresql_where"])
