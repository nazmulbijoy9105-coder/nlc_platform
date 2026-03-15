from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base
import enum


class NotificationType(str, enum.Enum):
    FILING_DEADLINE = "FILING_DEADLINE"
    COMPLIANCE_ALERT = "COMPLIANCE_ALERT"
    DOCUMENT_APPROVAL = "DOCUMENT_APPROVAL"
    RESCUE_UPDATE = "RESCUE_UPDATE"
    SYSTEM = "SYSTEM"


class NotificationStatus(str, enum.Enum):
    UNREAD = "UNREAD"
    READ = "READ"
    ARCHIVED = "ARCHIVED"


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    notification_type = Column(Enum(NotificationType), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    status = Column(Enum(NotificationStatus), default=NotificationStatus.UNREAD)
    link = Column(String(500), nullable=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="notifications")


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    notification_type = Column(Enum(NotificationType), nullable=False)
    email_enabled = Column(String(10), default="true")
    dashboard_enabled = Column(String(10), default="true")
    whatsapp_enabled = Column(String(10), default="false")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class EmailQueueStatus(str, enum.Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


class EmailQueue(Base):
    __tablename__ = "email_queue"

    id = Column(String(36), primary_key=True)
    recipient_email = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    status = Column(Enum(EmailQueueStatus), default=EmailQueueStatus.PENDING)
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class WhatsAppQueueStatus(str, enum.Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"


class WhatsAppQueue(Base):
    __tablename__ = "whatsapp_queue"

    id = Column(String(36), primary_key=True)
    recipient_phone = Column(String(20), nullable=False)
    message = Column(Text, nullable=False)
    status = Column(Enum(WhatsAppQueueStatus), default=WhatsAppQueueStatus.PENDING)
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    entity_type = Column(String(50), nullable=True)
    entity_id = Column(String(36), nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="audit_logs")


class SystemSetting(Base):
    __tablename__ = "system_settings"

    id = Column(String(36), primary_key=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=True)
    description = Column(String(255), nullable=True)
    is_sensitive = Column(String(10), default="false")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
