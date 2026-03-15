from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
import enum


class RiskBand(str, enum.Enum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"
    BLACK = "BLACK"


class FilingStatus(str, enum.Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    OVERDUE = "OVERDUE"


class CompanyStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    DORMANT = "DORMANT"
    UNDER_RESCUE = "UNDER_RESCUE"
    LIQUIDATION = "LIQUIDATION"
    DISSOLVED = "DISSOLVED"


class Company(Base):
    __tablename__ = "companies"

    id = Column(String(36), primary_key=True)
    rjsc_number = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    registration_date = Column(DateTime(timezone=True), nullable=False)
    status = Column(Enum(CompanyStatus), default=CompanyStatus.ACTIVE)
    risk_band = Column(Enum(RiskBand), default=RiskBand.GREEN)
    compliance_score = Column(Integer, default=100)
    authorized_capital = Column(Float, default=0)
    paid_up_capital = Column(Float, default=0)
    registered_address = Column(Text, nullable=True)
    business_address = Column(Text, nullable=True)
    sector = Column(String(100), nullable=True)
    created_by_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    contacts = relationship("CompanyContact", back_populates="company", cascade="all, delete-orphan")
    compliance_scores = relationship("ComplianceScore", back_populates="company", cascade="all, delete-orphan")
    violations = relationship("Violation", back_populates="company", cascade="all, delete-orphan")
    filings = relationship("Filing", back_populates="company", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="company", cascade="all, delete-orphan")
    rescue_cases = relationship("RescueCase", back_populates="company", cascade="all, delete-orphan")
    engagements = relationship("Engagement", back_populates="company", cascade="all, delete-orphan")


class CompanyContact(Base):
    __tablename__ = "company_contacts"

    id = Column(String(36), primary_key=True)
    company_id = Column(String(36), ForeignKey("companies.id"), nullable=False)
    name = Column(String(255), nullable=False)
    designation = Column(String(100), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(20), nullable=True)
    is_primary = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    company = relationship("Company", back_populates="contacts")
