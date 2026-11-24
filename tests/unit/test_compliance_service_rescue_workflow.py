"""Automatic rescue workflows are entitlement-gated and isolated in a savepoint."""

import ast
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from canonical_architecture.rjsc_scope import (
    RJSC_OUT_OF_SCOPE_RULE_IDS,
    is_rjsc_rule_in_scope,
)

from app.services.compliance_service import (
    ComplianceService,
    RescueWorkflowOutcome,
    _score_blocking_catalogue_conflicts,
)


@pytest.fixture
def workflow(monkeypatch):
    events = []

    class FakeSavepoint:
        async def __aenter__(self):
            events.append("savepoint_begin")
            return self

        async def __aexit__(self, exc_type, exc_value, traceback):
            events.append("savepoint_rollback" if exc_type is not None else "savepoint_release")
            return False

    async def generate(*args, **kwargs):
        events.append("generate")
        if rescue.generation_error is not None:
            raise rescue.generation_error

    db = MagicMock()
    db.begin_nested.side_effect = FakeSavepoint
    db.execute = AsyncMock(return_value=MagicMock())
    staff_id = uuid.uuid4()
    db.execute.return_value.scalar_one_or_none.return_value = staff_id
    service = ComplianceService(db)
    service._current_user_id = uuid.uuid4()
    rescue = SimpleNamespace(
        get_active_plan=AsyncMock(return_value=None),
        generate_rescue_plan=AsyncMock(side_effect=generate),
        generation_error=None,
    )
    subscription = SimpleNamespace(has_entitlement=AsyncMock(return_value=True))

    class FakeRescueService:
        def __init__(self, session):
            assert session is db
            self.get_active_plan = rescue.get_active_plan
            self.generate_rescue_plan = rescue.generate_rescue_plan

    class FakeSubscriptionService:
        def __init__(self, session):
            assert session is db
            self.has_entitlement = subscription.has_entitlement

    monkeypatch.setattr("app.services.rescue_service.RescueService", FakeRescueService)
    monkeypatch.setattr(
        "app.services.subscription_service.SubscriptionService", FakeSubscriptionService
    )
    return SimpleNamespace(
        events=events,
        db=db,
        service=service,
        company_id=uuid.uuid4(),
        staff_id=staff_id,
        rescue=rescue,
        subscription=subscription,
        output=SimpleNamespace(
            rescue_sequence=[{"title": "Remediate AGM"}],
            flags=[SimpleNamespace(rule_id="AGM-001", severity="RED", resolved=False)],
        ),
    )


@pytest.mark.asyncio
async def test_unentitled_company_does_not_start_rescue(workflow):
    workflow.subscription.has_entitlement.return_value = False

    result = await workflow.service._start_rescue_workflow(
        workflow.company_id, workflow.output, score_withheld=True, score_blocking_conflicts=set()
    )

    assert result == RescueWorkflowOutcome("NOT_ENTITLED")
    workflow.rescue.get_active_plan.assert_awaited_once_with(workflow.company_id)
    workflow.rescue.generate_rescue_plan.assert_not_awaited()
    workflow.subscription.has_entitlement.assert_awaited_once_with(
        company_id=workflow.company_id, feature_code="corporate_rescue"
    )
    workflow.db.execute.assert_awaited_once()
    assert workflow.events == []


