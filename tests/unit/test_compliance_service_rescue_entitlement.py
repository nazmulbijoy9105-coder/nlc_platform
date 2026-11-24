"""Automatic rescue workflows require the company's corporate rescue entitlement."""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.compliance_service import ComplianceService


@pytest.fixture
def workflow(monkeypatch):
    db = MagicMock()
    db.execute = AsyncMock(return_value=MagicMock())
    staff_id = uuid.uuid4()
    db.execute.return_value.scalar_one_or_none.return_value = staff_id
    service = ComplianceService(db)
    service._current_user_id = uuid.uuid4()
    rescue = SimpleNamespace(
        get_active_plan=AsyncMock(return_value=None),
        generate_rescue_plan=AsyncMock(),
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
        workflow.company_id, workflow.output, score_withheld=True
    )

    assert result is None
    workflow.rescue.get_active_plan.assert_awaited_once_with(workflow.company_id)
    workflow.rescue.generate_rescue_plan.assert_not_awaited()
    workflow.subscription.has_entitlement.assert_awaited_once_with(
        company_id=workflow.company_id, feature_code="corporate_rescue"
    )
    workflow.db.execute.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("score_withheld", [True, False])
async def test_entitled_company_starts_rescue(workflow, score_withheld):
    result = await workflow.service._start_rescue_workflow(
        workflow.company_id, workflow.output, score_withheld=score_withheld
    )

    assert result is None
    workflow.subscription.has_entitlement.assert_awaited_once_with(
        company_id=workflow.company_id, feature_code="corporate_rescue"
    )
    workflow.db.execute.assert_awaited_once()
    workflow.rescue.generate_rescue_plan.assert_awaited_once_with(
        company_id=workflow.company_id,
        engine_output=workflow.output,
        assigned_staff_id=workflow.staff_id,
        created_by=workflow.service._current_user_id,
        engagement_id=None,
        score_withheld=score_withheld,
    )


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
        workflow.company_id, workflow.output, score_withheld=True
    )

    assert result is None
    workflow.rescue.generate_rescue_plan.assert_not_awaited()
    workflow.subscription.has_entitlement.assert_not_called()
    workflow.db.execute.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("entitled", [True, False], ids=["entitled", "unentitled"])
async def test_stale_untouched_plan_requires_entitlement_to_regenerate(workflow, entitled):
    workflow.subscription.has_entitlement.return_value = entitled
    workflow.rescue.get_active_plan.return_value = SimpleNamespace(
        completed_steps=0,
        steps=[SimpleNamespace(step_title="Old title", step_status="PENDING")],
    )

    result = await workflow.service._start_rescue_workflow(
        workflow.company_id, workflow.output, score_withheld=True
    )

    assert result is None
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
        )
    else:
        workflow.rescue.generate_rescue_plan.assert_not_awaited()
        workflow.db.execute.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "expected"),
    [(ValueError("boom"), "boom"), (RuntimeError("bad"), "unexpected: bad")],
)
async def test_generation_error_is_returned(workflow, error, expected):
    workflow.rescue.generate_rescue_plan.side_effect = error

    result = await workflow.service._start_rescue_workflow(
        workflow.company_id, workflow.output, score_withheld=True
    )

    assert result == expected
    workflow.rescue.generate_rescue_plan.assert_awaited_once()


@pytest.mark.asyncio
async def test_entitlement_error_is_returned_without_generation(workflow):
    workflow.subscription.has_entitlement.side_effect = RuntimeError("db down")

    result = await workflow.service._start_rescue_workflow(
        workflow.company_id, workflow.output, score_withheld=True
    )

    assert result == "unexpected: db down"
    workflow.subscription.has_entitlement.assert_awaited_once_with(
        company_id=workflow.company_id, feature_code="corporate_rescue"
    )
    workflow.rescue.generate_rescue_plan.assert_not_awaited()
    workflow.db.execute.assert_not_awaited()
