from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base
import enum


class EngagementStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    PENDING = "PENDING"
    TERMINATED = "TERMINATED"


class PipelineStage(str, enum.Enum):
    LEAD = "LEAD"
    PROSPECT = "PROSPECT"
    PROPOSAL = "PROPOSAL"
    NEGOTIATION = "NEGOTIATION"
    WON = "WON"
    LOST = "LOST"


class Engagement(Base):
    __tablename__ = "engagements"

    id = Column(String(36), primary_key=True)
    company_id = Column(String(36), ForeignKey("companies.id"), nullable=False)
    status = Column(Enum(EngagementStatus), default=EngagementStatus.PENDING)
    service_type = Column(String(100), nullable=True)
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    monthly_fee = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    created_by_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    company = relationship("Company", back_populates="engagements")
    pipeline = relationship("Pipeline", back_populates="engagement", cascade="all, delete-orphan")


class Pipeline(Base):
    __tablename__ = "pipeline"

    id = Column(String(36), primary_key=True)
    engagement_id = Column(String(36), ForeignKey("engagements.id"), nullable=False)
    stage = Column(Enum(PipelineStage), default=PipelineStage.LEAD)
    value = Column(Float, nullable=True)
    expected_close_date = Column(DateTime(timezone=True), nullable=True)
    probability = Column(Integer, default=0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    engagement = relationship("Engagement", back_populates="pipeline")
    invoices = relationship("Invoice", back_populates="pipeline", cascade="all, delete-orphan")


class InvoiceStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SENT = "SENT"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(String(36), primary_key=True)
    pipeline_id = Column(String(36), ForeignKey("pipeline.id"), nullable=False)
    invoice_number = Column(String(50), unique=True, nullable=False)
    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.DRAFT)
    issue_date = Column(DateTime(timezone=True), nullable=False)
    due_date = Column(DateTime(timezone=True), nullable=False)
    paid_date = Column(DateTime(timezone=True), nullable=True)
    subtotal = Column(Float, nullable=False)
    tax = Column(Float, default=0)
    total = Column(Float, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    pipeline = relationship("Pipeline", back_populates="invoices")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id = Column(String(36), primary_key=True)
    invoice_id = Column(String(36), ForeignKey("invoices.id"), nullable=False)
    description = Column(String(255), nullable=False)
    quantity = Column(Integer, default=1)
    unit_price = Column(Float, nullable=False)
    total = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    invoice = relationship("Invoice", back_populates="items")
