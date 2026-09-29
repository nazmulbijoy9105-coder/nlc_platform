"""RJSC Forms API — manage statutory form filings

Endpoints:
  GET    /rjsc-forms/{company_id}          List all forms for company
  GET    /rjsc-forms/{company_id}/pending   List pending forms
  GET    /rjsc-forms/{company_id}/overdue   List overdue forms
  POST   /rjsc-forms/{company_id}           Create form filing
  PATCH  /rjsc-forms/{form_id}/filed        Mark as filed
  GET    /rjsc-forms/reference              Get all RJSC form types
"""
from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db_for_user, require_company_access, require_roles
from app.models.rjsc_forms import RJSC_FORMS_REFERENCE
from app.services.rjsc_form_service import RJSCFormService

router = APIRouter()


class FormFilingResponse(BaseModel):
    id: str
    company_id: str
    form_code: str
    form_number: str
    form_name: str
    section_reference: str
    related_rule_id: str | None
    filing_status: str
    due_date: str | None
    filed_date: str | None
    rjsc_receipt_number: str | None
    notes: str | None
    financial_year: str | None


class CreateFormFilingRequest(BaseModel):
    form_code: str
    due_date: date | None = None
    financial_year: str | None = None


class MarkFiledRequest(BaseModel):
    filed_date: date
    rjsc_receipt_number: str | None = None
    notes: str | None = None


@router.get("/reference", dependencies=[Depends(get_current_user)])
async def get_form_reference():
    """Get all RJSC form types with section references."""
    return {"forms": RJSC_FORMS_REFERENCE, "total": len(RJSC_FORMS_REFERENCE)}


@router.get("/{company_id}", response_model=list[FormFilingResponse],
            dependencies=[Depends(require_company_access("company_id"))],
            summary="List all RJSC form filings for a company")
async def list_forms(company_id: str, db: AsyncSession = Depends(get_db_for_user)):
    svc = RJSCFormService(db)
    forms = await svc.get_forms_for_company(company_id)
    return [FormFilingResponse(
        id=str(f.id), company_id=f.company_id, form_code=f.form_code,
        form_number=f.form_number, form_name=f.form_name,
        section_reference=f.section_reference, related_rule_id=f.related_rule_id,
        filing_status=f.filing_status, due_date=f.due_date.isoformat() if f.due_date else None,
        filed_date=f.filed_date.isoformat() if f.filed_date else None,
        rjsc_receipt_number=f.rjsc_receipt_number, notes=f.notes,
        financial_year=f.financial_year,
    ) for f in forms]


@router.get("/{company_id}/pending", response_model=list[FormFilingResponse],
            dependencies=[Depends(require_company_access("company_id"))],
            summary="List pending RJSC forms")
async def list_pending_forms(company_id: str, db: AsyncSession = Depends(get_db_for_user)):
    svc = RJSCFormService(db)
    await svc.update_overdue_status(company_id)
    forms = await svc.get_pending_forms(company_id)
    return [FormFilingResponse(
        id=str(f.id), company_id=f.company_id, form_code=f.form_code,
        form_number=f.form_number, form_name=f.form_name,
        section_reference=f.section_reference, related_rule_id=f.related_rule_id,
        filing_status=f.filing_status, due_date=f.due_date.isoformat() if f.due_date else None,
        filed_date=f.filed_date.isoformat() if f.filed_date else None,
        rjsc_receipt_number=f.rjsc_receipt_number, notes=f.notes,
        financial_year=f.financial_year,
    ) for f in forms]


@router.get("/{company_id}/overdue", response_model=list[FormFilingResponse],
            dependencies=[Depends(require_company_access("company_id"))],
            summary="List overdue RJSC forms")
async def list_overdue_forms(company_id: str, db: AsyncSession = Depends(get_db_for_user)):
    svc = RJSCFormService(db)
    forms = await svc.get_overdue_forms(company_id)
    return [FormFilingResponse(
        id=str(f.id), company_id=f.company_id, form_code=f.form_code,
        form_number=f.form_number, form_name=f.form_name,
        section_reference=f.section_reference, related_rule_id=f.related_rule_id,
        filing_status=f.filing_status, due_date=f.due_date.isoformat() if f.due_date else None,
        filed_date=f.filed_date.isoformat() if f.filed_date else None,
        rjsc_receipt_number=f.rjsc_receipt_number, notes=f.notes,
        financial_year=f.financial_year,
    ) for f in forms]


@router.post("/{company_id}", response_model=FormFilingResponse, status_code=201,
             dependencies=[Depends(require_roles("ADMIN_STAFF", "SUPER_ADMIN", "LEGAL_STAFF")),
                           Depends(require_company_access("company_id"))],
             summary="Create RJSC form filing")
async def create_form_filing(
    company_id: str,
    body: CreateFormFilingRequest,
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = RJSCFormService(db)
    try:
        filing = await svc.create_form_filing(
            company_id=company_id,
            form_code=body.form_code,
            due_date=body.due_date,
            financial_year=body.financial_year,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return FormFilingResponse(
        id=str(filing.id), company_id=filing.company_id, form_code=filing.form_code,
        form_number=filing.form_number, form_name=filing.form_name,
        section_reference=filing.section_reference, related_rule_id=filing.related_rule_id,
        filing_status=filing.filing_status, due_date=filing.due_date.isoformat() if filing.due_date else None,
        filed_date=None, rjsc_receipt_number=None, notes=None,
        financial_year=filing.financial_year,
    )


@router.patch("/{form_id}/filed", response_model=FormFilingResponse,
              dependencies=[Depends(require_roles("ADMIN_STAFF", "SUPER_ADMIN", "LEGAL_STAFF"))],
              summary="Mark RJSC form as filed")
async def mark_form_filed(
    form_id: str,
    body: MarkFiledRequest,
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = RJSCFormService(db)
    filing = await svc.mark_filed(
        form_id=form_id,
        filed_date=body.filed_date,
        rjsc_receipt_number=body.rjsc_receipt_number,
        notes=body.notes,
    )
    if not filing:
        raise HTTPException(status_code=404, detail="Form filing not found")
    return FormFilingResponse(
        id=str(filing.id), company_id=filing.company_id, form_code=filing.form_code,
        form_number=filing.form_number, form_name=filing.form_name,
        section_reference=filing.section_reference, related_rule_id=filing.related_rule_id,
        filing_status=filing.filing_status, due_date=filing.due_date.isoformat() if filing.due_date else None,
        filed_date=filing.filed_date.isoformat() if filing.filed_date else None,
        rjsc_receipt_number=filing.rjsc_receipt_number, notes=filing.notes,
        financial_year=filing.financial_year,
    )
