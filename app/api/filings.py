"""
app/api/filings.py — Filings Router
NEUM LEX COUNSEL

Endpoints:
  AGM:
    POST   /filings/agm                    Create AGM record
    GET    /filings/agm/{company_id}        List AGMs for a company
    PATCH  /filings/agm/{agm_id}/held       Mark AGM as held with details
    PATCH  /filings/agm/{agm_id}/filed      Mark AGM as filed with RJSC

  AUDIT:
    POST   /filings/audit                   Create audit engagement record
    GET    /filings/audit/{company_id}      List audits for a company
    PATCH  /filings/audit/{audit_id}/complete  Mark audit as complete + signed

  ANNUAL RETURN:
    POST   /filings/annual-return           Create annual return record
    GET    /filings/annual-return/{company_id}   List annual returns
    PATCH  /filings/annual-return/{return_id}/filed   Mark as filed with RJSC

All filing endpoints auto-trigger compliance re-evaluation via Celery task
after update so the company score is always fresh.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Optional, List

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    get_db_for_user,
    get_current_user,
    require_roles,
    require_company_access,
)
from app.models.user import User
from app.services.filing_service import AGMService, AuditService, AnnualReturnService, StatutoryRegisterService
from app.services.notification_service import ActivityService

logger = structlog.get_logger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas — AGM
# ---------------------------------------------------------------------------

class AGMCreateRequest(BaseModel):
    company_id: uuid.UUID
    financial_year: int = Field(ge=2000, le=2100)
    agm_due_date: date
    scheduled_date: Optional[date] = None
    notice_sent_date: Optional[date] = None


class AGMMarkHeldRequest(BaseModel):
    held_date: date
    venue: Optional[str] = None
    members_present: int = Field(ge=0)
    quorum_met: bool
    auditor_reappointed: bool
    accounts_adopted: bool
    agm_held_without_audit: bool = False
    minutes_document_id: Optional[uuid.UUID] = None


class AGMMarkFiledRequest(BaseModel):
    filed_date: date
    rjsc_acknowledgment_number: Optional[str] = None


class AGMResponse(BaseModel):
    agm_id: str
    company_id: str
    financial_year: int
    agm_due_date: str
    held_date: Optional[str]
    filed_date: Optional[str]
    quorum_met: Optional[bool]
    auditor_reappointed: Optional[bool]
    accounts_adopted: Optional[bool]
    agm_held_without_audit: bool
    is_default: bool
    created_at: str


# ---------------------------------------------------------------------------
# Schemas — Audit
# ---------------------------------------------------------------------------

class AuditCreateRequest(BaseModel):
    company_id: uuid.UUID
    financial_year: int = Field(ge=2000, le=2100)
    auditor_firm: Optional[str] = None
    auditor_icab_number: Optional[str] = None


class AuditMarkCompleteRequest(BaseModel):
    signed_date: date
    auditor_firm: str
    auditor_icab_number: str
    audit_opinion: str = Field(default="UNQUALIFIED")
    report_document_id: Optional[uuid.UUID] = None


class AuditResponse(BaseModel):
    audit_id: str
    company_id: str
    financial_year: int
    is_complete: bool
    signed_date: Optional[str]
    auditor_firm: Optional[str]
    audit_opinion: Optional[str]
    created_at: str


# ---------------------------------------------------------------------------
# Schemas — Annual Return
# ---------------------------------------------------------------------------

class AnnualReturnCreateRequest(BaseModel):
    company_id: uuid.UUID
    financial_year: int = Field(ge=2000, le=2100)
    agm_date: Optional[date] = None


class AnnualReturnMarkFiledRequest(BaseModel):
    filed_date: date
    rjsc_acknowledgment_number: Optional[str] = None
    late_fee_paid: bool = False
    late_fee_amount: Optional[float] = None
    filing_document_id: Optional[uuid.UUID] = None


class AnnualReturnResponse(BaseModel):
    return_id: str
    company_id: str
    financial_year: int
    is_filed: bool
    filed_date: Optional[str]
    rjsc_acknowledgment_number: Optional[str]
    late_fee_paid: bool
    created_at: str


class StatutoryRegisterCreateRequest(BaseModel):
    company_id: uuid.UUID
    register_type: str
    is_maintained: bool = False
    last_updated_date: Optional[date] = None
    location: Optional[str] = None
    notes: Optional[str] = None


class StatutoryRegisterUpdateRequest(BaseModel):
    is_maintained: Optional[bool] = None
    last_updated_date: Optional[date] = None
    location: Optional[str] = None
    notes: Optional[str] = None


class StatutoryRegisterResponse(BaseModel):
    register_id: str
    company_id: str
    register_type: str
    is_maintained: bool
    last_updated_date: Optional[str]
    location: Optional[str]
    notes: Optional[str]
    updated_at: str


class MessageResponse(BaseModel):
    message: str
    success: bool = True


# ---------------------------------------------------------------------------
# Helper: trigger background re-evaluation
# ---------------------------------------------------------------------------

def _dispatch_reevaluation(company_id: uuid.UUID, trigger: str) -> None:
    """Fire Celery task to re-evaluate after a filing update. Non-blocking."""
    try:
        from app.worker.tasks import evaluate_company_compliance
        evaluate_company_compliance.apply_async(
            kwargs={"company_id": str(company_id), "trigger_source": trigger},
            countdown=5,  # small delay to let DB commit settle
        )
        logger.info("reevaluation_dispatched", company_id=str(company_id), trigger=trigger)
    except Exception as e:
        # Non-fatal — next nightly cron will catch it
        logger.warning("reevaluation_dispatch_failed", company_id=str(company_id), error=str(e))


# ===========================================================================
# AGM ENDPOINTS
# ===========================================================================

@router.post(
    "/agm",
    response_model=AGMResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles("ADMIN_STAFF", "SUPER_ADMIN", "LEGAL_STAFF"))],
    summary="Create an AGM record for a company",
)
async def create_agm(
    body: AGMCreateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = AGMService(db)
    activity = ActivityService(db)

    # Check for duplicate (same company + year)
    existing = await svc.get_by_company_and_year(body.company_id, body.financial_year)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"AGM record for financial year {body.financial_year} already exists.",
        )

    agm = await svc.create_agm(
        company_id=body.company_id,
        financial_year=body.financial_year,
        agm_due_date=body.agm_due_date,
        scheduled_date=body.scheduled_date,
        notice_sent_date=body.notice_sent_date,
    )

    await activity.log(
        action="AGM_CREATED",
        resource_type="agm",
        resource_id=str(agm.id),
        description=f"AGM record created for FY {body.financial_year}",
        ip_address=request.client.host if request.client else None,
        actor_user_id=current_user.id,
    )
    return _agm_to_response(agm)


@router.get(
    "/agm/{company_id}",
    response_model=List[AGMResponse],
    dependencies=[Depends(require_company_access("company_id"))],
    summary="List all AGM records for a company",
)
async def list_agms(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = AGMService(db)
    agms = await svc.get_for_company(company_id)
    return [_agm_to_response(a) for a in agms]


@router.patch(
    "/agm/{agm_id}/held",
    response_model=AGMResponse,
    dependencies=[Depends(require_roles("ADMIN_STAFF", "SUPER_ADMIN", "LEGAL_STAFF"))],
    summary="Mark an AGM as held with meeting details",
)
async def mark_agm_held(
    agm_id: uuid.UUID,
    body: AGMMarkHeldRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = AGMService(db)
    activity = ActivityService(db)

    agm = await svc.mark_held(
        agm_id=agm_id,
        held_date=body.held_date,
        venue=body.venue,
        members_present=body.members_present,
        quorum_met=body.quorum_met,
        auditor_reappointed=body.auditor_reappointed,
        accounts_adopted=body.accounts_adopted,
        agm_held_without_audit=body.agm_held_without_audit,
        minutes_document_id=body.minutes_document_id,
    )
    if not agm:
        raise HTTPException(status_code=404, detail="AGM record not found.")

    await activity.log(
        action="AGM_HELD",
        resource_type="agm",
        resource_id=str(agm_id),
        description=f"AGM marked as held on {body.held_date}",
        ip_address=request.client.host if request.client else None,
        actor_user_id=current_user.id,
    )
    _dispatch_reevaluation(agm.company_id, "AGM_HELD")
    return _agm_to_response(agm)


@router.patch(
    "/agm/{agm_id}/filed",
    response_model=AGMResponse,
    dependencies=[Depends(require_roles("ADMIN_STAFF", "SUPER_ADMIN", "LEGAL_STAFF"))],
    summary="Mark AGM filing as submitted to RJSC",
)
async def mark_agm_filed(
    agm_id: uuid.UUID,
    body: AGMMarkFiledRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = AGMService(db)
    agm = await svc.get_by_id_or_404(agm_id)

    update_data = {
        "filed_date": body.filed_date,
        "rjsc_acknowledgment_number": body.rjsc_acknowledgment_number,
        "is_filed": True,
    }
    updated = await svc.update_by_id(agm_id, update_data)
    _dispatch_reevaluation(updated.company_id, "AGM_FILED")
    return _agm_to_response(updated)


# ===========================================================================
# AUDIT ENDPOINTS
# ===========================================================================

@router.post(
    "/audit",
    response_model=AuditResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles("ADMIN_STAFF", "SUPER_ADMIN", "LEGAL_STAFF"))],
    summary="Create an audit engagement record",
)
async def create_audit(
    body: AuditCreateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = AuditService(db)
    audit = await svc.create_audit(
        company_id=body.company_id,
        financial_year=body.financial_year,
        auditor_firm=body.auditor_firm,
        auditor_icab_number=body.auditor_icab_number,
    )
    return _audit_to_response(audit)


@router.get(
    "/audit/{company_id}",
    response_model=List[AuditResponse],
    dependencies=[Depends(require_company_access("company_id"))],
    summary="List all audit records for a company",
)
async def list_audits(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = AuditService(db)
    audits = await svc.get_for_company(company_id)
    return [_audit_to_response(a) for a in audits]


@router.patch(
    "/audit/{audit_id}/complete",
    response_model=AuditResponse,
    dependencies=[Depends(require_roles("ADMIN_STAFF", "SUPER_ADMIN", "LEGAL_STAFF"))],
    summary="Mark an audit as complete with signed date",
)
async def mark_audit_complete(
    audit_id: uuid.UUID,
    body: AuditMarkCompleteRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = AuditService(db)
    activity = ActivityService(db)

    audit = await svc.mark_complete(
        audit_id=audit_id,
        signed_date=body.signed_date,
        auditor_firm=body.auditor_firm,
        auditor_icab_number=body.auditor_icab_number,
        audit_opinion=body.audit_opinion,
        report_document_id=body.report_document_id,
    )
    if not audit:
        raise HTTPException(status_code=404, detail="Audit record not found.")

    await activity.log(
        action="AUDIT_COMPLETE",
        resource_type="audit",
        resource_id=str(audit_id),
        description=f"Audit marked complete, signed {body.signed_date}",
        ip_address=request.client.host if request.client else None,
        actor_user_id=current_user.id,
    )
    _dispatch_reevaluation(audit.company_id, "AUDIT_COMPLETE")
    return _audit_to_response(audit)


# ===========================================================================
# ANNUAL RETURN ENDPOINTS
# ===========================================================================

@router.post(
    "/annual-return",
    response_model=AnnualReturnResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles("ADMIN_STAFF", "SUPER_ADMIN", "LEGAL_STAFF"))],
    summary="Create an annual return record",
)
async def create_annual_return(
    body: AnnualReturnCreateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = AnnualReturnService(db)
    annual_return = await svc.create_return(
        company_id=body.company_id,
        financial_year=body.financial_year,
        agm_date=body.agm_date,
    )
    return _return_to_response(annual_return)


@router.get(
    "/annual-return/{company_id}",
    response_model=List[AnnualReturnResponse],
    dependencies=[Depends(require_company_access("company_id"))],
    summary="List all annual return records for a company",
)
async def list_annual_returns(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = AnnualReturnService(db)
    returns = await svc.get_for_company(company_id)
    return [_return_to_response(r) for r in returns]


@router.patch(
    "/annual-return/{return_id}/filed",
    response_model=AnnualReturnResponse,
    dependencies=[Depends(require_roles("ADMIN_STAFF", "SUPER_ADMIN", "LEGAL_STAFF"))],
    summary="Mark an annual return as filed with RJSC",
)
async def mark_return_filed(
    return_id: uuid.UUID,
    body: AnnualReturnMarkFiledRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = AnnualReturnService(db)
    activity = ActivityService(db)

    annual_return = await svc.mark_filed(
        return_id=return_id,
        filed_date=body.filed_date,
        rjsc_acknowledgment_number=body.rjsc_acknowledgment_number,
        late_fee_paid=body.late_fee_paid,
        late_fee_amount=body.late_fee_amount,
        filing_document_id=body.filing_document_id,
    )
    if not annual_return:
        raise HTTPException(status_code=404, detail="Annual return record not found.")

    await activity.log(
        action="ANNUAL_RETURN_FILED",
        resource_type="annual_return",
        resource_id=str(return_id),
        description=f"Annual return filed on {body.filed_date}",
        ip_address=request.client.host if request.client else None,
        actor_user_id=current_user.id,
    )
    _dispatch_reevaluation(annual_return.company_id, "ANNUAL_RETURN_FILED")
    return _return_to_response(annual_return)


# ==========================================================================
# STATUTORY REGISTER ENDPOINTS
# ===========================================================================

@router.post(
    "/statutory-register",
    response_model=StatutoryRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles("ADMIN_STAFF", "SUPER_ADMIN", "LEGAL_STAFF"))],
    summary="Create a statutory register record",
)
async def create_statutory_register(
    body: StatutoryRegisterCreateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = StatutoryRegisterService(db)
    activity = ActivityService(db)

    entry = await svc.create_register_entry(
        company_id=body.company_id,
        register_type=body.register_type,
        is_maintained=body.is_maintained,
        last_updated_date=body.last_updated_date,
        location=body.location,
        notes=body.notes,
    )

    await activity.log(
        action="STATUTORY_REGISTER_CREATED",
        resource_type="statutory_register",
        resource_id=str(entry.id),
        description=f"Statutory register {body.register_type} created",
        ip_address=request.client.host if request.client else None,
        actor_user_id=current_user.id,
    )
    _dispatch_reevaluation(body.company_id, "STATUTORY_REGISTER_CREATED")
    return _statutory_register_to_response(entry)


@router.get(
    "/statutory-register/{company_id}",
    response_model=List[StatutoryRegisterResponse],
    dependencies=[Depends(require_company_access("company_id"))],
    summary="List statutory register entries for a company",
)
async def list_statutory_registers(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = StatutoryRegisterService(db)
    entries = await svc.get_for_company(company_id)
    return [_statutory_register_to_response(e) for e in entries]


@router.patch(
    "/statutory-register/{register_id}",
    response_model=StatutoryRegisterResponse,
    dependencies=[Depends(require_roles("ADMIN_STAFF", "SUPER_ADMIN", "LEGAL_STAFF"))],
    summary="Update a statutory register entry",
)
async def update_statutory_register(
    register_id: uuid.UUID,
    body: StatutoryRegisterUpdateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = StatutoryRegisterService(db)
    entry = await svc.update_register_entry(
        register_id=register_id,
        is_maintained=body.is_maintained,
        last_updated_date=body.last_updated_date,
        location=body.location,
        notes=body.notes,
    )
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Statutory register entry not found")

    await ActivityService(db).log(
        action="STATUTORY_REGISTER_UPDATED",
        resource_type="statutory_register",
        resource_id=str(register_id),
        description=f"Statutory register {entry.register_type} updated",
        ip_address=request.client.host if request.client else None,
        actor_user_id=current_user.id,
    )
    _dispatch_reevaluation(entry.company_id, "STATUTORY_REGISTER_UPDATED")
    return _statutory_register_to_response(entry)


# ---------------------------------------------------------------------------
# Serialisers
# ---------------------------------------------------------------------------

def _agm_to_response(agm) -> AGMResponse:
    return AGMResponse(
        agm_id=str(agm.id),
        company_id=str(agm.company_id),
        financial_year=agm.financial_year,
        agm_due_date=agm.agm_due_date.isoformat(),
        held_date=agm.held_date.isoformat() if agm.held_date else None,
        filed_date=agm.filed_date.isoformat() if agm.filed_date else None,
        quorum_met=agm.quorum_met,
        auditor_reappointed=agm.auditor_reappointed,
        accounts_adopted=agm.accounts_adopted,
        agm_held_without_audit=agm.agm_held_without_audit,
        is_default=agm.is_default,
        created_at=agm.created_at.isoformat(),
    )


def _audit_to_response(audit) -> AuditResponse:
    return AuditResponse(
        audit_id=str(audit.id),
        company_id=str(audit.company_id),
        financial_year=audit.financial_year,
        is_complete=audit.is_complete,
        signed_date=audit.signed_date.isoformat() if audit.signed_date else None,
        auditor_firm=audit.auditor_firm,
        audit_opinion=audit.audit_opinion,
        created_at=audit.created_at.isoformat(),
    )


def _return_to_response(r) -> AnnualReturnResponse:
    return AnnualReturnResponse(
        return_id=str(r.id),
        company_id=str(r.company_id),
        financial_year=r.financial_year,
        is_filed=r.is_filed,
        filed_date=r.filed_date.isoformat() if r.filed_date else None,
        rjsc_acknowledgment_number=r.rjsc_acknowledgment_number,
        late_fee_paid=r.late_fee_paid,
        created_at=r.created_at.isoformat(),
    )


def _statutory_register_to_response(r) -> StatutoryRegisterResponse:
    return StatutoryRegisterResponse(
        register_id=str(r.id),
        company_id=str(r.company_id),
        register_type=r.register_type,
        is_maintained=r.is_maintained,
        last_updated_date=r.last_updated_date.isoformat() if r.last_updated_date else None,
        location=r.location,
        notes=r.notes,
        updated_at=r.updated_at.isoformat(),
    )
