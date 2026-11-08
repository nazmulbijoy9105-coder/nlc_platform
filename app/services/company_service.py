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
from datetime import UTC, date, datetime

from sqlalchemy import func, or_, select, text, update
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.elements import ColumnElement

from app.models.company import Company, CompanyUserAccess
from app.models.charges import CompanyCharge
from app.models.enums import CompanyStatus, CompanyType, LifecycleStage, RevenueTier, RiskBand
from app.models.people import Director, Shareholder
from app.services.base import BaseService


def _agm_profile_evidence(latest_agm) -> dict:
    """Expose AGM facts only when the underlying evidence and reviewer are verified."""
    empty = {
        "agm_held_this_cycle": None,
        "agm_held_this_cycle_verified": False,
        "members_present_at_agm": None,
        "agm_attendance_verified": False,
        "agm_attendance_evidence_ref": None,
        "agm_quorum_required": None,
        "agm_quorum_basis_verified": False,
        "agm_quorum_evidence_ref": None,
        "agm_quorum_met": None,
        "auditor_reappointed_at_agm": None,
        "auditor_reappointment_verified": False,
        "auditor_reappointment_evidence_ref": None,
        "agm_minutes_prepared": None,
        "notice_sent_date": None,
        "agm_notice_verified_absent": None,
        "agm_held_without_audit": None,
        "accounts_adopted_at_agm": None,
        "short_notice_consent_obtained": None,
        "short_notice_consent_verified": False,
        "short_notice_consent_evidence_ref": None,
    }
    if latest_agm is None:
        return empty

    held_verified = (
        getattr(latest_agm, "agm_held_verified", False) is True
        and bool(getattr(latest_agm, "agm_held_evidence_ref", None))
        and getattr(latest_agm, "agm_held_verified_at", None) is not None
        and getattr(latest_agm, "agm_held_verified_by", None) is not None
    )
    attendance_verified = (
        getattr(latest_agm, "members_present_verified", False) is True
        and bool(getattr(latest_agm, "members_present_evidence_ref", None))
        and getattr(latest_agm, "members_present_verified_at", None) is not None
        and getattr(latest_agm, "members_present_verified_by", None) is not None
    )
    quorum_basis_verified = (
        getattr(latest_agm, "quorum_required_verified", False) is True
        and bool(getattr(latest_agm, "quorum_evidence_ref", None))
        and getattr(latest_agm, "quorum_verified_at", None) is not None
        and getattr(latest_agm, "quorum_verified_by", None) is not None
        and getattr(latest_agm, "quorum_required", None) is not None
    )
    quorum_result_verified = (
        held_verified and latest_agm.agm_held is True
        and attendance_verified and quorum_basis_verified
        and getattr(latest_agm, "quorum_met", None) is not None
    )
    auditor_reappointment_verified = (
        getattr(latest_agm, "auditor_reappointment_verified", False) is True
        and bool(getattr(latest_agm, "auditor_reappointment_evidence_ref", None))
        and getattr(latest_agm, "auditor_reappointment_verified_at", None) is not None
        and getattr(latest_agm, "auditor_reappointment_verified_by", None) is not None
    )

    notice_rows = [row for row in getattr(latest_agm, "notice_evidence", []) if row.is_active]
    roster_verified = (
        getattr(latest_agm, "member_register_snapshot_verified", False) is True
        and bool(getattr(latest_agm, "member_register_evidence_ref", None))
        and getattr(latest_agm, "member_register_verified_at", None) is not None
        and getattr(latest_agm, "member_register_verified_by", None) is not None
        and getattr(latest_agm, "entitled_members_count", None) is not None
        and latest_agm.entitled_members_count >= 1
    )
    recipients_complete = (
        roster_verified
        and len(notice_rows) == latest_agm.entitled_members_count
        and all(
            row.entitled_member_verified is True
            and bool(row.entitlement_evidence_ref)
            and row.entitlement_verified_at is not None
            and row.entitlement_verified_by is not None
            for row in notice_rows
        )
    )
    service_verified = (
        recipients_complete
        and all(
            row.notice_verified is True
            and bool(row.notice_evidence_ref)
            and row.notice_verified_at is not None
            and row.notice_verified_by is not None
            for row in notice_rows
        )
    )
    short_notice_consent_verified = (
        recipients_complete
        and all(
            row.consent_verified is True
            and row.consent_given is not None
            and bool(row.consent_evidence_ref)
            and row.consent_verified_at is not None
            and row.consent_verified_by is not None
            for row in notice_rows
        )
    )
    short_notice_consent_obtained = (
        all(row.consent_given is True for row in notice_rows)
        if short_notice_consent_verified else None
    )
    service_exception_valid = service_verified and all(
        row.notice_delivery_status in {"SERVED", "NOT_RECEIVED"}
        or (
            row.notice_delivery_status == "NOT_SERVED"
            and row.omission_verified is True
            and row.omission_accidental is True
            and bool(row.omission_evidence_ref)
            and row.omission_verified_at is not None
            and row.omission_verified_by is not None
        )
        for row in notice_rows
    )
    verified_notice_dates = [
        row.notice_sent_date for row in notice_rows
        if row.notice_delivery_status == "SERVED" and row.notice_sent_date is not None
    ]
    notice_sent_date = (
        max(verified_notice_dates)
        if service_exception_valid and verified_notice_dates else None
    )
    notice_absent = (
        service_verified
        and any(
            row.notice_delivery_status == "NOT_SERVED"
            and not (
                row.omission_verified is True
                and row.omission_accidental is True
                and bool(row.omission_evidence_ref)
                and row.omission_verified_at is not None
                and row.omission_verified_by is not None
            )
            for row in notice_rows
        )
    )

    return {
        "agm_held_this_cycle": latest_agm.agm_held if held_verified else None,
        "agm_held_this_cycle_verified": held_verified,
        "members_present_at_agm": getattr(latest_agm, "members_present", None) if attendance_verified else None,
        "agm_attendance_verified": attendance_verified,
        "agm_attendance_evidence_ref": getattr(latest_agm, "members_present_evidence_ref", None),
        "agm_quorum_required": getattr(latest_agm, "quorum_required", None) if quorum_basis_verified else None,
        "agm_quorum_basis_verified": quorum_basis_verified,
        "agm_quorum_evidence_ref": getattr(latest_agm, "quorum_evidence_ref", None),
        "agm_quorum_met": getattr(latest_agm, "quorum_met", None) if quorum_result_verified else None,
        "auditor_reappointed_at_agm": getattr(latest_agm, "auditor_reappointed", None) if auditor_reappointment_verified else None,
        "auditor_reappointment_verified": auditor_reappointment_verified,
        "auditor_reappointment_evidence_ref": getattr(latest_agm, "auditor_reappointment_evidence_ref", None),
        "agm_minutes_prepared": None,
        "notice_sent_date": notice_sent_date,
        "agm_notice_verified_absent": notice_absent if service_verified else None,
        "agm_held_without_audit": None,
        "accounts_adopted_at_agm": None,
        "short_notice_consent_obtained": short_notice_consent_obtained,
        "short_notice_consent_verified": short_notice_consent_verified,
        "short_notice_consent_evidence_ref": (
            ";".join(row.consent_evidence_ref for row in notice_rows)
            if short_notice_consent_verified else None
        ),
    }


