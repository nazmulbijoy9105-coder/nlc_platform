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


import uuid
from datetime import UTC, date, datetime
from typing import Literal

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    get_current_user,
    get_db_for_user,
    require_company_access,
    require_roles,
)
from app.core.entitlement import require_entitlement
from app.models.user import User
from app.models.people import ShareComplianceEvent, Shareholder, ShareTransfer
from app.services.filing_service import (
    AGMService,
    AnnualReturnService,
    AuditService,
    StatutoryRegisterService,
)
from app.services.notification_service import ActivityService
from app.rule_engine.engine import LEGAL_SCORE_RELEASED
from app.services.compliance_calendar import LEGAL_CALENDAR_RELEASED

logger = structlog.get_logger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas — AGM
# ---------------------------------------------------------------------------

class AGMCreateRequest(BaseModel):
    company_id: uuid.UUID
    financial_year: int = Field(ge=2000, le=2100)
    agm_due_date: date
    scheduled_date: date | None = None
    notice_sent_date: date | None = None


class AGMMarkHeldRequest(BaseModel):
    held_date: date
    venue: str | None = None
    members_present: int | None = Field(default=None, ge=0)
    # Client-supplied quorum conclusions are intentionally not accepted.
    auditor_reappointed: bool | None = None
    minutes_prepared: bool | None = None
    accounts_adopted: bool | None = None
    agm_held_without_audit: bool | None = None
    minutes_document_id: uuid.UUID | None = None


class AGMMarkFiledRequest(BaseModel):
    filed_date: date
    rjsc_acknowledgment_number: str | None = None


class AGMResponse(BaseModel):
    agm_id: str
    company_id: str
    financial_year: int
    agm_due_date: str | None
    held_date: str | None
    filed_date: str | None
    quorum_met: bool | None
    quorum_required: int | None = None
    quorum_basis: str | None = None
    venue: str | None = None
    members_present: int | None = None
    auditor_reappointed: bool | None
    accounts_adopted: bool | None
    agm_held_without_audit: bool | None
    minutes_prepared: bool | None
    is_default: bool | None
    created_at: str



class ShareEventCreateRequest(BaseModel):
    event_type: Literal["ALLOTMENT", "CAPITAL_INCREASE_RESOLUTION", "TRANSFER_REGISTERED"]
    event_reference: str = Field(min_length=2, max_length=160)
    event_date: date
    event_evidence_ref: str = Field(min_length=4, max_length=2000)
    share_transfer_id: uuid.UUID | None = None
    shareholder_id: uuid.UUID | None = None
    shares_affected: int | None = Field(default=None, gt=0)


class ShareEventVerifyRequest(BaseModel):
    filing_status: bool | None = None
    filing_evidence_ref: str | None = Field(default=None, min_length=4, max_length=2000)
    filing_date: date | None = None
    certificate_issued: bool | None = None
    certificate_evidence_ref: str | None = Field(default=None, min_length=4, max_length=2000)
    certificate_issue_date: date | None = None


def _share_event_response(event: ShareComplianceEvent) -> dict:
    return {
        "event_id": str(event.id),
        "company_id": str(event.company_id),
        "event_reference": event.event_reference,
        "event_type": event.event_type,
        "event_date": event.event_date.isoformat(),
        "event_verified": event.event_verified,
        "event_evidence_ref": event.event_evidence_ref,
        "submitted_by": str(event.submitted_by),
        "submitted_at": event.submitted_at.isoformat(),
        "event_verified_by": str(event.event_verified_by) if event.event_verified_by else None,
        "event_verified_at": event.event_verified_at.isoformat() if event.event_verified_at else None,
        "filing_form": event.filing_form,
        "filing_status": event.filing_status if event.filing_status_verified else None,
        "filing_status_verified": event.filing_status_verified,
        "filing_date": event.filing_date.isoformat() if event.filing_date else None,
        "filing_evidence_ref": event.filing_evidence_ref if event.filing_status_verified else None,
        "certificate_issued": event.certificate_issued if event.certificate_status_verified else None,
        "certificate_status_verified": event.certificate_status_verified,
        "certificate_issue_date": event.certificate_issue_date.isoformat() if event.certificate_issue_date else None,
        "certificate_evidence_ref": event.certificate_evidence_ref if event.certificate_status_verified else None,
    }


