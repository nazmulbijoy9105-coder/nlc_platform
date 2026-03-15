from datetime import datetime, timezone
from typing import Any, Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser, RequireLegalStaff
from app.core.schemas import create_data_response, create_paginated_response
from app.models import Company, CompanyContact, CompanyStatus, RiskBand, ComplianceScore, Violation
from app.rule_engine.engine import evaluate_company

router = APIRouter(prefix="/companies", tags=["Companies"])


class CompanyContactCreate(BaseModel):
    name: str
    designation: str | None = None
    email: str | None = None
    phone: str | None = None
    is_primary: bool = False


class CompanyCreate(BaseModel):
    rjsc_number: str
    name: str
    registration_date: datetime
    registered_address: str | None = None
    business_address: str | None = None
    sector: str | None = None
    authorized_capital: float = 0
    paid_up_capital: float = 0
    contacts: list[CompanyContactCreate] = []


class CompanyUpdate(BaseModel):
    name: str | None = None
    registered_address: str | None = None
    business_address: str | None = None
    sector: str | None = None
    authorized_capital: float | None = None
    paid_up_capital: float | None = None
    status: CompanyStatus | None = None


class CompanyResponse(BaseModel):
    id: str
    rjsc_number: str
    name: str
    registration_date: datetime
    status: CompanyStatus
    risk_band: RiskBand
    compliance_score: int
    authorized_capital: float
    paid_up_capital: float
    registered_address: str | None
    business_address: str | None
    sector: str | None


class ComplianceEvaluationRequest(BaseModel):
    director_count: int = 2
    directors_qualified: bool = True
    independent_directors: int = 0
    board_diversity_score: int = 1
    annual_statements_filed: bool = True
    fs_filing_date: bool = True
    cost_audit_applicable: bool = False
    rpt_disclosed: bool = True
    agm_date: bool = True
    egm_documentation: bool = True
    minutes_maintained: bool = True
    annual_return_date: bool = True
    director_change_date: bool = True
    registered_office_changed: bool = True
    form28_filed: bool = True
    paid_up_capital: float = 100000
    net_assets: float = 100000
    capital_increase_registered: bool = True
    board_meetings_per_year: int = 4
    quorum_maintained: bool = True
    notice_period_met: bool = True
    audit_committee_exists: bool = True
    auditor_appointed: bool = True
    internal_audit_required: bool = False
    cg_compliance_score: int = 70
    charge_registration_date: bool = True
    charge_modification_filed: bool = True
    charge_satisfaction_filed: bool = True
    registers_maintained: bool = True
    seal_usage_documented: bool = True
    books_of_account: bool = True
    bcp_exists: bool = False


import uuid


def generate_uuid() -> str:
    return str(uuid.uuid4())


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_company(
    request: CompanyCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Company).where(Company.rjsc_number == request.rjsc_number))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="RJSC number already exists")

    company = Company(
        id=generate_uuid(),
        rjsc_number=request.rjsc_number,
        name=request.name,
        registration_date=request.registration_date,
        registered_address=request.registered_address,
        business_address=request.business_address,
        sector=request.sector,
        authorized_capital=request.authorized_capital,
        paid_up_capital=request.paid_up_capital,
        created_by_id=current_user.id,
    )

    for contact_data in request.contacts:
        contact = CompanyContact(
            id=generate_uuid(),
            company_id=company.id,
            **contact_data.model_dump(),
        )
        db.add(contact)

    db.add(company)
    await db.commit()
    await db.refresh(company)

    return create_data_response(
        data=CompanyResponse.model_validate(company),
        message="Company created successfully",
    )


