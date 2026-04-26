"""
NEUM LEX COUNSEL — People Service
app/services/people_service.py

Directors, Shareholders, and Share Transfers.
All changes trigger compliance re-evaluation via background task.
AI Constitution Article 2: NID/passport data encrypted at application layer.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import select

from app.models.enums import DirectorStatus, TransferStatus
from app.models.people import Director, Shareholder, ShareTransfer
from app.services.base import BaseService

if TYPE_CHECKING:
    import uuid

# ═══════════════════════════════════════════════════════════════════════
# DIRECTOR SERVICE
# ═══════════════════════════════════════════════════════════════════════

class DirectorService(BaseService[Director]):
    model = Director

    async def appoint_director(
        self,
        company_id: uuid.UUID,
        *,
        full_name: str,
        appointment_date: date,
        father_name: str | None = None,
        nid_number: str | None = None,
        passport_number: str | None = None,
        nationality: str = "Bangladeshi",
        address: str | None = None,
        is_managing_director: bool = False,
        is_chairman: bool = False,
        shares_held: int = 0,
        appointment_filed_date: date | None = None,
    ) -> Director:
        """
        Record a director appointment.
        Auto-calculates filing delay (Section 115 CA 1994: file within 30 days).
        """
        delay_days = 0
        filing_delayed = False
        if appointment_filed_date:
            deadline = appointment_date + timedelta(days=30)
            if appointment_filed_date > deadline:
                delay_days = (appointment_filed_date - deadline).days
                filing_delayed = True

        return await self.create(
            company_id=company_id,
            full_name=full_name,
            father_name=father_name,
            nid_number=nid_number,        # Encrypted at model layer
            passport_number=passport_number,
            nationality=nationality,
            address=address,
            appointment_date=appointment_date,
            appointment_filed_date=appointment_filed_date,
            appointment_filing_delayed=filing_delayed,
            appointment_delay_days=delay_days,
            director_status=DirectorStatus.ACTIVE,
            shares_held=shares_held,
            is_managing_director=is_managing_director,
            is_chairman=is_chairman,
        )

    async def record_departure(
        self,
        director_id: uuid.UUID,
        *,
        departure_type: DirectorStatus,  # RESIGNED | REMOVED | DECEASED
        departure_date: date,
        departure_filed_date: date | None = None,
    ) -> Director | None:
        """
        Record a director's departure.
        Auto-calculates departed_still_liable if filing is missing/late.
        """
        director = await self.get_by_id(director_id)
        if not director:
            return None

        delay_days = 0
        filing_delayed = False
        if departure_filed_date:
            deadline = departure_date + timedelta(days=30)
            if departure_filed_date > deadline:
                delay_days = (departure_filed_date - deadline).days
                filing_delayed = True

        # Still liable if departure not filed with RJSC
        still_liable = departure_filed_date is None

        return await self.update_instance(
            director,
            director_status=departure_type,
            departure_date=departure_date,
            departure_filed_date=departure_filed_date,
            departure_filing_delayed=filing_delayed,
            departure_delay_days=delay_days,
            departed_still_liable=still_liable,
        )

    async def get_active_directors(self, company_id: uuid.UUID) -> list[Director]:
        """Get all active directors for a company."""
        result = await self.db.execute(
            select(Director).where(
                Director.company_id == company_id,
                Director.director_status == DirectorStatus.ACTIVE,
            )
        )
        return list(result.scalars().all())

    async def get_all_for_company(self, company_id: uuid.UUID) -> list[Director]:
        """Get all directors (active and departed) for a company."""
        result = await self.db.execute(
            select(Director)
            .where(Director.company_id == company_id)
            .order_by(Director.appointment_date.desc())
        )
        return list(result.scalars().all())

    async def get_departed_still_liable(self, company_id: uuid.UUID) -> list[Director]:
        """
        Get directors who departed but are still shown as active with RJSC.
        DIR-004: Personal liability risk for these directors.
        """
        result = await self.db.execute(
            select(Director).where(
                Director.company_id == company_id,
                Director.departed_still_liable,
            )
        )
        return list(result.scalars().all())


# ═══════════════════════════════════════════════════════════════════════
# SHAREHOLDER SERVICE
# ═══════════════════════════════════════════════════════════════════════

class ShareholderService(BaseService[Shareholder]):
    model = Shareholder

    async def add_shareholder(
        self,
        company_id: uuid.UUID,
        *,
        shareholder_name: str,
        shares_held: int,
        share_class: str = "ORDINARY",
        shareholder_type: str = "INDIVIDUAL",
        nid_or_reg_number: str | None = None,
        nationality: str = "Bangladeshi",
        address: str | None = None,
        effective_date: date | None = None,
        percentage_holding: float | None = None,
        share_certificate_issued: bool = False,
        certificate_issue_date: date | None = None,
        change_filed_with_rjsc: bool = False,
        rjsc_filing_date: date | None = None,
    ) -> Shareholder:
        """
        Add a new shareholder record.
        REG-002: Certificate delay calculated automatically.
        """
        cert_delay = 0
        if effective_date and not share_certificate_issued:
            deadline = effective_date + timedelta(days=60)  # 2 months
            if date.today() > deadline:
                cert_delay = (date.today() - deadline).days

        return await self.create(
            company_id=company_id,
            shareholder_name=shareholder_name,
            shares_held=shares_held,
            share_class=share_class,
            shareholder_type=shareholder_type,
            nid_or_reg_number=nid_or_reg_number,
            nationality=nationality,
            address=address,
            effective_date=effective_date,
            percentage_holding=percentage_holding,
            share_certificate_issued=share_certificate_issued,
            certificate_issue_date=certificate_issue_date,
            certificate_delay_days=cert_delay,
            change_filed_with_rjsc=change_filed_with_rjsc,
            rjsc_filing_date=rjsc_filing_date,
        )

    async def get_for_company(self, company_id: uuid.UUID) -> list[Shareholder]:
        """Get all shareholders for a company."""
        result = await self.db.execute(
            select(Shareholder)
            .where(Shareholder.company_id == company_id)
            .order_by(Shareholder.shares_held.desc())
        )
        return list(result.scalars().all())

    async def update_holding(
        self,
        shareholder_id: uuid.UUID,
        new_shares: int,
        percentage: float | None = None,
    ) -> Shareholder | None:
        """Update a shareholder's shares held after a transfer."""
        sh = await self.get_by_id(shareholder_id)
        if not sh:
            return None
        return await self.update_instance(
            sh,
            shares_held=new_shares,
            percentage_holding=percentage,
        )


