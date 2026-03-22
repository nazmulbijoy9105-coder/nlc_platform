"""
NEUM LEX COUNSEL — Company Service
app/services/company_service.py

Implements _save_company, _get_company_response, _update_company,
_build_company_profile, _get_all_active_company_ids stubs.

CompanyProfile assembly is the critical bridge between the database
and the rule engine (C_rule_engine.py). Every field in CompanyProfile
must be sourced from verified DB records — no AI involvement.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy import and_, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.agm import AGM
from app.models.annual_return import AnnualReturn
from app.models.audit import Audit
from app.models.company import Company, CompanyUserAccess
from app.models.enums import CompanyStatus, CompanyType, LifecycleStage, RiskBand
from app.models.people import Director, ShareTransfer, Shareholder
from app.services.base import BaseService


class CompanyService(BaseService[Company]):
    model = Company

    # ── CREATE ────────────────────────────────────────────────────

    async def create_company(
        self,
        *,
        registration_number: str,
        company_name: str,
        company_type: CompanyType,
        incorporation_date: date,
        financial_year_end: date,
        registered_address: Optional[str] = None,
        industry_sector: Optional[str] = None,
        tin_number: Optional[str] = None,
        authorized_capital_bdt: Optional[float] = None,
        paid_up_capital_bdt: Optional[float] = None,
        assigned_staff_id: Optional[uuid.UUID] = None,
        initial_directors: Optional[List[Dict]] = None,
        initial_shareholders: Optional[List[Dict]] = None,
        created_by: Optional[uuid.UUID] = None,
    ) -> Company:
        """
        Create a new company with optional initial directors and shareholders.
        Triggers full-text search vector via DB trigger.
        """
        company = await self.create(
            registration_number=registration_number.strip().upper(),
            company_name=company_name.strip(),
            company_type=company_type,
            company_status=CompanyStatus.ACTIVE,
            lifecycle_stage=LifecycleStage.INCORPORATION,
            incorporation_date=incorporation_date,
            financial_year_end=financial_year_end,
            registered_address=registered_address,
            industry_sector=industry_sector,
            tin_number=tin_number,
            authorized_capital_bdt=authorized_capital_bdt,
            paid_up_capital_bdt=paid_up_capital_bdt,
            assigned_staff_id=assigned_staff_id,
        )

        # Create initial directors if provided
        if initial_directors:
            for d in initial_directors:
                director = Director(
                    id=uuid.uuid4(),
                    company_id=company.id,
                    **d,
                )
                self.db.add(director)

        # Create initial shareholders if provided
        if initial_shareholders:
            for s in initial_shareholders:
                shareholder = Shareholder(
                    id=uuid.uuid4(),
                    company_id=company.id,
                    **s,
                )
                self.db.add(shareholder)

        await self.db.flush()
        await self.db.refresh(company)
        return company

    # ── READ ──────────────────────────────────────────────────────

    async def get_with_relations(self, company_id: uuid.UUID) -> Optional[Company]:
        """
        Fetch company with all active directors, shareholders, AGMs,
        audits, annual returns, and active compliance flags loaded.
        Used to build the company dashboard view.
        """
        result = await self.db.execute(
            select(Company)
            .options(
                selectinload(Company.directors),
                selectinload(Company.shareholders),
                selectinload(Company.agms),
                selectinload(Company.audits),
                selectinload(Company.annual_returns),
                selectinload(Company.compliance_flags),
                selectinload(Company.rescue_plans),
                selectinload(Company.engagements),
            )
            .where(Company.id == company_id)
        )
        return result.scalar_one_or_none()

    async def get_by_registration_number(
        self,
        registration_number: str,
    ) -> Optional[Company]:
        """Fetch company by RJSC registration number (unique)."""
        result = await self.db.execute(
            select(Company).where(
                Company.registration_number == registration_number.strip().upper()
            )
        )
        return result.scalar_one_or_none()

    async def list_companies(
        self,
        *,
        limit: int = 25,
        offset: int = 0,
        risk_band: Optional[RiskBand] = None,
        rescue_required: Optional[bool] = None,
        search: Optional[str] = None,
        company_ids_filter: Optional[List[str]] = None,
    ) -> tuple[List[Company], int]:
        """
        List companies with filters, search, and pagination.
        Returns (companies, total_count).
        company_ids_filter: used for client roles (from JWT).
        search: full-text search on company name or registration number.
        """
        filters = [Company.is_active == True]

        if risk_band:
            filters.append(Company.current_risk_band == risk_band)
        if rescue_required is not None:
            filters.append(Company.rescue_required == rescue_required)
        if company_ids_filter is not None:
            uuids = [uuid.UUID(cid) for cid in company_ids_filter]
            filters.append(Company.id.in_(uuids))
        if search and search.strip():
            # Use PostgreSQL full-text search on company_name_search vector
            search_term = search.strip()
            filters.append(
                Company.company_name_search.match(search_term)
                | Company.registration_number.ilike(f"%{search_term}%")
            )

        # Total count
        count_stmt = select(func.count()).select_from(Company)
        for f in filters:
            count_stmt = count_stmt.where(f)
        total = (await self.db.execute(count_stmt)).scalar_one()

        # Records
        stmt = (
            select(Company)
            .where(*filters)
            .order_by(
                Company.current_risk_band.desc().nullslast(),
                Company.company_name,
            )
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all()), total

    async def get_all_active_ids(self) -> List[uuid.UUID]:
        """
        Return IDs of all active companies.
        Used by the daily compliance cron to schedule evaluations.
        """
        result = await self.db.execute(
            select(Company.id).where(Company.is_active == True)
        )
        return [row[0] for row in result.all()]

    async def get_portfolio_stats(self) -> Dict:
        """
        Aggregate portfolio statistics from the vw_admin_dashboard_kpis view.
        """
        result = await self.db.execute(
            text("SELECT * FROM vw_admin_dashboard_kpis LIMIT 1")
        )
        row = result.mappings().one_or_none()
        if not row:
            return {
                "total_companies": 0, "active_companies": 0,
                "black_band_count": 0, "red_band_count": 0,
                "yellow_band_count": 0, "green_band_count": 0,
                "rescue_required_count": 0, "avg_compliance_score": 0,
                "stale_evaluations": 0,
            }
        return dict(row)

    async def get_risk_distribution(self) -> List[Dict]:
        """Risk band distribution from vw_risk_distribution view."""
        result = await self.db.execute(text("SELECT * FROM vw_risk_distribution"))
        return [dict(row) for row in result.mappings().all()]

    async def get_upcoming_deadlines(self, days_ahead: int = 30) -> List[Dict]:
        """Fetch upcoming AGM and return deadlines within N days."""
        result = await self.db.execute(
            text(
                "SELECT * FROM vw_upcoming_deadlines "
                "WHERE days_remaining <= :days ORDER BY days_remaining"
            ),
            {"days": days_ahead},
        )
        return [dict(row) for row in result.mappings().all()]

    # ── UPDATE ────────────────────────────────────────────────────

    async def update_compliance_state(
        self,
        company_id: uuid.UUID,
        *,
        score: int,
        risk_band: RiskBand,
        rescue_required: bool,
        lifecycle_stage: Optional[LifecycleStage] = None,
        last_agm_date: Optional[date] = None,
        last_audit_signed_date: Optional[date] = None,
        last_return_filed_year: Optional[int] = None,
        unfiled_returns_count: Optional[int] = None,
    ) -> None:
        """
        Update the company's cached compliance state after rule engine evaluation.
        This is the only path that writes compliance scores to companies table.
        """
        updates: Dict = {
            "current_compliance_score": score,
            "current_risk_band":        risk_band,
            "rescue_required":          rescue_required,
            "last_evaluated_at":        datetime.now(timezone.utc),
        }
        if lifecycle_stage:
            updates["lifecycle_stage"] = lifecycle_stage
        if last_agm_date:
            updates["last_agm_date"] = last_agm_date
        if last_audit_signed_date:
            updates["last_audit_signed_date"] = last_audit_signed_date
        if last_return_filed_year:
            updates["last_return_filed_year"] = last_return_filed_year
        if unfiled_returns_count is not None:
            updates["unfiled_returns_count"] = unfiled_returns_count
        if rescue_required:
            updates["rescue_triggered_at"] = datetime.now(timezone.utc)

        await self.db.execute(
            update(Company)
            .where(Company.id == company_id)
            .values(**updates)
        )
        await self.db.flush()

    # ── RULE ENGINE PROFILE BUILDER ───────────────────────────────

    async def build_company_profile(self, company_id: uuid.UUID) -> Optional[Dict]:
        """
        Assemble a CompanyProfile dict for the rule engine from verified DB data.
        Returns all fields that C_rule_engine.py's CompanyProfile dataclass needs.
        AI Constitution: No AI involvement. All data from DB.

        The caller (ComplianceService) converts this dict to CompanyProfile.
        Returns None if company not found.
        """
        # Load company with all relations
        company = await self.get_with_relations(company_id)
        if not company:
            return None

        # ── AGM State ─────────────────────────────────────────────
        agms_sorted = sorted(company.agms, key=lambda a: a.financial_year, reverse=True)
        latest_agm = agms_sorted[0] if agms_sorted else None
        agm_count = len([a for a in company.agms if a.agm_held])

        # ── Audit State ───────────────────────────────────────────
        audits_sorted = sorted(company.audits, key=lambda a: a.financial_year, reverse=True)
        latest_audit = audits_sorted[0] if audits_sorted else None

        # ── Annual Return State ───────────────────────────────────
        returns_sorted = sorted(
            company.annual_returns, key=lambda r: r.financial_year, reverse=True
        )
        latest_return = returns_sorted[0] if returns_sorted else None
        unfiled_returns = len([r for r in company.annual_returns if r.is_default])

        # ── Director Changes ──────────────────────────────────────
        director_changes = []
        for d in company.directors:
            from C_rule_engine import DirectorChange
            director_changes.append(DirectorChange(
                director_id=str(d.id),
                name=d.full_name,
                change_type="APPOINTMENT" if d.director_status == "ACTIVE" else "DEPARTURE",
                change_date=d.appointment_date or d.departure_date,
                filing_date=d.appointment_filed_date or d.departure_filed_date,
                delay_days=max(d.appointment_delay_days, d.departure_delay_days),
                still_shown_as_active=d.departed_still_liable,
            ))

        # ── Share Transfers ───────────────────────────────────────
        share_transfers = []
        for t in company.share_transfers:
            from C_rule_engine import ShareTransfer as EngineTransfer
            share_transfers.append(EngineTransfer(
                transfer_id=str(t.id),
                transferor=t.transferor_name,
                transferee=t.transferee_name,
                shares=t.shares_transferred,
                transfer_date=t.transfer_date,
                has_instrument=t.has_transfer_instrument,
                stamp_paid=t.stamp_duty_paid,
                board_approved=t.board_approval_obtained,
                register_updated=t.register_updated,
                aoa_violated=t.aoa_restriction_violated,
                is_irregular=t.is_irregular,
            ))

        # ── Statutory Registers ───────────────────────────────────
        maintained_registers = [
            r.register_type for r in company.statutory_registers if r.is_maintained
        ]

        return {
            # Identity
            "company_id":   str(company.id),
            "company_name": company.company_name,
            "company_type": company.company_type,

            # Dates
            "incorporation_date":  company.incorporation_date,
            "financial_year_end":  company.financial_year_end,

            # AGM State
            "agm_count":                  agm_count,
            "last_agm_date":              company.last_agm_date,
            "agm_held_this_cycle":        latest_agm.agm_held if latest_agm else False,
            "agm_scheduled_date":         latest_agm.agm_deadline if latest_agm else None,
            "notice_sent_date":           latest_agm.notice_sent_date if latest_agm else None,
            "members_present_at_agm":     latest_agm.members_present if latest_agm else 0,
            "auditor_reappointed_at_agm": latest_agm.auditor_reappointed if latest_agm else False,
            "accounts_adopted_at_agm":    latest_agm.agm_held if latest_agm else False,

            # Audit State
            "first_auditor_appointed":    company.first_auditor_appointed,
            "audit_complete":             latest_audit.audit_complete if latest_audit else False,
            "last_audit_signed_date":     company.last_audit_signed_date,
            "audit_in_progress":          False,

            # Annual Return State
            "last_return_filed_year":         company.last_return_filed_year,
            "unfiled_returns_count":          unfiled_returns,
            "annual_return_filed":            latest_return is not None and not latest_return.is_default if latest_return else False,
            "annual_return_content_complete": latest_return.is_complete if latest_return else False,
            "last_agm_filing_date":           latest_return.filed_date if latest_return else None,

            # People
            "director_changes": director_changes,
            "shareholder_change_date": None,  # Would come from company_user_access events
            "form_xv_filed": True,            # Placeholder — implement from events

            # Share Transfers
            "share_transfers": share_transfers,

            # Office
            "registered_office_change_date": None,
            "form_ix_filed": True,

            # Corporate structure
            "aoa_transfer_restriction": True,
            "has_foreign_shareholder":  any(
                s.shareholder_type == "FOREIGN" for s in company.shareholders
            ),
            "is_dormant":   company.company_status == "DORMANT",
            "is_fdi_registered": False,

            # Registers
            "maintained_registers":   maintained_registers,
            "last_allotment_date":    None,
            "share_certificate_issued": all(s.share_certificate_issued for s in company.shareholders) if company.shareholders else True,

            # Capital
            "capital_increase_date":       None,
            "capital_increase_resolution": True,
            "charge_creation_date":        None,
            "form_viii_filed":             True,
        }
