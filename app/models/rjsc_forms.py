"""
Maps RJSC forms and statutory filing references used by NLC:
  Form I     → Declaration of Compliance (Section 9)
  Form III   → Capital consolidation/division notice (Sections 53-54)
  Form IV    → Notice of increase in capital (Section 56, 15 days)
  Form VI    → Change of registered office (Section 77, 28 days)
  Form VIII  → Copy of special resolution (Section 88(1), 15 days)
  Form IX    → Consent of director to act (Section 92, 30 days)
  Form XII   → Director particulars (Section 115, 14 days)
  Form XV    → Return of allotment (Section 151, 60 days)
  Form XVIII → Registration of charge (Section 159(1), 21 days)
  Form XIX   → Modification of charge (Section 167(3), 21 days)
  Form XXVIII→ Satisfaction of charge (Section 172, 21 days)
  Schedule X → Annual return (Section 36, 21 days after AGM)
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base
from .mixins import TimestampMixin, UUIDPrimaryKeyMixin


class RJSCFormFiling(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Tracks individual RJSC form filings per company."""
    __tablename__ = "rjsc_form_filings"

    company_id: Mapped[str] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Form identification
    form_code: Mapped[str] = mapped_column(String(20), nullable=False)  # FORM_XII, FORM_XV, FORM_117
    form_number: Mapped[str] = mapped_column(String(20), nullable=False)  # XII, XV, 117
    form_name: Mapped[str] = mapped_column(String(255), nullable=False)
    section_reference: Mapped[str] = mapped_column(String(100), nullable=False)
    related_rule_id: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Filing status
    filing_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PENDING"
    )  # PENDING, FILED, OVERDUE, NOT_APPLICABLE

    # Dates
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    filed_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # RJSC receipt
    rjsc_receipt_number: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rjsc_acknowledgment_number: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Who filed it
    filed_by: Mapped[str | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    # Notes
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Financial year
    financial_year: Mapped[str | None] = mapped_column(String(20), nullable=True)

    def __repr__(self) -> str:
        return f"<RJSCFormFiling {self.form_code} company={self.company_id} status={self.filing_status}>"


# Reference data: all RJSC forms for private limited companies
RJSC_FORMS_REFERENCE = [
    {"form_code": "FORM_I", "form_number": "I", "form_name": "Declaration of Compliance", "section": "Section 9", "rule_id": "INC-001", "deadline_days": 0},
    {"form_code": "FORM_III", "form_number": "III", "form_name": "Notice of Consolidation/Division of Share Capital", "section": "Sections 53-54", "rule_id": "CAP-001", "deadline_days": 15},
    {"form_code": "FORM_IV", "form_number": "IV", "form_name": "Notice of Increase in Capital", "section": "Section 56", "rule_id": "SH-003", "deadline_days": 15},
    {"form_code": "FORM_VI", "form_number": "VI", "form_name": "Notice of Change of Registered Office", "section": "Section 77", "rule_id": "OFF-001", "deadline_days": 28},
    {"form_code": "FORM_VIII", "form_number": "VIII", "form_name": "Copy of Special Resolution", "section": "Section 88(1)", "rule_id": "CAP-004", "deadline_days": 15},
    {"form_code": "FORM_IX", "form_number": "IX", "form_name": "Consent of Director to Act", "section": "Section 92", "rule_id": "DIR-007", "deadline_days": 30},
    {"form_code": "FORM_XII", "form_number": "XII", "form_name": "Particulars of Directors, Manager and Managing Agent", "section": "Section 115", "rule_id": "DIR-001", "deadline_days": 14},
    {"form_code": "FORM_XV", "form_number": "XV", "form_name": "Return of Allotment", "section": "Section 151", "rule_id": "SH-001", "deadline_days": 60},
    {"form_code": "FORM_XVII", "form_number": "XVII", "form_name": "Share Transfer Registration", "section": "Section 108", "rule_id": "TR-001", "deadline_days": 0},
    {"form_code": "FORM_XVIII", "form_number": "XVIII", "form_name": "Registration of Charge", "section": "Section 159(1)", "rule_id": "CAP-002", "deadline_days": 21},
    {"form_code": "FORM_XIX", "form_number": "XIX", "form_name": "Modification of Charge", "section": "Section 167(3)", "rule_id": None, "deadline_days": 21},
    {"form_code": "FORM_117", "form_number": "117", "form_name": "Transfer Instrument", "section": "Section 108", "rule_id": "TR-001", "deadline_days": 0},
    {"form_code": "FORM_XXVIII", "form_number": "XXVIII", "form_name": "Notice of Satisfaction of Charge", "section": "Section 172", "rule_id": "CHG-001", "deadline_days": 21},
    {"form_code": "SCHEDULE_X", "form_number": "Schedule X", "form_name": "Annual Return", "section": "Section 36", "rule_id": "AR-001", "deadline_days": 21},
]
