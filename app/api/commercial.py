"""
app/api/commercial.py — Commercial / Revenue Pipeline Router
NEUM LEX COUNSEL

All revenue data is ADMIN_STAFF / SUPER_ADMIN only.
Clients never see this data — enforced via require_roles().

Endpoints:
  GET   /commercial/pipeline              Full engagement pipeline (ADMIN+)
  GET   /commercial/funnel                Conversion funnel stats (ADMIN+)
  GET   /commercial/engagements/{company_id}  Engagements for a company
  POST  /commercial/engagements           Create engagement
  PATCH /commercial/engagements/{id}/status  Advance engagement status

  POST  /commercial/quotations            Create quotation
  PATCH /commercial/quotations/{id}/accept  Accept quotation
  PATCH /commercial/quotations/{id}/reject  Reject quotation

  POST  /commercial/tasks                 Create task
  GET   /commercial/tasks/{company_id}    Tasks for a company
  PATCH /commercial/tasks/{id}/complete   Mark task complete
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.core.dependencies import (
    get_current_user,
    get_db_for_user,
    require_roles,
)
from app.services.commercial_service import EngagementService, QuotationService, TaskService
from app.services.notification_service import ActivityService

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.enums import EngagementStatus, RevenueTier
    from app.models.user import User

logger = structlog.get_logger(__name__)
router = APIRouter()

ADMIN_ROLES = ["ADMIN_STAFF", "SUPER_ADMIN"]
STAFF_ROLES = ["ADMIN_STAFF", "SUPER_ADMIN", "LEGAL_STAFF"]


# ---------------------------------------------------------------------------
# Schemas — Engagement
# ---------------------------------------------------------------------------

class EngagementCreateRequest(BaseModel):
    company_id: uuid.UUID
    engagement_type: str = Field(description="COMPLIANCE_PACKAGE | STRUCTURED_REGULARIZATION | CORPORATE_RESCUE")
    revenue_tier: RevenueTier
    description: str | None = None
    estimated_fee_bdt: float | None = Field(None, gt=0)
    assigned_officer_id: uuid.UUID | None = None
    notes: str | None = None


class EngagementStatusUpdateRequest(BaseModel):
    new_status: EngagementStatus
    note: str | None = None


class EngagementResponse(BaseModel):
    engagement_id: str
    company_id: str
    engagement_type: str
    revenue_tier: str
    status: str
    description: str | None
    estimated_fee_bdt: float | None
    confirmed_fee_bdt: float | None
    assigned_officer_id: str | None
    created_at: str
    updated_at: str


# ---------------------------------------------------------------------------
# Schemas — Quotation
# ---------------------------------------------------------------------------

class QuotationCreateRequest(BaseModel):
    engagement_id: uuid.UUID
    company_id: uuid.UUID
    professional_fee_bdt: float = Field(gt=0)
    government_fee_bdt: float = Field(default=0, ge=0)
    vat_bdt: float = Field(default=0, ge=0)
    line_items: list[dict] | None = None
    valid_until_days: int = Field(default=30, ge=7, le=90)
    notes: str | None = None


class QuotationResponse(BaseModel):
    quotation_id: str
    quotation_number: str
    engagement_id: str
    company_id: str
    professional_fee_bdt: float
    government_fee_bdt: float
    vat_bdt: float
    total_fee_bdt: float
    status: str
    valid_until: str
    created_at: str


class QuotationRejectRequest(BaseModel):
    reason: str | None = None


# ---------------------------------------------------------------------------
# Schemas — Task
# ---------------------------------------------------------------------------

class TaskCreateRequest(BaseModel):
    company_id: uuid.UUID
    title: str = Field(min_length=3, max_length=255)
    description: str | None = None
    due_date: str | None = None
    assigned_to_id: uuid.UUID | None = None
    linked_flag_id: uuid.UUID | None = None
    linked_rescue_step_id: uuid.UUID | None = None
    priority: str = Field(default="MEDIUM", description="LOW | MEDIUM | HIGH | CRITICAL")


class TaskCompleteRequest(BaseModel):
    completion_note: str | None = None


class TaskResponse(BaseModel):
    task_id: str
    company_id: str
    title: str
    description: str | None
    status: str
    priority: str
    due_date: str | None
    assigned_to_id: str | None
    completed_at: str | None
    created_at: str


class MessageResponse(BaseModel):
    message: str
    success: bool = True


# ---------------------------------------------------------------------------
# Serialisers
# ---------------------------------------------------------------------------

def _engagement_to_response(e) -> EngagementResponse:
    return EngagementResponse(
        engagement_id=str(e.id),
        company_id=str(e.company_id),
        engagement_type=e.engagement_type,
        revenue_tier=e.revenue_tier,
        status=e.status,
        description=e.description,
        estimated_fee_bdt=e.estimated_fee_bdt,
        confirmed_fee_bdt=e.confirmed_fee_bdt,
        assigned_officer_id=str(e.assigned_officer_id) if e.assigned_officer_id else None,
        created_at=e.created_at.isoformat(),
        updated_at=e.updated_at.isoformat(),
    )


def _quotation_to_response(q) -> QuotationResponse:
    return QuotationResponse(
        quotation_id=str(q.id),
        quotation_number=q.quotation_number,
        engagement_id=str(q.engagement_id),
        company_id=str(q.company_id),
        professional_fee_bdt=q.professional_fee_bdt,
        government_fee_bdt=q.government_fee_bdt,
        vat_bdt=q.vat_bdt,
        total_fee_bdt=q.professional_fee_bdt + q.government_fee_bdt + q.vat_bdt,
        status=q.status,
        valid_until=q.valid_until.isoformat(),
        created_at=q.created_at.isoformat(),
    )


def _task_to_response(t) -> TaskResponse:
    return TaskResponse(
        task_id=str(t.id),
        company_id=str(t.company_id),
        title=t.title,
        description=t.description,
        status=t.status,
        priority=t.priority,
        due_date=str(t.due_date) if t.due_date else None,
        assigned_to_id=str(t.assigned_to_id) if t.assigned_to_id else None,
        completed_at=t.completed_at.isoformat() if t.completed_at else None,
        created_at=t.created_at.isoformat(),
    )


# ===========================================================================
# PIPELINE / ANALYTICS
# ===========================================================================

@router.get(
    "/pipeline",
    dependencies=[Depends(require_roles(*ADMIN_ROLES))],
    summary="Full revenue pipeline with stage breakdown",
)
async def get_pipeline(db: AsyncSession = Depends(get_db_for_user)):
    svc = EngagementService(db)
    return await svc.get_pipeline()


@router.get(
    "/funnel",
    dependencies=[Depends(require_roles(*ADMIN_ROLES))],
    summary="Conversion funnel statistics",
)
async def get_funnel(db: AsyncSession = Depends(get_db_for_user)):
    svc = EngagementService(db)
    return await svc.get_conversion_funnel()


# ===========================================================================
# ENGAGEMENTS
# ===========================================================================

@router.post(
    "/engagements",
    response_model=EngagementResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*ADMIN_ROLES))],
    summary="Create a commercial engagement",
)
async def create_engagement(
    body: EngagementCreateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = EngagementService(db)
    activity = ActivityService(db)

    engagement = await svc.create(
        company_id=body.company_id,
        engagement_type=body.engagement_type,
        revenue_tier=body.revenue_tier,
        description=body.description,
        estimated_fee_bdt=body.estimated_fee_bdt,
        assigned_officer_id=body.assigned_officer_id,
        notes=body.notes,
        created_by=current_user.id,
    )

    await activity.log(
        action="ENGAGEMENT_CREATED",
        resource_type="engagement",
        resource_id=str(engagement.id),
        description=f"Engagement created: {body.engagement_type} for company {body.company_id}",
        ip_address=request.client.host if request.client else None,
        actor_user_id=current_user.id,
    )
    return _engagement_to_response(engagement)


@router.get(
    "/engagements/{company_id}",
    response_model=list[EngagementResponse],
    dependencies=[Depends(require_roles(*ADMIN_ROLES))],
    summary="List engagements for a company",
)
async def list_engagements(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = EngagementService(db)
    engagements = await svc.get_for_company(company_id)
    return [_engagement_to_response(e) for e in engagements]


@router.patch(
    "/engagements/{engagement_id}/status",
    response_model=EngagementResponse,
    dependencies=[Depends(require_roles(*ADMIN_ROLES))],
    summary="Advance engagement to next pipeline stage",
)
async def advance_engagement_status(
    engagement_id: uuid.UUID,
    body: EngagementStatusUpdateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = EngagementService(db)
    activity = ActivityService(db)

    engagement = await svc.advance_status(
        engagement_id=engagement_id,
        new_status=body.new_status,
        note=body.note,
        updated_by=current_user.id,
    )
    if not engagement:
        raise HTTPException(status_code=404, detail="Engagement not found.")

    await activity.log(
        action="ENGAGEMENT_STATUS_UPDATED",
        resource_type="engagement",
        resource_id=str(engagement_id),
        description=f"Engagement status → {body.new_status}",
        ip_address=request.client.host if request.client else None,
        actor_user_id=current_user.id,
    )
    return _engagement_to_response(engagement)


# ===========================================================================
# QUOTATIONS
# ===========================================================================

@router.post(
    "/quotations",
    response_model=QuotationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*ADMIN_ROLES))],
    summary="Create a quotation for an engagement",
)
async def create_quotation(
    body: QuotationCreateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = QuotationService(db)
    activity = ActivityService(db)

    quotation = await svc.create_quotation(
        engagement_id=body.engagement_id,
        company_id=body.company_id,
        professional_fee_bdt=body.professional_fee_bdt,
        government_fee_bdt=body.government_fee_bdt,
        vat_bdt=body.vat_bdt,
        line_items=body.line_items,
        valid_until_days=body.valid_until_days,
        notes=body.notes,
        created_by=current_user.id,
    )

    await activity.log(
        action="QUOTATION_CREATED",
        resource_type="quotation",
        resource_id=str(quotation.id),
        description=f"Quotation {quotation.quotation_number} created",
        ip_address=request.client.host if request.client else None,
        actor_user_id=current_user.id,
    )
    return _quotation_to_response(quotation)


@router.patch(
    "/quotations/{quotation_id}/accept",
    response_model=QuotationResponse,
    dependencies=[Depends(require_roles(*ADMIN_ROLES))],
    summary="Mark a quotation as accepted",
)
async def accept_quotation(
    quotation_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = QuotationService(db)
    activity = ActivityService(db)

    quotation = await svc.accept(quotation_id=quotation_id, accepted_by=current_user.id)
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found.")

    await activity.log(
        action="QUOTATION_ACCEPTED",
        resource_type="quotation",
        resource_id=str(quotation_id),
        description=f"Quotation {quotation.quotation_number} accepted",
        ip_address=request.client.host if request.client else None,
        actor_user_id=current_user.id,
    )
    return _quotation_to_response(quotation)


@router.patch(
    "/quotations/{quotation_id}/reject",
    response_model=QuotationResponse,
    dependencies=[Depends(require_roles(*ADMIN_ROLES))],
    summary="Mark a quotation as rejected",
)
async def reject_quotation(
    quotation_id: uuid.UUID,
    body: QuotationRejectRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = QuotationService(db)
    quotation = await svc.reject(quotation_id=quotation_id, reason=body.reason)
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found.")
    return _quotation_to_response(quotation)


# ===========================================================================
# TASKS
# ===========================================================================

@router.post(
    "/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*STAFF_ROLES))],
    summary="Create a task",
)
async def create_task(
    body: TaskCreateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = TaskService(db)
    task = await svc.create_task(
        company_id=body.company_id,
        title=body.title,
        description=body.description,
        due_date=body.due_date,
        assigned_to_id=body.assigned_to_id,
        linked_flag_id=body.linked_flag_id,
        linked_rescue_step_id=body.linked_rescue_step_id,
        priority=body.priority,
        created_by=current_user.id,
    )
    return _task_to_response(task)


@router.get(
    "/tasks/{company_id}",
    response_model=list[TaskResponse],
    dependencies=[Depends(require_roles(*STAFF_ROLES))],
    summary="List tasks for a company",
)
async def list_tasks(
    company_id: uuid.UUID,
    status_filter: str | None = None,
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = TaskService(db)
    tasks = await svc.get_for_company(company_id=company_id, status_filter=status_filter)
    return [_task_to_response(t) for t in tasks]


@router.patch(
    "/tasks/{task_id}/complete",
    response_model=TaskResponse,
    dependencies=[Depends(require_roles(*STAFF_ROLES))],
    summary="Mark a task as complete",
)
async def complete_task(
    task_id: uuid.UUID,
    body: TaskCompleteRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = TaskService(db)
    task = await svc.complete_task(
        task_id=task_id,
        completed_by=current_user.id,
        completion_note=body.completion_note,
    )
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    return _task_to_response(task)
