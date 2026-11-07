from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entitlement import require_entitlement
from app.core.company_authorization import ensure_staff_company_scope
from app.core.dependencies import (
    get_current_user,
    get_db_for_user,
    require_company_access,
)
from app.services.compliance_calendar import ComplianceCalendarService

router = APIRouter(prefix="/calendar", tags=["Compliance Calendar"])


@router.post("/companies/{company_id}/generate",
            dependencies=[Depends(require_company_access("company_id")), Depends(require_entitlement("compliance_package"))])
async def generate_calendar(
    company_id: UUID,
    years_ahead: int = Query(3, ge=1, le=5),
    db: AsyncSession = Depends(get_db_for_user),
    current_user=Depends(get_current_user),
):
    await ensure_staff_company_scope(company_id, current_user, db)
    service = ComplianceCalendarService(db)
    events = await service.get_calendar(company_id, years_ahead=years_ahead)
    return {"message": f"Generated {len(events)} events", "count": len(events)}


@router.get(
    "/companies/{company_id}",
    dependencies=[Depends(require_company_access("company_id")), Depends(require_entitlement("compliance_package"))],
)
async def get_calendar(
    company_id: UUID,
    days_ahead: int = Query(90, ge=30, le=365),
    db: AsyncSession = Depends(get_db_for_user),
    current_user=Depends(get_current_user),
):
    await ensure_staff_company_scope(company_id, current_user, db)
    service = ComplianceCalendarService(db)
    events = await service.get_upcoming(company_id, days_ahead=days_ahead)
    return {"company_id": str(company_id), "events": events}
