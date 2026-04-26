"""
NEUM LEX COUNSEL — ORM LAYER
models/__init__.py — Single import point for all 28 ORM models.

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

# ── Companies ────────────────────────────────────────────────────────
from .company import Company, CompanyUserAccess

# ── Compliance (Flags, Score History, Events) ────────────────────────
from .compliance import (
    ComplianceEvent,
    ComplianceFlag,
    ComplianceScoreHistory,
)
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
from .filings import AGM, AnnualReturn, Audit

# ── Infrastructure (Notifications, SRO, Registers, Activity Log) ─────
from .infrastructure import (
    Notification,
    RegisteredOfficeHistory,
    SRORegistry,
    StatutoryRegister,
    UserActivityLog,
)

# ── People (Directors, Shareholders, Transfers) ──────────────────────
from .people import Director, Shareholder, ShareTransfer

# ── Rescue (Plans + Steps) ───────────────────────────────────────────
from .rescue import RescuePlan, RescueStep

# ── Rules (Legal Rules + Version History) ────────────────────────────
from .rules import LegalRule, LegalRuleVersion

# ── Users ────────────────────────────────────────────────────────────
from .user import User

# ── All models (28 tables) for reference ─────────────────────────────
__all__ = [
    "AGM",                      # TABLE: agms
    "AIOutputLog",              # TABLE: ai_output_log
    "AIPromptTemplate",         # TABLE: ai_prompt_templates
    "AiModel",
    "AnnualReturn",             # TABLE: annual_returns
    "Audit",                    # TABLE: audits
    # Database
    "Base",
    "Company",                  # TABLE: companies
    "CompanyStatus",
    "CompanyType",
    "CompanyUserAccess",        # TABLE: company_user_access
    "ComplexityLevel",
    "ComplianceEvent",          # TABLE: compliance_events
    "ComplianceFlag",           # TABLE: compliance_flags
    "ComplianceScoreHistory",   # TABLE: compliance_score_history
    "Director",                 # TABLE: directors
    "DirectorStatus",
    "Document",                 # TABLE: documents
    "DocumentAccessLog",        # TABLE: document_access_log
    "DocumentType",
    "Engagement",               # TABLE: engagements
    "EngagementStatus",
    "EventAction",
    "ExposureBand",
    "FlagStatus",
    "LegalRule",                # TABLE: legal_rules
    "LegalRuleVersion",         # TABLE: legal_rule_versions
    "LifecycleStage",
    "Notification",             # TABLE: notifications
    "NotificationChannel",
    "NotificationStatus",
    "Quotation",                # TABLE: quotations
    "RegisteredOfficeHistory",  # TABLE: registered_office_history
    "RescuePlan",               # TABLE: rescue_plans
    "RescueStep",               # TABLE: rescue_steps
    "RescueStepStatus",
    "RevenueTier",
    # Enums
    "RiskBand",
    "RuleType",
    "SRORegistry",              # TABLE: sro_registry
    "SeverityLevel",
    "ShareTransfer",            # TABLE: share_transfers
    "Shareholder",              # TABLE: shareholders
    "SroType",
    "StatutoryRegister",        # TABLE: statutory_registers
    "Task",                     # TABLE: tasks
    "TaskPriority",
    "TaskStatus",
    "TransferStatus",
    # Models (28 tables)
    "User",                     # TABLE: users
    "UserActivityLog",          # TABLE: user_activity_logs
    "UserRole",
    "get_db",
    "set_admin_context",
    "set_rls_context",
]
