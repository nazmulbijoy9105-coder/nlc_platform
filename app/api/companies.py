"""
app/api/companies.py - Companies Router
NEUM LEX COUNSEL
"""

import uuid
from datetime import date

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    Pagination,
    get_current_user,
    get_db_for_user,
    require_company_access,
    require_roles,
)
from app.models.enums import CompanyStatus, CompanyType, RevenueTier, RiskBand
from app.models.user import User
from app.services.company_service import CompanyService
from app.services.compliance_service import ComplianceService
from app.services.notification_service import ActivityService

logger = structlog.get_logger(__name__)
router = APIRouter()


class CompanyCreateRequest(BaseModel):
    company_name: str = Field(min_length=2, max_length=255)
    registration_number: str = Field(min_length=3, max_length=50)
    incorporation_date: date
    registered_address: str = Field(min_length=5, max_length=500)
    company_type: CompanyType = Field(default=CompanyType.PRIVATE_LIMITED)
    financial_year_end: date | None = None
    revenue_tier: RevenueTier | None = None
    assigned_staff_id: uuid.UUID | None = None
    trade_license_obtained: bool = False
    trade_license_expiry: date | None = None
    tax_return_filed_for_current_fy: bool = False
    advance_tax_q1_paid: bool = False
    advance_tax_q2_paid: bool = False
    advance_tax_q3_paid: bool = False
    advance_tax_q4_paid: bool = False
    tds_deposited_up_to_date: bool = True
    last_tds_deposit_date: date | None = None
    last_vat_return_filed: date | None = None
    vat_annual_return_filed_for_fy: bool = False
    minimum_tax_paid: bool = True
    tax_clearance_obtained: bool = False
    tax_return_deadline_extended: bool = False
    any_director_disqualified: bool = False
    penalty_notices_received: int = 0
    penalty_notices_resolved: int = 0


class CompanyUpdateRequest(BaseModel):
    company_name: str | None = Field(None, min_length=2, max_length=255)
    registered_address: str | None = None
    financial_year_end: date | None = None
    revenue_tier: RevenueTier | None = None
    assigned_staff_id: uuid.UUID | None = None
    internal_notes: str | None = None
    trade_license_obtained: bool | None = None
    trade_license_expiry: date | None = None
    tax_return_filed_for_current_fy: bool | None = None
    last_tax_return_filed: date | None = None
    advance_tax_q1_paid: bool | None = None
    advance_tax_q2_paid: bool | None = None
    advance_tax_q3_paid: bool | None = None
    advance_tax_q4_paid: bool | None = None
    tds_deposited_up_to_date: bool | None = None
    last_tds_deposit_date: date | None = None
    last_vat_return_filed: date | None = None
    vat_annual_return_filed_for_fy: bool | None = None
    minimum_tax_paid: bool | None = None
    tax_clearance_obtained: bool | None = None
    tax_return_deadline_extended: bool | None = None
    any_director_disqualified: bool | None = None
    disqualification_details: list[str] | None = None
    penalty_notices_received: int | None = None
    penalty_notices_resolved: int | None = None


class FlagResolveRequest(BaseModel):
    resolution_note: str = Field(min_length=5, max_length=1000)
    resolution_document_id: uuid.UUID | None = None


class CompanyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    registration_number: str
    incorporation_date: str
    compliance_score: int | None
    band: str | None
    last_evaluated_at: str | None
    director_count: int = 0
    violation_count: int = 0
    company_type: str | None = None
    company_status: str | None = None
    financial_year_end: date | None = None
    registered_address: str | None = None
    revenue_tier: str | None = None
    is_fdi_registered: bool | None = None
    is_dormant: bool | None = None
    created_at: str | None = None
    active_flags: int = 0
    black_flags: int = 0
    red_flags: int = 0
    yellow_flags: int = 0
    trade_license_obtained: bool | None = None
    trade_license_expiry: str | None = None
    tax_return_filed_for_current_fy: bool | None = None
    advance_tax_q1_paid: bool | None = None
    advance_tax_q2_paid: bool | None = None
    advance_tax_q3_paid: bool | None = None
    advance_tax_q4_paid: bool | None = None
    any_director_disqualified: bool | None = None
    penalty_notices_received: int | None = None
    penalty_notices_resolved: int | None = None


class ComplianceSummaryResponse(BaseModel):
    company_id: str
    company_name: str
    current_score: int | None
    risk_band: str | None
    active_flags: int
    black_flags: int
    red_flags: int
    yellow_flags: int
    last_evaluated_at: str | None
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
    resolved_at: str | None
    resolution_note: str | None


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


