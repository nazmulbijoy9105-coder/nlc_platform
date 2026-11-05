"""RJSC Forms Model — statutory filing references and deadlines.

The reference catalogue distinguishes RJSC forms from statutory returns. A form
number is never inferred from a rule ID; confirm the current RJSC workflow before
creating a filing task.
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
    form_code: Mapped[str] = mapped_column(String(20), nullable=False)
    form_number: Mapped[str] = mapped_column(String(20), nullable=False)
    form_name: Mapped[str] = mapped_column(String(255), nullable=False)
    section_reference: Mapped[str] = mapped_column(String(100), nullable=False)
    related_rule_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    filing_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PENDING"
    )
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    filed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    rjsc_receipt_number: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rjsc_acknowledgment_number: Mapped[str | None] = mapped_column(String(255), nullable=True)
    filed_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    financial_year: Mapped[str | None] = mapped_column(String(20), nullable=True)

    def __repr__(self) -> str:
        return f"<RJSCFormFiling {self.form_code} company={self.company_id} status={self.filing_status}>"


# RJSC's current public forms/FAQ and the prescribed forms were checked.
# This is a reference catalogue, not independent legal approval. "deadline_days"
# is a statutory period only where stated;
# 0 means event-driven/no fixed day count, and None means do not auto-schedule.
RJSC_FORMS_REFERENCE = [
    {"form_code": "FORM_I", "form_number": "I", "form_name": "Declaration on Registration of Company", "section": "Section 25", "rule_id": None, "deadline_days": 0},
    {"form_code": "FORM_III", "form_number": "III", "form_name": "Notice of Consolidation/Division of Share Capital", "section": "Sections 53-54", "rule_id": "CAP-001", "deadline_days": 15},
    {"form_code": "FORM_IV", "form_number": "IV", "form_name": "Notice of Increase in Share Capital", "section": "Section 56", "rule_id": "SH-003", "deadline_days": 15},
    {"form_code": "FORM_VI", "form_number": "VI", "form_name": "Notice of Change of Registered Office", "section": "Section 77", "rule_id": "OFF-001", "deadline_days": 28},
    {"form_code": "FORM_VIII", "form_number": "VIII", "form_name": "Special or Extraordinary Resolution", "section": "Section 88(1)", "rule_id": "CAP-004", "deadline_days": 15},
    {"form_code": "FORM_IX", "form_number": "IX", "form_name": "Consent of Director to Act", "section": "Section 92", "rule_id": "DIR-007", "deadline_days": 30},
    {"form_code": "FORM_X", "form_number": "X", "form_name": "List of Persons Consenting to be Directors", "section": "Section 92", "rule_id": None, "deadline_days": 0},
    {"form_code": "SCHEDULE_X", "form_number": "Schedule X", "form_name": "Annual Return", "section": "Section 36", "rule_id": "AR-001", "deadline_days": 21},
    {"form_code": "FORM_XII", "form_number": "XII", "form_name": "Particulars of Directors, Managers and Changes", "section": "Section 115", "rule_id": "DIR-001", "deadline_days": 14},
    {"form_code": "FORM_XV", "form_number": "XV", "form_name": "Return of Allotment", "section": "Section 151", "rule_id": "SH-001", "deadline_days": 60},
    {"form_code": "FORM_XVIII", "form_number": "XVIII", "form_name": "Particulars of Mortgage or Charge", "section": "Section 159", "rule_id": "CAP-002", "deadline_days": 21},
    {"form_code": "FORM_XIX", "form_number": "XIX", "form_name": "Particulars of Modification of Mortgage or Charge", "section": "Section 167(3)", "rule_id": "CHG-002", "deadline_days": 21},
    {"form_code": "FORM_XXVIII", "form_number": "XXVIII", "form_name": "Memorandum of Satisfaction of Mortgage or Charge", "section": "Section 172", "rule_id": "CHG-001", "deadline_days": 21},
    # Auditor's separate notice duty under s.210(2); do not map to AUD-001,
    # which evaluates the company's first-auditor appointment under s.210(6).
    # The 30-day period runs from the auditor receiving appointment information,
    # a trigger not currently captured by the filing model.
    {"form_code": "FORM_23B", "form_number": "23B", "form_name": "Notice by Auditor of Appointment", "section": "Section 210(2)", "rule_id": None, "deadline_days": None},
    {"form_code": "FORM_117", "form_number": "117", "form_name": "Instrument of Transfer", "section": "Section 108", "rule_id": "TR-001", "deadline_days": 0},
]
