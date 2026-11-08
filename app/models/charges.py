"""Evidence-backed company charge and mortgage records."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base
from .mixins import FullMixin

if TYPE_CHECKING:
    from .company import Company


class CompanyCharge(FullMixin, Base):
    """A reported charge; legal facts remain UNKNOWN until independently verified."""
    __tablename__ = "company_charges"

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    creation_date: Mapped[date] = mapped_column(Date, nullable=False)
    charge_type: Mapped[str] = mapped_column(String(100), nullable=False)
    amount_bdt: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False)
    charge_holder: Mapped[str] = mapped_column(String(500), nullable=False)
    charge_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Reported facts are nullable and are never trusted without provenance.
    form_xviii_filed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    form_xviii_filed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    registrable_under_s159: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    satisfied: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    satisfaction_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    satisfaction_filed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    satisfaction_filed_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    creation_date_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    creation_date_evidence_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    creation_date_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    creation_date_verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    form_xviii_filing_status_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    form_xviii_filing_evidence_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    form_xviii_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    form_xviii_verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    registrability_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    registrability_evidence_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    registrability_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    registrability_verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    satisfaction_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    satisfaction_evidence_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    satisfaction_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    satisfaction_verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    satisfaction_filing_status_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    satisfaction_filing_evidence_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    satisfaction_filing_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    satisfaction_filing_verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    company: Mapped[Company] = relationship("Company", back_populates="charges")

    def __repr__(self) -> str:
        return f"<CompanyCharge {self.id} company={self.company_id}>"