def _company_to_response(company) -> CompanyResponse:
    director_count = 0
    if hasattr(company, "directors") and company.directors is not None:
        director_count = len(company.directors)
    violation_count = 0
    if hasattr(company, "compliance_flags") and company.compliance_flags is not None:
        violation_count = len([
            f for f in company.compliance_flags
            if hasattr(f, "status") and str(f.status) == "ACTIVE"
        ])

    def _s(val):
        if val is None:
            return None
        return str(val.value if hasattr(val, "value") else val)

    return CompanyResponse(
        id=str(company.id),
        name=company.company_name,
        registration_number=company.registration_number,
        incorporation_date=company.incorporation_date.isoformat() if company.incorporation_date else None,
        compliance_score=company.current_compliance_score,
        band=_s(company.current_risk_band),
        last_evaluated_at=company.last_evaluated_at.isoformat() if company.last_evaluated_at else None,
        director_count=director_count,
        violation_count=violation_count,
        active_flags=len([f for f in getattr(company, "compliance_flags", []) if str(getattr(f, "flag_status", "")) in ("ACTIVE", "FlagStatus.ACTIVE")]),
        black_flags=len([f for f in getattr(company, "compliance_flags", []) if str(getattr(f, "flag_status", "")) in ("ACTIVE", "FlagStatus.ACTIVE") and str(getattr(f, "severity", "")) in ("BLACK", "Severity.BLACK")]),
        red_flags=len([f for f in getattr(company, "compliance_flags", []) if str(getattr(f, "flag_status", "")) in ("ACTIVE", "FlagStatus.ACTIVE") and str(getattr(f, "severity", "")) in ("RED", "Severity.RED")]),
        yellow_flags=len([f for f in getattr(company, "compliance_flags", []) if str(getattr(f, "flag_status", "")) in ("ACTIVE", "FlagStatus.ACTIVE") and str(getattr(f, "severity", "")) in ("YELLOW", "Severity.YELLOW")]),
    )


@router.post("", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_roles("ADMIN_STAFF", "SUPER_ADMIN"))], summary="Create a new company")
async def create_company(body: CompanyCreateRequest, request: Request, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db_for_user)):
    svc = CompanyService(db)
    activity = ActivityService(db)
    existing = await svc.get_by_registration_number(body.registration_number)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Company with registration number already exists.")
    company = await svc.create_company(
        company_name=body.company_name, registration_number=body.registration_number,
        incorporation_date=body.incorporation_date, registered_address=body.registered_address,
        company_type=body.company_type, financial_year_end=body.financial_year_end,
        assigned_staff_id=body.assigned_staff_id, created_by=current_user.id,
    )
    _tax_fields = ["trade_license_obtained", "trade_license_expiry", "tax_return_filed_for_current_fy", "advance_tax_q1_paid", "advance_tax_q2_paid", "advance_tax_q3_paid", "advance_tax_q4_paid", "tds_deposited_up_to_date", "last_tds_deposit_date", "last_vat_return_filed", "vat_annual_return_filed_for_fy", "minimum_tax_paid", "tax_clearance_obtained", "tax_return_deadline_extended", "any_director_disqualified", "penalty_notices_received", "penalty_notices_resolved"]
    _tax_update = {k: getattr(body, k) for k in _tax_fields if getattr(body, k, None) is not None}
    if _tax_update:
        await svc.update_by_id(company.id, **_tax_update)
        await db.refresh(company)
    await activity.log(action="COMPANY_CREATED", resource_type="company", resource_id=str(company.id), description=f"Company created: {company.company_name}", ip_address=request.client.host if request.client else None, actor_user_id=None if current_user.role == "SUPER_ADMIN" else current_user.id)
    logger.info("company_created", company_id=str(company.id), name=company.company_name)
    return _company_to_response(company)


@router.get("", response_model=list[CompanyResponse], summary="List companies")
async def list_companies(search: str | None = Query(None), risk_band: RiskBand | None = Query(None), company_status: CompanyStatus | None = Query(None), revenue_tier: RevenueTier | None = Query(None), is_dormant: bool | None = Query(None), pagination: Pagination = Depends(), current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db_for_user)):
    svc = CompanyService(db)
    companies, _total = await svc.list_companies(search=search, risk_band=risk_band, company_status=company_status, revenue_tier=revenue_tier, is_dormant=is_dormant, offset=pagination.offset, limit=pagination.page_size,     user_id=None if current_user.role == "SUPER_ADMIN" else current_user.id)
    return [_company_to_response(c) for c in companies]


