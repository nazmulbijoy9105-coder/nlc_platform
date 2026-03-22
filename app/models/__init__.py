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
from .database import Base, get_db, set_rls_context, set_admin_context  # noqa: F401

# ── Enums (22 types) ────────────────────────────────────────────────
from .enums import (  # noqa: F401
    RiskBand, SeverityLevel, ExposureBand, RevenueTier,
    CompanyStatus, LifecycleStage, CompanyType,
    UserRole, FlagStatus, TaskPriority, TaskStatus,
    DocumentType, EventAction,
    NotificationChannel, NotificationStatus,
    TransferStatus, DirectorStatus, EngagementStatus,
    RescueStepStatus, ComplexityLevel, RuleType,
    AiModel, SroType,
)

# ── Users ────────────────────────────────────────────────────────────
from .user import User  # noqa: F401

# ── Companies ────────────────────────────────────────────────────────
from .company import Company, CompanyUserAccess  # noqa: F401

# ── People (Directors, Shareholders, Transfers) ──────────────────────
from .people import Director, Shareholder, ShareTransfer  # noqa: F401

# ── Filings (AGM, Audit, Annual Return) ──────────────────────────────
from .filings import AGM, Audit, AnnualReturn  # noqa: F401

# ── Compliance (Flags, Score History, Events) ────────────────────────
from .compliance import (  # noqa: F401
    ComplianceFlag, ComplianceScoreHistory, ComplianceEvent,
)

# ── Rules (Legal Rules + Version History) ────────────────────────────
from .rules import LegalRule, LegalRuleVersion  # noqa: F401

# ── Rescue (Plans + Steps) ───────────────────────────────────────────
from .rescue import RescuePlan, RescueStep  # noqa: F401

# ── Commercial (Tasks, Engagements, Quotations) ──────────────────────
from .commercial import Task, Engagement, Quotation  # noqa: F401

# ── Documents (Documents, Access Log, AI Templates, AI Log) ──────────
from .documents import (  # noqa: F401
    Document, DocumentAccessLog,
    AIPromptTemplate, AIOutputLog,
)

# ── Infrastructure (Notifications, SRO, Registers, Activity Log) ─────
from .infrastructure import (  # noqa: F401
    Notification, SRORegistry,
    StatutoryRegister, RegisteredOfficeHistory,
    UserActivityLog,
)

# ── All models (28 tables) for reference ─────────────────────────────
__all__ = [
    # Database
    "Base", "get_db", "set_rls_context", "set_admin_context",

    # Enums
    "RiskBand", "SeverityLevel", "ExposureBand", "RevenueTier",
    "CompanyStatus", "LifecycleStage", "CompanyType",
    "UserRole", "FlagStatus", "TaskPriority", "TaskStatus",
    "DocumentType", "EventAction",
    "NotificationChannel", "NotificationStatus",
    "TransferStatus", "DirectorStatus", "EngagementStatus",
    "RescueStepStatus", "ComplexityLevel", "RuleType",
    "AiModel", "SroType",

    # Models (28 tables)
    "User",                     # TABLE: users
    "Company",                  # TABLE: companies
    "CompanyUserAccess",        # TABLE: company_user_access
    "Director",                 # TABLE: directors
    "Shareholder",              # TABLE: shareholders
    "ShareTransfer",            # TABLE: share_transfers
    "AGM",                      # TABLE: agms
    "Audit",                    # TABLE: audits
    "AnnualReturn",             # TABLE: annual_returns
    "ComplianceFlag",           # TABLE: compliance_flags
    "ComplianceScoreHistory",   # TABLE: compliance_score_history
    "ComplianceEvent",          # TABLE: compliance_events
    "LegalRule",                # TABLE: legal_rules
    "LegalRuleVersion",         # TABLE: legal_rule_versions
    "RescuePlan",               # TABLE: rescue_plans
    "RescueStep",               # TABLE: rescue_steps
    "Task",                     # TABLE: tasks
    "Engagement",               # TABLE: engagements
    "Quotation",                # TABLE: quotations
    "Document",                 # TABLE: documents
    "DocumentAccessLog",        # TABLE: document_access_log
    "AIPromptTemplate",         # TABLE: ai_prompt_templates
    "AIOutputLog",              # TABLE: ai_output_log
    "Notification",             # TABLE: notifications
    "SRORegistry",              # TABLE: sro_registry
    "StatutoryRegister",        # TABLE: statutory_registers
    "RegisteredOfficeHistory",  # TABLE: registered_office_history
    "UserActivityLog",          # TABLE: user_activity_logs
]
