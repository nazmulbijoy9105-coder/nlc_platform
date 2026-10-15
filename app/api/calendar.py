from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_current_user
from app.services.compliance_calendar import ComplianceCalendarService

router = APIRouter(prefix="/calendar", tags=["Compliance Calendar"])


@router.post("/companies/{company_id}/generate")
async def generate_calendar(
    company_id: UUID,
    years_ahead: int = Query(3, ge=1, le=5),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = ComplianceCalendarService(db)
    events = await service.generate_and_persist(company_id, years_ahead=years_ahead)
    return {"message": f"Generated {len(events)} events", "count": len(events)}


@router.get("/companies/{company_id}")
async def get_calendar(
    company_id: UUID,
    days_ahead: int = Query(90, ge=30, le=365),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = ComplianceCalendarService(db)
    events = await service.get_upcoming_events(company_id, days_ahead=days_ahead)
    return {"company_id": str(company_id), "events": events}
