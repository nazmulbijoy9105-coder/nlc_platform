"""
Service to dynamically calculate BD statutory deadlines based on FYE.
"""
from datetime import date, timedelta
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
            # 1. AGM Deadline (FYE + 182 days)
            agm_due_date = current_fye + timedelta(days=182)
            events.append(ComplianceCalendarEvent(
                company_id=company_id,
                event_type=CalendarEventType.SUBSEQUENT_AGM,
                title=f"AGM for FY {current_fye.year}",
                due_date=agm_due_date,
                period_label=f"FY-{current_fye.year}",
                status=CalendarEventStatus.UPCOMING,
                statutory_basis="Section 81(3), Companies Act 1994"
            ))

            # 2. Annual Return (Form XII) Deadline (AGM + 21 days)
            ar_due_date = agm_due_date + timedelta(days=21)
            events.append(ComplianceCalendarEvent(
                company_id=company_id,
                event_type=CalendarEventType.ANNUAL_RETURN,
                title=f"Annual Return (Form XII) FY {current_fye.year}",
                due_date=ar_due_date,
                period_label=f"FY-{current_fye.year}",
                status=CalendarEventStatus.UPCOMING,
                statutory_basis="Section 36, Companies Act 1994"
            ))

            # 3. Income Tax Return (NBR) Deadline (FYE + 4.5 months)
            # Usually Nov 30th for June FYE
            tax_due_date = current_fye + timedelta(days=135) 
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
            try:
                current_fye = current_fye.replace(year=current_fye.year + 1)
            except ValueError:
                # Handle Feb 29th edge case
                current_fye = current_fye.replace(year=current_fye.year + 1, day=28)

        self.db.add_all(events)
        await self.db.commit()
        return events