@pytest.mark.asyncio
@pytest.mark.parametrize("score_withheld", [True, False])
async def test_entitled_company_starts_rescue(workflow, score_withheld):
    result = await workflow.service._start_rescue_workflow(
        workflow.company_id, workflow.output,
        score_withheld=score_withheld, score_blocking_conflicts=set()
    )

    assert result == RescueWorkflowOutcome("PLAN_CREATED")
    workflow.subscription.has_entitlement.assert_awaited_once_with(
        company_id=workflow.company_id, feature_code="corporate_rescue"
    )
    assert workflow.db.execute.await_count == 2
    workflow.rescue.generate_rescue_plan.assert_awaited_once_with(
        company_id=workflow.company_id,
        engine_output=workflow.output,
        assigned_staff_id=workflow.staff_id,
        created_by=workflow.service._current_user_id,
        engagement_id=None,
        score_withheld=score_withheld,
        replace_existing=False,
    )
    assert workflow.events == ["savepoint_begin", "generate", "savepoint_release"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("completed_steps", "step_status", "step_title"),
    [(1, "PENDING", "Old title"), (0, "IN_PROGRESS", "Old title"),
     (0, "PENDING", "Remediate AGM")],
    ids=["completed-step", "non-pending-step", "identical-titles"],
)
async def test_existing_plan_is_kept_without_entitlement_query(
    workflow, completed_steps, step_status, step_title
):
    workflow.rescue.get_active_plan.return_value = SimpleNamespace(
        completed_steps=completed_steps,
        steps=[SimpleNamespace(step_title=step_title, step_status=step_status)],
    )

    result = await workflow.service._start_rescue_workflow(
        workflow.company_id, workflow.output, score_withheld=True, score_blocking_conflicts=set()
    )

    assert result == RescueWorkflowOutcome("ACTIVE_PLAN_RETAINED")
    workflow.rescue.generate_rescue_plan.assert_not_awaited()
    workflow.subscription.has_entitlement.assert_not_called()
    workflow.db.execute.assert_awaited_once()
    assert workflow.events == []


@pytest.mark.asyncio
@pytest.mark.parametrize("entitled", [True, False], ids=["entitled", "unentitled"])
async def test_stale_untouched_plan_requires_entitlement_to_regenerate(workflow, entitled):
    workflow.subscription.has_entitlement.return_value = entitled
    workflow.rescue.get_active_plan.return_value = SimpleNamespace(
        completed_steps=0,
        steps=[SimpleNamespace(step_title="Old title", step_status="PENDING")],
    )

    result = await workflow.service._start_rescue_workflow(
        workflow.company_id, workflow.output, score_withheld=True, score_blocking_conflicts=set()
    )

    assert result == RescueWorkflowOutcome("PLAN_CREATED" if entitled else "NOT_ENTITLED")
    workflow.subscription.has_entitlement.assert_awaited_once_with(
        company_id=workflow.company_id, feature_code="corporate_rescue"
    )
    if entitled:
        workflow.rescue.generate_rescue_plan.assert_awaited_once_with(
            company_id=workflow.company_id,
            engine_output=workflow.output,
            assigned_staff_id=workflow.staff_id,
            created_by=workflow.service._current_user_id,
            engagement_id=None,
            score_withheld=True,
            replace_existing=True,
        )
    else:
        workflow.rescue.generate_rescue_plan.assert_not_awaited()
        workflow.db.execute.assert_awaited_once()
        assert workflow.events == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "expected"),
    [(ValueError("boom"), "boom"), (RuntimeError("bad"), "unexpected: bad")],
)
async def test_generation_error_is_returned(workflow, error, expected):
    workflow.rescue.generation_error = error

    result = await workflow.service._start_rescue_workflow(
        workflow.company_id, workflow.output, score_withheld=True, score_blocking_conflicts=set()
    )

    assert result == RescueWorkflowOutcome("GENERATION_FAILED", expected)
    workflow.rescue.generate_rescue_plan.assert_awaited_once()
    assert workflow.events == ["savepoint_begin", "generate", "savepoint_rollback"]


@pytest.mark.asyncio
async def test_entitlement_error_is_returned_without_generation(workflow):
    workflow.subscription.has_entitlement.side_effect = RuntimeError("db down")

    result = await workflow.service._start_rescue_workflow(
        workflow.company_id, workflow.output, score_withheld=True, score_blocking_conflicts=set()
    )

    assert result == RescueWorkflowOutcome("GENERATION_FAILED", "unexpected: db down")
    workflow.subscription.has_entitlement.assert_awaited_once_with(
        company_id=workflow.company_id, feature_code="corporate_rescue"
    )
    workflow.rescue.generate_rescue_plan.assert_not_awaited()
    workflow.db.execute.assert_not_awaited()
    assert workflow.events == []