@router.get("")
async def list_companies(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: CompanyStatus | None = None,
    risk_band: RiskBand | None = None,
    current_user: CurrentUser = Depends(get_db),
    db: AsyncSession = Depends(get_db),
):
    query = select(Company)

    if status:
        query = query.where(Company.status == status)
    if risk_band:
        query = query.where(Company.risk_band == risk_band)

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    companies = result.scalars().all()

    count_query = select(Company)
    if status:
        count_query = count_query.where(Company.status == status)
    if risk_band:
        count_query = count_query.where(Company.risk_band == risk_band)

    from sqlalchemy import func

    total_result = await db.execute(select(func.count()).select_from(count_query.subquery()))
    total = total_result.scalar()

    return create_paginated_response(
        data=[CompanyResponse.model_validate(c) for c in companies],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{company_id}")
async def get_company(company_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()

    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    return create_data_response(data=CompanyResponse.model_validate(company))


@router.put("/{company_id}")
async def update_company(
    company_id: str,
    request: CompanyUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()

    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(company, field, value)

    company.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(company)

    return create_data_response(
        data=CompanyResponse.model_validate(company),
        message="Company updated successfully",
    )


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company(company_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()

    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    await db.delete(company)
    await db.commit()


@router.post("/{company_id}/evaluate")
async def evaluate_company_compliance(
    company_id: str,
    request: ComplianceEvaluationRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()

    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    company_data = request.model_dump()
    company_data["id"] = company_id
    company_data["paid_up_capital"] = company.paid_up_capital

    eval_result = evaluate_company(company_data)

    compliance_score = ComplianceScore(
        id=generate_uuid(),
        company_id=company_id,
        score=eval_result.total_score,
        risk_band=eval_result.risk_band.value,
        total_rules=eval_result.total_rules,
        passed_rules=eval_result.passed_rules,
        failed_rules=eval_result.failed_rules,
    )
    db.add(compliance_score)

    for rule_result in eval_result.results:
        if not rule_result.passed:
            violation = Violation(
                id=generate_uuid(),
                company_id=company_id,
                rule_id=rule_result.rule_code,
                severity="HIGH" if rule_result.score == 0 else "MEDIUM",
                description=rule_result.details,
                score_impact=rule_result.max_score,
                violation_details=rule_result.violation_details,
            )
            db.add(violation)

    company.compliance_score = eval_result.total_score
    company.risk_band = eval_result.risk_band

    await db.commit()

    return create_data_response(
        data={
            "score": eval_result.total_score,
            "risk_band": eval_result.risk_band.value,
            "total_rules": eval_result.total_rules,
            "passed_rules": eval_result.passed_rules,
            "failed_rules": eval_result.failed_rules,
            "results": [
                {
                    "rule_code": r.rule_code,
                    "passed": r.passed,
                    "score": r.score,
                    "details": r.details,
                }
                for r in eval_result.results
            ],
        },
        message="Company evaluated successfully",
    )


@router.get("/{company_id}/score")
async def get_company_score(company_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ComplianceScore)
        .where(ComplianceScore.company_id == company_id)
        .order_by(ComplianceScore.evaluated_at.desc())
    )
    scores = result.scalars().all()

    if not scores:
        raise HTTPException(status_code=404, detail="No compliance scores found")

    latest = scores[0]
    return create_data_response(
        data={
            "score": latest.score,
            "risk_band": latest.risk_band,
            "total_rules": latest.total_rules,
            "passed_rules": latest.passed_rules,
            "failed_rules": latest.failed_rules,
            "evaluated_at": latest.evaluated_at,
        }
    )


@router.get("/{company_id}/violations")
async def get_company_violations(company_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Violation).where(Violation.company_id == company_id))
    violations = result.scalars().all()

    return create_data_response(
        data=[
            {
                "id": v.id,
                "rule_id": v.rule_id,
                "severity": v.severity,
                "description": v.description,
                "statutory_basis": v.statutory_basis,
                "score_impact": v.score_impact,
                "is_resolved": v.is_resolved,
                "created_at": v.created_at,
            }
            for v in violations
        ]
    )


@router.get("/{company_id}/rescue-status")
async def get_rescue_status(company_id: str, db: AsyncSession = Depends(get_db)):
    from app.models import RescueCase

    result = await db.execute(select(RescueCase).where(RescueCase.company_id == company_id))
    rescue = result.scalar_one_or_none()

    if not rescue:
        return create_data_response(data={"has_rescue": False})

    return create_data_response(
        data={
            "has_rescue": True,
            "status": rescue.status.value,
            "current_score": rescue.current_score,
            "target_score": rescue.target_score,
            "start_date": rescue.start_date,
            "target_date": rescue.target_date,
        }
    )
