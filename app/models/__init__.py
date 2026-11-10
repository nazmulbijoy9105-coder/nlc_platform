"""
NEUM LEX COUNSEL — ORM LAYER
models/__init__.py — Single import point for all 29 ORM models.

Usage:
    from app.models import User, Company, ComplianceFlag, ...
    from app.models import Base, get_db

Import order matters: Base must be imported before models that
use it, so SQLAlchemy can resolve all relationships correctly.
All models are imported here to ensure they're registered with Base.metadata
before Alembic migrations are generated.
"""

# ── Database infrastructure ─────────────────────────────────────────
# ── Commercial (Tasks, Engagements, Quotations) ──────────────────────
from .commercial import Engagement, Quotation, Task
from .finance import (
    ClientSubscription,
    Invoice,
    InvoiceLine,
    Payment,
    PaymentAllocation,
    PaymentIntent,
    PaymentLedgerEvent,
    PaymentProviderEvent,
    PaymentSubmission,
)

# ── Companies ────────────────────────────────────────────────────────
from .company import Company, CompanyUserAccess
from .company_fact import CompanyFact
from .charges import CompanyCharge

# ── Compliance (Flags, Score History, Events) ────────────────────────
from .compliance import (
    ComplianceEvent,
    ComplianceEvaluationRun,
    ComplianceFlag,
    ComplianceScoreHistory,
)
from .compliance_calendar import ComplianceCalendarEvent
from .database import Base, get_db, set_admin_context, set_rls_context

# ── Documents (Documents, Access Log, AI Templates, AI Log) ──────────
from .documents import (
    AIOutputLog,
    AIPromptTemplate,
    Document,
    DocumentAccessLog,
)

# ── Enums (22 types) ────────────────────────────────────────────────
from .enums import (
    AiModel,
    CompanyStatus,
    CompanyType,
    ComplexityLevel,
    DirectorStatus,
    DocumentType,
    EngagementStatus,
    EventAction,
    ExposureBand,
    FlagStatus,
    LifecycleStage,
    NotificationChannel,
    NotificationStatus,
    RescueStepStatus,
    RevenueTier,
    RiskBand,
    RuleType,
    SeverityLevel,
    SroType,
    TaskPriority,
    TaskStatus,
    TransferStatus,
    UserRole,
)

# ── Filings (AGM, Audit, Annual Return) ──────────────────────────────
from .filings import AGM, AGMNoticeEvidence, AnnualReturn, Audit

# ── Infrastructure (Notifications, SRO, Registers, Activity Log) ─────
from .infrastructure import (
    Notification,
    RegisteredOfficeHistory,
    SRORegistry,
    StatutoryRegister,
    UserActivityLog,
)

# ── People (Directors, Shareholders, Transfers) ──────────────────────
from .people import Director, ShareComplianceEvent, Shareholder, ShareTransfer
from .regulatory_rule import RegulatoryRule
from .subscription import (
    ClientSubscriptionFeature,
    SubscriptionEvent,
    SubscriptionPlan,
    SubscriptionPlanFeature,
    SubscriptionPlanPrice,
)

# ── Rescue (Plans + Steps) ───────────────────────────────────────────
from .rescue import RescuePlan, RescueStep
from .rjsc_forms import RJSCFormFiling

# ── Rules (Legal Rules + Version History) ────────────────────────────
from .rules import LegalRule, LegalRuleVersion

# ── Users ────────────────────────────────────────────────────────────
from .user import User

# ── All models (29 tables) for reference ─────────────────────────────
__all__ = [
    "AGM",
    "AGMNoticeEvidence",
    "AIOutputLog",
    "AIPromptTemplate",
    "AiModel",
    "AnnualReturn",
    "Audit",
    "Base",
    "Company",
    "CompanyFact",
    "CompanyCharge",
    "CompanyStatus",
    "CompanyType",
    "CompanyUserAccess",
    "ClientSubscription",
    "Invoice",
    "InvoiceLine",
    "Payment",
    "PaymentAllocation",
    "PaymentIntent",
    "PaymentLedgerEvent",
    "PaymentProviderEvent",
    "PaymentSubmission",
    "ClientSubscriptionFeature",
    "SubscriptionEvent",
    "SubscriptionPlan",
    "SubscriptionPlanFeature",
    "SubscriptionPlanPrice",
    "ComplexityLevel",
    "ComplianceCalendarEvent",
    "ComplianceEvent",
    "ComplianceEvaluationRun",
    "ComplianceFlag",
    "ComplianceScoreHistory",
    "DeliveryStatus",
    "Director",
    "DirectorStatus",
    "Document",
    "DocumentAccessLog",
    "DocumentType",
    "Engagement",
    "EngagementStatus",
    "EventAction",
    "ExposureBand",
    "FlagStatus",
    "LegalRule",
    "LegalRuleVersion",
    "LifecycleStage",
    "Notification",
    "NotificationChannel",
    "NotificationStatus",
    "Quotation",
    "RJSCFormFiling",
    "RegisteredOfficeHistory",
    "RegulatoryRule",
    "RescuePlan",
    "RescueStep",
    "RescueStepStatus",
    "RevenueTier",
    "RiskBand",
    "RuleType",
    "SRORegistry",
    "SeverityLevel",
    "ShareComplianceEvent",
    "ShareTransfer",
    "Shareholder",
    "SroType",
    "StatutoryRegister",
    "Task",
    "TaskPriority",
    "TaskStatus",
    "TransferStatus",
    "User",
    "UserActivityLog",
    "UserRole",
    "WebhookDelivery",
    "WebhookEndpoint",
    "WebhookEvent",
    "get_db",
    "set_admin_context",
    "set_rls_context",
]

from .webhook import DeliveryStatus, WebhookDelivery, WebhookEndpoint, WebhookEvent
