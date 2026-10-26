"""RES-011: Contract test for rescue→engagement function call.

Verifies that:
1. generate_rescue_plan accepts engagement_id parameter
2. RescuePlan model has engagement_id field
3. engagement_id column is nullable
4. RescueAuditLog model exists (RES-017)
5. When engagement_id is passed, the plan preserves it
"""
from __future__ import annotations

import inspect
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest


def test_generate_rescue_plan_accepts_engagement_id_parameter():
    """RES-011: generate_rescue_plan must accept engagement_id as a parameter."""
    from app.services.rescue_service import RescueService
    sig = inspect.signature(RescueService.generate_rescue_plan)
    params = sig.parameters
    assert "engagement_id" in params, (
        "generate_rescue_plan must accept engagement_id parameter (RES-010/RES-011). "
        f"Found parameters: {list(params.keys())}"
    )
    assert params["engagement_id"].default is None, (
        "engagement_id default should be None (optional parameter)"
    )


def test_rescue_plan_has_engagement_id_field():
    """RES-011: RescuePlan model must have engagement_id field."""
    from app.models.rescue import RescuePlan
    assert hasattr(RescuePlan, "engagement_id"), (
        "RescuePlan model must have engagement_id field (RES-010)"
    )


def test_rescue_plan_engagement_id_is_nullable():
    """RES-011: engagement_id column should be nullable."""
    from app.models.rescue import RescuePlan
    col = RescuePlan.__table__.columns.get("engagement_id")
    assert col is not None, "RescuePlan.engagement_id column must exist"
    assert col.nullable is True, "engagement_id must be nullable"


def test_rescue_audit_log_model_exists():
    """RES-017: RescueAuditLog model must exist for audit trail."""
    from app.models.rescue_audit_log import RescueAuditLog
    assert RescueAuditLog.__tablename__ == "rescue_audit_log"


@pytest.mark.asyncio
async def test_generate_rescue_plan_passes_engagement_id_to_create():
    """RES-011: the supplied engagement ID must reach plan persistence."""
    from app.services.rescue_service import RescueService

    db = MagicMock()
    db.execute = AsyncMock()
    db.refresh = AsyncMock()

    svc = RescueService(db=db)
    test_engagement_id = uuid.uuid4()
    company_id = uuid.uuid4()

    # Return a minimal plan-like object so this test isolates the create contract.
    created_plan = MagicMock()
    created_plan.id = uuid.uuid4()
    created_plan.engagement_id = test_engagement_id
    svc.create = AsyncMock(return_value=created_plan)
    svc._create_step = AsyncMock(return_value=MagicMock())
    svc._create_tasks_from_steps = AsyncMock()

    engine_output = MagicMock()
    engine_output.rescue_sequence = [{"title": "Test rescue step"}]
    engine_output.score_breakdown = MagicMock(
        final_score=50,
        risk_band="RED",
    )

    result = await svc.generate_rescue_plan(
        company_id=company_id,
        engine_output=engine_output,
        engagement_id=test_engagement_id,
    )

    assert result is created_plan
    svc.create.assert_awaited_once()
    create_kwargs = svc.create.await_args.kwargs
    assert create_kwargs["company_id"] == company_id
    assert create_kwargs["engagement_id"] == test_engagement_id
