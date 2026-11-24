"""Rescue step updates lock the plan before refreshing steps and calculating progress."""

import ast
import inspect
import textwrap
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.dialects import postgresql

from app.models.enums import RescueStepStatus
from app.services.rescue_service import RescueService


@pytest.fixture
def workflow():
    events = []
    statements = {}
    plan_id = uuid.uuid4()
    step = SimpleNamespace(
        id=uuid.uuid4(), rescue_plan_id=plan_id,
        step_status=RescueStepStatus.PENDING, updated_by=None,
        completed_at=None, completion_notes=None,
    )
    state = SimpleNamespace(
        plan_id=plan_id, lock_id=plan_id, step=step,
        steps=[step], events=events, statements=statements,
    )

    async def execute(stmt):
        sql = str(stmt.compile(dialect=postgresql.dialect()))
        result = MagicMock()
        if sql.startswith("SELECT rescue_steps.rescue_plan_id \n"):
            label = "step plan lookup"
            result.scalar_one_or_none.return_value = state.plan_id
        elif sql.startswith("SELECT rescue_plans.id"):
            label = "plan lock"
            assert "FOR UPDATE" in sql and "rescue_plans" in sql
            result.scalar_one_or_none.return_value = state.lock_id
        elif sql.startswith("UPDATE rescue_plans"):
            label = "plan UPDATE"
        elif "WHERE rescue_steps.id =" in sql:
            label = "step reload"
            result.scalar_one_or_none.return_value = step
        elif "WHERE rescue_steps.rescue_plan_id =" in sql:
            label = "progress select"
            result.scalars.return_value.all.return_value = state.steps
        else:
            raise AssertionError(f"Unexpected statement: {sql}")
        events.append(label)
        statements[label] = (stmt, stmt.get_execution_options())
        return result

    async def flush():
        events.append("flush")

    state.db = MagicMock()
    state.db.execute = AsyncMock(side_effect=execute)
    state.db.flush = AsyncMock(side_effect=flush)
    state.service = RescueService(state.db)
    return state


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("completed", "remaining_status", "percentage", "blocked"),
    [(8, RescueStepStatus.COMPLETE, 100, 0),
     (7, RescueStepStatus.PENDING, 87, 0),
     (7, RescueStepStatus.BLOCKED, 87, 1)],
)
async def test_update_locks_before_refresh_and_progress(
    workflow, completed, remaining_status, percentage, blocked,
):
    workflow.steps = [workflow.step] + [
        SimpleNamespace(step_status=RescueStepStatus.COMPLETE) for _ in range(6)
    ] + [SimpleNamespace(step_status=remaining_status)]
    actor_id = uuid.uuid4()

    result = await workflow.service.update_step(
        workflow.step.id, status=RescueStepStatus.COMPLETE,
        completion_notes="Done", updated_by=actor_id,
    )

    assert result is workflow.step
    assert result.step_status == RescueStepStatus.COMPLETE
    assert result.updated_by == actor_id
    assert result.completion_notes == "Done"
    assert result.completed_at is not None
    workflow.db.add.assert_called_once_with(workflow.step)
    assert workflow.events == [
        "step plan lookup", "plan lock", "step reload", "flush",
        "progress select", "plan UPDATE", "flush",
    ]
    for label in ("step reload", "progress select"):
        assert workflow.statements[label][1].get("populate_existing") is True
    params = workflow.statements["plan UPDATE"][0].compile(
        dialect=postgresql.dialect(),
    ).params
    assert params["completed_steps"] == completed
    assert params["blocked_steps"] == blocked
    assert params["completion_percentage"] == percentage
    assert (params["completed_at"] is not None) is (completed == 8)


@pytest.mark.asyncio
async def test_unknown_step_does_not_lock_or_flush(workflow):
    workflow.plan_id = None

    result = await workflow.service.update_step(
        workflow.step.id, status=RescueStepStatus.COMPLETE,
    )

    assert result is None
    assert workflow.events == ["step plan lookup"]
    workflow.db.add.assert_not_called()
    workflow.db.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_inaccessible_plan_does_not_reload_or_modify_step(workflow):
    workflow.lock_id = None

    result = await workflow.service.update_step(
        workflow.step.id, status=RescueStepStatus.COMPLETE,
    )

    assert result is None
    assert workflow.events == ["step plan lookup", "plan lock"]
    assert workflow.step.step_status == RescueStepStatus.PENDING
    workflow.db.add.assert_not_called()
    workflow.db.flush.assert_not_awaited()


def test_plan_lock_precedes_step_mutation_in_update_step():
    tree = ast.parse(textwrap.dedent(inspect.getsource(RescueService.update_step)))
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    lock_lines = [
        node.lineno for node in calls
        if isinstance(node.func, ast.Attribute) and node.func.attr == "with_for_update"
    ]
    mutation_lines = [
        node.lineno for node in calls
        if (isinstance(node.func, ast.Name) and node.func.id == "setattr")
        or (isinstance(node.func, ast.Attribute)
            and ast.unparse(node.func) == "self.db.add")
    ]
    assert lock_lines and mutation_lines
    assert min(lock_lines) < min(mutation_lines)
