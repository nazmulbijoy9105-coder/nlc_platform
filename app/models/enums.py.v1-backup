"""
NEUM LEX COUNSEL — ORM LAYER
enums.py — All 22 PostgreSQL ENUM types as Python/SQLAlchemy equivalents
Mirrors A_database_schema.sql exactly. Do NOT add or remove values.
AI Constitution Article 1: Only Super Admin may change rule/severity types.
"""
import enum


# ── RISK & SEVERITY ──────────────────────────────────────────────────
class RiskBand(enum.StrEnum):
    GREEN  = "GREEN"
    YELLOW = "YELLOW"
    RED    = "RED"
    BLACK  = "BLACK"


class SeverityLevel(enum.StrEnum):
    GREEN  = "GREEN"
    YELLOW = "YELLOW"
    RED    = "RED"
    BLACK  = "BLACK"


class ExposureBand(enum.StrEnum):
    LOW      = "LOW"
    MODERATE = "MODERATE"
    HIGH     = "HIGH"
    SEVERE   = "SEVERE"


# ── REVENUE ──────────────────────────────────────────────────────────
class RevenueTier(enum.StrEnum):
    COMPLIANCE_PACKAGE        = "COMPLIANCE_PACKAGE"
    STRUCTURED_REGULARIZATION = "STRUCTURED_REGULARIZATION"
    CORPORATE_RESCUE          = "CORPORATE_RESCUE"


# ── COMPANY ──────────────────────────────────────────────────────────
class CompanyStatus(enum.StrEnum):
    ACTIVE          = "ACTIVE"
    IRREGULAR       = "IRREGULAR"
    STATUTORY_DEFAULT = "STATUTORY_DEFAULT"
    DORMANT         = "DORMANT"
    STRUCK_OFF      = "STRUCK_OFF"
    WINDING_UP      = "WINDING_UP"
    DISSOLVED       = "DISSOLVED"


class LifecycleStage(enum.StrEnum):
    INCORPORATION      = "INCORPORATION"
    PRE_FIRST_AGM      = "PRE_FIRST_AGM"
    ACTIVE_COMPLIANT   = "ACTIVE_COMPLIANT"
    ACTIVE_IRREGULAR   = "ACTIVE_IRREGULAR"
    IN_DEFAULT         = "IN_DEFAULT"
    RESCUE_IN_PROGRESS = "RESCUE_IN_PROGRESS"
    POST_RESCUE        = "POST_RESCUE"


class CompanyType(enum.StrEnum):
    PRIVATE_LIMITED = "PRIVATE_LIMITED"
    PUBLIC_LIMITED  = "PUBLIC_LIMITED"
    ONE_PERSON      = "ONE_PERSON"
    FOREIGN_BRANCH  = "FOREIGN_BRANCH"


# ── USER ─────────────────────────────────────────────────────────────
class UserRole(enum.StrEnum):
    SUPER_ADMIN      = "SUPER_ADMIN"
    ADMIN_STAFF      = "ADMIN_STAFF"
    LEGAL_STAFF      = "LEGAL_STAFF"
    CLIENT_DIRECTOR  = "CLIENT_DIRECTOR"
    CLIENT_VIEW_ONLY = "CLIENT_VIEW_ONLY"


# ── COMPLIANCE ───────────────────────────────────────────────────────
class FlagStatus(enum.StrEnum):
    ACTIVE       = "ACTIVE"
    RESOLVED     = "RESOLVED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    ESCALATED    = "ESCALATED"


class TaskPriority(enum.StrEnum):
    CRITICAL = "CRITICAL"
    HIGH     = "HIGH"
    MEDIUM   = "MEDIUM"
    LOW      = "LOW"


class TaskStatus(enum.StrEnum):
    PENDING     = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED   = "COMPLETED"
    CANCELLED   = "CANCELLED"