@router.get("/{company_id}", response_model=CompanyResponse, dependencies=[Depends(require_company_access("company_id"))], summary="Get company")
async def get_company(company_id: uuid.UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db_for_user)):
    svc = CompanyService(db)
    company = await svc.get_with_relations(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found.")
    return _company_to_response(company)


@router.patch("/{company_id}", response_model=CompanyResponse, dependencies=[Depends(require_roles("ADMIN_STAFF", "SUPER_ADMIN")), Depends(require_company_access("company_id"))], summary="Update company")
async def update_company(company_id: uuid.UUID, body: CompanyUpdateRequest, request: Request, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db_for_user)):
    svc = CompanyService(db)
    activity = ActivityService(db)
    update_data = body.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided for update.")
    _field_map = {"assigned_officer_id": "assigned_staff_id", "notes": "internal_notes"}
    mapped_data = {}
    for k, v in update_data.items():
        mapped_data[_field_map.get(k, k)] = v
    for _non_model in ("is_fdi_registered", "is_dormant"):
        mapped_data.pop(_non_model, None)
    company = await svc.update_by_id(company_id, **mapped_data)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found.")
    await activity.log(action="COMPANY_UPDATED", resource_type="company", resource_id=str(company_id), description=f"Updated fields: {list(update_data.keys())}", ip_address=request.client.host if request.client else None, actor_user_id=None if current_user.role == "SUPER_ADMIN" else current_user.id)
    return _company_to_response(company)


@router.delete("/{company_id}", response_model=MessageResponse, dependencies=[Depends(require_roles("SUPER_ADMIN"))], summary="Soft-delete company")
async def delete_company(company_id: uuid.UUID, request: Request, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db_for_user)):
    svc = CompanyService(db)
    activity = ActivityService(db)
    company = await svc.get_by_id_or_404(company_id)
    await svc.soft_delete(company_id)
    await activity.log(action="COMPANY_DELETED", resource_type="company", resource_id=str(company_id), description=f"Company soft-deleted: {company.company_name}", ip_address=request.client.host if request.client else None, actor_user_id=None if current_user.role == "SUPER_ADMIN" else current_user.id)
    return MessageResponse(message=f"Company deactivated.")


@router.post("/{company_id}/evaluate", response_model=ComplianceSummaryResponse, dependencies=[Depends(require_roles("ADMIN_STAFF", "SUPER_ADMIN", "LEGAL_STAFF")), Depends(require_company_access("company_id"))], summary="Trigger compliance evaluation")
async def evaluate_company(company_id: uuid.UUID, request: Request, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db_for_user)):
    company_svc = CompanyService(db)
    compliance_svc = ComplianceService(db)
    activity = ActivityService(db)
    company = await company_svc.get_by_id_or_404(company_id)
    result = await compliance_svc.evaluate_company(company_id=company_id, trigger_source="API_MANUAL")
    await activity.log(action="COMPLIANCE_EVALUATED", resource_type="company", resource_id=str(company_id), description=f"Evaluation: Score={result['score']}, Band={result['risk_band']}", ip_address=request.client.host if request.client else None, actor_user_id=None if current_user.role == "SUPER_ADMIN" else current_user.id)
    flag_summary = await compliance_svc.get_flag_summary(company_id)
    return ComplianceSummaryResponse(company_id=str(company_id), company_name=company.company_name, current_score=result["score"], risk_band=result["risk_band"], active_flags=flag_summary.get("total_active", 0), black_flags=flag_summary.get("black", 0), red_flags=flag_summary.get("red", 0), yellow_flags=flag_summary.get("yellow", 0), last_evaluated_at=None, evaluation_triggered=True)


@router.get("/{company_id}/compliance", response_model=ComplianceSummaryResponse, dependencies=[Depends(require_company_access("company_id"))], summary="Get compliance state")
async def get_compliance(company_id: uuid.UUID, db: AsyncSession = Depends(get_db_for_user)):
    company_svc = CompanyService(db)
    compliance_svc = ComplianceService(db)
    company = await company_svc.get_by_id_or_404(company_id)
    flag_summary = await compliance_svc.get_flag_summary(company_id)
    return ComplianceSummaryResponse(company_id=str(company_id), company_name=company.company_name, current_score=company.current_compliance_score, risk_band=company.current_risk_band, active_flags=flag_summary.get("total_active", 0), black_flags=flag_summary.get("black", 0), red_flags=flag_summary.get("red", 0), yellow_flags=flag_summary.get("yellow", 0), last_evaluated_at=company.last_evaluated_at.isoformat() if company.last_evaluated_at else None)


