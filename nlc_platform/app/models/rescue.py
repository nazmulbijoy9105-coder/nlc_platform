from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base
import enum


class RescueStatus(str, enum.Enum):
    ASSESSMENT = "ASSESSMENT"
    STRATEGY = "STRATEGY"
    EXECUTION = "EXECUTION"
    MONITORING = "MONITORING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class RescueCase(Base):
    __tablename__ = "rescue_cases"

    id = Column(String(36), primary_key=True)
    company_id = Column(String(36), ForeignKey("companies.id"), nullable=False)
    status = Column(Enum(RescueStatus), default=RescueStatus.ASSESSMENT)
    risk_band_at_creation = Column(String(20), nullable=False)
    score_at_creation = Column(Integer, nullable=False)
    current_score = Column(Integer, nullable=True)
    target_score = Column(Integer, default=80)
    strategy = Column(Text, nullable=True)
    assigned_to_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    start_date = Column(DateTime(timezone=True), nullable=False)
    target_date = Column(DateTime(timezone=True), nullable=True)
    completion_date = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
    created_by_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    company = relationship("Company", back_populates="rescue_cases")
    milestones = relationship("RescueMilestone", back_populates="rescue_case", cascade="all, delete-orphan")
    documents = relationship("RescueDocument", back_populates="rescue_case", cascade="all, delete-orphan")


class RescueMilestone(Base):
    __tablename__ = "rescue_milestones"

    id = Column(String(36), primary_key=True)
    rescue_case_id = Column(String(36), ForeignKey("rescue_cases.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    is_completed = Column(String(10), default="false")
    order = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    rescue_case = relationship("RescueCase", back_populates="milestones")


class RescueDocument(Base):
    __tablename__ = "rescue_documents"

    id = Column(String(36), primary_key=True)
    rescue_case_id = Column(String(36), ForeignKey("rescue_cases.id"), nullable=False)
    title = Column(String(255), nullable=False)
    s3_key = Column(String(500), nullable=True)
    file_url = Column(String(500), nullable=True)
    document_type = Column(String(50), nullable=True)
    created_by_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    rescue_case = relationship("RescueCase", back_populates="documents")