# ---------------------------------------------------------------------------
# Schemas — Audit
# ---------------------------------------------------------------------------

class AuditCreateRequest(BaseModel):
    company_id: uuid.UUID
    financial_year: int = Field(ge=2000, le=2100)
    auditor_firm: str | None = None
    auditor_icab_number: str | None = None


class AuditMarkCompleteRequest(BaseModel):
    signed_date: date
    auditor_firm: str
    auditor_icab_number: str
    audit_opinion: str = Field(default="UNQUALIFIED")
    report_document_id: uuid.UUID | None = None


class AuditResponse(BaseModel):
    audit_id: str
    company_id: str
    financial_year: int
    is_complete: bool
    signed_date: str | None
    auditor_firm: str | None
    audit_opinion: str | None
    created_at: str


# ---------------------------------------------------------------------------
# Schemas — Annual Return
# ---------------------------------------------------------------------------

class AnnualReturnCreateRequest(BaseModel):
    company_id: uuid.UUID
    financial_year: int = Field(ge=2000, le=2100)
    agm_date: date | None = None


class AnnualReturnMarkFiledRequest(BaseModel):
    filed_date: date
    rjsc_acknowledgment_number: str | None = None
    late_fee_paid: bool = False
    late_fee_amount: float | None = None
    filing_document_id: uuid.UUID | None = None


class AnnualReturnResponse(BaseModel):
    return_id: str
    company_id: str
    financial_year: int
    is_filed: bool
    filing_evidence_status: str
    filing_deadline: str | None
    is_default: bool | None
    filed_date: str | None
    rjsc_acknowledgment_number: str | None
    late_fee_paid: bool
    created_at: str


class StatutoryRegisterCreateRequest(BaseModel):
    company_id: uuid.UUID
    register_type: str
    is_maintained: bool = False
    last_updated_date: date | None = None
    location: str | None = None
    notes: str | None = None


class StatutoryRegisterUpdateRequest(BaseModel):
    is_maintained: bool | None = None
    last_updated_date: date | None = None
    location: str | None = None
    notes: str | None = None


class StatutoryRegisterResponse(BaseModel):
    register_id: str
    company_id: str
    register_type: str
    is_maintained: bool
    last_updated_date: str | None
    location: str | None
    notes: str | None
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
# PORTFOLIO LIST — GET /filings
# All filings across portfolio (admin) or accessible companies (client)
# ===========================================================================

