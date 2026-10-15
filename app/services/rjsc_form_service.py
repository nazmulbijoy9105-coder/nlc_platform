"""RJSC Form Service — manages statutory form filings"""
from __future__ import annotations

import uuid
from datetime import date, timedelta

from sqlalchemy import select

from app.models.rjsc_forms import RJSC_FORMS_REFERENCE, RJSCFormFiling
from app.services.base import BaseService


class RJSCFormService(BaseService[RJSCFormFiling]):
    model = RJSCFormFiling

    async def get_forms_for_company(self, company_id: str) -> list[RJSCFormFiling]:
        """Get all RJSC form filings for a company."""
        result = await self.db.execute(
            select(RJSCFormFiling)
            .where(RJSCFormFiling.company_id == company_id)
            .order_by(RJSCFormFiling.form_code)
        )
        return list(result.scalars().all())

    async def get_pending_forms(self, company_id: str) -> list[RJSCFormFiling]:
        """Get forms that are pending or overdue."""
        result = await self.db.execute(
            select(RJSCFormFiling)
            .where(
                RJSCFormFiling.company_id == company_id,
                RJSCFormFiling.filing_status.in_(["PENDING", "OVERDUE"]),
            )
            .order_by(RJSCFormFiling.due_date)
        )
        return list(result.scalars().all())

    async def get_overdue_forms(self, company_id: str) -> list[RJSCFormFiling]:
        """Get forms that are overdue."""
        today = date.today()
        result = await self.db.execute(
            select(RJSCFormFiling)
            .where(
                RJSCFormFiling.company_id == company_id,
                RJSCFormFiling.filing_status == "PENDING",
                RJSCFormFiling.due_date < today,
            )
        )
        return list(result.scalars().all())

    async def create_form_filing(
        self,
        company_id: str,
        form_code: str,
        due_date: date | None = None,
        financial_year: str | None = None,
    ) -> RJSCFormFiling:
        """Create a new form filing record."""
        form_ref = next((f for f in RJSC_FORMS_REFERENCE if f["form_code"] == form_code), None)
        if not form_ref:
            raise ValueError(f"Unknown form code: {form_code}")

        filing = RJSCFormFiling(
            id=str(uuid.uuid4()),
            company_id=company_id,
            form_code=form_ref["form_code"],
            form_number=form_ref["form_number"],
            form_name=form_ref["form_name"],
            section_reference=form_ref["section"],
            related_rule_id=form_ref["rule_id"],
            filing_status="PENDING",
            due_date=due_date or (date.today() + timedelta(days=form_ref["deadline_days"])),  # type: ignore
            financial_year=financial_year,
        )
        self.db.add(filing)
        await self.db.flush()
        return filing

    async def mark_filed(
        self,
        form_id: str,
        filed_date: date,
        rjsc_receipt_number: str | None = None,
        filed_by: str | None = None,
        notes: str | None = None,
    ) -> RJSCFormFiling | None:
        """Mark a form as filed with RJSC."""
        filing = await self.get_by_id(form_id)  # type: ignore
        if not filing:
            return None
        filing.filing_status = "FILED"
        filing.filed_date = filed_date
        filing.rjsc_receipt_number = rjsc_receipt_number
        filing.filed_by = filed_by
        if notes:
            filing.notes = notes
        self.db.add(filing)
        await self.db.flush()
        return filing

    async def initialize_forms_for_new_company(
        self,
        company_id: str,
        incorporation_date: date,
    ) -> list[RJSCFormFiling]:
        """Create initial form filing records for a newly incorporated company."""
        filings = []
        for form_ref in RJSC_FORMS_REFERENCE:
            due = incorporation_date + timedelta(days=form_ref["deadline_days"]) if form_ref["deadline_days"] > 0 else None  # type: ignore
            filing = await self.create_form_filing(
                company_id=company_id,
                form_code=form_ref["form_code"],  # type: ignore
                due_date=due,
            )
            filings.append(filing)
        return filings

    async def update_overdue_status(self, company_id: str) -> int:
        """Update PENDING forms to OVERDUE if past due date. Returns count updated."""
        today = date.today()
        result = await self.db.execute(
            select(RJSCFormFiling)
            .where(
                RJSCFormFiling.company_id == company_id,
                RJSCFormFiling.filing_status == "PENDING",
                RJSCFormFiling.due_date < today,
            )
        )
        overdue_forms = result.scalars().all()
        for form in overdue_forms:
            form.filing_status = "OVERDUE"
            self.db.add(form)
        await self.db.flush()
        return len(overdue_forms)
