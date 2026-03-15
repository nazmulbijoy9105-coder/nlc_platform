from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base
import enum


class FilingStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    OVERDUE = "OVERDUE"


class FilingType(str, enum.Enum):
    ANNUAL_RETURN = "ANNUAL_RETURN"
    FINANCIAL_STATEMENTS = "FINANCIAL_STATEMENTS"
    CHANGE_OF_DIRECTORS = "CHANGE_OF_DIRECTORS"
    CHANGE_OF_ADDRESS = "CHANGE_OF_ADDRESS"
    INCREASE_OF_CAPITAL = "INCREASE_OF_CAPITAL"
    APPOINTMENT_OF_AUDITOR = "APPOINTMENT_OF_AUDITOR"
    OTHER = "OTHER"


class Filing(Base):
    __tablename__ = "filings"

    id = Column(String(36), primary_key=True)
    company_id = Column(String(36), ForeignKey("companies.id"), nullable=False)
    filing_type = Column(Enum(FilingType), nullable=False)
    status = Column(Enum(FilingStatus), default=FilingStatus.PENDING)
    form_number = Column(String(50), nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=False)
    submission_date = Column(DateTime(timezone=True), nullable=True)
    rjsc_receipt_number = Column(String(50), nullable=True)
    amount_paid = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    created_by_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    company = relationship("Company", back_populates="filings")
    history = relationship("FilingHistory", back_populates="filing", cascade="all, delete-orphan")


class FilingHistory(Base):
    __tablename__ = "filing_history"

    id = Column(String(36), primary_key=True)
    filing_id = Column(String(36), ForeignKey("filings.id"), nullable=False)
    status = Column(Enum(FilingStatus), nullable=False)
    notes = Column(Text, nullable=True)
    changed_by_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    filing = relationship("Filing", back_populates="history")


class FilingDeadline(Base):
    __tablename__ = "filing_deadlines"

    id = Column(String(36), primary_key=True)
    company_id = Column(String(36), nullable=False)
    filing_type = Column(Enum(FilingType), nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=False)
    reminder_sent = Column(String(10), default="false")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
