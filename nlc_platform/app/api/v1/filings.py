from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser
from app.core.schemas import create_data_response, create_paginated_response
from app.models import Filing, FilingStatus, FilingType, FilingHistory
import uuid


def generate_uuid() -> str:
    return str(uuid.uuid4())


router = APIRouter(prefix="/filings", tags=["Filings"])


class FilingCreate(BaseModel):
    company_id: str
    filing_type: FilingType
    form_number: str | None = None
    due_date: datetime
    notes: str | None = None


class FilingUpdate(BaseModel):
    status: FilingStatus | None = None
    form_number: str | None = None
    submission_date: datetime | None = None
    rjsc_receipt_number: str | None = None
    amount_paid: int | None = None
    notes: str | None = None


class FilingResponse(BaseModel):
    id: str
    company_id: str
    filing_type: str
    status: str
    form_number: str | None
    due_date: datetime
    submission_date: datetime | None
    rjsc_receipt_number: str | None
    amount_paid: int | None
    notes: str | None


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_filing(
    request: FilingCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    filing = Filing(
        id=generate_uuid(),
        company_id=request.company_id,
        filing_type=request.filing_type,
        form_number=request.form_number,
        due_date=request.due_date,
        notes=request.notes,
        created_by_id=current_user.id,
    )
    db.add(filing)
    await db.commit()
    await db.refresh(filing)
    return create_data_response(
        data=FilingResponse.model_validate(filing),
        message="Filing created successfully",
    )


@router.get("")
async def list_filings(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: FilingStatus | None = None,
    company_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Filing)
    if status:
        query = query.where(Filing.status == status)
    if company_id:
        query = query.where(Filing.company_id == company_id)

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    filings = result.scalars().all()

    from sqlalchemy import func

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar()

    return create_paginated_response(
        data=[FilingResponse.model_validate(f) for f in filings],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{filing_id}")
async def get_filing(filing_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Filing).where(Filing.id == filing_id))
    filing = result.scalar_one_or_none()
    if not filing:
        raise HTTPException(status_code=404, detail="Filing not found")
    return create_data_response(data=FilingResponse.model_validate(filing))


@router.put("/{filing_id}")
async def update_filing(
    filing_id: str,
    request: FilingUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Filing).where(Filing.id == filing_id))
    filing = result.scalar_one_or_none()
    if not filing:
        raise HTTPException(status_code=404, detail="Filing not found")

    old_status = filing.status
    for field, value in request.model_dump(exclude_unset=True).items():
        setattr(filing, field, value)

    if request.status and request.status != old_status:
        history = FilingHistory(
            id=generate_uuid(),
            filing_id=filing_id,
            status=request.status,
            changed_by_id=current_user.id,
        )
        db.add(history)

    filing.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(filing)
    return create_data_response(
        data=FilingResponse.model_validate(filing),
        message="Filing updated successfully",
    )


@router.delete("/{filing_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_filing(filing_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Filing).where(Filing.id == filing_id))
    filing = result.scalar_one_or_none()
    if not filing:
        raise HTTPException(status_code=404, detail="Filing not found")
    await db.delete(filing)
    await db.commit()


@router.get("/company/{company_id}")
async def get_company_filings(company_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Filing).where(Filing.company_id == company_id))
    filings = result.scalars().all()
    return create_data_response(data=[FilingResponse.model_validate(f) for f in filings])


@router.get("/upcoming")
async def get_upcoming_filings(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    from datetime import timedelta

    cutoff = datetime.now(timezone.utc) + timedelta(days=days)
    result = await db.execute(
        select(Filing)
        .where(Filing.due_date <= cutoff)
        .where(Filing.status == FilingStatus.PENDING)
        .order_by(Filing.due_date)
    )
    filings = result.scalars().all()
    return create_data_response(data=[FilingResponse.model_validate(f) for f in filings])


@router.get("/overdue")
async def get_overdue_filings(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Filing)
        .where(Filing.due_date < datetime.now(timezone.utc))
        .where(Filing.status.in_([FilingStatus.PENDING, FilingStatus.IN_PROGRESS]))
    )
    filings = result.scalars().all()
    return create_data_response(data=[FilingResponse.model_validate(f) for f in filings])


@router.post("/{filing_id}/submit")
async def submit_filing(
    filing_id: str,
    rjsc_receipt_number: str | None = None,
    amount_paid: int | None = None,
    current_user: CurrentUser = Depends(get_db),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Filing).where(Filing.id == filing_id))
    filing = result.scalar_one_or_none()
    if not filing:
        raise HTTPException(status_code=404, detail="Filing not found")

    filing.status = FilingStatus.SUBMITTED
    filing.submission_date = datetime.now(timezone.utc)
    if rjsc_receipt_number:
        filing.rjsc_receipt_number = rjsc_receipt_number
    if amount_paid:
        filing.amount_paid = amount_paid

    history = FilingHistory(
        id=generate_uuid(),
        filing_id=filing_id,
        status=FilingStatus.SUBMITTED,
        notes="Filed submitted",
        changed_by_id=current_user.id,
    )
    db.add(history)
    await db.commit()
    return create_data_response(
        data=FilingResponse.model_validate(filing),
        message="Filing submitted successfully",
    )