# ── DOCUMENT ─────────────────────────────────────────────────────────
class DocumentType(enum.StrEnum):
    AGM_MINUTES        = "AGM_MINUTES"
    BOARD_RESOLUTION   = "BOARD_RESOLUTION"
    ANNUAL_RETURN      = "ANNUAL_RETURN"
    AUDIT_REPORT       = "AUDIT_REPORT"
    SHARE_CERTIFICATE  = "SHARE_CERTIFICATE"
    TRANSFER_INSTRUMENT= "TRANSFER_INSTRUMENT"
    ENGAGEMENT_LETTER  = "ENGAGEMENT_LETTER"
    RESCUE_PLAN        = "RESCUE_PLAN"
    DUE_DILIGENCE      = "DUE_DILIGENCE"
    STATUTORY_NOTICE   = "STATUTORY_NOTICE"
    OTHER              = "OTHER"


# ── AUDIT ────────────────────────────────────────────────────────────
class EventAction(enum.StrEnum):
    CREATED  = "CREATED"
    UPDATED  = "UPDATED"
    DELETED  = "DELETED"
    VIEWED   = "VIEWED"
    EXPORTED = "EXPORTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


# ── NOTIFICATION ─────────────────────────────────────────────────────
class NotificationChannel(enum.StrEnum):
    EMAIL     = "EMAIL"
    DASHBOARD = "DASHBOARD"
    WHATSAPP  = "WHATSAPP"


class NotificationStatus(enum.StrEnum):
    PENDING      = "PENDING"
    SENT         = "SENT"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    FAILED       = "FAILED"


# ── SHARE TRANSFER ───────────────────────────────────────────────────
class TransferStatus(enum.StrEnum):
    COMPLETE       = "COMPLETE"
    IRREGULAR      = "IRREGULAR"
    PENDING_REVIEW = "PENDING_REVIEW"
    VOID           = "VOID"


# ── DIRECTOR ─────────────────────────────────────────────────────────
class DirectorStatus(enum.StrEnum):
    ACTIVE   = "ACTIVE"
    RESIGNED = "RESIGNED"
    REMOVED  = "REMOVED"
    DECEASED = "DECEASED"


# ── ENGAGEMENT ───────────────────────────────────────────────────────
class EngagementStatus(enum.StrEnum):
    IDENTIFIED = "IDENTIFIED"
    QUOTED     = "QUOTED"
    CONFIRMED  = "CONFIRMED"
    IN_PROGRESS= "IN_PROGRESS"
    COMPLETED  = "COMPLETED"
    CANCELLED  = "CANCELLED"


# ── RESCUE ───────────────────────────────────────────────────────────
class RescueStepStatus(enum.StrEnum):
    PENDING     = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETE    = "COMPLETE"
    BLOCKED     = "BLOCKED"


# ── RULE ENGINE ──────────────────────────────────────────────────────
class ComplexityLevel(enum.StrEnum):
    LOW      = "LOW"
    MEDIUM   = "MEDIUM"
    HIGH     = "HIGH"
    CRITICAL = "CRITICAL"


class RuleType(enum.StrEnum):
    AGM        = "AGM"
    AUDIT      = "AUDIT"
    RETURN     = "RETURN"
    DIRECTOR   = "DIRECTOR"
    TRANSFER   = "TRANSFER"
    REGISTER   = "REGISTER"
    ESCALATION = "ESCALATION"
    CASCADE    = "CASCADE"


# ── AI ───────────────────────────────────────────────────────────────
class AiModel(enum.StrEnum):
    GPT4      = "GPT4"
    CLAUDE    = "CLAUDE"
    LOCAL_LLM = "LOCAL_LLM"


# ── SRO ──────────────────────────────────────────────────────────────
class SroType(enum.StrEnum):
    FEE       = "FEE"
    FORM      = "FORM"
    DEADLINE  = "DEADLINE"
    PROCEDURE = "PROCEDURE"
    EXEMPTION = "EXEMPTION"
