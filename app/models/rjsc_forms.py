"""RJSC Forms Model — tracks all statutory form filings

Maps each RJSC form to its rule, section, and deadline:
  Form I    → Declaration of Compliance (Section 9)
  Form III  → MoA/AoA Filing (Section 11)
  Form IV   → Capital Increase (Section 52)
  Form VI   → Office Change (Section 81)
  Form VIII → Charge Registration (Section 87)
  Form IX   → Situation of Office (Section 81)
  Form XII  → Annual Return (Section 119)
  Form XIV  → Director Change (Section 92)
  Form XV   → Return of Allotment (Section 50)
  Form XVII → Share Transfer (Section 108)
  Form XIX  → Charge Satisfaction (Section 87)
  Form 117  → Transfer Instrument (Section 108)
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
    {"form_code": "FORM_III", "form_number": "III", "form_name": "Memorandum and Articles Filing", "section": "Section 11", "rule_id": "INC-002", "deadline_days": 0},
    {"form_code": "FORM_IV", "form_number": "IV", "form_name": "Notice of Increase in Capital", "section": "Section 52", "rule_id": "SH-003", "deadline_days": 30},
    {"form_code": "FORM_VI", "form_number": "VI", "form_name": "Notice of Change of Registered Office", "section": "Section 81", "rule_id": "OFF-001", "deadline_days": 28},
    {"form_code": "FORM_VIII", "form_number": "VIII", "form_name": "Registration of Charge", "section": "Section 87", "rule_id": "CAP-002", "deadline_days": 30},
    {"form_code": "FORM_IX", "form_number": "IX", "form_name": "Situation of Registered Office", "section": "Section 81", "rule_id": "OFF-001", "deadline_days": 0},
    {"form_code": "FORM_XII", "form_number": "XII", "form_name": "Annual Return", "section": "Section 119", "rule_id": "AR-001", "deadline_days": 30},
    {"form_code": "FORM_XIV", "form_number": "XIV", "form_name": "Notice of Director Change", "section": "Section 92", "rule_id": "DIR-001", "deadline_days": 14},
    {"form_code": "FORM_XV", "form_number": "XV", "form_name": "Return of Allotment", "section": "Section 50", "rule_id": "SH-001", "deadline_days": 30},
    {"form_code": "FORM_XVII", "form_number": "XVII", "form_name": "Share Transfer Registration", "section": "Section 108", "rule_id": "TR-001", "deadline_days": 0},
    {"form_code": "FORM_XIX", "form_number": "XIX", "form_name": "Satisfaction of Charge", "section": "Section 87", "rule_id": "CHG-001", "deadline_days": 30},
    {"form_code": "FORM_117", "form_number": "117", "form_name": "Transfer Instrument (Form 117)", "section": "Section 108", "rule_id": "TR-001", "deadline_days": 0},
    {"form_code": "FORM_XXVIII", "form_number": "XXVIII", "form_name": "Satisfaction of Charge (Full)", "section": "Section 87", "rule_id": "CHG-001", "deadline_days": 30},
]