@pytest.mark.asyncio
@pytest.mark.parametrize("active_plan", [False, True], ids=["no-plan", "active-plan"])
async def test_blocking_catalogue_conflicts_prevent_rescue_before_any_lookup(workflow, active_plan):
    if active_plan:
        workflow.rescue.get_active_plan.return_value = SimpleNamespace(
            completed_steps=0,
            steps=[SimpleNamespace(step_title="Old title", step_status="PENDING")],
        )

    result = await workflow.service._start_rescue_workflow(
        workflow.company_id, workflow.output,
        score_withheld=False, score_blocking_conflicts={"AGM-002", "AGM-001"},
    )

    assert result.status == "BLOCKED_CATALOGUE_CONFLICTS"
    assert result.note.startswith(
        "Rescue generation blocked by unresolved RJSC catalogue/evaluator "
        "identity conflicts: AGM-001, AGM-002"
    )
    workflow.rescue.get_active_plan.assert_not_awaited()
    workflow.subscription.has_entitlement.assert_not_called()
    workflow.rescue.generate_rescue_plan.assert_not_awaited()
    workflow.db.execute.assert_awaited_once()
    assert workflow.events == []


@pytest.mark.asyncio
async def test_blocking_conflict_note_is_truncated_to_500_characters(workflow):
    result = await workflow.service._start_rescue_workflow(
        workflow.company_id, workflow.output,
        score_withheld=False,
        score_blocking_conflicts={f"RULE-{i:03d}" for i in range(200)},
    )

    assert result.status == "BLOCKED_CATALOGUE_CONFLICTS"
    assert len(result.note) == 500


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("rule_id", "blocks_rescue"),
    [("AGM-001", True), (sorted(RJSC_OUT_OF_SCOPE_RULE_IDS)[0], False)],
    ids=["in-scope-conflict", "out-of-scope-conflict"],
)
async def test_catalogue_conflict_scope_matches_automatic_rescue_gate(
    workflow, rule_id, blocks_rescue
):
    assert is_rjsc_rule_in_scope(rule_id) is blocks_rescue
    conflicts = _score_blocking_catalogue_conflicts({rule_id: {"catalogue_is_active": True}})
    assert conflicts == ({rule_id} if blocks_rescue else set())

    result = await workflow.service._start_rescue_workflow(
        workflow.company_id, workflow.output,
        score_withheld=False, score_blocking_conflicts=conflicts,
    )

    if blocks_rescue:
        assert result.status == "BLOCKED_CATALOGUE_CONFLICTS"
        assert result.note.startswith(
            "Rescue generation blocked by unresolved RJSC catalogue/evaluator identity conflicts: "
        )
        workflow.rescue.generate_rescue_plan.assert_not_awaited()
        assert workflow.events == []
    else:
        assert result == RescueWorkflowOutcome("PLAN_CREATED")
        workflow.rescue.generate_rescue_plan.assert_awaited_once()


def test_generation_is_inside_savepoint():
    source = Path(__file__).resolve().parents[2] / "app/services/compliance_service.py"
    tree = ast.parse(source.read_text())
    parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "generate_rescue_plan"
    ]
    assert len(calls) == 1
    ancestors = []
    node = calls[0]
    while node in parents:
        node = parents[node]
        ancestors.append(node)
    assert any(
        isinstance(ancestor, ast.AsyncWith)
        and any(
            isinstance(item.context_expr, ast.Call)
            and isinstance(item.context_expr.func, ast.Attribute)
            and item.context_expr.func.attr == "begin_nested"
            for item in ancestor.items
        )
        for ancestor in ancestors
    )