def _charge_event_from_record(charge: CompanyCharge):
    """Map a persisted charge to the engine without promoting unverified reports."""
    from app.rule_engine.engine import ChargeEvent

    creation_verified = bool(
        charge.creation_date_verified and charge.creation_date_evidence_ref
        and charge.creation_date_verified_at and charge.creation_date_verified_by
    )
    form_xviii_verified = bool(
        charge.form_xviii_filing_status_verified and charge.form_xviii_filing_evidence_ref
        and charge.form_xviii_verified_at and charge.form_xviii_verified_by
    )
    registrability_verified = bool(
        charge.registrability_verified and charge.registrability_evidence_ref
        and charge.registrability_verified_at and charge.registrability_verified_by
    )
    satisfaction_verified = bool(
        charge.satisfaction_verified and charge.satisfaction_evidence_ref
        and charge.satisfaction_verified_at and charge.satisfaction_verified_by
    )
    satisfaction_filing_verified = bool(
        charge.satisfaction_filing_status_verified and charge.satisfaction_filing_evidence_ref
        and charge.satisfaction_filing_verified_at and charge.satisfaction_filing_verified_by
    )
    return ChargeEvent(
        charge_id=str(charge.id),
        creation_date=charge.creation_date,
        charge_type=charge.charge_type,
        amount_bdt=float(charge.amount_bdt),
        charge_holder=charge.charge_holder,
        form_xviii_filed=charge.form_xviii_filed if form_xviii_verified else None,
        form_xviii_filed_date=charge.form_xviii_filed_date if form_xviii_verified else None,
        creation_date_verified=creation_verified,
        creation_date_evidence_ref=charge.creation_date_evidence_ref if creation_verified else None,
        form_xviii_filing_status_verified=form_xviii_verified,
        form_xviii_filing_evidence_ref=charge.form_xviii_filing_evidence_ref if form_xviii_verified else None,
        satisfied=charge.satisfied if satisfaction_verified else None,
        satisfaction_date=charge.satisfaction_date if satisfaction_verified else None,
        satisfaction_filed=charge.satisfaction_filed if satisfaction_filing_verified else None,
        satisfaction_filed_date=charge.satisfaction_filed_date if satisfaction_filing_verified else None,
        registrable_under_s159=charge.registrable_under_s159 if registrability_verified else None,
        registrability_verified=registrability_verified,
        registrability_evidence_ref=charge.registrability_evidence_ref if registrability_verified else None,
        satisfaction_verified=satisfaction_verified,
        satisfaction_evidence_ref=charge.satisfaction_evidence_ref if satisfaction_verified else None,
        satisfaction_filing_status_verified=satisfaction_filing_verified,
        satisfaction_filing_evidence_ref=charge.satisfaction_filing_evidence_ref if satisfaction_filing_verified else None,
    )

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
        registered_address: str | None = None,
        industry_sector: str | None = None,
        tin_number: str | None = None,
        authorized_capital_bdt: float | None = None,
        paid_up_capital_bdt: float | None = None,
        assigned_staff_id: uuid.UUID | None = None,
        initial_directors: list[dict] | None = None,
        initial_shareholders: list[dict] | None = None,
        created_by: uuid.UUID | None = None,
        is_manufacturing: bool | None = None,
    ) -> Company:
        """
        Create a new company with optional initial directors and shareholders.
        Triggers full-text search vector via DB trigger.
        """
        # Commercial default: If not provided, default FY end to Dec 31 of incorporation year
        if financial_year_end is None:
            financial_year_end = date(incorporation_date.year, 12, 31)

        company = await self.create(
            registration_number=registration_number.strip().upper(),
            company_name=company_name.strip(),
            company_type=company_type,
            company_status=CompanyStatus.ACTIVE,
            lifecycle_stage=LifecycleStage.INCORPORATION,
            incorporation_date=incorporation_date,
            financial_year_end=financial_year_end,
            registered_address=registered_address,
            register_location="registered_office",
            industry_sector=industry_sector,
            tin_number=tin_number,
            authorized_capital_bdt=authorized_capital_bdt,
            paid_up_capital_bdt=paid_up_capital_bdt,
            assigned_staff_id=assigned_staff_id,
            is_manufacturing=is_manufacturing,
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

    async def get_with_relations(self, company_id: uuid.UUID) -> Company | None:
        """
        Fetch company with all active directors, shareholders, AGMs,
        audits, annual returns, and active compliance flags loaded.
        Used to build the company dashboard view.
        """
        from app.models.filings import AGM

        result = await self.db.execute(
            select(Company)
            .options(
                selectinload(Company.directors),
                selectinload(Company.shareholders),
                selectinload(Company.charges),
                selectinload(Company.agms).selectinload(AGM.notice_evidence),
                selectinload(Company.share_compliance_events),
                selectinload(Company.audits),
                selectinload(Company.annual_returns),
                selectinload(Company.compliance_flags),
                selectinload(Company.rescue_plans),
                selectinload(Company.engagements),
                selectinload(Company.statutory_registers),
            )
            .where(Company.id == company_id)
        )
        return result.scalar_one_or_none()

    async def get_by_registration_number(
        self,
        registration_number: str,
    ) -> Company | None:
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
        risk_band: RiskBand | None = None,
        company_status: CompanyStatus | None = None,
        revenue_tier: RevenueTier | None = None,
        is_dormant: bool | None = None,
        rescue_required: bool | None = None,
        search: str | None = None,
        company_ids_filter: list[str] | None = None,
        user_id: uuid.UUID | None = None,
        include_assigned_staff: bool = False,
    ) -> tuple[list[Company], int]:
        """
        List companies with filters, search, and pagination.
        Returns (companies, total_count).
        company_ids_filter: used for client roles (from JWT).
        search: full-text search on company name or registration number.
        """
        filters: list[ColumnElement[bool]] = [Company.is_active.is_(True)]

        if risk_band:
            filters.append(Company.current_risk_band == risk_band)  # type: ignore
        if company_status:
            filters.append(Company.company_status == company_status)  # type: ignore
        if revenue_tier:
            filters.append(Company.revenue_tier == revenue_tier)  # type: ignore
        if is_dormant is not None:
            dormant_filter = Company.company_status == CompanyStatus.DORMANT
            filters.append(dormant_filter if is_dormant else Company.company_status != CompanyStatus.DORMANT)  # type: ignore
        if rescue_required is not None:
            filters.append(Company.rescue_required == rescue_required)  # type: ignore
        if company_ids_filter is not None:
            uuids = [uuid.UUID(cid) for cid in company_ids_filter]
            filters.append(Company.id.in_(uuids))  # type: ignore
        if user_id is not None:
            accessible_company_ids = select(CompanyUserAccess.company_id).where(
                CompanyUserAccess.user_id == user_id,
                CompanyUserAccess.is_active.is_(True),
            )
            if include_assigned_staff:
                filters.append(
                    or_(
                        Company.assigned_staff_id == user_id,
                        Company.id.in_(accessible_company_ids),
                    )
                )  # type: ignore
            else:
                filters.append(Company.id.in_(accessible_company_ids))  # type: ignore
        if search and search.strip():
            # Use PostgreSQL full-text search on company_name_search vector
            search_term = search.strip()
            filters.append(
                Company.company_name_search.match(search_term)  # type: ignore
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
            .options(selectinload(Company.compliance_flags))
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

    async def get_all_active_ids(self) -> list[uuid.UUID]:
        """
        Return IDs of all active companies.
        Used by the daily compliance cron to schedule evaluations.
        """
        result = await self.db.execute(
            select(Company.id).where(Company.is_active)
        )
        return [row[0] for row in result.all()]

    async def get_portfolio_stats(self) -> dict:
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

    async def get_risk_distribution(self, user_id: uuid.UUID) -> list[dict]:
        """Return risk distribution for companies the user can currently access.

        The global materialized/view aggregate is deliberately not used here:
        aggregation must happen *after* membership filtering.
        """
        if user_id is None:
            raise ValueError("user_id is required for tenant-scoped risk distribution")
        result = await self.db.execute(
            text(
                """
                SELECT
                    c.current_risk_band AS risk_band,
                    COUNT(*) AS company_count,
                    ROUND(
                        COUNT(*) * 100.0 / NULLIF(SUM(COUNT(*)) OVER (), 0),
                        1
                    ) AS percentage
                FROM companies c
                WHERE c.is_active = TRUE
                  AND EXISTS (
                      SELECT 1
                      FROM company_user_access cua
                      WHERE cua.company_id = c.id
                        AND cua.user_id = :user_id
                        AND cua.is_active = TRUE
                  )
                GROUP BY c.current_risk_band
                ORDER BY CASE c.current_risk_band
                    WHEN 'BLACK' THEN 1
                    WHEN 'RED' THEN 2
                    WHEN 'YELLOW' THEN 3
                    WHEN 'GREEN' THEN 4
                    ELSE 5
                END
                """
            ),
            {"user_id": str(user_id)},
        )
        return [dict(row) for row in result.mappings().all()]

    async def get_upcoming_deadlines(
        self, days_ahead: int = 30, user_id: uuid.UUID | None = None
    ) -> list[dict]:
        """Return deadlines scoped to active memberships; no implicit global mode."""
        if user_id is None:
            raise ValueError(
                "user_id is required; use get_upcoming_deadlines_for_system for worker scans"
            )
        result = await self.db.execute(
            text(
                """
                SELECT d.*
                FROM vw_upcoming_deadlines d
                WHERE d.days_remaining <= :days
                  AND EXISTS (
                      SELECT 1
                      FROM company_user_access cua
                      WHERE cua.company_id = d.company_id
                        AND cua.user_id = :user_id
                        AND cua.is_active = TRUE
                  )
                ORDER BY d.days_remaining
                """
            ),
            {"days": days_ahead, "user_id": str(user_id)},
        )
        return [dict(row) for row in result.mappings().all()]

    async def get_risk_distribution(
        self, user_id: uuid.UUID, *, include_assigned_staff: bool = False
    ) -> list[dict]:
        """Return risk aggregates after filtering to the caller's company scope."""
        result = await self.db.execute(
            text(
                """
                SELECT
                    c.current_risk_band AS risk_band,
                    COUNT(*) AS company_count,
                    ROUND(
                        COUNT(*) * 100.0 / NULLIF(SUM(COUNT(*)) OVER (), 0),
                        1
                    ) AS percentage
                FROM companies c
                WHERE c.is_active IS TRUE
                  AND (
                      (:include_assigned_staff IS TRUE AND c.assigned_staff_id = :user_id)
                      OR EXISTS (
                          SELECT 1
                          FROM company_user_access cua
                          WHERE cua.company_id = c.id
                            AND cua.user_id = :user_id
                            AND cua.is_active IS TRUE
                      )
                  )
                GROUP BY c.current_risk_band
                ORDER BY CASE c.current_risk_band
                    WHEN 'BLACK' THEN 1
                    WHEN 'RED' THEN 2
                    WHEN 'YELLOW' THEN 3
                    WHEN 'GREEN' THEN 4
                    ELSE 5
                END
                """
            ),
            {"user_id": str(user_id), "include_assigned_staff": include_assigned_staff},
        )
        return [dict(row) for row in result.mappings().all()]

    async def get_upcoming_deadlines(
        self,
        days_ahead: int = 30,
        user_id: uuid.UUID | None = None,
        *,
        include_assigned_staff: bool = False,
    ) -> list[dict]:
        """Return deadlines scoped to active company memberships."""
        if user_id is None:
            raise ValueError(
                "user_id is required; use get_upcoming_deadlines_for_system for worker scans"
            )
        result = await self.db.execute(
            text(
                """
                SELECT d.*
                FROM vw_upcoming_deadlines d
                WHERE d.days_remaining <= :days
                  AND (
                      (:include_assigned_staff IS TRUE AND EXISTS (
                          SELECT 1 FROM companies c
                          WHERE c.id = d.company_id
                            AND c.assigned_staff_id = :user_id
                      ))
                      OR EXISTS (
                          SELECT 1
                          FROM company_user_access cua
                          WHERE cua.company_id = d.company_id
                            AND cua.user_id = :user_id
                            AND cua.is_active IS TRUE
                      )
                  )
                ORDER BY d.days_remaining
                """
            ),
            {
                "days": days_ahead,
                "user_id": str(user_id),
                "include_assigned_staff": include_assigned_staff,
            },
        )
        return [dict(row) for row in result.mappings().all()]

    async def get_upcoming_deadlines_for_system(
        self, days_ahead: int = 30
    ) -> list[dict]:
        """Privileged worker-only global deadline scan; never expose via user API."""
        if days_ahead < 0:
            raise ValueError("days_ahead must be non-negative")
        result = await self.db.execute(
            text(
                """
                SELECT d.*
                FROM vw_upcoming_deadlines d
                WHERE public.nlc_current_user_principal() = 'ADMIN'
                  AND d.days_remaining BETWEEN 0 AND :days
                ORDER BY d.days_remaining
                """
            ),
            {"days": days_ahead},
        )
        return [dict(row) for row in result.mappings().all()]

    async def update_compliance_state(
        self,
        company_id: uuid.UUID,
        *,
        score: int,
        risk_band: RiskBand,
        rescue_required: bool,
        lifecycle_stage: LifecycleStage | None = None,
        last_agm_date: date | None = None,
        last_audit_signed_date: date | None = None,
        last_return_filed_year: int | None = None,
        unfiled_returns_count: int | None = None,
    ) -> None:
        """
        Update the company's cached compliance state after rule engine evaluation.
        This is the only path that writes compliance scores to companies table.
        """
        updates: dict = {
            "current_compliance_score": score,
            "current_risk_band":        risk_band,
            "rescue_required":          rescue_required,
            "last_evaluated_at":        datetime.now(UTC),
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
            updates["rescue_triggered_at"] = datetime.now(UTC)

        await self.db.execute(
            update(Company)
            .where(Company.id == company_id)
            .values(**updates)
        )
        await self.db.flush()

    # ── RULE ENGINE PROFILE BUILDER ───────────────────────────────

    async def build_company_profile(self, company_id: uuid.UUID) -> dict | None:
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
        active_agms = [row for row in company.agms if row.is_active]
        history_marker_verified = (
            company.agm_history_verified is True
            and bool(company.agm_history_evidence_ref)
            and company.agm_history_verified_at is not None
            and company.agm_history_verified_by is not None
        )
        all_cycle_statuses_verified = all(
            row.agm_held_verified is True
            and bool(row.agm_held_evidence_ref)
            and row.agm_held_verified_at is not None
            and row.agm_held_verified_by is not None
            for row in active_agms
        )
        agm_history_verified = history_marker_verified and all_cycle_statuses_verified
        verified_held_agms = [
            row for row in active_agms
            if row.agm_held is True
            and row.agm_held_verified is True
            and bool(row.agm_held_evidence_ref)
            and row.agm_held_verified_at is not None
            and row.agm_held_verified_by is not None
            and row.agm_date is not None
        ]
        agm_count = len(verified_held_agms) if agm_history_verified else None
        last_verified_agm_date = (
            max((row.agm_date for row in verified_held_agms), default=None)
            if agm_history_verified else None
        )

        annual_agms = [row for row in active_agms if row.agm_type in {"ANNUAL", "FIRST"}]
        latest_financial_year = max((row.financial_year for row in annual_agms), default=None)
        latest_year_rows = [
            row for row in annual_agms if row.financial_year == latest_financial_year
        ]
        latest_agm = latest_year_rows[0] if len(latest_year_rows) == 1 else None
        current_year_rows = [
            row for row in annual_agms
            if row.financial_year == date.today().year and row.agm_type == "ANNUAL"
        ]
        current_cycle_agm = current_year_rows[0] if len(current_year_rows) == 1 else None
        current_cycle_verified = bool(
            current_cycle_agm is not None
            and current_cycle_agm.agm_held_verified is True
            and current_cycle_agm.agm_held_evidence_ref
            and current_cycle_agm.agm_held_verified_at is not None
            and current_cycle_agm.agm_held_verified_by is not None
        )

        # ── Audit State ───────────────────────────────────────────
        audits_sorted = sorted(company.audits, key=lambda a: a.financial_year, reverse=True)
        latest_audit = audits_sorted[0] if audits_sorted else None

        agm_profile_evidence = _agm_profile_evidence(latest_agm)

        # ── Annual Return State ───────────────────────────────────
        returns_sorted = sorted(
            company.annual_returns, key=lambda r: r.financial_year, reverse=True
        )
        latest_return = returns_sorted[0] if returns_sorted else None
        unfiled_returns = len([r for r in company.annual_returns if r.is_default])

        # ── Director Changes ──────────────────────────────────────
        director_changes = []
        for d in company.directors:
            from app.rule_engine import DirectorChange
            form_xii_verified = bool(
                d.form_xii_status_verified
                and d.form_xii_filed is not None
                and d.form_xii_evidence_ref
                and d.form_xii_verified_at
                and d.form_xii_verified_by
            )
            consent_verified = bool(
                d.consent_verified
                and d.consent_filed is not None
                and d.consent_evidence_ref
                and d.consent_verified_at
                and d.consent_verified_by
            )
            director_changes.append(DirectorChange(
                director_id=str(d.id),
                event_type="appointment" if d.director_status.value == "ACTIVE" else "resignation",
                event_date=d.appointment_date or d.departure_date or date.today(),
                form_filed=d.form_xii_filed if form_xii_verified else None,
                form_filed_date=d.form_xii_filed_date if form_xii_verified else None,
                form_type="XII",
                form_filed_verified=form_xii_verified,
                form_filed_evidence_ref=d.form_xii_evidence_ref if form_xii_verified else None,
                consent_filed=d.consent_filed if consent_verified else None,
                consent_filed_date=d.consent_filed_date if consent_verified else None,
                consent_verified=consent_verified,
                consent_evidence_ref=d.consent_evidence_ref if consent_verified else None,
            ))

        # ── Share Compliance Events ───────────────────────────────
        from app.rule_engine.engine import ShareComplianceEventEvidence

        share_compliance_events = []
        for event in company.share_compliance_events:
            if not event.is_active:
                continue
            event_verified = bool(
                event.event_verified
                and event.event_evidence_ref
                and event.event_verified_at
                and event.event_verified_by
            )
            filing_verified = bool(
                event_verified
                and event.filing_status_verified
                and event.filing_status is not None
                and event.filing_evidence_ref
                and event.filing_verified_at
                and event.filing_verified_by
            )
            certificate_verified = bool(
                event_verified
                and event.certificate_status_verified
                and event.certificate_issued is not None
                and event.certificate_evidence_ref
                and event.certificate_verified_at
                and event.certificate_verified_by
            )
            share_compliance_events.append(ShareComplianceEventEvidence(
                event_reference=event.event_reference,
                event_type=event.event_type,
                event_date=event.event_date,
                event_verified=event_verified,
                event_evidence_ref=event.event_evidence_ref if event_verified else None,
                filing_form=event.filing_form if filing_verified else None,
                filing_status=event.filing_status if filing_verified else None,
                filing_status_verified=filing_verified,
                filing_date=event.filing_date if filing_verified else None,
                filing_evidence_ref=event.filing_evidence_ref if filing_verified else None,
                certificate_issued=event.certificate_issued if certificate_verified else None,
                certificate_status_verified=certificate_verified,
                certificate_issue_date=event.certificate_issue_date if certificate_verified else None,
                certificate_evidence_ref=event.certificate_evidence_ref if certificate_verified else None,
            ))

        # ── Share Transfers ───────────────────────────────────────
        # Only evidence-bound statuses are passed to the deterministic engine.
        share_transfers = []
        for t in company.share_transfers:
            from app.rule_engine import ShareTransfer as EngineTransfer
            instrument_verified = bool(
                t.transfer_instrument_verified and t.transfer_instrument_evidence_ref
            )
            stamp_verified = bool(
                t.stamp_duty_applicability_verified and t.stamp_duty_evidence_ref
            )
            board_verified = bool(t.board_approval_verified and t.board_approval_evidence_ref)
            registration_verified = bool(
                t.transfer_registered is not None and t.transfer_registration_evidence_ref
            )
            refusal_verified = bool(
                t.registration_refusal_verified and t.refusal_decision_evidence_ref
            )
            refusal_notice_verified = bool(
                t.refusal_notice_verified and t.refusal_notice_evidence_ref
            )
            lodgement_verified = bool(
                t.instrument_lodged_date and t.instrument_lodgement_evidence_ref
            )
            articles_verified = bool(t.aoa_restriction_apply is not None and t.articles_clause_evidence_ref)
            share_transfers.append(EngineTransfer(
                transfer_id=str(t.id),
                transfer_date=t.transfer_date,  # type: ignore
                instrument_recorded=t.has_transfer_instrument if instrument_verified else None,
                form_117_filed=t.form_117_filed if instrument_verified and t.form_117_evidence_ref else None,
                stamp_duty_paid=t.stamp_duty_paid if stamp_verified else None,
                stamp_duty_applicability_verified=stamp_verified,
                stamp_duty_amount=float(t.stamp_duty_amount_bdt) if t.stamp_duty_amount_bdt else None,
                board_approval=t.board_approval_obtained if board_verified else None,
                board_approval_obtained=t.board_approval_obtained if board_verified else None,
                share_register_updated=t.register_updated if t.register_update_verified and t.register_update_evidence_ref else None,
                aoa_restriction_apply=t.aoa_restriction_apply if articles_verified else None,
                transfer_registered=t.transfer_registered if registration_verified else None,
                registration_refused=t.registration_refused if refusal_verified else None,
                refusal_notice_sent=t.refusal_notice_sent if refusal_notice_verified else None,
                instrument_lodged_date=t.instrument_lodged_date if lodgement_verified else None,
                articles_clause_evidence_ref=t.articles_clause_evidence_ref if articles_verified else None,
                refusal_decision_evidence_ref=t.refusal_decision_evidence_ref if refusal_verified else None,
                transfer_registration_evidence_ref=t.transfer_registration_evidence_ref if registration_verified else None,
            ))

        # ── Mortgage / charge evidence ─────────────────────────────
        charge_events = [
            _charge_event_from_record(charge)
            for charge in company.charges
            if charge.is_active
        ]

        # ── Statutory Registers ───────────────────────────────────
        maintained_registers = [
            r.register_type for r in company.statutory_registers if r.is_maintained
        ]

        profile = {
            # Identity
            "company_id":   str(company.id),
            "company_name": company.company_name,
            "company_type": company.company_type,
            "charges": charge_events,

            # Dates
            "incorporation_date":  company.incorporation_date,
            "financial_year_end":  company.financial_year_end,

            # AGM State
            "agm_count": agm_count,
            "last_agm_date": last_verified_agm_date,
            "agm_history_verified": agm_history_verified,
            "agm_history_evidence_ref": company.agm_history_evidence_ref if agm_history_verified else None,
            "agm_history_verified_at": company.agm_history_verified_at.date() if agm_history_verified else None,
            "agm_history_verified_by": str(company.agm_history_verified_by) if agm_history_verified else None,
            "agm_extension_granted_until": company.agm_extension_granted_until,
            "agm_extension_application_date": company.agm_extension_application_date,
            "agm_extension_verified": (
                company.agm_extension_verified is True
                and bool(company.agm_extension_evidence_ref)
                and company.agm_extension_verified_at is not None
                and company.agm_extension_verified_by is not None
            ),
            "agm_extension_evidence_ref": company.agm_extension_evidence_ref,
            "agm_extension_verified_at": company.agm_extension_verified_at.date() if company.agm_extension_verified_at else None,
            "agm_extension_verified_by": str(company.agm_extension_verified_by) if company.agm_extension_verified_by else None,
            "agm_held_this_cycle": (
                current_cycle_agm.agm_held if current_cycle_verified else None
            ),
            "agm_minutes_prepared":       agm_profile_evidence["agm_minutes_prepared"],

            # Audit State
            "first_auditor_appointed": (
                bool(company.first_auditor_appointed)
                if (
                    company.first_auditor_appointment_verified is True
                    and bool(company.first_auditor_appointment_evidence_ref)
                    and company.first_auditor_appointment_verified_at is not None
                    and company.first_auditor_appointment_verified_by is not None
                    and company.first_auditor_appointed is not None
                ) else None
            ),
            "first_auditor_appointment_verified": (
                company.first_auditor_appointment_verified is True
                and bool(company.first_auditor_appointment_evidence_ref)
                and company.first_auditor_appointment_verified_at is not None
                and company.first_auditor_appointment_verified_by is not None
            ),
            "first_auditor_appointment_evidence_ref": company.first_auditor_appointment_evidence_ref,
            "first_auditor_appointment_verified_at": company.first_auditor_appointment_verified_at.date() if company.first_auditor_appointment_verified_at else None,
            "first_auditor_appointment_verified_by": str(company.first_auditor_appointment_verified_by) if company.first_auditor_appointment_verified_by else None,
            "audit_complete": (
                latest_audit.audit_complete
                if (
                    latest_audit
                    and latest_audit.audit_completion_verified is True
                    and bool(latest_audit.audit_completion_evidence_ref)
                    and latest_audit.audit_completion_verified_at is not None
                    and latest_audit.audit_completion_verified_by is not None
                ) else None
            ),
            "audit_completion_verified": bool(
                latest_audit
                and latest_audit.audit_completion_verified is True
                and latest_audit.audit_completion_evidence_ref
                and latest_audit.audit_completion_verified_at is not None
                and latest_audit.audit_completion_verified_by is not None
            ),
            "audit_completion_evidence_ref": latest_audit.audit_completion_evidence_ref if latest_audit else None,
            "audit_completion_verified_at": latest_audit.audit_completion_verified_at.date() if latest_audit and latest_audit.audit_completion_verified_at else None,
            "audit_completion_verified_by": str(latest_audit.audit_completion_verified_by) if latest_audit and latest_audit.audit_completion_verified_by else None,
            "last_audit_signed_date":     company.last_audit_signed_date,

            # Annual Return State
            "last_return_filed_year":         company.last_return_filed_year,
            "unfiled_returns_count":          unfiled_returns,
            "annual_return_filed":            (latest_return is not None and not latest_return.is_default) if latest_return else None,
            "annual_return_content_complete": latest_return.is_complete if latest_return else None,
            "annual_return_filed_date":       latest_return.filed_date if latest_return else None,

            # People
            "director_changes": director_changes,

            # Share Transfers
            "share_transfers": share_transfers,
            "share_compliance_events": share_compliance_events,

            # Office

            # Corporate structure

            # Registers
            "maintained_registers":   maintained_registers,

            # Capital
            "authorized_capital_bdt":       float(company.authorized_capital_bdt) if company.authorized_capital_bdt else 0.0,
            "paid_up_capital_bdt":          float(company.paid_up_capital_bdt) if company.paid_up_capital_bdt else 0.0,
            "capital_increase_date":       None,  # unverified event date; legal engine remains NOT_EVALUATED
            "capital_increase_resolution": getattr(company, "capital_increase_resolution", None),
            "charges":                     [],
            # form_viii_filed removed — not a CompanyProfile field

            # Tax & director fields — prevent false positives
            "tin_obtained":            True if getattr(company, "tin_number", None) else None,
            "tin_number":              company.tin_number,
            "vat_registered":          True if getattr(company, "vat_number", None) else None,
            "vat_number":              getattr(company, "vat_number", None),
            # Tax Compliance v3
            "trade_license_obtained":       getattr(company, "trade_license_obtained", None),
            "trade_license_expiry":         company.trade_license_expiry,
            "tax_return_filed_for_current_fy": company.tax_return_filed_for_current_fy,
            "advance_tax_q1_paid":          company.advance_tax_q1_paid,
            "advance_tax_q2_paid":          company.advance_tax_q2_paid,
            "advance_tax_q3_paid":          company.advance_tax_q3_paid,
            "advance_tax_q4_paid":          company.advance_tax_q4_paid,
            "tds_deposited_up_to_date":     company.tds_deposited_up_to_date,
            "last_tds_deposit_date":        company.last_tds_deposit_date,
            "last_vat_return_filed":        company.last_vat_return_filed,
            "vat_annual_return_filed_for_fy": company.vat_annual_return_filed_for_fy,
            "minimum_tax_paid":             company.minimum_tax_paid,
            "tax_clearance_obtained":       company.tax_clearance_obtained,
            "tax_return_deadline_extended": company.tax_return_deadline_extended,
            # Enforcement
            "any_director_disqualified":    company.any_director_disqualified,
            "disqualification_details": list(company.disqualification_details or []),
            "penalty_notices_received":     company.penalty_notices_received,
            "penalty_notices_resolved":     company.penalty_notices_resolved,
            "current_director_count": len([d for d in company.directors if d.director_status.value == "ACTIVE"]) if company.directors is not None else None,
            "directors_verified": (
                company.directors_verified is True
                and bool(company.directors_verification_evidence_ref)
                and company.directors_verified_at is not None
                and company.directors_verified_by is not None
            ),
            "directors_verification_evidence_ref": company.directors_verification_evidence_ref,
            "directors_verified_at": company.directors_verified_at.date() if company.directors_verified_at else None,
            "directors_verified_by": str(company.directors_verified_by) if company.directors_verified_by else None,
            "is_private_subsidiary_of_public_company": (
                company.is_private_subsidiary_of_public_company
                if (
                    company.subsidiary_status_verified is True
                    and bool(company.subsidiary_status_evidence_ref)
                    and company.subsidiary_status_verified_at is not None
                    and company.subsidiary_status_verified_by is not None
                    and company.is_private_subsidiary_of_public_company is not None
                ) else None
            ),
            "subsidiary_status_verified": (
                company.subsidiary_status_verified is True
                and bool(company.subsidiary_status_evidence_ref)
                and company.subsidiary_status_verified_at is not None
                and company.subsidiary_status_verified_by is not None
            ),
            "subsidiary_status_evidence_ref": company.subsidiary_status_evidence_ref,
            "subsidiary_status_verified_at": company.subsidiary_status_verified_at.date() if company.subsidiary_status_verified_at else None,
            "subsidiary_status_verified_by": str(company.subsidiary_status_verified_by) if company.subsidiary_status_verified_by else None,

            # BSEC Corporate Governance
            "bsec_listed":                   getattr(company, "bsec_listed", False),
            "bsec_quarterly_report_filed":  getattr(company, "bsec_quarterly_report_filed", False),
            "cg_certificate_obtained":     getattr(company, "cg_certificate_obtained", False),
            "board_independent_director":   getattr(company, "board_independent_director", False),
            "audit_committee_established":  getattr(company, "audit_committee_established", False),

            # Labour Compliance
            "is_manufacturing":             company.is_manufacturing,
            "factory_license_obtained":     getattr(company, "factory_license_obtained", None),
            "factory_license_expiry":       getattr(company, "factory_license_expiry", None),
            "labour_court_order_pending":   getattr(company, "labour_court_order_pending", False),
            "worker_compensation_filed":    getattr(company, "worker_compensation_filed", False),

            # Bankruptcy / Winding Up
            "winding_up_petition_filed":    getattr(company, "winding_up_petition_filed", False),
            "winding_up_petition_date":     getattr(company, "winding_up_petition_date", None),
            "liquidator_appointed":         getattr(company, "liquidator_appointed", False),
            "court_ordered_winding_up":     getattr(company, "court_ordered_winding_up", False),
            "voluntary_winding_up":         getattr(company, "voluntary_winding_up", False),

            # Escalation / Strike-Off
            "on_rjsc_strike_off_list":      getattr(company, "on_rjsc_strike_off_list", False),
            "rjsc_strike_off_notice_date":  getattr(company, "rjsc_strike_off_notice_date", None),
            "rjsc_status":                  getattr(company, "rjsc_status", None),
            "last_rjsc_compliance_date":    getattr(company, "last_rjsc_compliance_date", None),
            "investigation_order":          getattr(company, "investigation_order", False),

            # Foreign Exchange / FDI
            "foreign_exchange_violation":    getattr(company, "foreign_exchange_violation", False),
            "encashment_certificate_uploaded": getattr(company, "encashment_certificate_uploaded", False),
            "encashment_certificate_date":  getattr(company, "encashment_certificate_date", None),
            "bida_registered":              getattr(company, "bida_registered", False),
            "fdi_registration_date":        getattr(company, "fdi_registration_date", None),
            "remittance_amount_usd":        float(getattr(company, "remittance_amount_usd", None) or 0),
            "foreign_shareholding_pct":     float(getattr(company, "foreign_shareholding_pct", None) or 0),

            # RJSC Form Filings
            "form_iii_filed":               getattr(company, "form_iii_filed", False),
            "form_iii_filed_date":          getattr(company, "form_iii_filed_date", None),
            "form_iv_filed":                None,  # no evidence-bound Form IV status yet
            "form_iv_filed_date":           None,
            "form_vi_filed":                getattr(company, "form_vi_filed", None),
            "form_vi_filed_date":           getattr(company, "form_vi_filed_date", None),
            "form_xv_filed":                None,  # no evidence-bound Form XV status yet
            "form_xv_filed_date":           None,

            # Annual Return Attachments
            "balance_sheet_attached":       getattr(company, "balance_sheet_attached", False),
            "schedule_x_attached":          getattr(company, "schedule_x_attached", False),
            "directors_list_attached":      getattr(company, "directors_list_attached", False),
            "shareholders_list_attached":   getattr(company, "shareholders_list_attached", False),
            "profit_loss_attached":         getattr(company, "profit_loss_attached", False),

            # Capital / Resolutions
            "special_resolution_filed":     getattr(company, "special_resolution_filed", False),
            "special_resolution_date":      getattr(company, "special_resolution_date", None),
            "special_resolution_filed_date": getattr(company, "special_resolution_filed_date", None),
            "capital_reduction_pending":    getattr(company, "capital_reduction_pending", False),
            "capital_reduction_date":       getattr(company, "capital_reduction_date", None),
            "capital_reduction_court_order_obtained": getattr(company, "capital_reduction_court_order_obtained", False),
            "paid_up_ge_authorized":        getattr(company, "paid_up_ge_authorized", False),

            # Corporate Structure Changes
            "moa_aoa_filed":                getattr(company, "moa_aoa_filed", None),
            "moa_aoa_verified": (
                company.moa_aoa_verified is True
                and bool(company.moa_aoa_evidence_ref)
                and company.moa_aoa_verified_at is not None
                and company.moa_aoa_verified_by is not None
            ),
            "moa_aoa_evidence_ref": company.moa_aoa_evidence_ref,
            "moa_aoa_verified_at": company.moa_aoa_verified_at.date() if company.moa_aoa_verified_at else None,
            "moa_aoa_verified_by": str(company.moa_aoa_verified_by) if company.moa_aoa_verified_by else None,
            "name_change_pending":          getattr(company, "name_change_pending", False),
            "name_change_date":             getattr(company, "name_change_date", None),
            "name_change_sr_passed":         getattr(company, "name_change_sr_passed", False),
            "object_clause_change_pending": getattr(company, "object_clause_change_pending", False),
            "object_clause_change_date":    getattr(company, "object_clause_change_date", None),
            "aoa_alteration_pending":       getattr(company, "aoa_alteration_pending", False),
            "aoa_alteration_date":          getattr(company, "aoa_alteration_date", None),

            # Statutory Registers
            "register_of_members_maintained": getattr(company, "register_of_members_maintained", None),
            "register_of_directors_maintained": getattr(company, "register_of_directors_maintained", None),
            "register_of_charges_maintained": getattr(company, "register_of_charges_maintained", None),
            "register_of_contracts":        getattr(company, "register_of_contracts", True),
            "register_of_directors_interests": getattr(company, "register_of_directors_interests", None),
            "register_location":            getattr(company, "register_location", None),
            "minutes_book_agm_maintained":  getattr(company, "minutes_book_agm_maintained", True),
            "minutes_book_board_maintained": getattr(company, "minutes_book_board_maintained", True),

            # AGM Details
            "agm_adjourned_without_notice":  getattr(company, "agm_adjourned_without_notice", False),
            "agm_scheduled_date":            getattr(company, "agm_scheduled_date", None),
            "notice_sent_date":              agm_profile_evidence["notice_sent_date"],
            "short_notice_consent_obtained": agm_profile_evidence.get("short_notice_consent_obtained"),
            "short_notice_consent_verified": agm_profile_evidence.get("short_notice_consent_verified", False),
            "short_notice_consent_evidence_ref": agm_profile_evidence.get("short_notice_consent_evidence_ref"),
            "members_present_at_agm":        agm_profile_evidence["members_present_at_agm"],
            "agm_attendance_verified":       agm_profile_evidence.get("agm_attendance_verified", False),
            "agm_attendance_evidence_ref":   agm_profile_evidence.get("agm_attendance_evidence_ref"),
            "agm_quorum_required":           agm_profile_evidence.get("agm_quorum_required"),
            "agm_quorum_basis_verified":     agm_profile_evidence.get("agm_quorum_basis_verified", False),
            "agm_quorum_evidence_ref":       agm_profile_evidence.get("agm_quorum_evidence_ref"),
            "auditor_reappointed_at_agm":    agm_profile_evidence["auditor_reappointed_at_agm"],
            "auditor_reappointment_verified": agm_profile_evidence.get("auditor_reappointment_verified", False),
            "auditor_reappointment_evidence_ref": agm_profile_evidence.get("auditor_reappointment_evidence_ref"),
            "accounts_adopted_at_agm":       getattr(company, "accounts_adopted_at_agm", None),

            # Audit Details
            "audit_in_progress":             getattr(company, "audit_in_progress", False),
            "first_auditor_appointment_date": getattr(company, "first_auditor_appointment_date", None),
            "auditor_name":                  getattr(company, "auditor_name", None),
            "auditor_firm_reg_no":           getattr(company, "auditor_firm_reg_no", None),

            # Financial
            "annual_turnover_bdt":          float(getattr(company, "annual_turnover_bdt", None) or 0),
            "last_tax_return_filed_year":   getattr(company, "last_tax_return_filed_year", None),

            # Shareholders
            "share_certificates_issued":     None,  # no evidence-bound certificate status yet
            "share_certificates_issued_date": None,

            # Misc
            "is_dormant":                    getattr(company, "is_dormant", False),
            "aoa_transfer_restriction":       getattr(company, "aoa_transfer_restriction", False),
            "is_fdi_registered":              getattr(company, "is_fdi_registered", False),
            "last_allotment_date":            None,  # no authenticated allotment event provenance yet
            "registered_office_change_date":  getattr(company, "registered_office_change_date", None),
            "shareholder_change_date":        getattr(company, "shareholder_change_date", None),
            "has_foreign_shareholder":       getattr(company, "has_foreign_shareholder", False),
            "capital_increase_special_resolution": None,  # legacy assertion; resolution type requires Articles/source review
            "minimum_directors_met":        getattr(company, "minimum_directors_met", False),
            "registered_office_address":    getattr(company, "registered_office_address", None),

        }

        # Capital: set only when BOTH are recorded; a single NULL must not become 0.0
        if company.authorized_capital_bdt is not None and company.paid_up_capital_bdt is not None:
            profile["authorized_capital_bdt"] = float(company.authorized_capital_bdt)
            profile["paid_up_capital_bdt"] = float(company.paid_up_capital_bdt)
        # ── 0027: DEAD rule inputs (from new DB columns) ─────────────
        profile.update({
            "moa_aoa_filed": getattr(company, "moa_aoa_filed", None),
            "capital_reduction_pending": getattr(company, "capital_reduction_pending", None),
            "special_resolution_date": company.special_resolution_date,
            "special_resolution_filed": getattr(company, "special_resolution_filed", None),
            "register_of_directors_interests": getattr(company, "register_of_directors_interests", None),
            "register_of_contracts": getattr(company, "register_of_contracts", None),
            "winding_up_petition_filed": getattr(company, "winding_up_petition_filed", None),
            "liquidator_appointed": getattr(company, "liquidator_appointed", None),
            "court_ordered_winding_up": getattr(company, "court_ordered_winding_up", None),
            "voluntary_winding_up": getattr(company, "voluntary_winding_up", None),
            "investigation_order": getattr(company, "investigation_order", None),
            "factory_license_obtained": getattr(company, "factory_license_obtained", None),
            "factory_license_expiry": company.factory_license_expiry,
            "labour_court_order_pending": getattr(company, "labour_court_order_pending", None),
            "bsec_listed": getattr(company, "bsec_listed", None),
            "bsec_quarterly_report_filed": getattr(company, "bsec_quarterly_report_filed", None),
            "cg_certificate_obtained": getattr(company, "cg_certificate_obtained", None),
            "board_independent_director": getattr(company, "board_independent_director", None),
            "audit_committee_established": getattr(company, "audit_committee_established", None),
            "agm_adjourned_without_notice": getattr(company, "agm_adjourned_without_notice", None),
            "name_change_pending": getattr(company, "name_change_pending", None),
            "name_change_date": company.name_change_date,
            "name_change_sr_passed": company.name_change_sr_passed,
            "object_clause_change_pending": getattr(company, "object_clause_change_pending", None),
            "object_clause_change_date": company.object_clause_change_date,
            "aoa_alteration_pending": getattr(company, "aoa_alteration_pending", None),
            "aoa_alteration_date": company.aoa_alteration_date,
            "foreign_exchange_violation": getattr(company, "foreign_exchange_violation", None),
            "annual_turnover_bdt": float(company.annual_turnover_bdt) if company.annual_turnover_bdt else 0.0,
        })

        # ── 0028: Remaining compliance fields + derived fields ──
        profile.update({
            # AR-004 attachments
            "balance_sheet_attached": company.balance_sheet_attached,
            "directors_list_attached": company.directors_list_attached,
            "profit_loss_attached": company.profit_loss_attached,
            "schedule_x_attached": company.schedule_x_attached,
            "shareholders_list_attached": company.shareholders_list_attached,
            # FDI / Foreign shareholding
            "has_foreign_shareholder": company.has_foreign_shareholder,
            "foreign_shareholding_pct": float(company.foreign_shareholding_pct) if company.foreign_shareholding_pct else 0.0,
            "encashment_certificate_uploaded": company.encashment_certificate_uploaded,
            "encashment_certificate_date": company.encashment_certificate_date,
            "bida_registered": company.bida_registered,
            "is_fdi_registered": company.is_fdi_registered,
            "fdi_registration_date": company.fdi_registration_date,
            "remittance_amount_usd": float(company.remittance_amount_usd) if company.remittance_amount_usd else 0.0,
            # Form filing status
            "form_iii_filed": None,
            "form_iv_filed": None,
            # RJSC strike-off
            "rjsc_status": company.rjsc_status or "ACTIVE",
            "rjsc_strike_off_notice_date": company.rjsc_strike_off_notice_date,
            "last_rjsc_compliance_date": company.last_rjsc_compliance_date,
            # Director disqualification + penalties
            "any_director_disqualified": company.any_director_disqualified,
            "disqualification_details": company.disqualification_details or [],
            "penalty_notices_received": company.penalty_notices_received or 0,
            "penalty_notices_resolved": company.penalty_notices_resolved or 0,
            # Capital reduction
            "capital_reduction_date": company.capital_reduction_date,
            "capital_reduction_court_order_obtained": company.capital_reduction_court_order_obtained,
            # Winding up
            "winding_up_petition_date": company.winding_up_petition_date,
            # Derived fields (no DB column needed)
            "tin_obtained": bool(company.tin_number) if company.tin_number is not None else None,
            "vat_registered": bool(company.vat_number) if company.vat_number is not None else None,
            "annual_return_filed": bool(company.last_return_filed_year) if company.last_return_filed_year is not None else None,
        })

        # ── 0031: Board/Accounts/Director extended fields ──
        profile.update({
            "last_board_meeting_date": company.last_board_meeting_date,
            "board_meeting_notice_given": company.board_meeting_notice_given,
            "board_minutes_prepared": company.board_minutes_prepared,
            "financial_statements_presented": company.financial_statements_presented,
            "financial_statements_filed": company.financial_statements_filed,
            "books_of_account_kept": company.books_of_account_kept,
            "director_consent_filed": company.director_consent_filed,
            "director_office_of_profit": company.director_office_of_profit,
            "managing_director_appointment_date": company.managing_director_appointment_date,
            "member_count": company.member_count or 0,
            "business_commencement_declaration_filed": (
                company.business_commencement_declaration_filed
                if (
                    company.business_commencement_declaration_verified
                    and company.business_commencement_declaration_evidence_ref
                    and company.business_commencement_declaration_verified_at
                    and company.business_commencement_declaration_verified_by
                ) else None
            ),
            "business_commencement_declaration_verified": bool(
                company.business_commencement_declaration_verified
                and company.business_commencement_declaration_evidence_ref
                and company.business_commencement_declaration_verified_at
                and company.business_commencement_declaration_verified_by
            ),
            "business_commencement_declaration_evidence_ref": company.business_commencement_declaration_evidence_ref,
            "section150_prospectus_issued": (
                company.section150_prospectus_issued
                if (
                    company.section150_applicability_verified
                    and company.section150_applicability_evidence_ref
                    and company.section150_applicability_verified_at
                    and company.section150_applicability_verified_by
                ) else None
            ),
            "section150_applicability_verified": bool(
                company.section150_applicability_verified
                and company.section150_applicability_evidence_ref
                and company.section150_applicability_verified_at
                and company.section150_applicability_verified_by
            ),
            "section150_applicability_evidence_ref": company.section150_applicability_evidence_ref,
        })

        return profile
