"""
app/api/rescue.py — Corporate Rescue Router
NEUM LEX COUNSEL

Endpoints:
  POST  /rescue/plans                       Generate rescue plan (BLACK band only)
  GET   /rescue/plans/{company_id}/active   Get active rescue plan for a company
  GET   /rescue/plans/{plan_id}             Get rescue plan with all steps
  PATCH /rescue/plans/{plan_id}/steps/{step_number}   Update a rescue step status
  POST  /rescue/plans/{plan_id}/engagement  Create engagement from rescue plan
  GET   /rescue/plans                       List all rescue plans (ADMIN_STAFF+)

Business rules:
  - Rescue plans may only be created for companies in BLACK or RED band
  - Only one active rescue plan per company at a time
  - Step 8 completion triggers automatic compliance re-evaluation via Celery
  - Engagement creation is admin-only (revenue tracking)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.core.dependencies import (
    get_current_user,
    get_db_for_user,
    require_company_access,
    require_roles,
)
from app.models.enums import RiskBand
from app.services.company_service import CompanyService
from app.services.notification_service import ActivityService
from app.services.rescue_service import RescueService

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.user import User

logger = structlog.get_logger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class RescuePlanCreateRequest(BaseModel):
    company_id: uuid.UUID
    notes: str | None = None
    assigned_officer_id: uuid.UUID | None = None
    estimated_fee_bdt: float | None = Field(None, gt=0)
    target_completion_date: str | None = None


class RescueStepUpdateRequest(BaseModel):
    status: str = Field(description="PENDING | IN_PROGRESS | COMPLETED | BLOCKED")
    completion_note: str | None = None
    completion_document_id: uuid.UUID | None = None


class EngagementFromRescueRequest(BaseModel):
    confirmed_fee_bdt: float = Field(gt=0)
    payment_terms: str | None = None
    notes: str | None = None


class RescueStepResponse(BaseModel):
    step_id: str
    step_number: int
    step_name: str
    description: str
    status: str
    completion_note: str | None
    started_at: str | None
    completed_at: str | None
    triggers_reevaluation: bool


class RescuePlanResponse(BaseModel):
    plan_id: str
    company_id: str
    company_name: str | None
    status: str
    completion_percentage: float
    total_steps: int
    completed_steps: int
    estimated_fee_bdt: float | None
    assigned_officer_id: str | None
    target_completion_date: str | None
    engagement_id: str | None
    steps: list[RescueStepResponse]
    created_at: str
    updated_at: str


class MessageResponse(BaseModel):
    message: str
    success: bool = True


# ---------------------------------------------------------------------------
# Serialisers
# ---------------------------------------------------------------------------

def _step_to_response(step) -> RescueStepResponse:
    return RescueStepResponse(
        step_id=str(step.id),
        step_number=step.step_number,
        step_name=step.step_name,
        description=step.description,
        status=step.status,
        completion_note=step.completion_note,
        started_at=step.started_at.isoformat() if step.started_at else None,
        completed_at=step.completed_at.isoformat() if step.completed_at else None,
        triggers_reevaluation=step.triggers_reevaluation,
    )


def _plan_to_response(plan, company=None) -> RescuePlanResponse:
    return RescuePlanResponse(
        plan_id=str(plan.id),
        company_id=str(plan.company_id),
        company_name=company.company_name if company else None,
        status=plan.status,
        completion_percentage=plan.completion_percentage,
        total_steps=plan.total_steps,
        completed_steps=plan.completed_steps,
        estimated_fee_bdt=plan.estimated_fee_bdt,
        assigned_officer_id=str(plan.assigned_officer_id) if plan.assigned_officer_id else None,
        target_completion_date=str(plan.target_completion_date) if plan.target_completion_date else None,
        engagement_id=str(plan.engagement_id) if plan.engagement_id else None,
        steps=[_step_to_response(s) for s in (plan.steps or [])],
        created_at=plan.created_at.isoformat(),
        updated_at=plan.updated_at.isoformat(),
    )


# ---------------------------------------------------------------------------
# POST /rescue/plans — Generate rescue plan
# ---------------------------------------------------------------------------

@router.post(
    "/plans",
    response_model=RescuePlanResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles("ADMIN_STAFF", "SUPER_ADMIN", "LEGAL_STAFF"))],
    summary="Generate a corporate rescue plan for a BLACK or RED band company",
)
async def create_rescue_plan(
    body: RescuePlanCreateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    company_svc = CompanyService(db)
    rescue_svc = RescueService(db)
    activity = ActivityService(db)

    # Verify company exists and fetch
    company = await company_svc.get_by_id_or_404(body.company_id)

    # Enforce: rescue plans only for RED or BLACK companies
    if company.current_risk_band not in (RiskBand.RED, RiskBand.BLACK, "RED", "BLACK"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Rescue plans may only be created for companies in RED or BLACK band. "
                f"'{company.company_name}' is currently in {company.current_risk_band} band."
            ),
        )

    # Check for existing active plan
    existing = await rescue_svc.get_active_plan(body.company_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"An active rescue plan (ID: {existing.id}) already exists for this company. "
                f"Complete or close the existing plan before creating a new one."
            ),
        )

    plan = await rescue_svc.generate_rescue_plan(
        company_id=body.company_id,
        created_by=current_user.id,
        assigned_officer_id=body.assigned_officer_id,
        estimated_fee_bdt=body.estimated_fee_bdt,
        target_completion_date=body.target_completion_date,
        notes=body.notes,
    )

    await activity.log(
        action="RESCUE_PLAN_CREATED",
        resource_type="rescue_plan",
        resource_id=str(plan.id),
        description=f"8-step rescue plan created for '{company.company_name}'",
        ip_address=request.client.host if request.client else None,
        actor_user_id=current_user.id,
    )

    logger.info("rescue_plan_created", plan_id=str(plan.id), company_id=str(body.company_id))
    return _plan_to_response(plan, company)


# ---------------------------------------------------------------------------
# GET /rescue/plans — List all rescue plans (admin)
# ---------------------------------------------------------------------------

@router.get(
    "/plans",
    response_model=list[RescuePlanResponse],
    dependencies=[Depends(require_roles("ADMIN_STAFF", "SUPER_ADMIN", "LEGAL_STAFF"))],
    summary="List all rescue plans across the portfolio",
)
async def list_rescue_plans(
    db: AsyncSession = Depends(get_db_for_user),
):
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.models.rescue import RescuePlan

    result = await db.execute(
        select(RescuePlan)
        .options(selectinload(RescuePlan.steps))
        .order_by(RescuePlan.created_at.desc())
    )
    plans = result.scalars().all()
    return [_plan_to_response(p) for p in plans]


# ---------------------------------------------------------------------------
# GET /rescue/plans/{company_id}/active — Active plan for a company
# ---------------------------------------------------------------------------

@router.get(
    "/plans/{company_id}/active",
    response_model=RescuePlanResponse,
    dependencies=[Depends(require_company_access("company_id"))],
    summary="Get the active rescue plan for a company",
)
async def get_active_plan(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_for_user),
):
    rescue_svc = RescueService(db)
    company_svc = CompanyService(db)

    plan = await rescue_svc.get_active_plan(company_id)
    if not plan:
        raise HTTPException(
            status_code=404,
            detail="No active rescue plan found for this company.",
        )

    company = await company_svc.get_by_id_or_404(company_id)
    return _plan_to_response(plan, company)


# ---------------------------------------------------------------------------
# GET /rescue/plans/{plan_id} — Get plan by ID
# ---------------------------------------------------------------------------

@router.get(
    "/plans/detail/{plan_id}",
    response_model=RescuePlanResponse,
    summary="Get a rescue plan by ID with all steps",
)
async def get_rescue_plan(
    plan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_for_user),
):
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.models.rescue import RescuePlan

    result = await db.execute(
        select(RescuePlan)
        .where(RescuePlan.id == plan_id)
        .options(selectinload(RescuePlan.steps))
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Rescue plan not found.")
    return _plan_to_response(plan)


# ---------------------------------------------------------------------------
# PATCH /rescue/plans/{plan_id}/steps/{step_number} — Update step
# ---------------------------------------------------------------------------

@router.patch(
    "/plans/{plan_id}/steps/{step_number}",
    response_model=RescuePlanResponse,
    dependencies=[Depends(require_roles("ADMIN_STAFF", "SUPER_ADMIN", "LEGAL_STAFF"))],
    summary="Update the status of a rescue step",
    description=(
        "Updating Step 8 to COMPLETED automatically triggers compliance re-evaluation "
        "via Celery (AI Constitution: deterministic rule engine, not AI)."
    ),
)
async def update_rescue_step(
    plan_id: uuid.UUID,
    step_number: int,
    body: RescueStepUpdateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    rescue_svc = RescueService(db)
    activity = ActivityService(db)

    valid_statuses = ("PENDING", "IN_PROGRESS", "COMPLETED", "BLOCKED")
    if body.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{body.status}'. Must be one of: {valid_statuses}",
        )

    plan = await rescue_svc.update_step(
        plan_id=plan_id,
        step_number=step_number,
        new_status=body.status,
        completion_note=body.completion_note,
        completion_document_id=body.completion_document_id,
        updated_by=current_user.id,
    )
    if not plan:
        raise HTTPException(status_code=404, detail="Rescue plan or step not found.")

    await activity.log(
        action="RESCUE_STEP_UPDATED",
        resource_type="rescue_plan",
        resource_id=str(plan_id),
        description=f"Step {step_number} updated to {body.status}",
        ip_address=request.client.host if request.client else None,
        actor_user_id=current_user.id,
    )

    # Step 8 COMPLETED → trigger re-evaluation via Celery
    if step_number == 8 and body.status == "COMPLETED":
        try:
            from app.worker.tasks import trigger_rescue_reevaluation
            trigger_rescue_reevaluation.apply_async(
                kwargs={
                    "company_id": str(plan.company_id),
                    "rescue_plan_id": str(plan_id),
                    "completed_step_number": 8,
                },
                countdown=10,
            )
            logger.info("rescue_reevaluation_dispatched", plan_id=str(plan_id))
        except Exception as e:
            logger.warning("rescue_reevaluation_dispatch_failed", error=str(e))

    return _plan_to_response(plan)


# ---------------------------------------------------------------------------
# POST /rescue/plans/{plan_id}/engagement — Create engagement from rescue
# ---------------------------------------------------------------------------

@router.post(
    "/plans/{plan_id}/engagement",
    response_model=MessageResponse,
    dependencies=[Depends(require_roles("ADMIN_STAFF", "SUPER_ADMIN"))],
    summary="Create a commercial engagement record from a rescue plan",
)
async def create_engagement_from_rescue(
    plan_id: uuid.UUID,
    body: EngagementFromRescueRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    rescue_svc = RescueService(db)
    activity = ActivityService(db)

    engagement = await rescue_svc.create_engagement_from_rescue(
        plan_id=plan_id,
        confirmed_fee_bdt=body.confirmed_fee_bdt,
        payment_terms=body.payment_terms,
        notes=body.notes,
        created_by=current_user.id,
    )
    if not engagement:
        raise HTTPException(status_code=404, detail="Rescue plan not found.")

    await activity.log(
        action="ENGAGEMENT_CREATED_FROM_RESCUE",
        resource_type="engagement",
        resource_id=str(engagement.id),
        description=f"Engagement created from rescue plan {plan_id}. Fee: {body.confirmed_fee_bdt} BDT",
        ip_address=request.client.host if request.client else None,
        actor_user_id=current_user.id,
    )
    return MessageResponse(
        message="Engagement created successfully. Quotation will be generated shortly."
    )
