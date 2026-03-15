from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base
import enum


class DocumentStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    RELEASED = "RELEASED"


class DocumentType(str, enum.Enum):
    NOTICE = "NOTICE"
    RESOLUTION = "RESOLUTION"
    APPLICATION = "APPLICATION"
    LETTER = "LETTER"
    REPORT = "REPORT"
    OTHER = "OTHER"


class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True)
    company_id = Column(String(36), ForeignKey("companies.id"), nullable=False)
    document_type = Column(Enum(DocumentType), nullable=False)
    title = Column(String(255), nullable=False)
    status = Column(Enum(DocumentStatus), default=DocumentStatus.DRAFT)
    content = Column(Text, nullable=True)
    s3_key = Column(String(500), nullable=True)
    file_url = Column(String(500), nullable=True)
    ai_generated = Column(String(10), default="false")
    approved_by_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    released_at = Column(DateTime(timezone=True), nullable=True)
    created_by_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    company = relationship("Company", back_populates="documents")
    versions = relationship("DocumentVersion", back_populates="document", cascade="all, delete-orphan")
    approvals = relationship("DocumentApproval", back_populates="document", cascade="all, delete-orphan")


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id = Column(String(36), primary_key=True)
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False)
    version_number = Column(Integer, nullable=False)
    content = Column(Text, nullable=True)
    s3_key = Column(String(500), nullable=True)
    change_notes = Column(Text, nullable=True)
    created_by_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    document = relationship("Document", back_populates="versions")


class DocumentApproval(Base):
    __tablename__ = "document_approvals"

    id = Column(String(36), primary_key=True)
    document_id = Column(String(36), ForeignKey("documents.id"), nullable=False)
    approver_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    status = Column(String(20), nullable=False)
    comments = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    document = relationship("Document", back_populates="approvals")