@router.get(
    "",
    dependencies=[Depends(require_entitlement("compliance_package"))],
    summary="List all filings across portfolio",
)
async def list_all_filings(
    request: Request,
    company_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    from sqlalchemy import select

    from app.models.company import Company
    from app.models.filings import AGM, AnnualReturn, Audit

    # Customer and legal-staff portfolio views are restricted to the exact
    # companies for which the entitlement dependency verified an active plan.
    role_value = str(getattr(current_user.role, "value", current_user.role))
    entitled_company_ids = [
        uuid.UUID(str(value))
        for value in getattr(request.state, "entitled_company_ids", [])
    ]
    if role_value in {"CLIENT_DIRECTOR", "CLIENT_VIEW_ONLY", "LEGAL_STAFF"}:
        company_filter = Company.id.in_(entitled_company_ids)
        company_filter = entitled_company_ids
    else:
        company_filter = None

    results = {"agms": [], "audits": [], "annual_returns": []}  # type: ignore

    # AGMs
    stmt = select(AGM)
    if company_id:
        stmt = stmt.where(AGM.company_id == company_id)
    if company_filter is not None:
        stmt = stmt.where(AGM.company_id.in_(company_filter))
    agms = (await db.execute(stmt.order_by(getattr(AGM, "agm_due_date", None).desc()).limit(50))).scalars().all()  # type: ignore
    results["agms"] = [_agm_to_response(a) for a in agms]

    # Audits
    stmt = select(Audit)
    if company_id:
        stmt = stmt.where(Audit.company_id == company_id)
    if company_filter is not None:
        stmt = stmt.where(Audit.company_id.in_(company_filter))
    audits = (await db.execute(stmt.order_by(Audit.financial_year.desc()).limit(50))).scalars().all()
    results["audits"] = [_audit_to_response(a) for a in audits]

    # Annual Returns
    stmt = select(AnnualReturn)
    if company_id:
        stmt = stmt.where(AnnualReturn.company_id == company_id)
    if company_filter is not None:
        stmt = stmt.where(AnnualReturn.company_id.in_(company_filter))
    returns = (await db.execute(stmt.order_by(AnnualReturn.financial_year.desc()).limit(50))).scalars().all()
    results["annual_returns"] = [_return_to_response(r) for r in returns]

    return results


# ===========================================================================
# AGM ENDPOINTS
# ===========================================================================

@router.post(
    "/agm",
    response_model=AGMResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles("ADMIN_STAFF", "SUPER_ADMIN", "LEGAL_STAFF")), Depends(require_entitlement("compliance_package"))],
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
        agm_deadline=body.agm_due_date,
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
    response_model=list[AGMResponse],
    dependencies=[Depends(require_company_access("company_id")), Depends(require_entitlement("compliance_package"))],
    summary="List all AGM records for a company",
)
async def list_agms(
    company_id: uuid.UUID,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = AGMService(db)
    agms = await svc.get_for_company(company_id)
    return [_agm_to_response(a) for a in agms]


@router.patch(
    "/agm/{agm_id}/held",
    response_model=AGMResponse,
    dependencies=[Depends(require_roles("ADMIN_STAFF", "SUPER_ADMIN", "LEGAL_STAFF")), Depends(require_entitlement("compliance_package"))],
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
        agm_date=body.held_date,
        venue=body.venue,
        members_present=body.members_present,
        auditor_reappointed=body.auditor_reappointed,
        minutes_prepared=body.minutes_prepared,
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
    dependencies=[Depends(require_roles("ADMIN_STAFF", "SUPER_ADMIN", "LEGAL_STAFF")), Depends(require_entitlement("compliance_package"))],
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
    _agm = await svc.get_by_id_or_404(agm_id)
    # RJSC-001: verify user has access to this company's AGM
    if current_user.role in ("CLIENT_DIRECTOR", "CLIENT_VIEW_ONLY"):
        from sqlalchemy import select as _sel

        from app.models.company import CompanyUserAccess as _CMA
        _access = await db.execute(_sel(_CMA).where(_CMA.user_id == current_user.id, _CMA.company_id == _agm.company_id))
        if not _access.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Access denied — AGM belongs to another company")

    update_data = {
        "filed_date": body.filed_date,
        "rjsc_acknowledgment_number": body.rjsc_acknowledgment_number,
        "is_filed": True,
    }
    updated = await svc.update_by_id(agm_id, update_data)  # type: ignore
    _dispatch_reevaluation(updated.company_id, "AGM_FILED")  # type: ignore
    return _agm_to_response(updated)


# ===========================================================================
# AUDIT ENDPOINTS
# ===========================================================================

@router.post(
    "/audit",
    response_model=AuditResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles("ADMIN_STAFF", "SUPER_ADMIN", "LEGAL_STAFF")), Depends(require_entitlement("compliance_package"))],
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
        icab_number=body.auditor_icab_number,
    )
    return _audit_to_response(audit)