@router.get("/{company_id}/flags", response_model=list[FlagResponse], dependencies=[Depends(require_company_access("company_id"))], summary="Get active flags")
async def get_flags(company_id: uuid.UUID, db: AsyncSession = Depends(get_db_for_user)):
    svc = ComplianceService(db)
    flags = await svc.get_active_flags(company_id)
    return [FlagResponse(flag_id=str(f.id), rule_id=f.rule_id, rule_name=getattr(f, "description", f.flag_code) or f.flag_code, severity=f.severity.value if hasattr(f.severity, "value") else str(f.severity), score_impact=f.score_impact, status=f.flag_status.value if hasattr(f.flag_status, "value") else str(f.flag_status), is_black_override=getattr(f, "is_black_override", False), triggered_at=f.triggered_date.isoformat() if f.triggered_date else "", resolved_at=f.resolved_date.isoformat() if getattr(f, "resolved_date", None) else None, resolution_note=getattr(f, "resolution_notes", None)) for f in flags]


@router.post("/{company_id}/flags/{flag_id}/resolve", response_model=MessageResponse, dependencies=[Depends(require_roles("ADMIN_STAFF", "SUPER_ADMIN", "LEGAL_STAFF")), Depends(require_company_access("company_id"))], summary="Resolve flag")
async def resolve_flag(company_id: uuid.UUID, flag_id: uuid.UUID, body: FlagResolveRequest, request: Request, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db_for_user)):
    svc = ComplianceService(db)
    activity = ActivityService(db)
    flag = await svc.resolve_flag(flag_id=flag_id, resolved_by=current_user.id, resolution_notes=body.resolution_note)
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found.")
    await activity.log(action="FLAG_RESOLVED", resource_type="compliance_flag", resource_id=str(flag_id), description=f"Flag {flag.rule_id} resolved", ip_address=request.client.host if request.client else None, actor_user_id=None if current_user.role == "SUPER_ADMIN" else current_user.id)
    return MessageResponse(message=f"Flag resolved.")


@router.post("/{company_id}/flags/{flag_id}/acknowledge", response_model=MessageResponse, dependencies=[Depends(require_company_access("company_id"))], summary="Acknowledge flag")
async def acknowledge_flag(company_id: uuid.UUID, flag_id: uuid.UUID, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db_for_user)):
    svc = ComplianceService(db)
    flag = await svc.acknowledge_flag(flag_id=flag_id, acknowledged_by=current_user.id)
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found.")
    return MessageResponse(message=f"Flag acknowledged.")


@router.get("/{company_id}/score-history", response_model=list[ScoreHistoryEntry], dependencies=[Depends(require_company_access("company_id"))], summary="Score history")
async def get_score_history(company_id: uuid.UUID, months: int = Query(default=12, ge=1, le=60), db: AsyncSession = Depends(get_db_for_user)):
    svc = ComplianceService(db)
    history = await svc.get_score_history(company_id=company_id, months=months)
    return [ScoreHistoryEntry(snapshot_month=h["month"], score=h["score"], risk_band=h["risk_band"], active_flags=h["active_flags"], black_flags=h["black_flags"], red_flags=0, yellow_flags=0, snapshot_date=h["calculated_at"]) for h in history]


@router.get("/dashboard/kpis", dependencies=[Depends(require_roles("ADMIN_STAFF", "SUPER_ADMIN", "LEGAL_STAFF"))], summary="Portfolio KPIs")
async def get_dashboard_kpis(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db_for_user)):
    svc = ComplianceService(db)
    return await svc.get_dashboard_kpis(user_id=None if current_user.role == "SUPER_ADMIN" else current_user.id)


@router.get("/dashboard/deadlines", dependencies=[Depends(require_roles("ADMIN_STAFF", "SUPER_ADMIN", "LEGAL_STAFF"))], summary="Upcoming deadlines")
async def get_upcoming_deadlines(days_ahead: int = Query(default=30, ge=7, le=90), current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db_for_user)):
    svc = CompanyService(db)
    return await svc.get_upcoming_deadlines(days_ahead=days_ahead, user_id=None if current_user.role == "SUPER_ADMIN" else current_user.id)


@router.get("/dashboard/risk", dependencies=[Depends(require_roles("ADMIN_STAFF", "SUPER_ADMIN", "LEGAL_STAFF"))], summary="Risk distribution")
async def get_risk_distribution(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db_for_user)):
    svc = CompanyService(db)
    return await svc.get_risk_distribution(user_id=None if current_user.role == "SUPER_ADMIN" else current_user.id)
