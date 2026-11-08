from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    get_current_user,
    get_db_for_user,
    require_company_access,
)
from app.services.compliance_calendar import (
    ComplianceCalendarService,
    LEGAL_CALENDAR_RELEASED,
    VERIFIED_CALENDAR_EVENT_TYPES,
)


def _require_calendar_release() -> None:
    if not LEGAL_CALENDAR_RELEASED or not VERIFIED_CALENDAR_EVENT_TYPES:
        raise HTTPException(
            status_code=503,
            detail=(
                "Statutory calendar is unavailable pending rule-level legal "
                "validation, company-specific applicability and independent counsel approval."
            ),
        )


router = APIRouter(prefix="/calendar", tags=["Compliance Calendar"])


@router.post("/companies/{company_id}/generate",
            dependencies=[Depends(require_company_access("company_id"))])
async def generate_calendar(
    company_id: UUID,
    years_ahead: int = Query(3, ge=1, le=5),
    db: AsyncSession = Depends(get_db_for_user),
    current_user=Depends(get_current_user),
):
    _require_calendar_release()
    service = ComplianceCalendarService(db)
    events = await service.get_calendar(
        company_id,
        include_past_days=0,
        include_future_days=years_ahead * 366,
    )
    return {"message": f"Generated {len(events)} events", "count": len(events)}


@router.get(
    "/companies/{company_id}",
    dependencies=[Depends(require_company_access("company_id"))],
)
async def get_calendar(
    company_id: UUID,
    days_ahead: int = Query(90, ge=30, le=365),
    db: AsyncSession = Depends(get_db_for_user),
    current_user=Depends(get_current_user),
):
    _require_calendar_release()
    service = ComplianceCalendarService(db)
    events = await service.get_upcoming(company_id, days_ahead=days_ahead)
    return {"company_id": str(company_id), "events": events}