@router.get(
    "/audit/{company_id}",
    response_model=list[AuditResponse],
    dependencies=[Depends(require_company_access("company_id")), Depends(require_entitlement("compliance_package"))],
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
    dependencies=[Depends(require_roles("ADMIN_STAFF", "SUPER_ADMIN", "LEGAL_STAFF")), Depends(require_entitlement("compliance_package"))],
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

    audit = await svc.mark_complete(  # type: ignore
        audit_id=audit_id,
        signed_date=body.signed_date,
        auditor_firm=body.auditor_firm,
        icab_number=body.auditor_icab_number,
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
    dependencies=[Depends(require_roles("ADMIN_STAFF", "SUPER_ADMIN", "LEGAL_STAFF")), Depends(require_entitlement("compliance_package"))],
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
    )
    return _return_to_response(annual_return)


@router.get(
    "/annual-return/{company_id}",
    response_model=list[AnnualReturnResponse],
    dependencies=[Depends(require_company_access("company_id")), Depends(require_entitlement("compliance_package"))],
    summary="List all annual return records for a company",
)
async def list_annual_returns(
    company_id: uuid.UUID,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = AnnualReturnService(db)
    returns = await svc.get_for_company(company_id)
    return [_return_to_response(r) for r in returns]


@router.patch(
    "/annual-return/{return_id}/filed",
    response_model=AnnualReturnResponse,
    dependencies=[Depends(require_roles("ADMIN_STAFF", "SUPER_ADMIN", "LEGAL_STAFF")), Depends(require_entitlement("compliance_package"))],
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

    # RJSC-001: verify user has access before marking filed
    _existing = await svc.get_by_id(return_id)
    if not _existing:
        raise HTTPException(status_code=404, detail="Annual return record not found.")
    if current_user.role in ("CLIENT_DIRECTOR", "CLIENT_VIEW_ONLY"):
        from sqlalchemy import select as _sel

        from app.models.company import CompanyUserAccess as _CMA
        _access = await db.execute(_sel(_CMA).where(_CMA.user_id == current_user.id, _CMA.company_id == _existing.company_id))
        if not _access.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Access denied — return belongs to another company")

    annual_return = await svc.mark_filed(  # type: ignore
        return_id=return_id,
        filed_date=body.filed_date,
        rjsc_receipt_number=body.rjsc_acknowledgment_number,
        late_fee_paid_bdt=body.late_fee_amount if body.late_fee_paid else None,
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
    dependencies=[Depends(require_roles("ADMIN_STAFF", "SUPER_ADMIN", "LEGAL_STAFF")), Depends(require_entitlement("compliance_package"))],
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
    response_model=list[StatutoryRegisterResponse],
    dependencies=[Depends(require_company_access("company_id")), Depends(require_entitlement("compliance_package"))],
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
    dependencies=[Depends(require_roles("ADMIN_STAFF", "SUPER_ADMIN", "LEGAL_STAFF")), Depends(require_entitlement("compliance_package"))],
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
        agm_due_date=(agm.agm_deadline.isoformat() if LEGAL_CALENDAR_RELEASED and agm.agm_deadline else None),
        held_date=agm.agm_date.isoformat() if agm.agm_date else None,
        filed_date=agm.rjsc_filing_date.isoformat() if agm.rjsc_filing_date else None,
        quorum_met=(
            agm.quorum_met
            if (
                getattr(agm, "members_present_verified", False) is True
                and bool(getattr(agm, "members_present_evidence_ref", None))
                and getattr(agm, "members_present_verified_at", None) is not None
                and getattr(agm, "members_present_verified_by", None) is not None
                and getattr(agm, "quorum_required_verified", False) is True
                and bool(getattr(agm, "quorum_evidence_ref", None))
                and getattr(agm, "quorum_verified_at", None) is not None
                and getattr(agm, "quorum_verified_by", None) is not None
            ) else None
        ),
        quorum_required=(
            agm.quorum_required
            if (
                getattr(agm, "quorum_required_verified", False) is True
                and bool(getattr(agm, "quorum_evidence_ref", None))
                and getattr(agm, "quorum_verified_at", None) is not None
                and getattr(agm, "quorum_verified_by", None) is not None
            ) else None
        ),
        quorum_basis=(
            agm.quorum_basis
            if (
                getattr(agm, "quorum_required_verified", False) is True
                and bool(getattr(agm, "quorum_evidence_ref", None))
                and getattr(agm, "quorum_verified_at", None) is not None
                and getattr(agm, "quorum_verified_by", None) is not None
            ) else None
        ),
        venue=getattr(agm, "venue", None),
        members_present=(
            agm.members_present
            if (
                getattr(agm, "members_present_verified", False) is True
                and bool(getattr(agm, "members_present_evidence_ref", None))
                and getattr(agm, "members_present_verified_at", None) is not None
                and getattr(agm, "members_present_verified_by", None) is not None
            ) else None
        ),
        auditor_reappointed=(
            agm.auditor_reappointed
            if (
                getattr(agm, "auditor_reappointment_verified", False) is True
                and bool(getattr(agm, "auditor_reappointment_evidence_ref", None))
                and getattr(agm, "auditor_reappointment_verified_at", None) is not None
                and getattr(agm, "auditor_reappointment_verified_by", None) is not None
            ) else None
        ),
        # These raw legacy fields have no independent review/provenance path.
        # Never expose them as affirmative or negative legal findings.
        accounts_adopted=None,
        agm_held_without_audit=None,
        minutes_prepared=None,
        is_default=(agm.is_default if LEGAL_SCORE_RELEASED else None),
        created_at=agm.created_at.isoformat() if hasattr(agm, 'created_at') and agm.created_at else '',
    )


def _audit_to_response(audit) -> AuditResponse:
    return AuditResponse(
        audit_id=str(audit.id),
        company_id=str(audit.company_id),
        financial_year=audit.financial_year,
        is_complete=audit.audit_complete,
        signed_date=audit.audit_signed_date.isoformat() if audit.audit_signed_date else None,
        auditor_firm=audit.auditor_firm,
        audit_opinion=(
            ("QUALIFIED" if audit.report_qualified else "UNQUALIFIED")
            if audit.audit_complete else None
        ),
        created_at=audit.created_at.isoformat() if audit.created_at else '',
    )


def _return_to_response(r) -> AnnualReturnResponse:
    filing_evidence_status = (
        "RECEIPT_REFERENCE_RECORDED_UNVERIFIED"
        if r.filed_date and r.rjsc_receipt_number
        else "DATE_RECORDED_UNVERIFIED"
        if r.filed_date
        else "NO_FILING_EVIDENCE_RECORDED"
    )
    return AnnualReturnResponse(
        return_id=str(r.id),
        company_id=str(r.company_id),
        financial_year=r.financial_year,
        is_filed=r.filed_date is not None,
        filing_evidence_status=filing_evidence_status,
        filing_deadline=(
            r.filing_deadline.isoformat()
            if LEGAL_CALENDAR_RELEASED and r.filing_deadline else None
        ),
        is_default=(r.is_default if LEGAL_SCORE_RELEASED else None),
        filed_date=r.filed_date.isoformat() if r.filed_date else None,
        rjsc_acknowledgment_number=r.rjsc_receipt_number,
        late_fee_paid=bool(r.late_fee_paid_bdt),
        created_at=r.created_at.isoformat() if r.created_at else '',
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


# ---------------------------------------------------------------------------
# Share statutory event evidence
# ---------------------------------------------------------------------------

@router.post(
    "/share-events/{company_id}",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles("LEGAL_STAFF", "ADMIN_STAFF", "SUPER_ADMIN"))],
    summary="Record an unverified share statutory event with source provenance",
)
async def create_share_compliance_event(
    company_id: uuid.UUID,
    body: ShareEventCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    from app.core.company_authorization import ensure_staff_company_scope

    await ensure_staff_company_scope(company_id, current_user, db)
    event_type = body.event_type
    if event_type == "TRANSFER_REGISTERED":
        if body.share_transfer_id is None:
            raise HTTPException(status_code=422, detail="A registered-transfer event must reference its share transfer.")
        transfer_result = await db.execute(
            select(ShareTransfer.id).where(
                ShareTransfer.id == body.share_transfer_id,
                ShareTransfer.company_id == company_id,
                ShareTransfer.is_active.is_(True),
            ).limit(1)
        )
        if transfer_result.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Share transfer not found in this company.")
    elif body.share_transfer_id is not None:
        raise HTTPException(status_code=422, detail="Only TRANSFER_REGISTERED events may reference a transfer row.")

    if body.shareholder_id is not None:
        shareholder_result = await db.execute(
            select(Shareholder.id).where(
                Shareholder.id == body.shareholder_id,
                Shareholder.company_id == company_id,
                Shareholder.is_active.is_(True),
            ).limit(1)
        )
        if shareholder_result.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Shareholder not found in this company.")

    filing_form = {
        "ALLOTMENT": "FORM_XV",
        "CAPITAL_INCREASE_RESOLUTION": "FORM_IV",
        "TRANSFER_REGISTERED": None,
    }[event_type]
    event = ShareComplianceEvent(
        company_id=company_id,
        share_transfer_id=body.share_transfer_id,
        shareholder_id=body.shareholder_id,
        event_reference=body.event_reference.strip(),
        shares_affected=body.shares_affected,
        event_type=event_type,
        event_date=body.event_date,
        event_verified=False,
        event_evidence_ref=body.event_evidence_ref.strip(),
        submitted_by=current_user.id,
        submitted_at=datetime.now(UTC),
        filing_form=filing_form,
        filing_status=None,
        filing_status_verified=False,
        certificate_issued=None,
        certificate_status_verified=False,
    )
    db.add(event)
    await db.flush()
    await db.refresh(event)
    return _share_event_response(event)


@router.post(
    "/share-events/{event_id}/verify",
    dependencies=[Depends(require_roles("LEGAL_STAFF", "ADMIN_STAFF", "SUPER_ADMIN"))],
    summary="Independently verify share event, filing and certificate evidence",
)
async def verify_share_compliance_event(
    event_id: uuid.UUID,
    body: ShareEventVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    from app.core.company_authorization import ensure_staff_company_scope

    result = await db.execute(
        select(ShareComplianceEvent)
        .where(ShareComplianceEvent.id == event_id, ShareComplianceEvent.is_active.is_(True))
        .with_for_update()
    )
    event = result.scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=404, detail="Share event not found.")
    await ensure_staff_company_scope(event.company_id, current_user, db)
    if event.submitted_by == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A different authorized reviewer must verify the submitted event.",
        )
    if not event.event_evidence_ref.strip():
        raise HTTPException(status_code=422, detail="The original event evidence reference is missing.")

    updates = {
        "event_verified": True,
        "event_verified_at": datetime.now(UTC),
        "event_verified_by": current_user.id,
    }
    if body.filing_status is not None:
        expected_form = {
            "ALLOTMENT": "FORM_XV",
            "CAPITAL_INCREASE_RESOLUTION": "FORM_IV",
        }.get(event.event_type)
        if expected_form is None or event.filing_form != expected_form:
            raise HTTPException(status_code=422, detail="This event type has no Form XV/Form IV filing trigger.")
        if not body.filing_evidence_ref:
            raise HTTPException(status_code=422, detail="Filing status verification requires a filing evidence reference.")
        if body.filing_status and body.filing_date is None:
            raise HTTPException(status_code=422, detail="A filed status requires the filing date.")
        if not body.filing_status and body.filing_date is not None:
            raise HTTPException(status_code=422, detail="An unfiled status cannot carry a filing date.")
        updates.update({
            "filing_status": body.filing_status,
            "filing_evidence_ref": body.filing_evidence_ref.strip(),
            "filing_date": body.filing_date,
            "filing_status_verified": True,
            "filing_verified_at": datetime.now(UTC),
            "filing_verified_by": current_user.id,
        })
    elif body.filing_evidence_ref is not None or body.filing_date is not None:
        raise HTTPException(status_code=422, detail="Filing evidence/date cannot be supplied without a filing status.")

    if body.certificate_issued is not None:
        if event.event_type not in {"ALLOTMENT", "TRANSFER_REGISTERED"}:
            raise HTTPException(status_code=422, detail="Section 158 certificate status requires an allotment or registered-transfer event.")
        if not body.certificate_evidence_ref:
            raise HTTPException(status_code=422, detail="Certificate status verification requires a certificate evidence reference.")
        if body.certificate_issued and body.certificate_issue_date is None:
            raise HTTPException(status_code=422, detail="An issued certificate requires its issue date.")
        if not body.certificate_issued and body.certificate_issue_date is not None:
            raise HTTPException(status_code=422, detail="An unissued certificate cannot carry an issue date.")
        updates.update({
            "certificate_issued": body.certificate_issued,
            "certificate_evidence_ref": body.certificate_evidence_ref.strip(),
            "certificate_issue_date": body.certificate_issue_date,
            "certificate_status_verified": True,
            "certificate_verified_at": datetime.now(UTC),
            "certificate_verified_by": current_user.id,
        })
    elif body.certificate_evidence_ref is not None or body.certificate_issue_date is not None:
        raise HTTPException(status_code=422, detail="Certificate evidence/date cannot be supplied without a certificate status.")

    for key, value in updates.items():
        setattr(event, key, value)
    await db.flush()
    await db.refresh(event)
    return _share_event_response(event)
