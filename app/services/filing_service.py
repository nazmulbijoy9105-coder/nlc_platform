"""
NEUM LEX COUNSEL — Filing Service
app/services/filing_service.py

Implements _create_agm, _update_agm, _get_agm_response stubs
and equivalent functions for Audit and AnnualReturn.

These three tables feed directly into the rule engine evaluation.
Every create/update triggers a score re-evaluation via background task.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import select

from app.models.company import Company
from app.models.filings import AGM, AnnualReturn, Audit
from app.rule_engine.engine import NLCRuleEngine
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
        minutes_prepared: bool | None = None,
        minutes_filed_rjsc: bool = False,
        rjsc_filing_date: date | None = None,
        is_default: bool = False,
        delay_days: int = 0,
        notice_defective: bool = False,
        notice_missing: bool = False,
        quorum_met: bool | None = None,
        created_by: uuid.UUID | None = None,
        agm_due_date=None
    ) -> AGM:
        """
        Create an AGM record. Calculates is_default and delay_days automatically
        if agm_deadline is provided.
        """
        # Always derive the statutory deadline from server-held company/AGM facts.
        # Never trust a client-supplied due date as a legal deadline.
        company_result = await self.db.execute(
            select(Company).where(Company.id == company_id)
        )
        company = company_result.scalar_one_or_none()
        if company is not None:
            previous_agm_result = await self.db.execute(
                select(AGM)
                .where(AGM.company_id == company_id, AGM.agm_held.is_(True), AGM.agm_date.is_not(None))
                .order_by(AGM.agm_date.desc())
                .limit(1)
            )
            previous_agm = previous_agm_result.scalar_one_or_none()
            previous_agm_date = (
                previous_agm.agm_date if previous_agm is not None else company.last_agm_date
            )
            if previous_agm_date is not None:
                agm_deadline = self.calculate_subsequent_agm_deadline(
                    previous_agm_date, company.financial_year_end
                )
            elif company.incorporation_date is not None:
                agm_deadline = self.calculate_first_agm_deadline(
                    company.incorporation_date
                )
            else:
                agm_deadline = None
        else:
            agm_deadline = None

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

        # Quorum can only be calculated when the applicable threshold has been
        # verified from the Articles or the Section 85(2)(b) statutory default.
        if agm_held and members_present is not None and quorum_required is not None:
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
            members_present=members_present,
            quorum_required=quorum_required,
            quorum_met=quorum_met,
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
        held_date: date | None = None,
        agm_date: date | None = None,
        members_present: int | None = None,
        quorum_met: bool | None = None,
        auditor_reappointed: bool | None = None,
        accounts_adopted: bool | None = None,
        agm_held_without_audit: bool | None = None,
        venue: str | None = None,
        minutes_document_id: uuid.UUID | None = None,
        quorum_required: int | None = None,
        minutes_prepared: bool | None = None,
        notice_missing: bool | None = None,
    ) -> AGM | None:
        """Persist AGM facts without inferring quorum from a fixed threshold.

        quorum_met must be explicitly determined from the company's Articles
        and, where applicable, the Section 85(2)(b) statutory default.
        """
        agm = await self.get_by_id(agm_id)
        if not agm:
            return None
        meeting_date = held_date or agm_date
        if meeting_date is None:
            raise ValueError("held_date is required to mark an AGM as held")

        # Only calculate quorum when the applicable threshold has been reviewed.
        if quorum_met is None and members_present is not None and quorum_required is not None:
            quorum_met = members_present >= quorum_required

        is_default = False
        delay_days = 0
        if agm.agm_deadline and meeting_date > agm.agm_deadline:
            is_default = True
            delay_days = (meeting_date - agm.agm_deadline).days

        return await self.update_instance(
            agm,
            agm_held=True,
            agm_date=meeting_date,
            venue=venue,
            members_present=members_present,
            quorum_required=quorum_required,
            quorum_met=quorum_met,
            auditor_reappointed=auditor_reappointed,
            accounts_adopted=accounts_adopted,
            agm_held_without_audit=agm_held_without_audit,
            minutes_prepared=True if minutes_document_id else minutes_prepared,
            minutes_document_id=minutes_document_id,
            notice_missing=notice_missing if notice_missing is not None else agm.notice_missing,
            is_default=is_default,
            delay_days=delay_days,
        )

    @staticmethod
    def calculate_first_agm_deadline(incorporation_date: date) -> date:
        """Section 81: first AGM deadline is 18 calendar months after incorporation."""
        return NLCRuleEngine._add_months(incorporation_date, 18)

    @staticmethod
    def calculate_subsequent_agm_deadline(
        last_agm_date: date,
        financial_year_end: date | None = None,
    ) -> date:
        """Section 81: maximum 15 calendar months between subsequent AGMs.

        financial_year_end is retained for backward-compatible callers only.
        A generic six-month-after-FY-end deadline is not imposed on ordinary
        private companies by the Companies Act rule.
        """
        return NLCRuleEngine._add_months(last_agm_date, 15)


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
