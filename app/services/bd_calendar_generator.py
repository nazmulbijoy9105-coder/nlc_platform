"""
Service to dynamically calculate BD statutory deadlines based on Companies Act 1994 (amended 2008).
"""
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.compliance_calendar import ComplianceCalendarEvent, CalendarEventType, CalendarEventStatus

class BDCalendarGenerator:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_for_company(self, company_id, incorporation_date: date, fye: date, years_ahead: int = 3) -> List[ComplianceCalendarEvent]:
        """Generates AGM, Annual Return, and Tax deadlines for a BD company."""
        events = []
        current_fye = fye
        
        for i in range(years_ahead):
            # 1. AGM Deadline
            # Rule: First AGM within 18 months of incorporation. Subsequent AGMs max 15 months apart.
            # Standard practice: FYE + 6 months (182 days)
            agm_due_date = current_fye + timedelta(days=182)
            
            # Adjust for first AGM if incorporation was recent
            if i == 0:
                first_agm_deadline = incorporation_date + relativedelta(months=18)
                if first_agm_deadline > agm_due_date:
                    agm_due_date = first_agm_deadline

            events.append(ComplianceCalendarEvent(
                company_id=company_id,
                event_type=CalendarEventType.SUBSEQUENT_AGM if i > 0 else CalendarEventType.FIRST_AGM,
                title=f"AGM for FY {current_fye.year}",
                due_date=agm_due_date,
                period_label=f"FY-{current_fye.year}",
                status=CalendarEventStatus.UPCOMING,
                statutory_basis="Section 81(3), Companies Act 1994 (Amended 2008) - Max 15 months gap"
            ))

            # 2. Annual Return (Form XII) Deadline (AGM + 21 days)
            # Correct citation: Section 36(3), not Section 190 (which is Balance Sheet)
            ar_due_date = agm_due_date + timedelta(days=21)
            events.append(ComplianceCalendarEvent(
                company_id=company_id,
                event_type=CalendarEventType.ANNUAL_RETURN,
                title=f"Annual Return (Form XII) FY {current_fye.year}",
                due_date=ar_due_date,
                period_label=f"FY-{current_fye.year}",
                status=CalendarEventStatus.UPCOMING,
                statutory_basis="Section 36(3), Companies Act 1994 - 21 days after AGM"
            ))

            # 3. Income Tax Return (NBR) Deadline (Usually Nov 30th for June FYE)
            tax_due_date = current_fye + relativedelta(months=5) 
            events.append(ComplianceCalendarEvent(
                company_id=company_id,
                event_type=CalendarEventType.TAX_RETURN,
                title=f"Corporate Tax Return FY {current_fye.year}",
                due_date=tax_due_date,
                period_label=f"FY-{current_fye.year}",
                status=CalendarEventStatus.UPCOMING,
                statutory_basis="Income Tax Act 2023"
            ))

            # Increment FYE by 1 year
            current_fye = current_fye + relativedelta(years=1)

        self.db.add_all(events)
        await self.db.commit()
        return events
