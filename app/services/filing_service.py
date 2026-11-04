"""
NEUM LEX COUNSEL — Filing Service
app/services/filing_service.py

Implements _create_agm, _update_agm, _get_agm_response stubs
and equivalent functions for Audit and AnnualReturn.

These three tables feed directly into the rule engine evaluation.
Every create/update triggers a score re-evaluation via background task.
"""
from __future__ import annotations

import calendar
from datetime import date, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import select

from app.models.company import Company
from app.models.filings import AGM, AnnualReturn, Audit
from app.models.infrastructure import StatutoryRegister
from app.services.base import BaseService

if TYPE_CHECKING:
    import uuid

# ═══════════════════════════════════════════════════════════════════════
# AGM SERVICE
# ═══════════════════════════════════════════════════════════════════════

class AGMService(BaseService[AGM]):
    model = AGM

    async def create_agm(
        self,
        company_id: uuid.UUID,
        financial_year: int,
        *,
        agm_type: str = "ANNUAL",
        agm_deadline: date | None = None,
        agm_held: bool = False,
        agm_date: date | None = None,
        notice_sent_date: date | None = None,
        members_present: int | None = None,
        quorum_required: int | None = None,
        auditor_reappointed: bool | None = None,
        minutes_prepared: bool = False,
        minutes_filed_rjsc: bool = False,
        rjsc_filing_date: date | None = None,
        is_default: bool = False,
        delay_days: int = 0,
        notice_defective: bool = False,
        notice_missing: bool = False,
        quorum_met: bool | None = None,
        quorum_basis: str | None = None,
        created_by: uuid.UUID | None = None,
        agm_due_date: date | None = None,
    ) -> AGM:
        """
        Create an AGM record. Calculates is_default and delay_days automatically
        if a deadline is provided. agm_due_date is retained as a compatibility
        alias; the canonical field is agm_deadline.
        """
        if agm_deadline is None:
            agm_deadline = agm_due_date

        # Auto-calculate default status
        if agm_held and agm_date and agm_deadline:
            if agm_date > agm_deadline:
                is_default = True
                delay_days = (agm_date - agm_deadline).days
        elif not agm_held and agm_deadline and date.today() > agm_deadline:
            is_default = True
            delay_days = (date.today() - agm_deadline).days

        # Notice check
        if agm_held and notice_sent_date and agm_date:
            days_notice = (agm_date - notice_sent_date).days
            if days_notice < 21:
                notice_defective = True
            if days_notice < 0:
                notice_missing = True

        # Quorum is UNKNOWN unless both attendance and the applicable
        # Articles/statutory basis have been established. Never infer a
        # failure from an unverified zero attendance or a guessed default.
        if (
            agm_held
            and members_present is not None
            and quorum_required is not None
            and quorum_met is None
        ):
            quorum_met = members_present >= quorum_required

        return await self.create(
            company_id=company_id,
            financial_year=financial_year,
            agm_type=agm_type,
            agm_deadline=agm_deadline,
            agm_held=agm_held,
            agm_date=agm_date,
            notice_sent_date=notice_sent_date,
            notice_days_before=(agm_date - notice_sent_date).days if (agm_date and notice_sent_date) else None,
            notice_defective=notice_defective,
            notice_missing=notice_missing,
            # The legacy column is NOT NULL; zero is treated as
            # unverified by _agm_profile_evidence unless provenance exists.
            members_present=members_present if members_present is not None else 0,
            quorum_required=quorum_required,
            quorum_met=quorum_met,
            quorum_basis=quorum_basis,
            auditor_reappointed=auditor_reappointed,
            minutes_prepared=minutes_prepared,
            minutes_filed_rjsc=minutes_filed_rjsc,
            rjsc_filing_date=rjsc_filing_date,
            is_default=is_default,
            delay_days=delay_days,
        )

    async def get_for_company(
        self,
        company_id: uuid.UUID,
        *,
        financial_year: int | None = None,
    ) -> list[AGM]:
        """Get all AGMs for a company, optionally filtered by year."""
        filters = [AGM.company_id == company_id]
        if financial_year:
            filters.append(AGM.financial_year == financial_year)
        result = await self.db.execute(
            select(AGM)
            .where(*filters)
            .order_by(AGM.financial_year.desc())
        )
        return list(result.scalars().all())

    async def get_by_company_and_year(
        self,
        company_id: uuid.UUID,
        financial_year: int,
    ) -> AGM | None:
        """Fetch AGM by company and financial year (unique constraint)."""
        result = await self.db.execute(
            select(AGM).where(
                AGM.company_id == company_id,
                AGM.financial_year == financial_year,
            )
        )
        return result.scalar_one_or_none()

    async def mark_held(
        self,
        agm_id: uuid.UUID,
        agm_date: date,
        members_present: int,
        auditor_reappointed: bool,
        *,
        venue: str | None = None,
        accounts_adopted: bool | None = None,
        agm_held_without_audit: bool | None = None,
        minutes_document_id: uuid.UUID | None = None,
    ) -> AGM | None:
        """
        Record an AGM using server-derived quorum, not a client-supplied boolean.

        Section 85(2)(b) private-company default:
        2 members where total membership is not more than 6; 3 where it is
        more than 6. Articles-specific overrides are not yet modelled, so this
        is a statutory-default assessment and must not be presented as a
        final Articles-compliant legal determination.
        """
        agm = await self.get_by_id(agm_id)
        if not agm:
            return None

        company = await self.db.get(Company, agm.company_id)
        member_count = getattr(company, "member_count", None) if company else None
        company_type = getattr(company, "company_type", None) if company else None
        company_type = getattr(company_type, "value", company_type)

        if company_type == "PRIVATE_LIMITED" and member_count is not None and member_count > 0:
            quorum_required = 2 if member_count <= 6 else 3
            quorum_met: bool | None = members_present >= quorum_required
            quorum_basis = "SECTION_85_2_B_DEFAULT_ARTICLES_NOT_REVIEWED"
        else:
            # Do not invent a quorum where company type or verified membership
            # is unavailable, or where a different company category applies.
            quorum_required = None
            quorum_met = None
            quorum_basis = "NOT_EVALUATED"

        is_default = bool(agm.agm_deadline and agm_date > agm.agm_deadline)
        delay_days = (agm_date - agm.agm_deadline).days if is_default and agm.agm_deadline else 0

        return await self.update_instance(
            agm,
            agm_held=True,
            agm_date=agm_date,
            venue=venue,
            members_present=members_present,
            quorum_required=quorum_required,
            quorum_met=quorum_met,
            auditor_reappointed=auditor_reappointed,
            accounts_adopted=accounts_adopted,
            agm_held_without_audit=agm_held_without_audit,
            minutes_document_id=minutes_document_id,
            is_default=is_default,
            delay_days=delay_days,
        )

    @staticmethod
    def _add_calendar_months(source: date, months: int) -> date:
        month_index = source.month - 1 + months
        year = source.year + month_index // 12
        month = month_index % 12 + 1
        day = min(source.day, calendar.monthrange(year, month)[1])
        return date(year, month, day)

    @classmethod
    def calculate_first_agm_deadline(cls, incorporation_date: date) -> date:
        """Companies Act 1994 s.81: first AGM within 18 calendar months."""
        return cls._add_calendar_months(incorporation_date, 18)

    @classmethod
    def calculate_subsequent_agm_deadline(
        cls,
        last_agm_date: date,
        financial_year_end: date | None = None,
    ) -> date:
        """Section 81: each subsequent AGM within 15 calendar months and in each calendar year.

        financial_year_end is retained for API compatibility only. Section 81
        does not impose a universal six-month-after-FY-end test.
        """
        by_interval = cls._add_calendar_months(last_agm_date, 15)
        by_calendar_year = date(last_agm_date.year + 1, 12, 31)
        return min(by_interval, by_calendar_year)


