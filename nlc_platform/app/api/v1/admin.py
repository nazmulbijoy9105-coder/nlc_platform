from fastapi import APIRouter
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.dependencies import RequireAdmin
from app.core.schemas import create_data_response
from app.models import User, Company, Filing, RescueCase

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/analytics/compliance")
async def get_compliance_analytics(
    current_user: RequireAdmin,
    db=Depends(get_db),
):
    companies_result = await db.execute(select(Company))
    companies = companies_result.scalars().all()

    from app.models import RiskBand

    green = len([c for c in companies if c.risk_band == RiskBand.GREEN])
    yellow = len([c for c in companies if c.risk_band == RiskBand.YELLOW])
    red = len([c for c in companies if c.risk_band == RiskBand.RED])
    black = len([c for c in companies if c.risk_band == RiskBand.BLACK])

    avg_score = sum(c.compliance_score for c in companies) / len(companies) if companies else 0

    return create_data_response(
        data={
            "total_companies": len(companies),
            "risk_distribution": {
                "green": green,
                "yellow": yellow,
                "red": red,
                "black": black,
            },
            "average_compliance_score": round(avg_score, 2),
        }
    )


@router.get("/analytics/filings")
async def get_filings_analytics(
    current_user: RequireAdmin,
    db=Depends(get_db),
):
    from app.models import FilingStatus

    result = await db.execute(select(Filing))
    filings = result.scalars().all()

    pending = len([f for f in filings if f.status == FilingStatus.PENDING])
    submitted = len([f for f in filings if f.status == FilingStatus.SUBMITTED])
    approved = len([f for f in filings if f.status == FilingStatus.APPROVED])
    overdue = len([f for f in filings if f.status == FilingStatus.OVERDUE])

    return create_data_response(
        data={
            "total_filings": len(filings),
            "status_distribution": {
                "pending": pending,
                "submitted": submitted,
                "approved": approved,
                "overdue": overdue,
            },
        }
    )


@router.get("/analytics/rescue")
async def get_rescue_analytics(
    current_user: RequireAdmin,
    db=Depends(get_db),
):
    from app.models import RescueStatus

    result = await db.execute(select(RescueCase))
    rescues = result.scalars().all()

    return create_data_response(
        data={
            "total_rescue_cases": len(rescues),
            "by_status": {
                status.value: len([r for r in rescues if r.status == status])
                for status in RescueStatus
            },
        }
    )


@router.get("/health")
async def admin_health_check(current_user: RequireAdmin):
    return create_data_response(data={"status": "healthy", "admin_panel": "operational"})


from fastapi import Depends