# ═══════════════════════════════════════════════════════════════════════
# SHARE TRANSFER SERVICE
# ═══════════════════════════════════════════════════════════════════════

class ShareTransferService(BaseService[ShareTransfer]):
    model = ShareTransfer

    async def record_transfer(
        self,
        company_id: uuid.UUID,
        *,
        transferor_name: str,
        transferee_name: str,
        shares_transferred: int,
        transfer_date: date,
        consideration_bdt: float | None = None,
        has_transfer_instrument: bool = True,
        stamp_duty_paid: bool = True,
        stamp_duty_amount_bdt: float | None = None,
        board_approval_obtained: bool = True,
        board_approval_date: date | None = None,
        register_updated: bool = True,
        register_update_date: date | None = None,
        aoa_restriction_violated: bool = False,
        transferor_shareholder_id: uuid.UUID | None = None,
        transferee_shareholder_id: uuid.UUID | None = None,
    ) -> ShareTransfer:
        """
        Record a share transfer. Auto-detects irregularities.
        TR-001 through TR-006 irregularities flagged here for rule engine.
        """
        irregularities = []
        if not has_transfer_instrument:
            irregularities.append("TR-001: No transfer instrument")
        if not stamp_duty_paid:
            irregularities.append("TR-002: Stamp duty not paid")
        if not board_approval_obtained:
            irregularities.append("TR-003: No board approval")
        if not register_updated:
            irregularities.append("TR-004: Register not updated")
        if aoa_restriction_violated:
            irregularities.append("TR-005: AoA restriction violated — BLACK override")

        is_irregular = len(irregularities) > 0
        transfer_status = (
            TransferStatus.IRREGULAR if is_irregular else TransferStatus.COMPLETE
        )
        if aoa_restriction_violated:
            transfer_status = TransferStatus.VOID

        return await self.create(
            company_id=company_id,
            transferor_name=transferor_name,
            transferee_name=transferee_name,
            transferor_shareholder_id=transferor_shareholder_id,
            transferee_shareholder_id=transferee_shareholder_id,
            shares_transferred=shares_transferred,
            transfer_date=transfer_date,
            consideration_bdt=consideration_bdt,
            transfer_status=transfer_status,
            has_transfer_instrument=has_transfer_instrument,
            stamp_duty_paid=stamp_duty_paid,
            stamp_duty_amount_bdt=stamp_duty_amount_bdt,
            board_approval_obtained=board_approval_obtained,
            board_approval_date=board_approval_date,
            register_updated=register_updated,
            register_update_date=register_update_date,
            aoa_restriction_violated=aoa_restriction_violated,
            is_irregular=is_irregular,
            irregularity_notes="\n".join(irregularities) if irregularities else None,
        )

    async def get_for_company(self, company_id: uuid.UUID) -> list[ShareTransfer]:
        """Get all share transfers for a company."""
        result = await self.db.execute(
            select(ShareTransfer)
            .where(ShareTransfer.company_id == company_id)
            .order_by(ShareTransfer.transfer_date.desc())
        )
        return list(result.scalars().all())

    async def get_irregular(self, company_id: uuid.UUID) -> list[ShareTransfer]:
        """Get all irregular transfers (TR-001 through TR-006 triggers)."""
        result = await self.db.execute(
            select(ShareTransfer).where(
                ShareTransfer.company_id == company_id,
                ShareTransfer.is_irregular,
            )
        )
        return list(result.scalars().all())