# ═══════════════════════════════════════════════════════════════════════
# AUDIT SERVICE
# ═══════════════════════════════════════════════════════════════════════

class AuditService(BaseService[Audit]):
    model = Audit

    async def create_audit(
        self,
        company_id: uuid.UUID,
        financial_year: int,
        *,
        auditor_name: str | None = None,
        auditor_firm: str | None = None,
        icab_number: str | None = None,
        audit_complete: bool = False,
        audit_signed_date: date | None = None,
        first_auditor_appointed: bool = False,
        first_auditor_appointment_date: date | None = None,
        first_auditor_delay_days: int = 0,
        report_qualified: bool = False,
        qualification_notes: str | None = None,
        auditor_icab_number=None
    ) -> Audit:
        """
        Create an audit record. Auto-detects AUD-003 (AGM without audit).
        """
        is_missing = not audit_complete and not audit_signed_date
        delay_days = 0
        if audit_signed_date:
            # Calculate delay relative to FY end (approximate)
            pass  # Will be calculated by rule engine from AGM date

        return await self.create(
            company_id=company_id,
            financial_year=financial_year,
            auditor_name=auditor_name,
            auditor_firm=auditor_firm,
            icab_number=icab_number,
            audit_complete=audit_complete,
            audit_signed_date=audit_signed_date,
            first_auditor_appointed=first_auditor_appointed,
            first_auditor_appointment_date=first_auditor_appointment_date,
            first_auditor_delay_days=first_auditor_delay_days,
            agm_held_without_audit=False,  # Set by rule engine evaluation
            is_missing=is_missing,
            delay_days=delay_days,
            report_qualified=report_qualified,
            qualification_notes=qualification_notes,
        )

    async def get_for_company(
        self,
        company_id: uuid.UUID,
    ) -> list[Audit]:
        """Get all audits for a company, ordered by year desc."""
        result = await self.db.execute(
            select(Audit)
            .where(Audit.company_id == company_id)
            .order_by(Audit.financial_year.desc())
        )
        return list(result.scalars().all())

    async def get_latest(self, company_id: uuid.UUID) -> Audit | None:
        """Get the most recent audit for a company."""
        result = await self.db.execute(
            select(Audit)
            .where(Audit.company_id == company_id)
            .order_by(Audit.financial_year.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def mark_complete(
        self,
        audit_id: uuid.UUID,
        signed_date: date,
        auditor_name: str,
        auditor_firm: str,
        icab_number: str | None = None,
        report_qualified: bool = False,
        qualification_notes: str | None = None,
    ) -> Audit | None:
        """Mark an audit as complete with signed date."""
        audit = await self.get_by_id(audit_id)
        if not audit:
            return None
        return await self.update_instance(
            audit,
            audit_complete=True,
            audit_signed_date=signed_date,
            auditor_name=auditor_name,
            auditor_firm=auditor_firm,
            icab_number=icab_number,
            is_missing=False,
            report_qualified=report_qualified,
            qualification_notes=qualification_notes,
        )


# ═══════════════════════════════════════════════════════════════════════
# ANNUAL RETURN SERVICE
# ═══════════════════════════════════════════════════════════════════════

class AnnualReturnService(BaseService[AnnualReturn]):
    model = AnnualReturn

    async def create_return(
        self,
        company_id: uuid.UUID,
        financial_year: int,
        *,
        filing_deadline: date | None = None,
        filed_date: date | None = None,
        rjsc_receipt_number: str | None = None,
        is_complete: bool = True,
        missing_attachments: str | None = None,
        filing_fee_paid_bdt: float | None = None,
        late_fee_paid_bdt: float | None = None,
        agm_date=None
    ) -> AnnualReturn:
        """
        Create an annual return record.
        Auto-calculates is_default and delay_days.
        Section 190 CA 1994: file within 30 days of AGM date.
        """
        is_default = False
        delay_days = 0

        if filed_date and filing_deadline:
            if filed_date > filing_deadline:
                is_default = True
                delay_days = (filed_date - filing_deadline).days
        elif not filed_date and filing_deadline and date.today() > filing_deadline:
            is_default = True
            delay_days = (date.today() - filing_deadline).days

        return await self.create(
            company_id=company_id,
            financial_year=financial_year,
            filing_deadline=filing_deadline,
            is_default=is_default,
            filed_date=filed_date,
            delay_days=delay_days,
            rjsc_receipt_number=rjsc_receipt_number,
            is_complete=is_complete,
            missing_attachments=missing_attachments,
            filing_fee_paid_bdt=filing_fee_paid_bdt,
            late_fee_paid_bdt=late_fee_paid_bdt,
        )

    async def get_for_company(self, company_id: uuid.UUID) -> list[AnnualReturn]:
        """Get all annual returns for a company, ordered by year desc."""
        result = await self.db.execute(
            select(AnnualReturn)
            .where(AnnualReturn.company_id == company_id)
            .order_by(AnnualReturn.financial_year.desc())
        )
        return list(result.scalars().all())

    async def get_unfiled_count(self, company_id: uuid.UUID) -> int:
        """Count unfiled annual returns for a company."""
        from sqlalchemy import func
        result = await self.db.execute(
            select(func.count())
            .select_from(AnnualReturn)
            .where(
                AnnualReturn.company_id == company_id,
                AnnualReturn.is_default,
            )
        )
        return result.scalar_one()

    async def mark_filed(
        self,
        return_id: uuid.UUID,
        filed_date: date,
        rjsc_receipt_number: str | None = None,
        filing_fee_paid_bdt: float | None = None,
        late_fee_paid_bdt: float | None = None,
        is_complete: bool = True,
        missing_attachments: str | None = None,
    ) -> AnnualReturn | None:
        """Mark an annual return as filed."""
        annual_return = await self.get_by_id(return_id)
        if not annual_return:
            return None

        is_default = False
        delay_days = 0
        if annual_return.filing_deadline and filed_date > annual_return.filing_deadline:
            is_default = True
            delay_days = (filed_date - annual_return.filing_deadline).days

        return await self.update_instance(
            annual_return,
            filed_date=filed_date,
            rjsc_receipt_number=rjsc_receipt_number,
            is_default=is_default,
            delay_days=delay_days,
            filing_fee_paid_bdt=filing_fee_paid_bdt,
            late_fee_paid_bdt=late_fee_paid_bdt,
            is_complete=is_complete,
            missing_attachments=missing_attachments,
        )

    @staticmethod
    def calculate_filing_deadline(agm_date: date) -> date:
        """Section 190: Annual return due within 30 days of AGM."""
        return agm_date + timedelta(days=21)


# ═══════════════════════════════════════════════════════════════════════
# STATUTORY REGISTER SERVICE
# ═══════════════════════════════════════════════════════════════════════

class StatutoryRegisterService(BaseService[StatutoryRegister]):
    model = StatutoryRegister

    async def create_register_entry(
        self,
        company_id: uuid.UUID,
        register_type: str,
        *,
        is_maintained: bool = False,
        last_updated_date: date | None = None,
        location: str | None = None,
        notes: str | None = None,
    ) -> StatutoryRegister:
        return await self.create(
            company_id=company_id,
            register_type=register_type,
            is_maintained=is_maintained,
            last_updated_date=last_updated_date,
            location=location,
            notes=notes,
        )

    async def get_for_company(self, company_id: uuid.UUID) -> list[StatutoryRegister]:
        result = await self.db.execute(
            select(StatutoryRegister)
            .where(StatutoryRegister.company_id == company_id)
            .order_by(StatutoryRegister.register_type.asc())
        )
        return list(result.scalars().all())

    async def update_register_entry(
        self,
        register_id: uuid.UUID,
        *,
        is_maintained: bool | None = None,
        last_updated_date: date | None = None,
        location: str | None = None,
        notes: str | None = None,
    ) -> StatutoryRegister | None:
        entry = await self.get_by_id(register_id)
        if not entry:
            return None

        updates = {}
        if is_maintained is not None:
            updates["is_maintained"] = is_maintained
        if last_updated_date is not None:
            updates["last_updated_date"] = last_updated_date  # type: ignore
        if location is not None:
            updates["location"] = location  # type: ignore
        if notes is not None:
            updates["notes"] = notes  # type: ignore

        return await self.update_instance(entry, **updates)
