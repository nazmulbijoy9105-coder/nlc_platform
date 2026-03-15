from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser, RequireLegalStaff
from app.core.schemas import create_data_response
from app.models import Company, RescueCase, RescueStatus, RiskBand

import uuid


def generate_uuid() -> str:
    return str(uuid.uuid4())


router = APIRouter(prefix="/rescue", tags=["Rescue"])


class RescueCreate(BaseModel):
    company_id: str
    strategy: str | None = None
    target_score: int = 80
    target_date: datetime | None = None


class RescueUpdate(BaseModel):
    strategy: str | None = None
    target_score: int | None = None
    target_date: datetime | None = None
    notes: str | None = None


class RescueResponse(BaseModel):
    id: str
    company_id: str
    status: str
    risk_band_at_creation: str
    score_at_creation: int
    current_score: int | None
    target_score: int
    strategy: str | None
    start_date: datetime
    target_date: datetime | None
    completion_date: datetime | None


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_rescue(
    request: RescueCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Company).where(Company.id == request.company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if company.risk_band not in [RiskBand.RED, RiskBand.BLACK]:
        raise HTTPException(
            status_code=400,
            detail="Rescue cases are only for RED or BLACK risk companies",
        )

    rescue = RescueCase(
        id=generate_uuid(),
        company_id=request.company_id,
        status=RescueStatus.ASSESSMENT,
        risk_band_at_creation=company.risk_band.value,
        score_at_creation=company.compliance_score,
        current_score=company.compliance_score,
        target_score=request.target_score,
        strategy=request.strategy,
        target_date=request.target_date,
        start_date=datetime.now(timezone.utc),
        created_by_id=current_user.id,
    )
    db.add(rescue)

    company.status = CompanyStatus.UNDER_RESCUE

    await db.commit()
    await db.refresh(rescue)
    return create_data_response(
        data=RescueResponse.model_validate(rescue),
        message="Rescue case created successfully",
    )


@router.get("")
async def list_rescues(
    status: RescueStatus | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(RescueCase)
    if status:
        query = query.where(RescueCase.status == status)

    result = await db.execute(query)
    rescues = result.scalars().all()
    return create_data_response(data=[RescueResponse.model_validate(r) for r in rescues])


@router.get("/{rescue_id}")
async def get_rescue(rescue_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RescueCase).where(RescueCase.id == rescue_id))
    rescue = result.scalar_one_or_none()
    if not rescue:
        raise HTTPException(status_code=404, detail="Rescue case not found")
    return create_data_response(data=RescueResponse.model_validate(rescue))


@router.put("/{rescue_id}")
async def update_rescue(
    rescue_id: str,
    request: RescueUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(RescueCase).where(RescueCase.id == rescue_id))
    rescue = result.scalar_one_or_none()
    if not rescue:
        raise HTTPException(status_code=404, detail="Rescue case not found")

    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(rescue, field, value)

    rescue.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(rescue)
    return create_data_response(
        data=RescueResponse.model_validate(rescue),
        message="Rescue case updated successfully",
    )


@router.put("/{rescue_id}/status")
async def update_rescue_status(
    rescue_id: str,
    status: RescueStatus,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(RescueCase).where(RescueCase.id == rescue_id))
    rescue = result.scalar_one_or_none()
    if not rescue:
        raise HTTPException(status_code=404, detail="Rescue case not found")

    rescue.status = status
    if status == RescueStatus.COMPLETED:
        rescue.completion_date = datetime.now(timezone.utc)

    rescue.updated_at = datetime.now(timezone.utc)
    await db.commit()
    return create_data_response(
        data=RescueResponse.model_validate(rescue),
        message=f"Rescue status updated to {status.value}",
    )


@router.get("/company/{company_id}")
async def get_company_rescue(company_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RescueCase).where(RescueCase.company_id == company_id))
    rescue = result.scalar_one_or_none()
    if not rescue:
        raise HTTPException(status_code=404, detail="Rescue case not found")
    return create_data_response(data=RescueResponse.model_validate(rescue))
