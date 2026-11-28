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
  - Score-independent statutory workflows require eligible, active, evidence-supported RJSC findings
  - Only one active rescue plan per company at a time
  - Step 8 completion triggers automatic compliance re-evaluation via Celery
  - Engagement creation is admin-only (revenue tracking) and withheld while
    product score publication is disabled
"""


import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.core.entitlement import require_entitlement
from app.core.company_authorization import ensure_staff_company_scope
from app.core.dependencies import (
    get_current_user,
    get_db_for_user,
    require_company_access,
    require_roles,
)
from app.models.user import User
from app.models.company import Company
from app.models.company_fact import CompanyFact
from app.compliance.fact_provenance import (
    business_date_today,
    coerce_company_profile_fact_value,
    is_internal_profile_fact_key,
    verified_document_fact_keys,
)
from app.services.company_service import CompanyService
from app.services.notification_service import ActivityService
from app.services.rescue_service import ActiveRescuePlanExistsError, RescueService
async def _assert_rescue_entitlement(
    company_id: uuid.UUID, current_user: User, db: AsyncSession
) -> None:
    role = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    if role in ("SUPER_ADMIN", "ADMIN_STAFF"):
        return
    await ensure_staff_company_scope(company_id, current_user, db)
    from app.services.subscription_service import SubscriptionService

    if not await SubscriptionService(db).has_entitlement(
        company_id=company_id,
        feature_code="corporate_rescue",
    ):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="This company does not have an active corporate-rescue entitlement.",
        )


router = APIRouter()


def _require_commercial_engagement_release() -> None:
    """Withhold commercial engagements while product scoring is disabled.

    Statutory-action rescue workflows are not score-gated; only the commercial
    engagement record is.
    """
    from app.rule_engine.engine import legal_score_is_released

    if not legal_score_is_released():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Commercial engagements are withheld because product scoring is disabled."
            ),
        )

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class RescuePlanCreateRequest(BaseModel):
    company_id: uuid.UUID
    notes: str | None = None
    assigned_staff_id: uuid.UUID | None = None
    estimated_fee_bdt: float | None = Field(None, gt=0)
    target_completion_date: str | None = None


class RescueStepUpdateRequest(BaseModel):
    status: str = Field(description="PENDING | IN_PROGRESS | COMPLETE | BLOCKED")
    completion_notes: str | None = None
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
    completion_notes: str | None
    started_at: str | None
    completed_at: str | None
    statutory_basis: str | None = None
    complexity: str | None = None
    estimated_days_min: int | None = None
    estimated_days_max: int | None = None
    triggers_reevaluation: bool


class RescuePlanResponse(BaseModel):
    plan_id: str
    workflow_mode: str
    company_id: str
    company_name: str | None
    status: str
    completion_percentage: float
    total_steps: int
    completed_steps: int
    estimated_fee_bdt: float | None
    assigned_staff_id: str | None
    target_completion_date: str | None
    engagement_id: str | None
    source_rule_ids: list[str] = Field(default_factory=list)
    steps: list[RescueStepResponse]
    created_at: str
    updated_at: str


class MessageResponse(BaseModel):
    message: str

# ---------------------------------------------------------------------------

def _step_to_response(step) -> RescueStepResponse:
    return RescueStepResponse(
        step_id=str(step.id),
        step_number=step.step_number,
        step_name=step.step_title,
        description=step.step_description,
        status=step.step_status,
        completion_notes=step.completion_notes,
        started_at=step.started_at.isoformat() if step.started_at else None,
        completed_at=step.completed_at.isoformat() if step.completed_at else None,
        statutory_basis=getattr(step, "statutory_basis", None),
        complexity=getattr(step.complexity, "value", step.complexity),
        estimated_days_min=getattr(step, "estimated_days_min", None),
        estimated_days_max=getattr(step, "estimated_days_max", None),
        triggers_reevaluation=step.triggers_reevaluation,
    )


def _plan_to_response(plan, company=None) -> RescuePlanResponse:
    return RescuePlanResponse(
        plan_id=str(plan.id),
        workflow_mode=getattr(plan, "workflow_mode", "STATUTORY_ACTION_AUTHORIZED"),
        company_id=str(plan.company_id),
        company_name=company.company_name if company else None,
        status=("ACTIVE" if getattr(plan, "is_active", True) else "CLOSED"),
        completion_percentage=plan.completion_percentage,
        total_steps=plan.total_steps,
        completed_steps=plan.completed_steps,
        estimated_fee_bdt=plan.quoted_fee_bdt,
        assigned_staff_id=str(plan.assigned_staff_id) if plan.assigned_staff_id else None,
        target_completion_date=str(plan.target_completion_date) if plan.target_completion_date else None,
        engagement_id=str(plan.engagement_id) if getattr(plan, "engagement_id", None) else None,
        source_rule_ids=list(getattr(plan, "source_rule_ids", None) or []),
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
    dependencies=[Depends(require_roles("ADMIN_STAFF", "SUPER_ADMIN", "LEGAL_STAFF")), Depends(require_entitlement("corporate_rescue"))],
    summary="Generate an authorized RJSC statutory-action workflow from eligible findings",
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

    # Verify company exists, assigned legal-staff scope and company-specific rescue entitlement.
    await _assert_rescue_entitlement(body.company_id, current_user, db)
    company = await company_svc.get_by_id_or_404(body.company_id)

    # Serialize the preflight check with every other rescue-plan creator.
    await db.execute(
        select(Company.id).where(Company.id == body.company_id).with_for_update()
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

    # Run the rule engine to generate rescue sequence
    from app.rule_engine import CompanyProfile
    from app.rule_engine.engine import NLCRuleEngine
    from app.services.compliance_service import (
        _catalogue_identity_conflicts,
        _catalogue_identity_query,
        _company_profile_kwargs,
        _reconcile_engine_output_identity_conflicts,
    )

    profile_data = await company_svc.build_company_profile(body.company_id, refresh=True)
    if not profile_data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company profile data not found")

    # Match the ordinary compliance-evaluation fact overlay exactly: latest
    # non-rejected version per key wins, and only fresh, independently
    # verified document-backed facts authorize rule-engine evidence gates.
    fact_result = await db.execute(
        select(CompanyFact)
        .where(CompanyFact.company_id == body.company_id)
        .order_by(
            CompanyFact.fact_key.asc(),
            CompanyFact.created_at.desc(),
            CompanyFact.id.desc(),
        )
    )
    latest_facts: dict[str, CompanyFact] = {}
    for fact in fact_result.scalars().all():
        latest_facts.setdefault(fact.fact_key, fact)
    current_facts = [
        fact for fact in latest_facts.values()
        if fact.verification_status not in {"REJECTED", "SUPERSEDED"}
    ]
    profile_field_names = {
        name for name in CompanyProfile.__dataclass_fields__
        if not is_internal_profile_fact_key(name)
    } - {"company_id", "company_name"}
    used_facts = []
    for fact in current_facts:
        if fact.fact_key in profile_field_names:
            profile_data[fact.fact_key] = coerce_company_profile_fact_value(
                fact.fact_key, fact.fact_value
            )
            used_facts.append(fact)

    profile = CompanyProfile(**_company_profile_kwargs(profile_data, CompanyProfile))
    profile.verified_fact_keys = verified_document_fact_keys(
        used_facts, as_of=business_date_today()
    )
    profile.verified_fact_context = {
        fact.fact_key: {
            "document_id": str(fact.document_id) if fact.document_id else None,
            "source_reference": fact.source_reference,
        }
        for fact in used_facts
        if fact.fact_key in profile.verified_fact_keys
    }

    # Rescue-plan evaluation must use the same complete catalogue binding as
    # ordinary compliance evaluation. Never run an unbound rescue profile.
    catalogue_rows = list((
        await db.execute(_catalogue_identity_query())
    ).all())
    catalogue_identity_conflicts = _catalogue_identity_conflicts(catalogue_rows)
    profile.catalogue_binding_required = True
    profile.catalogue_rule_versions = {
        row.rule_id: row.rule_version for row in catalogue_rows
    }
    profile.catalogue_rule_active = {
        row.rule_id: bool(row.is_active) for row in catalogue_rows
    }
    profile.catalogue_rule_bases = {
        row.rule_id: row.statutory_basis for row in catalogue_rows
    }
    profile.catalogue_identity_conflicts = catalogue_identity_conflicts

    engine = NLCRuleEngine()
    engine_output = engine.evaluate(profile)
    _reconcile_engine_output_identity_conflicts(
        engine_output, catalogue_identity_conflicts
    )
    from app.services.compliance_service import _score_blocking_catalogue_conflicts

    # Preserve canonical identity integrity even though workflow authorization
    # is independent of score publication.
    conflicted_rule_ids = sorted(
        _score_blocking_catalogue_conflicts(catalogue_identity_conflicts)
    )
    if conflicted_rule_ids:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": (
                    "Rescue generation is blocked by unresolved RJSC catalogue/evaluator "
                    "identity conflicts, including rules with no emitted finding."
                ),
                "conflicted_rule_ids": conflicted_rule_ids,
            },
        )

    if not engine_output.rescue_sequence:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "A rescue plan requires an active, applicable, evidence-supported finding "
                "and an eligible RJSC rescue sequence."
            ),
        )

    # A rescue candidate may be actionable independently of product-score
    # publication. Never copy the raw engine score into the plan unless this
    # exact evaluation has a publishable score.
    from app.rule_engine.engine import legal_score_is_released

    score_breakdown = getattr(engine_output, "score_breakdown", None)
    risk_band_value = getattr(score_breakdown, "risk_band", None)
    risk_band_name = getattr(risk_band_value, "value", risk_band_value)
    score_publishable = bool(
        legal_score_is_released()
        and score_breakdown is not None
        and getattr(score_breakdown, "final_score", None) is not None
        and risk_band_name != "NOT_EVALUATED"
    )

    try:
        plan = await rescue_svc.generate_rescue_plan(  # type: ignore
            company_id=body.company_id,
            engine_output=engine_output,
            score_withheld=not score_publishable,
            created_by=current_user.id,
            assigned_staff_id=body.assigned_staff_id,
            estimated_fee_bdt=body.estimated_fee_bdt,
            target_completion_date=date.fromisoformat(body.target_completion_date) if body.target_completion_date else None,
            engagement_id=None,  # RES-010: explicit linkage, populated by service
        )
    except ActiveRescuePlanExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Rescue generation rejected: the evaluation is not authorized for this tenant or released rule set.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Rescue generation rejected: {exc}",
        ) from exc

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
    dependencies=[Depends(require_roles("ADMIN_STAFF", "SUPER_ADMIN", "LEGAL_STAFF")), Depends(require_entitlement("corporate_rescue"))],
    summary="List rescue plans, optionally filtered by company_id",
)
async def list_rescue_plans(
    company_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    """Issue 5: support optional company_id filter.
    Without company_id, returns all plans (admin/portfolio view).
    With company_id, returns only that company's plans.
    """
    # Historical rescue plans remain readable while statutory score publication
    # is paused. Creation and mutation endpoints retain the release gate.
    from sqlalchemy.orm import selectinload

    from app.models.rescue import RescuePlan

    query = select(RescuePlan).options(selectinload(RescuePlan.steps))
    if company_id is not None:
        await _assert_rescue_entitlement(company_id, current_user, db)
        query = query.where(RescuePlan.company_id == company_id)
    elif current_user.role not in ("SUPER_ADMIN", "ADMIN_STAFF"):
        raise HTTPException(status_code=403, detail="Portfolio-wide rescue plan access is restricted to platform administrators.")
    query = query.order_by(RescuePlan.created_at.desc())

    result = await db.execute(query)
    plans = result.scalars().all()
    return [_plan_to_response(p) for p in plans]


# ---------------------------------------------------------------------------
# GET /rescue/plans/{company_id}/active — Active plan for a company
# ---------------------------------------------------------------------------

@router.get(
    "/plans/{company_id}/active",
    response_model=RescuePlanResponse,
    dependencies=[
        Depends(require_company_access("company_id")),
        Depends(require_entitlement("corporate_rescue")),
    ],
    summary="Get the active rescue plan for a company",
)
async def get_active_plan(
    company_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    if current_user.role == "LEGAL_STAFF":
        await ensure_staff_company_scope(company_id, current_user, db)
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
    dependencies=[Depends(require_roles("ADMIN_STAFF", "SUPER_ADMIN", "LEGAL_STAFF"))],
    summary="Get a rescue plan by ID with all steps",
)
async def get_rescue_plan(
    plan_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    # Read-only retrieval of historical plans is safe while score release is paused.
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
    await ensure_staff_company_scope(plan.company_id, current_user, db, additional_staff_id=plan.assigned_staff_id)
    await _assert_rescue_entitlement(plan.company_id, current_user, db)
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
        "Updating the final rescue step to COMPLETE automatically triggers compliance re-evaluation "
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
    # Score publication does not gate this explicitly authorized workflow.
    rescue_svc = RescueService(db)
    activity = ActivityService(db)

    from app.models.enums import RescueStepStatus

    valid_statuses = tuple(item.value for item in RescueStepStatus)
    if body.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{body.status}'. Must be one of: {valid_statuses}",
        )

    plan = await rescue_svc.get_by_id_or_404(plan_id)
    await ensure_staff_company_scope(plan.company_id, current_user, db, additional_staff_id=plan.assigned_staff_id)
    await _assert_rescue_entitlement(plan.company_id, current_user, db)
    step = next((st for st in plan.steps if st.step_number == step_number), None)
    if step is None:
        raise HTTPException(status_code=404, detail="Rescue plan or step not found.")
    updated = await rescue_svc.update_step(
        step.id,
        status=RescueStepStatus(body.status),
        completion_notes=body.completion_notes,
        updated_by=current_user.id,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Rescue plan or step not found.")
    await db.refresh(plan)

    await activity.log(
        action="RESCUE_STEP_UPDATED",
        resource_type="rescue_plan",
        resource_id=str(plan_id),
        description=f"Step {step_number} updated to {body.status}",
        ip_address=request.client.host if request.client else None,
        actor_user_id=current_user.id,
    )

    # Step 8 COMPLETED → trigger re-evaluation via Celery
    if plan.total_steps and plan.completed_steps >= plan.total_steps:
        try:
            from app.worker.tasks import trigger_rescue_reevaluation
            trigger_rescue_reevaluation.apply_async(
                kwargs={
                    "company_id": str(plan.company_id),
                    "rescue_plan_id": str(plan_id),
                    "completed_step_number": step_number,
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
    _require_commercial_engagement_release()
    rescue_svc = RescueService(db)
    activity = ActivityService(db)

    plan = await rescue_svc.get_by_id_or_404(plan_id)
    await _assert_rescue_entitlement(plan.company_id, current_user, db)
    engagement = await rescue_svc.create_engagement_from_rescue(
        rescue_plan=plan,
        confirmed_fee_bdt=body.confirmed_fee_bdt,
        payment_terms=body.payment_terms,
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
