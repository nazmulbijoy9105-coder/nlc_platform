"""
app/api/companies.py — Companies Router
NEUM LEX COUNSEL

Endpoints:
  POST   /companies                     Create company (ADMIN_STAFF+)
  GET    /companies                     List companies with filters/pagination
  GET    /companies/{id}                Get company with full relations
  PATCH  /companies/{id}                Update company metadata
  DELETE /companies/{id}                Soft delete (SUPER_ADMIN only)

  POST   /companies/{id}/evaluate       Trigger compliance evaluation
  GET    /companies/{id}/compliance     Latest compliance state + flags
  GET    /companies/{id}/flags          Active compliance flags
  POST   /companies/{id}/flags/{flag_id}/resolve    Resolve a flag
  POST   /companies/{id}/flags/{flag_id}/acknowledge Acknowledge a flag
  GET    /companies/{id}/score-history  Score snapshots over time

  GET    /companies/dashboard/kpis      Portfolio-level KPIs (ADMIN_STAFF+)
  GET    /companies/dashboard/deadlines Upcoming deadlines across portfolio
  GET    /companies/dashboard/risk      Risk band distribution
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Optional, List

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    get_db,
    get_db_for_user,
    get_current_user,
    require_roles,
    require_company_access,
    Pagination,
    get_rule_engine,
)
from app.models.user import User
from app.models.enums import RiskBand, CompanyStatus, RevenueTier
from app.services.company_service import CompanyService
from app.services.compliance_service import ComplianceService
from app.services.notification_service import ActivityService

logger = structlog.get_logger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class CompanyCreateRequest(BaseModel):
    company_name: str = Field(min_length=2, max_length=255)
    registration_number: str = Field(min_length=3, max_length=50)
    incorporation_date: date
    registered_address: str = Field(min_length=5, max_length=500)
    company_type: str = Field(default="PRIVATE_LIMITED")
    financial_year_end: str = Field(
        default="12-31",
        description="Financial year end as MM-DD, e.g. '12-31'"
    )
    # Admin-only fields
    revenue_tier: Optional[RevenueTier] = None
    is_fdi_registered: bool = False
    assigned_officer_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None


class CompanyUpdateRequest(BaseModel):
    company_name: Optional[str] = Field(None, min_length=2, max_length=255)
    registered_address: Optional[str] = None
    financial_year_end: Optional[str] = None
    revenue_tier: Optional[RevenueTier] = None
    is_fdi_registered: Optional[bool] = None
    is_dormant: Optional[bool] = None
    assigned_officer_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None


class FlagResolveRequest(BaseModel):
    resolution_note: str = Field(min_length=5, max_length=1000)
    resolution_document_id: Optional[uuid.UUID] = None


class CompanyResponse(BaseModel):
    company_id: str
    company_name: str
    registration_number: str
    incorporation_date: date
    registered_address: str
    company_type: str
    financial_year_end: str
    current_compliance_score: Optional[int]
    current_risk_band: Optional[str]
    company_status: str
    revenue_tier: Optional[str]
    is_fdi_registered: bool
    is_dormant: bool
    last_evaluated_at: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


class ComplianceSummaryResponse(BaseModel):
    company_id: str
    company_name: str
    current_score: Optional[int]
    risk_band: Optional[str]
    active_flags: int
    black_flags: int
    red_flags: int
    yellow_flags: int
    last_evaluated_at: Optional[str]
    evaluation_triggered: bool = False


class FlagResponse(BaseModel):
    flag_id: str
    rule_id: str
    rule_name: str
    severity: str
    score_impact: int
    status: str
    is_black_override: bool
    triggered_at: str
    resolved_at: Optional[str]
    resolution_note: Optional[str]


class ScoreHistoryEntry(BaseModel):
    snapshot_month: str
    score: int
    risk_band: str
    active_flags: int
    black_flags: int
    red_flags: int
    yellow_flags: int
    snapshot_date: str


class MessageResponse(BaseModel):
    message: str
    success: bool = True


# ---------------------------------------------------------------------------
# Helper: serialise company ORM object
# ---------------------------------------------------------------------------

def _company_to_response(company) -> CompanyResponse:
    return CompanyResponse(
        company_id=str(company.id),
        company_name=company.company_name,
        registration_number=company.registration_number,
        incorporation_date=company.incorporation_date,
        registered_address=company.registered_address,
        company_type=company.company_type,
        financial_year_end=company.financial_year_end,
        current_compliance_score=company.current_compliance_score,
        current_risk_band=company.current_risk_band,
        company_status=company.company_status,
        revenue_tier=company.revenue_tier,
        is_fdi_registered=company.is_fdi_registered,
        is_dormant=company.is_dormant,
        last_evaluated_at=company.last_evaluated_at.isoformat() if company.last_evaluated_at else None,
        created_at=company.created_at.isoformat(),
    )


# ---------------------------------------------------------------------------
# POST /companies — Create
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=CompanyResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles("ADMIN_STAFF", "SUPER_ADMIN"))],
    summary="Create a new company",
)
async def create_company(
    body: CompanyCreateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = CompanyService(db)
    activity = ActivityService(db)

    # Check registration number uniqueness
    existing = await svc.get_by_registration_number(body.registration_number)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Company with registration number '{body.registration_number}' already exists.",
        )

    company = await svc.create_company(
        company_name=body.company_name,
        registration_number=body.registration_number,
        incorporation_date=body.incorporation_date,
        registered_address=body.registered_address,
        company_type=body.company_type,
        financial_year_end=body.financial_year_end,
        revenue_tier=body.revenue_tier,
        is_fdi_registered=body.is_fdi_registered,
        assigned_officer_id=body.assigned_officer_id,
        notes=body.notes,
        created_by=current_user.id,
    )

    await activity.log(
        action="COMPANY_CREATED",
        resource_type="company",
        resource_id=str(company.id),
        description=f"Company '{company.company_name}' created (reg: {company.registration_number})",
        ip_address=request.client.host if request.client else None,
        actor_user_id=current_user.id,
    )

    logger.info("company_created", company_id=str(company.id), name=company.company_name)
    return _company_to_response(company)


# ---------------------------------------------------------------------------
# GET /companies — List with filters
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=List[CompanyResponse],
    summary="List companies (filtered/paginated)",
)
async def list_companies(
    search: Optional[str] = Query(None, description="Full-text search on name or registration number"),
    risk_band: Optional[RiskBand] = Query(None),
    company_status: Optional[CompanyStatus] = Query(None),
    revenue_tier: Optional[RevenueTier] = Query(None),
    is_dormant: Optional[bool] = Query(None),
    pagination: Pagination = Depends(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = CompanyService(db)
    companies, total = await svc.list_companies(
        search=search,
        risk_band=risk_band,
        company_status=company_status,
        revenue_tier=revenue_tier,
        is_dormant=is_dormant,
        offset=pagination.offset,
        limit=pagination.page_size,
        user_id=current_user.id if current_user.role not in ("SUPER_ADMIN", "ADMIN_STAFF", "LEGAL_STAFF") else None,
    )
    return [_company_to_response(c) for c in companies]


# ---------------------------------------------------------------------------
# GET /companies/{company_id} — Get with full relations
# ---------------------------------------------------------------------------

@router.get(
    "/{company_id}",
    response_model=CompanyResponse,
    dependencies=[Depends(require_company_access("company_id"))],
    summary="Get a company with full relations",
)
async def get_company(
    company_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = CompanyService(db)
    company = await svc.get_with_relations(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found.")
    return _company_to_response(company)


# ---------------------------------------------------------------------------
# PATCH /companies/{company_id} — Update
# ---------------------------------------------------------------------------

@router.patch(
    "/{company_id}",
    response_model=CompanyResponse,
    dependencies=[
        Depends(require_roles("ADMIN_STAFF", "SUPER_ADMIN")),
        Depends(require_company_access("company_id")),
    ],
    summary="Update company metadata",
)
async def update_company(
    company_id: uuid.UUID,
    body: CompanyUpdateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = CompanyService(db)
    activity = ActivityService(db)

    update_data = body.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided for update.")

    company = await svc.update_by_id(company_id, update_data)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found.")

    await activity.log(
        action="COMPANY_UPDATED",
        resource_type="company",
        resource_id=str(company_id),
        description=f"Updated fields: {list(update_data.keys())}",
        ip_address=request.client.host if request.client else None,
        actor_user_id=current_user.id,
    )
    return _company_to_response(company)


# ---------------------------------------------------------------------------
# DELETE /companies/{company_id} — Soft delete
# ---------------------------------------------------------------------------

@router.delete(
    "/{company_id}",
    response_model=MessageResponse,
    dependencies=[Depends(require_roles("SUPER_ADMIN"))],
    summary="Soft-delete a company (Super Admin only)",
)
async def delete_company(
    company_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = CompanyService(db)
    activity = ActivityService(db)

    company = await svc.get_by_id_or_404(company_id)
    await svc.soft_delete(company_id)

    await activity.log(
        action="COMPANY_DELETED",
        resource_type="company",
        resource_id=str(company_id),
        description=f"Company '{company.company_name}' soft-deleted",
        ip_address=request.client.host if request.client else None,
        actor_user_id=current_user.id,
    )
    return MessageResponse(message=f"Company '{company.company_name}' has been deactivated.")


# ---------------------------------------------------------------------------
# POST /companies/{company_id}/evaluate — Trigger compliance evaluation
# ---------------------------------------------------------------------------

@router.post(
    "/{company_id}/evaluate",
    response_model=ComplianceSummaryResponse,
    dependencies=[
        Depends(require_roles("ADMIN_STAFF", "SUPER_ADMIN", "LEGAL_STAFF")),
        Depends(require_company_access("company_id")),
    ],
    summary="Trigger a full compliance evaluation for a company",
)
async def evaluate_company(
    company_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
    rule_engine=Depends(get_rule_engine),
):
    company_svc = CompanyService(db)
    compliance_svc = ComplianceService(db)
    activity = ActivityService(db)

    company = await company_svc.get_by_id_or_404(company_id)

    # Run evaluation pipeline
    result = await compliance_svc.evaluate_company(
        company_id=company_id,
        rule_engine=rule_engine,
        trigger_source="API_MANUAL",
        triggered_by=current_user.id,
    )

    await activity.log(
        action="COMPLIANCE_EVALUATED",
        resource_type="company",
        resource_id=str(company_id),
        description=f"Manual evaluation triggered. Score: {result.score}, Band: {result.risk_band}",
        ip_address=request.client.host if request.client else None,
        actor_user_id=current_user.id,
    )

    flag_summary = await compliance_svc.get_flag_summary(company_id)
    return ComplianceSummaryResponse(
        company_id=str(company_id),
        company_name=company.company_name,
        current_score=result.score,
        risk_band=result.risk_band,
        active_flags=flag_summary.get("total_active", 0),
        black_flags=flag_summary.get("black", 0),
        red_flags=flag_summary.get("red", 0),
        yellow_flags=flag_summary.get("yellow", 0),
        last_evaluated_at=result.evaluated_at.isoformat() if hasattr(result, "evaluated_at") else None,
        evaluation_triggered=True,
    )


# ---------------------------------------------------------------------------
# GET /companies/{company_id}/compliance — Latest compliance state
# ---------------------------------------------------------------------------

@router.get(
    "/{company_id}/compliance",
    response_model=ComplianceSummaryResponse,
    dependencies=[Depends(require_company_access("company_id"))],
    summary="Get the latest compliance state for a company",
)
async def get_compliance(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_for_user),
):
    company_svc = CompanyService(db)
    compliance_svc = ComplianceService(db)

    company = await company_svc.get_by_id_or_404(company_id)
    flag_summary = await compliance_svc.get_flag_summary(company_id)

    return ComplianceSummaryResponse(
        company_id=str(company_id),
        company_name=company.company_name,
        current_score=company.current_compliance_score,
        risk_band=company.current_risk_band,
        active_flags=flag_summary.get("total_active", 0),
        black_flags=flag_summary.get("black", 0),
        red_flags=flag_summary.get("red", 0),
        yellow_flags=flag_summary.get("yellow", 0),
        last_evaluated_at=company.last_evaluated_at.isoformat() if company.last_evaluated_at else None,
    )


# ---------------------------------------------------------------------------
# GET /companies/{company_id}/flags — Active flags
# ---------------------------------------------------------------------------

@router.get(
    "/{company_id}/flags",
    response_model=List[FlagResponse],
    dependencies=[Depends(require_company_access("company_id"))],
    summary="Get active compliance flags for a company",
)
async def get_flags(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = ComplianceService(db)
    flags = await svc.get_active_flags(company_id)
    return [
        FlagResponse(
            flag_id=str(f.id),
            rule_id=f.rule_id,
            rule_name=f.rule_name,
            severity=f.severity,
            score_impact=f.score_impact,
            status=f.status,
            is_black_override=f.is_black_override,
            triggered_at=f.triggered_at.isoformat(),
            resolved_at=f.resolved_at.isoformat() if f.resolved_at else None,
            resolution_note=f.resolution_note,
        )
        for f in flags
    ]


# ---------------------------------------------------------------------------
# POST /companies/{company_id}/flags/{flag_id}/resolve
# ---------------------------------------------------------------------------

@router.post(
    "/{company_id}/flags/{flag_id}/resolve",
    response_model=MessageResponse,
    dependencies=[
        Depends(require_roles("ADMIN_STAFF", "SUPER_ADMIN", "LEGAL_STAFF")),
        Depends(require_company_access("company_id")),
    ],
    summary="Resolve a compliance flag with a note",
)
async def resolve_flag(
    company_id: uuid.UUID,
    flag_id: uuid.UUID,
    body: FlagResolveRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = ComplianceService(db)
    activity = ActivityService(db)

    flag = await svc.resolve_flag(
        flag_id=flag_id,
        resolved_by=current_user.id,
        resolution_note=body.resolution_note,
        resolution_document_id=body.resolution_document_id,
    )
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found.")

    await activity.log(
        action="FLAG_RESOLVED",
        resource_type="compliance_flag",
        resource_id=str(flag_id),
        description=f"Flag {flag.rule_id} resolved: {body.resolution_note[:100]}",
        ip_address=request.client.host if request.client else None,
        actor_user_id=current_user.id,
    )
    return MessageResponse(message=f"Flag '{flag.rule_id}' has been resolved.")


# ---------------------------------------------------------------------------
# POST /companies/{company_id}/flags/{flag_id}/acknowledge
# ---------------------------------------------------------------------------

@router.post(
    "/{company_id}/flags/{flag_id}/acknowledge",
    response_model=MessageResponse,
    dependencies=[Depends(require_company_access("company_id"))],
    summary="Acknowledge a compliance flag",
)
async def acknowledge_flag(
    company_id: uuid.UUID,
    flag_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = ComplianceService(db)
    flag = await svc.acknowledge_flag(flag_id=flag_id, acknowledged_by=current_user.id)
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found.")
    return MessageResponse(message=f"Flag '{flag.rule_id}' acknowledged.")


# ---------------------------------------------------------------------------
# GET /companies/{company_id}/score-history
# ---------------------------------------------------------------------------

@router.get(
    "/{company_id}/score-history",
    response_model=List[ScoreHistoryEntry],
    dependencies=[Depends(require_company_access("company_id"))],
    summary="Get compliance score history (monthly snapshots)",
)
async def get_score_history(
    company_id: uuid.UUID,
    months: int = Query(default=12, ge=1, le=60, description="Number of months to retrieve"),
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = ComplianceService(db)
    history = await svc.get_score_history(company_id=company_id, months=months)
    return [
        ScoreHistoryEntry(
            snapshot_month=h.snapshot_month,
            score=h.score,
            risk_band=h.risk_band,
            active_flags=h.active_flags,
            black_flags=h.black_flags,
            red_flags=h.red_flags,
            yellow_flags=h.yellow_flags,
            snapshot_date=h.created_at.isoformat(),
        )
        for h in history
    ]


# ---------------------------------------------------------------------------
# GET /companies/dashboard/kpis — Portfolio KPIs
# ---------------------------------------------------------------------------

@router.get(
    "/dashboard/kpis",
    dependencies=[Depends(require_roles("ADMIN_STAFF", "SUPER_ADMIN", "LEGAL_STAFF"))],
    summary="Portfolio-level KPIs for the admin dashboard",
)
async def get_dashboard_kpis(
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = ComplianceService(db)
    return await svc.get_dashboard_kpis()


# ---------------------------------------------------------------------------
# GET /companies/dashboard/deadlines — Upcoming deadlines
# ---------------------------------------------------------------------------

@router.get(
    "/dashboard/deadlines",
    dependencies=[Depends(require_roles("ADMIN_STAFF", "SUPER_ADMIN", "LEGAL_STAFF"))],
    summary="Upcoming statutory deadlines across the portfolio",
)
async def get_upcoming_deadlines(
    days_ahead: int = Query(default=30, ge=7, le=90),
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = CompanyService(db)
    return await svc.get_upcoming_deadlines(days_ahead=days_ahead)


# ---------------------------------------------------------------------------
# GET /companies/dashboard/risk — Risk distribution
# ---------------------------------------------------------------------------

@router.get(
    "/dashboard/risk",
    dependencies=[Depends(require_roles("ADMIN_STAFF", "SUPER_ADMIN", "LEGAL_STAFF"))],
    summary="Risk band distribution across the portfolio",
)
async def get_risk_distribution(
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = CompanyService(db)
    return await svc.get_risk_distribution()
