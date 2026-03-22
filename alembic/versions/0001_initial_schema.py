"""Create complete initial schema

NEUM LEX COUNSEL — Database Migration
Revision:  0001
Previous:  None (initial)
Created:   2025-01-01

This migration creates the complete NLC database from scratch:
  - PostgreSQL extensions (uuid-ossp, pgcrypto)
  - 22 ENUM types
  - 28 tables (all with proper constraints, indexes, RLS hooks)
  - 2 trigger functions (updated_at, full-text search)
  - Triggers on all tables with updated_at
  - Company full-text search trigger
  - 5 analytics views (vw_admin_dashboard_kpis, etc.)
  - Row-Level Security enablement

Release Governance Protocol (Part III §7):
  [x] Initial schema — pre-release, no approval required
  [x] Staging tested
  [x] Rollback: drop all tables and types (downgrade below)
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# ── Revision identifiers ──────────────────────────────────────────────
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ═══════════════════════════════════════════════════════════════════════
# UPGRADE
# ═══════════════════════════════════════════════════════════════════════
def upgrade() -> None:
    conn = op.get_bind()

    # ── Extensions ────────────────────────────────────────────────
    conn.execute(sa.text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
    conn.execute(sa.text('CREATE EXTENSION IF NOT EXISTS "pgcrypto"'))

    # ── ENUM types (22) ───────────────────────────────────────────
    _create_enums(conn)

    # ── Tables ────────────────────────────────────────────────────
    _create_users()
    _create_companies()
    _create_company_user_access()
    _create_directors()
    _create_shareholders()
    _create_share_transfers()
    _create_agms()
    _create_audits()
    _create_annual_returns()
    _create_compliance_events()
    _create_compliance_flags()
    _create_compliance_score_history()
    _create_legal_rules()
    _create_legal_rule_versions()
    _create_rescue_plans()
    _create_rescue_steps()
    _create_tasks()
    _create_engagements()
    _create_quotations()
    _create_documents()
    _create_document_access_log()
    _create_notifications()
    _create_sro_registry()
    _create_statutory_registers()
    _create_registered_office_history()
    _create_ai_prompt_templates()
    _create_ai_output_log()
    _create_user_activity_logs()

    # ── Trigger functions ─────────────────────────────────────────
    _create_trigger_functions(conn)

    # ── Triggers ──────────────────────────────────────────────────
    _create_triggers(conn)

    # ── Performance indexes ───────────────────────────────────────
    _create_composite_indexes()

    # ── Analytics views ───────────────────────────────────────────
    _create_views(conn)

    # ── Row-Level Security ────────────────────────────────────────
    _enable_rls(conn)


# ═══════════════════════════════════════════════════════════════════════
# ENUM CREATION
# ═══════════════════════════════════════════════════════════════════════
def _create_enums(conn) -> None:
    enums = {
        "risk_band":          ["GREEN", "YELLOW", "RED", "BLACK"],
        "severity_level":     ["GREEN", "YELLOW", "RED", "BLACK"],
        "exposure_band":      ["LOW", "MODERATE", "HIGH", "SEVERE"],
        "revenue_tier":       ["COMPLIANCE_PACKAGE", "STRUCTURED_REGULARIZATION", "CORPORATE_RESCUE"],
        "company_status":     ["ACTIVE", "IRREGULAR", "STATUTORY_DEFAULT", "DORMANT", "STRUCK_OFF", "WINDING_UP", "DISSOLVED"],
        "lifecycle_stage":    ["INCORPORATION", "PRE_FIRST_AGM", "ACTIVE_COMPLIANT", "ACTIVE_IRREGULAR", "IN_DEFAULT", "RESCUE_IN_PROGRESS", "POST_RESCUE"],
        "company_type":       ["PRIVATE_LIMITED", "PUBLIC_LIMITED", "ONE_PERSON", "FOREIGN_BRANCH"],
        "user_role":          ["SUPER_ADMIN", "ADMIN_STAFF", "LEGAL_STAFF", "CLIENT_DIRECTOR", "CLIENT_VIEW_ONLY"],
        "flag_status":        ["ACTIVE", "RESOLVED", "ACKNOWLEDGED", "ESCALATED"],
        "task_priority":      ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
        "task_status":        ["PENDING", "IN_PROGRESS", "COMPLETED", "CANCELLED"],
        "document_type":      ["AGM_MINUTES", "BOARD_RESOLUTION", "ANNUAL_RETURN", "AUDIT_REPORT", "SHARE_CERTIFICATE", "TRANSFER_INSTRUMENT", "ENGAGEMENT_LETTER", "RESCUE_PLAN", "DUE_DILIGENCE", "STATUTORY_NOTICE", "OTHER"],
        "event_action":       ["CREATED", "UPDATED", "DELETED", "VIEWED", "EXPORTED", "APPROVED", "REJECTED"],
        "notification_channel": ["EMAIL", "DASHBOARD", "WHATSAPP"],
        "notification_status":  ["PENDING", "SENT", "ACKNOWLEDGED", "FAILED"],
        "transfer_status":    ["COMPLETE", "IRREGULAR", "PENDING_REVIEW", "VOID"],
        "director_status":    ["ACTIVE", "RESIGNED", "REMOVED", "DECEASED"],
        "engagement_status":  ["IDENTIFIED", "QUOTED", "CONFIRMED", "IN_PROGRESS", "COMPLETED", "CANCELLED"],
        "rescue_step_status": ["PENDING", "IN_PROGRESS", "COMPLETE", "BLOCKED"],
        "complexity_level":   ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
        "rule_type":          ["AGM", "AUDIT", "RETURN", "DIRECTOR", "TRANSFER", "REGISTER", "ESCALATION", "CASCADE"],
        "ai_model":           ["GPT4", "CLAUDE", "LOCAL_LLM"],
        "sro_type":           ["FEE", "FORM", "DEADLINE", "PROCEDURE", "EXEMPTION"],
    }
    for name, values in enums.items():
        values_sql = ", ".join(f"'{v}'" for v in values)
        conn.execute(sa.text(
            f"DO $$ BEGIN "
            f"  CREATE TYPE {name} AS ENUM ({values_sql}); "
            f"EXCEPTION WHEN duplicate_object THEN null; "
            f"END $$;"
        ))


# ═══════════════════════════════════════════════════════════════════════
# TABLE CREATION FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

def _create_users() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("email",         sa.String(255), nullable=False),
        sa.Column("full_name",     sa.String(255), nullable=False),
        sa.Column("role",          postgresql.ENUM(name="user_role"), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("totp_secret_encrypted", sa.Text, nullable=True),
        sa.Column("totp_enabled",  sa.Boolean, server_default="FALSE"),
        sa.Column("failed_login_attempts", sa.Integer, server_default="0"),
        sa.Column("locked_until",  sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("phone",         sa.String(50), nullable=True),
        sa.Column("designation",   sa.String(255), nullable=True),
        sa.Column("avatar_url",    sa.Text, nullable=True),
        sa.Column("is_active",     sa.Boolean, server_default="TRUE"),
        sa.Column("created_at",    sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",    sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("idx_users_email", "users", ["email"])
    op.create_index("idx_users_role",  "users", ["role"])


def _create_companies() -> None:
    op.create_table(
        "companies",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("registration_number",    sa.String(100), nullable=False),
        sa.Column("company_name",           sa.String(500), nullable=False),
        sa.Column("company_name_search",    postgresql.TSVECTOR, nullable=True),
        sa.Column("company_type",           postgresql.ENUM(name="company_type"), nullable=False),
        sa.Column("company_status",         postgresql.ENUM(name="company_status"),
                  server_default="ACTIVE", nullable=False),
        sa.Column("lifecycle_stage",        postgresql.ENUM(name="lifecycle_stage"),
                  server_default="INCORPORATION", nullable=False),
        sa.Column("incorporation_date",     sa.Date, nullable=False),
        sa.Column("financial_year_end",     sa.Date, nullable=False),
        sa.Column("registered_address",     sa.Text, nullable=True),
        sa.Column("industry_sector",        sa.String(255), nullable=True),
        sa.Column("tin_number",             sa.String(100), nullable=True),
        sa.Column("vat_number",             sa.String(100), nullable=True),
        sa.Column("authorized_capital_bdt", sa.Numeric(20, 2), nullable=True),
        sa.Column("paid_up_capital_bdt",    sa.Numeric(20, 2), nullable=True),
        # Compliance state
        sa.Column("current_compliance_score", sa.Integer, nullable=True),
        sa.Column("current_risk_band",      postgresql.ENUM(name="risk_band"), nullable=True),
        sa.Column("current_exposure_band",  postgresql.ENUM(name="exposure_band"), nullable=True),
        sa.Column("last_evaluated_at",      sa.DateTime(timezone=True), nullable=True),
        sa.Column("rescue_required",        sa.Boolean, server_default="FALSE"),
        sa.Column("rescue_triggered_at",    sa.DateTime(timezone=True), nullable=True),
        # AGM state
        sa.Column("first_agm_held",         sa.Boolean, server_default="FALSE"),
        sa.Column("last_agm_date",          sa.Date, nullable=True),
        sa.Column("agm_default_count",      sa.Integer, server_default="0"),
        # Audit state
        sa.Column("first_auditor_appointed",  sa.Boolean, server_default="FALSE"),
        sa.Column("last_audit_signed_date",   sa.Date, nullable=True),
        # Returns state
        sa.Column("last_return_filed_year", sa.Integer, nullable=True),
        sa.Column("unfiled_returns_count",  sa.Integer, server_default="0"),
        # Revenue intelligence (admin-only)
        sa.Column("revenue_tier",           postgresql.ENUM(name="revenue_tier"), nullable=True),
        sa.Column("estimated_fee_bdt",      sa.Numeric(15, 2), nullable=True),
        sa.Column("client_since",           sa.Date, nullable=True),
        sa.Column("assigned_staff_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("internal_notes",         sa.Text, nullable=True),
        sa.Column("is_active",              sa.Boolean, server_default="TRUE"),
        sa.Column("created_at",             sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",             sa.DateTime(timezone=True), server_default=sa.func.now()),
        # Constraints
        sa.UniqueConstraint("registration_number", name="uq_companies_reg_no"),
        sa.CheckConstraint(
            "current_compliance_score BETWEEN 0 AND 100",
            name="ck_companies_score_range"
        ),
    )
    op.create_index("idx_companies_reg_no",    "companies", ["registration_number"])
    op.create_index("idx_companies_status",    "companies", ["company_status"])
    op.create_index("idx_companies_risk_band", "companies", ["current_risk_band"])
    op.create_index("idx_companies_rescue",    "companies", ["rescue_required"])
    # GIN index for full-text search — cannot use op.create_index() for GIN on TSVECTOR
    op.execute(
        "CREATE INDEX idx_companies_name_search "
        "ON companies USING GIN(company_name_search)"
    )
    op.create_index("idx_companies_risk_active", "companies",
                    ["current_risk_band", "is_active"])


def _create_company_user_access() -> None:
    op.create_table(
        "company_user_access",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id",    postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("can_edit",             sa.Boolean, server_default="FALSE"),
        sa.Column("can_view_financials",  sa.Boolean, server_default="FALSE"),
        sa.Column("granted_by",  postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("granted_at",  sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active",   sa.Boolean, server_default="TRUE"),
        sa.Column("created_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("company_id", "user_id", name="uq_company_user_access"),
    )
    op.create_index("idx_cua_company", "company_user_access", ["company_id"])
    op.create_index("idx_cua_user",    "company_user_access", ["user_id"])


def _create_directors() -> None:
    op.create_table(
        "directors",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("full_name",           sa.String(500), nullable=False),
        sa.Column("father_name",         sa.String(500), nullable=True),
        sa.Column("nid_number",          sa.String(100), nullable=True),
        sa.Column("passport_number",     sa.String(100), nullable=True),
        sa.Column("nationality",         sa.String(100), nullable=True),
        sa.Column("address",             sa.Text, nullable=True),
        sa.Column("appointment_date",         sa.Date, nullable=True),
        sa.Column("appointment_filed_date",   sa.Date, nullable=True),
        sa.Column("appointment_filing_delayed", sa.Boolean, server_default="FALSE"),
        sa.Column("appointment_delay_days",   sa.Integer, server_default="0"),
        sa.Column("director_status", postgresql.ENUM(name="director_status"),
                  server_default="ACTIVE", nullable=False),
        sa.Column("departure_date",          sa.Date, nullable=True),
        sa.Column("departure_filed_date",    sa.Date, nullable=True),
        sa.Column("departure_filing_delayed", sa.Boolean, server_default="FALSE"),
        sa.Column("departure_delay_days",    sa.Integer, server_default="0"),
        sa.Column("departed_still_liable",   sa.Boolean, server_default="FALSE"),
        sa.Column("shares_held",             sa.Integer, server_default="0"),
        sa.Column("is_managing_director",    sa.Boolean, server_default="FALSE"),
        sa.Column("is_chairman",             sa.Boolean, server_default="FALSE"),
        sa.Column("is_active",   sa.Boolean, server_default="TRUE"),
        sa.Column("created_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_directors_company", "directors", ["company_id"])
    op.create_index("idx_directors_status",  "directors", ["director_status"])
    op.execute(
        "CREATE INDEX idx_directors_liable ON directors(departed_still_liable) "
        "WHERE departed_still_liable = TRUE"
    )


def _create_shareholders() -> None:
    op.create_table(
        "shareholders",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("shareholder_name",    sa.String(500), nullable=False),
        sa.Column("shareholder_type",    sa.String(50), server_default="INDIVIDUAL"),
        sa.Column("nid_or_reg_number",   sa.String(100), nullable=True),
        sa.Column("nationality",         sa.String(100), nullable=True),
        sa.Column("address",             sa.Text, nullable=True),
        sa.Column("shares_held",         sa.Integer, nullable=False, server_default="0"),
        sa.Column("share_class",         sa.String(50), server_default="ORDINARY"),
        sa.Column("percentage_holding",  sa.Numeric(5, 2), nullable=True),
        sa.Column("effective_date",      sa.Date, nullable=True),
        sa.Column("share_certificate_issued", sa.Boolean, server_default="FALSE"),
        sa.Column("certificate_issue_date",   sa.Date, nullable=True),
        sa.Column("certificate_delay_days",   sa.Integer, server_default="0"),
        sa.Column("change_filed_with_rjsc",   sa.Boolean, server_default="TRUE"),
        sa.Column("rjsc_filing_date",    sa.Date, nullable=True),
        sa.Column("is_active",   sa.Boolean, server_default="TRUE"),
        sa.Column("created_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_shareholders_company", "shareholders", ["company_id"])


def _create_share_transfers() -> None:
    op.create_table(
        "share_transfers",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("transferor_name", sa.String(500), nullable=False),
        sa.Column("transferee_name", sa.String(500), nullable=False),
        sa.Column("transferor_shareholder_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("shareholders.id"), nullable=True),
        sa.Column("transferee_shareholder_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("shareholders.id"), nullable=True),
        sa.Column("shares_transferred",   sa.Integer, nullable=False),
        sa.Column("transfer_date",        sa.Date, nullable=True),
        sa.Column("consideration_bdt",    sa.Numeric(20, 2), nullable=True),
        sa.Column("transfer_status", postgresql.ENUM(name="transfer_status"),
                  server_default="COMPLETE", nullable=False),
        sa.Column("has_transfer_instrument",  sa.Boolean, server_default="TRUE"),
        sa.Column("stamp_duty_paid",          sa.Boolean, server_default="TRUE"),
        sa.Column("stamp_duty_amount_bdt",    sa.Numeric(15, 2), nullable=True),
        sa.Column("board_approval_obtained",  sa.Boolean, server_default="TRUE"),
        sa.Column("board_approval_date",      sa.Date, nullable=True),
        sa.Column("register_updated",         sa.Boolean, server_default="TRUE"),
        sa.Column("register_update_date",     sa.Date, nullable=True),
        sa.Column("aoa_restriction_violated", sa.Boolean, server_default="FALSE"),
        sa.Column("is_irregular",    sa.Boolean, server_default="FALSE"),
        sa.Column("irregularity_notes", sa.Text, nullable=True),
        sa.Column("is_active",   sa.Boolean, server_default="TRUE"),
        sa.Column("created_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_transfers_company",   "share_transfers", ["company_id"])
    op.execute(
        "CREATE INDEX idx_transfers_irregular ON share_transfers(is_irregular) "
        "WHERE is_irregular = TRUE"
    )


def _create_agms() -> None:
    op.create_table(
        "agms",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("financial_year",   sa.Integer, nullable=False),
        sa.Column("agm_type",         sa.String(50), server_default="ANNUAL"),
        sa.Column("agm_deadline",     sa.Date, nullable=True),
        sa.Column("notice_sent_date", sa.Date, nullable=True),
        sa.Column("notice_days_before", sa.Integer, nullable=True),
        sa.Column("notice_defective", sa.Boolean, server_default="FALSE"),
        sa.Column("notice_missing",   sa.Boolean, server_default="FALSE"),
        sa.Column("agm_held",         sa.Boolean, server_default="FALSE"),
        sa.Column("agm_date",         sa.Date, nullable=True),
        sa.Column("is_default",       sa.Boolean, server_default="FALSE"),
        sa.Column("delay_days",       sa.Integer, server_default="0"),
        sa.Column("quorum_met",       sa.Boolean, server_default="TRUE"),
        sa.Column("members_present",  sa.Integer, server_default="0"),
        sa.Column("quorum_required",  sa.Integer, server_default="2"),
        sa.Column("auditor_reappointed", sa.Boolean, server_default="TRUE"),
        sa.Column("minutes_prepared", sa.Boolean, server_default="FALSE"),
        sa.Column("minutes_document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("minutes_filed_rjsc",  sa.Boolean, server_default="FALSE"),
        sa.Column("rjsc_filing_date",    sa.Date, nullable=True),
        sa.Column("is_active",   sa.Boolean, server_default="TRUE"),
        sa.Column("created_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("company_id", "financial_year", name="uq_agms_company_year"),
    )
    op.create_index("idx_agms_company",  "agms", ["company_id"])
    op.create_index("idx_agms_deadline", "agms", ["agm_deadline"])
    op.execute("CREATE INDEX idx_agms_default ON agms(is_default) WHERE is_default = TRUE")
    op.create_index("idx_agms_company_year", "agms", ["company_id", sa.text("financial_year DESC")])


def _create_audits() -> None:
    op.create_table(
        "audits",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("financial_year",   sa.Integer, nullable=False),
        sa.Column("audit_type",       sa.String(50), server_default="ANNUAL"),
        sa.Column("auditor_name",     sa.String(500), nullable=True),
        sa.Column("auditor_firm",     sa.String(500), nullable=True),
        sa.Column("icab_number",      sa.String(100), nullable=True),
        sa.Column("first_auditor_appointed",          sa.Boolean, server_default="FALSE"),
        sa.Column("first_auditor_appointment_date",   sa.Date, nullable=True),
        sa.Column("first_auditor_delay_days",         sa.Integer, server_default="0"),
        sa.Column("audit_complete",         sa.Boolean, server_default="FALSE"),
        sa.Column("audit_signed_date",      sa.Date, nullable=True),
        sa.Column("agm_held_without_audit", sa.Boolean, server_default="FALSE"),
        sa.Column("is_missing",     sa.Boolean, server_default="FALSE"),
        sa.Column("delay_days",     sa.Integer, server_default="0"),
        sa.Column("report_qualified",    sa.Boolean, server_default="FALSE"),
        sa.Column("qualification_notes", sa.Text, nullable=True),
        sa.Column("document_id",     postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active",   sa.Boolean, server_default="TRUE"),
        sa.Column("created_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("company_id", "financial_year", name="uq_audits_company_year"),
    )
    op.create_index("idx_audits_company", "audits", ["company_id"])
    op.execute("CREATE INDEX idx_audits_missing ON audits(is_missing) WHERE is_missing = TRUE")


def _create_annual_returns() -> None:
    op.create_table(
        "annual_returns",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("financial_year",    sa.Integer, nullable=False),
        sa.Column("filing_deadline",   sa.Date, nullable=True),
        sa.Column("is_default",        sa.Boolean, server_default="FALSE"),
        sa.Column("filed_date",        sa.Date, nullable=True),
        sa.Column("delay_days",        sa.Integer, server_default="0"),
        sa.Column("rjsc_receipt_number", sa.String(255), nullable=True),
        sa.Column("is_complete",       sa.Boolean, server_default="TRUE"),
        sa.Column("missing_attachments", sa.Text, nullable=True),
        sa.Column("filing_fee_paid_bdt", sa.Numeric(12, 2), nullable=True),
        sa.Column("late_fee_paid_bdt",   sa.Numeric(12, 2), nullable=True),
        sa.Column("is_active",   sa.Boolean, server_default="TRUE"),
        sa.Column("created_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("company_id", "financial_year", name="uq_returns_company_year"),
    )
    op.create_index("idx_returns_company",     "annual_returns", ["company_id"])
    op.execute("CREATE INDEX idx_returns_default ON annual_returns(is_default) WHERE is_default = TRUE")
    op.create_index("idx_returns_company_year", "annual_returns",
                    ["company_id", sa.text("financial_year DESC")])


def _create_compliance_events() -> None:
    op.create_table(
        "compliance_events",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type",    sa.String(100), nullable=False),
        sa.Column("event_date",    sa.Date, nullable=False),
        sa.Column("description",   sa.Text, nullable=False),
        sa.Column("action",        postgresql.ENUM(name="event_action"), nullable=False),
        sa.Column("performed_by",  postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reference_id",  postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("detail",        postgresql.JSONB, nullable=True),
        sa.Column("created_at",    sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",    sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_events_company", "compliance_events", ["company_id"])
    op.create_index("idx_events_type",    "compliance_events", ["event_type"])
    op.create_index("idx_events_date",    "compliance_events", [sa.text("event_date DESC")])


def _create_compliance_flags() -> None:
    op.create_table(
        "compliance_flags",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rule_id",         sa.String(50),  nullable=False),
        sa.Column("rule_version",    sa.String(20),  nullable=False),
        sa.Column("flag_code",       sa.String(100), nullable=False),
        sa.Column("statutory_basis", sa.String(500), nullable=False),
        sa.Column("severity",        postgresql.ENUM(name="severity_level"), nullable=False),
        sa.Column("score_impact",    sa.Integer, nullable=False, server_default="0"),
        sa.Column("exposure_band",   postgresql.ENUM(name="exposure_band"), nullable=True),
        sa.Column("revenue_tier",    postgresql.ENUM(name="revenue_tier"), nullable=False),
        sa.Column("flag_status",     postgresql.ENUM(name="flag_status"),
                  server_default="ACTIVE", nullable=False),
        sa.Column("triggered_date",  sa.Date, nullable=False),
        sa.Column("resolved_date",   sa.Date, nullable=True),
        sa.Column("resolved_by",     postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resolution_notes", sa.Text, nullable=True),
        sa.Column("description",     sa.Text, nullable=False),
        sa.Column("detail",          postgresql.JSONB, nullable=True),
        sa.Column("notification_sent", sa.Boolean, server_default="FALSE"),
        sa.Column("created_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_flags_company",  "compliance_flags", ["company_id"])
    op.create_index("idx_flags_severity", "compliance_flags", ["severity"])
    op.create_index("idx_flags_rule",     "compliance_flags", ["rule_id"])
    op.execute(
        "CREATE INDEX idx_flags_active ON compliance_flags(company_id, flag_status) "
        "WHERE flag_status = 'ACTIVE'"
    )
    op.create_index("idx_flags_company_active", "compliance_flags",
                    ["company_id", "flag_status", "severity"])


def _create_compliance_score_history() -> None:
    op.create_table(
        "compliance_score_history",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("score",           sa.Integer, nullable=False),
        sa.Column("risk_band",       postgresql.ENUM(name="risk_band"), nullable=False),
        sa.Column("snapshot_month",  sa.Date, nullable=False),
        sa.Column("calculated_at",   sa.DateTime(timezone=True), nullable=False),
        sa.Column("agm_score",         sa.Integer, nullable=True),
        sa.Column("audit_score",       sa.Integer, nullable=True),
        sa.Column("return_score",      sa.Integer, nullable=True),
        sa.Column("director_score",    sa.Integer, nullable=True),
        sa.Column("shareholding_score", sa.Integer, nullable=True),
        sa.Column("active_flags_count", sa.Integer, server_default="0"),
        sa.Column("black_flags_count",  sa.Integer, server_default="0"),
        sa.Column("override_applied",   sa.Boolean, server_default="FALSE"),
        sa.Column("score_hash",      sa.String(64), nullable=False),
        sa.Column("engine_version",  sa.String(20), nullable=False),
        sa.Column("trigger_source",  sa.String(100), server_default="CRON"),
        sa.UniqueConstraint("company_id", "snapshot_month",
                            name="uq_score_snapshot_month"),
        sa.CheckConstraint("score BETWEEN 0 AND 100",
                           name="ck_score_history_range"),
    )
    op.create_index("idx_score_history_company",  "compliance_score_history", ["company_id"])
    op.create_index("idx_score_history_snapshot", "compliance_score_history",
                    ["company_id", sa.text("snapshot_month DESC")])
    op.create_index("idx_score_history_recent",   "compliance_score_history",
                    ["company_id", sa.text("calculated_at DESC")])


def _create_legal_rules() -> None:
    op.create_table(
        "legal_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("rule_id",             sa.String(50), nullable=False),
        sa.Column("rule_name",           sa.String(500), nullable=False),
        sa.Column("rule_type",           postgresql.ENUM(name="rule_type"), nullable=False),
        sa.Column("statutory_basis",     sa.String(1000), nullable=False),
        sa.Column("statutory_effective_date", sa.Date, nullable=True),
        sa.Column("description",         sa.Text, nullable=False),
        sa.Column("rule_condition",      postgresql.JSONB, nullable=True),
        sa.Column("default_severity",    postgresql.ENUM(name="severity_level"), nullable=False),
        sa.Column("score_impact",        sa.Integer, nullable=False, server_default="0"),
        sa.Column("revenue_tier",        postgresql.ENUM(name="revenue_tier"), nullable=False),
        sa.Column("is_black_override",   sa.Boolean, server_default="FALSE"),
        sa.Column("rule_version",        sa.String(20), nullable=False, server_default="1.0"),
        sa.Column("is_active",           sa.Boolean, server_default="TRUE"),
        sa.Column("created_by",          postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=True),
        sa.Column("last_modified_by",    postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=True),
        sa.Column("last_modified_at",    sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("rule_id", name="uq_legal_rules_rule_id"),
    )
    op.execute("CREATE INDEX idx_rules_active ON legal_rules(rule_id) WHERE is_active = TRUE")
    op.create_index("idx_rules_type", "legal_rules", ["rule_type"])


def _create_legal_rule_versions() -> None:
    op.create_table(
        "legal_rule_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("rule_id",              sa.String(50),
                  sa.ForeignKey("legal_rules.rule_id"), nullable=False),
        sa.Column("version",              sa.String(20), nullable=False),
        sa.Column("change_reason",        sa.Text, nullable=False),
        sa.Column("changed_by",           postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=False),
        sa.Column("changed_at",           sa.DateTime(timezone=True), nullable=False),
        sa.Column("previous_definition",  postgresql.JSONB, nullable=False),
        sa.Column("sro_reference",        sa.String(255), nullable=True),
        sa.UniqueConstraint("rule_id", "version", name="uq_rule_versions"),
    )
    op.create_index("idx_rule_versions_rule", "legal_rule_versions", ["rule_id"])


def _create_rescue_plans() -> None:
    op.create_table(
        "rescue_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plan_name",          sa.String(500), nullable=False),
        sa.Column("revenue_tier",       postgresql.ENUM(name="revenue_tier"), nullable=False),
        sa.Column("initial_risk_band",  sa.String(20), nullable=False),
        sa.Column("initial_score",      sa.Integer, nullable=False),
        sa.Column("years_in_default",   sa.Integer, server_default="0"),
        sa.Column("is_active",          sa.Boolean, server_default="TRUE"),
        sa.Column("started_at",         sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at",       sa.DateTime(timezone=True), nullable=True),
        sa.Column("target_completion_date", sa.Date, nullable=True),
        sa.Column("total_steps",        sa.Integer, server_default="8"),
        sa.Column("completed_steps",    sa.Integer, server_default="0"),
        sa.Column("blocked_steps",      sa.Integer, server_default="0"),
        sa.Column("completion_percentage", sa.Integer, server_default="0"),
        sa.Column("quoted_fee_bdt",     sa.Numeric(15, 2), nullable=True),
        sa.Column("confirmed_fee_bdt",  sa.Numeric(15, 2), nullable=True),
        sa.Column("assigned_staff_id",  postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_by",         postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_rescue_company", "rescue_plans", ["company_id"])
    op.execute("CREATE INDEX idx_rescue_active ON rescue_plans(is_active) WHERE is_active = TRUE")


def _create_rescue_steps() -> None:
    op.create_table(
        "rescue_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("rescue_plan_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("rescue_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id",     postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_number",     sa.Integer, nullable=False),
        sa.Column("step_title",      sa.String(500), nullable=False),
        sa.Column("step_description", sa.Text, nullable=False),
        sa.Column("statutory_basis", sa.String(500), nullable=True),
        sa.Column("complexity",  postgresql.ENUM(name="complexity_level"),
                  server_default="MEDIUM", nullable=False),
        sa.Column("estimated_days_min",     sa.Integer, server_default="7"),
        sa.Column("estimated_days_max",     sa.Integer, server_default="21"),
        sa.Column("target_completion_date", sa.Date, nullable=True),
        sa.Column("step_status",  postgresql.ENUM(name="rescue_step_status"),
                  server_default="PENDING", nullable=False),
        sa.Column("started_at",     sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at",   sa.DateTime(timezone=True), nullable=True),
        sa.Column("blocked_reason", sa.Text, nullable=True),
        sa.Column("completion_notes", sa.Text, nullable=True),
        sa.Column("assigned_staff_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=True),
        sa.Column("updated_by",      postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=True),
        sa.Column("triggers_reevaluation", sa.Boolean, server_default="TRUE"),
        sa.Column("created_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("rescue_plan_id", "step_number",
                            name="uq_rescue_step_number"),
    )
    op.create_index("idx_rescue_steps_plan",     "rescue_steps", ["rescue_plan_id"])
    op.create_index("idx_rescue_steps_assigned", "rescue_steps", ["assigned_staff_id"])


def _create_tasks() -> None:
    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title",         sa.String(500), nullable=False),
        sa.Column("description",   sa.Text, nullable=True),
        sa.Column("task_status",   postgresql.ENUM(name="task_status"),
                  server_default="PENDING", nullable=False),
        sa.Column("priority",      postgresql.ENUM(name="task_priority"),
                  server_default="MEDIUM", nullable=False),
        sa.Column("due_date",      sa.Date, nullable=True),
        sa.Column("completed_at",  sa.DateTime(timezone=True), nullable=True),
        sa.Column("assigned_to",   postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_by",    postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=True),
        sa.Column("source_flag_id",         postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_rescue_step_id",  postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active",   sa.Boolean, server_default="TRUE"),
        sa.Column("created_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_tasks_company",  "tasks", ["company_id"])
    op.create_index("idx_tasks_assigned", "tasks", ["assigned_to"])
    op.create_index("idx_tasks_status",   "tasks", ["task_status"])
    op.create_index("idx_tasks_priority", "tasks", ["priority"])
    op.create_index("idx_tasks_company_status", "tasks",
                    ["company_id", "task_status", "priority"])


def _create_engagements() -> None:
    op.create_table(
        "engagements",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("engagement_title",  sa.String(500), nullable=False),
        sa.Column("engagement_type",   sa.String(100), nullable=False),
        sa.Column("engagement_status", postgresql.ENUM(name="engagement_status"),
                  server_default="IDENTIFIED", nullable=False),
        sa.Column("revenue_tier",      postgresql.ENUM(name="revenue_tier"), nullable=False),
        sa.Column("complexity",        postgresql.ENUM(name="complexity_level"),
                  server_default="MEDIUM", nullable=False),
        sa.Column("triggered_by_risk_band", sa.String(20), nullable=True),
        sa.Column("rescue_plan_id",    postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("identified_date",   sa.Date, nullable=False),
        sa.Column("quoted_date",       sa.Date, nullable=True),
        sa.Column("confirmed_date",    sa.Date, nullable=True),
        sa.Column("started_date",      sa.Date, nullable=True),
        sa.Column("completed_date",    sa.Date, nullable=True),
        sa.Column("target_completion_date", sa.Date, nullable=True),
        sa.Column("estimated_fee_bdt", sa.Numeric(15, 2), nullable=True),
        sa.Column("quoted_fee_bdt",    sa.Numeric(15, 2), nullable=True),
        sa.Column("confirmed_fee_bdt", sa.Numeric(15, 2), nullable=True),
        sa.Column("invoiced_bdt",      sa.Numeric(15, 2), nullable=True),
        sa.Column("collected_bdt",     sa.Numeric(15, 2), nullable=True),
        sa.Column("assigned_staff_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=True),
        sa.Column("notes",     sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, server_default="TRUE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_engagements_company", "engagements", ["company_id"])
    op.create_index("idx_engagements_status",  "engagements", ["engagement_status"])
    op.create_index("idx_engagements_tier",    "engagements", ["revenue_tier"])
    op.create_index("idx_engagements_active",  "engagements",
                    ["company_id", "engagement_status"])


def _create_quotations() -> None:
    op.create_table(
        "quotations",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("engagement_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("engagements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("company_id",    postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("quotation_number",    sa.String(100), nullable=False),
        sa.Column("quotation_date",      sa.Date, nullable=False),
        sa.Column("valid_until",         sa.Date, nullable=True),
        sa.Column("professional_fee_bdt", sa.Numeric(15, 2), nullable=False),
        sa.Column("government_fee_bdt",   sa.Numeric(15, 2), nullable=True),
        sa.Column("vat_bdt",             sa.Numeric(15, 2), nullable=True),
        sa.Column("total_bdt",           sa.Numeric(15, 2), nullable=False),
        sa.Column("status",              sa.String(50), server_default="DRAFT"),
        sa.Column("accepted_date",       sa.Date, nullable=True),
        sa.Column("rejection_reason",    sa.Text, nullable=True),
        sa.Column("line_items",          postgresql.JSONB, nullable=True),
        sa.Column("notes",               sa.Text, nullable=True),
        sa.Column("created_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("quotation_number", name="uq_quotation_number"),
    )


def _create_documents() -> None:
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_type",     postgresql.ENUM(name="document_type"), nullable=False),
        sa.Column("title",             sa.String(500), nullable=False),
        sa.Column("financial_year",    sa.Integer, nullable=True),
        sa.Column("version",           sa.Integer, server_default="1"),
        sa.Column("s3_key",            sa.Text, nullable=True),
        sa.Column("file_size_bytes",   sa.Integer, nullable=True),
        sa.Column("mime_type",         sa.String(100), nullable=True),
        sa.Column("checksum_sha256",   sa.String(64), nullable=True),
        # AI Governance — AI Constitution Article 3
        sa.Column("ai_generated",      sa.Boolean, server_default="FALSE"),
        sa.Column("ai_model_used",     postgresql.ENUM(name="ai_model"), nullable=True),
        sa.Column("ai_output_log_id",  postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("in_review_queue",   sa.Boolean, server_default="TRUE",
                  comment="AI Constitution Art.3: TRUE until human reviews"),
        sa.Column("human_approved",    sa.Boolean, server_default="FALSE"),
        sa.Column("approved_by",       postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=True),
        sa.Column("approved_at",       sa.DateTime(timezone=True), nullable=True),
        sa.Column("auto_sent_blocked", sa.Boolean, server_default="TRUE",
                  comment="AI Constitution Art.3: ALWAYS TRUE"),
        sa.Column("is_client_visible", sa.Boolean, server_default="FALSE"),
        sa.Column("client_released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by",        postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=True),
        sa.Column("notes",    sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, server_default="TRUE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_documents_company", "documents", ["company_id"])
    op.create_index("idx_documents_type",    "documents", ["document_type"])
    op.create_index("idx_documents_ai",      "documents", ["ai_generated", "human_approved"])


def _create_document_access_log() -> None:
    op.create_table(
        "document_access_log",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("accessed_by", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=False),
        sa.Column("access_type",  sa.String(50), nullable=False),
        sa.Column("ip_address",   sa.String(45), nullable=True),
        sa.Column("accessed_at",  sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at",   sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",   sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_doc_access_document", "document_access_log", ["document_id"])
    op.create_index("idx_doc_access_user",     "document_access_log", ["accessed_by"])


def _create_notifications() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=True),
        sa.Column("user_id",    postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
        sa.Column("title",                  sa.String(500), nullable=False),
        sa.Column("body",                   sa.Text, nullable=False),
        sa.Column("notification_type",      sa.String(100), nullable=False),
        sa.Column("channel",                postgresql.ENUM(name="notification_channel"), nullable=False),
        sa.Column("notification_status",    postgresql.ENUM(name="notification_status"),
                  server_default="PENDING", nullable=False),
        sa.Column("scheduled_for",          sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at",                sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_at",        sa.DateTime(timezone=True), nullable=True),
        sa.Column("days_until_deadline",    sa.Integer, nullable=True),
        sa.Column("related_flag_id",        postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("failure_reason",         sa.Text, nullable=True),
        sa.Column("retry_count",            sa.Integer, server_default="0"),
        sa.Column("created_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_notifications_company", "notifications", ["company_id"])
    op.create_index("idx_notifications_user",    "notifications", ["user_id"])
    op.execute(
        "CREATE INDEX idx_notifications_pending ON notifications(notification_status) "
        "WHERE notification_status = 'PENDING'"
    )


def _create_sro_registry() -> None:
    op.create_table(
        "sro_registry",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("sro_number",         sa.String(100), nullable=False),
        sa.Column("sro_type",           postgresql.ENUM(name="sro_type"), nullable=False),
        sa.Column("title",              sa.String(1000), nullable=False),
        sa.Column("description",        sa.Text, nullable=True),
        sa.Column("effective_date",     sa.Date, nullable=False),
        sa.Column("gazette_reference",  sa.String(255), nullable=True),
        sa.Column("affected_rule_ids",  postgresql.JSONB, nullable=True),
        sa.Column("rule_update_required", sa.Boolean, server_default="FALSE"),
        sa.Column("rule_updated_at",    sa.DateTime(timezone=True), nullable=True),
        sa.Column("rule_updated_by",    postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=True),
        sa.Column("source_url",         sa.Text, nullable=True),
        sa.Column("entered_by",         postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=False),
        sa.Column("verified_by",        postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=True),
        sa.Column("is_active",   sa.Boolean, server_default="TRUE"),
        sa.Column("created_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("sro_number", name="uq_sro_number"),
    )


def _create_statutory_registers() -> None:
    op.create_table(
        "statutory_registers",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("register_type",     sa.String(100), nullable=False),
        sa.Column("is_maintained",     sa.Boolean, server_default="FALSE"),
        sa.Column("last_updated_date", sa.Date, nullable=True),
        sa.Column("location",          sa.String(500), nullable=True),
        sa.Column("notes",             sa.Text, nullable=True),
        sa.Column("created_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("company_id", "register_type",
                            name="uq_statutory_register_type"),
    )


def _create_registered_office_history() -> None:
    op.create_table(
        "registered_office_history",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("companies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("address",         sa.Text, nullable=False),
        sa.Column("effective_date",  sa.Date, nullable=False),
        sa.Column("change_date",     sa.Date, nullable=True),
        sa.Column("filed_with_rjsc", sa.Boolean, server_default="FALSE"),
        sa.Column("rjsc_filing_date", sa.Date, nullable=True),
        sa.Column("filing_delay_days", sa.Integer, server_default="0"),
        sa.Column("is_current",      sa.Boolean, server_default="TRUE"),
        sa.Column("created_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_office_history_company", "registered_office_history", ["company_id"])


def _create_ai_prompt_templates() -> None:
    op.create_table(
        "ai_prompt_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("template_name",      sa.String(255), nullable=False),
        sa.Column("document_type",      postgresql.ENUM(name="document_type"), nullable=False),
        sa.Column("version",            sa.String(20), nullable=False, server_default="1.0"),
        sa.Column("system_prompt",      sa.Text, nullable=False),
        sa.Column("user_prompt_template", sa.Text, nullable=False),
        sa.Column("output_format_instructions", sa.Text, nullable=True),
        sa.Column("required_placeholders",      postgresql.JSONB, nullable=True),
        sa.Column("liability_disclaimer",        sa.Text, nullable=False),
        sa.Column("is_active",          sa.Boolean, server_default="TRUE"),
        sa.Column("approved_by",        postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=True),
        sa.Column("approved_at",        sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by",         postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("template_name", name="uq_template_name"),
    )


def _create_ai_output_log() -> None:
    op.create_table(
        "ai_output_log",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("company_id",     postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("template_id",    postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("ai_prompt_templates.id"), nullable=True),
        sa.Column("document_type",  postgresql.ENUM(name="document_type"), nullable=True),
        sa.Column("ai_model",       postgresql.ENUM(name="ai_model"), nullable=False),
        sa.Column("prompt_hash",    sa.String(64), nullable=False),
        sa.Column("output_token_count", sa.Integer, nullable=True),
        sa.Column("in_review_queue",    sa.Boolean, server_default="TRUE"),
        sa.Column("human_approved",     sa.Boolean, server_default="FALSE"),
        sa.Column("approved_by",        postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_at",        sa.DateTime(timezone=True), nullable=True),
        sa.Column("was_modified_before_approval", sa.Boolean, server_default="FALSE"),
        sa.Column("was_rejected",       sa.Boolean, server_default="FALSE"),
        sa.Column("rejection_reason",   sa.Text, nullable=True),
        sa.Column("requested_by",       postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=True),
        sa.Column("requested_at",       sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",  sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_ai_log_company", "ai_output_log", ["company_id"])
    op.execute(
        "CREATE INDEX idx_ai_log_review ON ai_output_log(in_review_queue) "
        "WHERE in_review_queue = TRUE"
    )


def _create_user_activity_logs() -> None:
    op.create_table(
        "user_activity_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True),
                  server_default=sa.text("uuid_generate_v4()"), primary_key=True),
        sa.Column("user_id",       postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id"), nullable=True),
        sa.Column("company_id",    postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("companies.id"), nullable=True),
        sa.Column("action",        sa.String(200), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=True),
        sa.Column("resource_id",   postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("description",   sa.Text, nullable=True),
        sa.Column("ip_address",    sa.String(45), nullable=True),
        sa.Column("user_agent",    sa.Text, nullable=True),
        sa.Column("request_id",    sa.String(36), nullable=True),
        sa.Column("detail",        postgresql.JSONB, nullable=True),
        sa.Column("logged_at",     sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at",    sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at",    sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_activity_user",       "user_activity_logs", ["user_id"])
    op.create_index("idx_activity_company",    "user_activity_logs", ["company_id"])
    op.create_index("idx_activity_action",     "user_activity_logs", ["action"])
    op.create_index("idx_activity_logged_at",  "user_activity_logs",
                    [sa.text("logged_at DESC")])


# ═══════════════════════════════════════════════════════════════════════
# TRIGGERS
# ═══════════════════════════════════════════════════════════════════════

def _create_trigger_functions(conn) -> None:
    # ── updated_at auto-maintenance ───────────────────────────────
    conn.execute(sa.text("""
        CREATE OR REPLACE FUNCTION update_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """))

    # ── Full-text search vector for company name ──────────────────
    conn.execute(sa.text("""
        CREATE OR REPLACE FUNCTION update_company_search_vector()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.company_name_search =
                to_tsvector('english', COALESCE(NEW.company_name, ''))
                || to_tsvector('english', COALESCE(NEW.registration_number, ''));
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """))


def _create_triggers(conn) -> None:
    # Tables that need updated_at trigger
    tables_with_updated_at = [
        "users", "companies", "company_user_access",
        "directors", "shareholders", "share_transfers",
        "agms", "audits", "annual_returns",
        "compliance_events", "compliance_flags",
        "legal_rules", "rescue_plans", "rescue_steps",
        "tasks", "engagements", "quotations",
        "documents", "document_access_log",
        "notifications", "sro_registry",
        "statutory_registers", "registered_office_history",
        "ai_prompt_templates", "ai_output_log",
        "user_activity_logs",
    ]
    for table in tables_with_updated_at:
        conn.execute(sa.text(f"""
            CREATE TRIGGER trg_{table}_updated_at
            BEFORE UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION update_updated_at();
        """))

    # Full-text search trigger on companies
    conn.execute(sa.text("""
        CREATE TRIGGER trg_company_search
        BEFORE INSERT OR UPDATE ON companies
        FOR EACH ROW EXECUTE FUNCTION update_company_search_vector();
    """))


# ═══════════════════════════════════════════════════════════════════════
# COMPOSITE INDEXES (performance — added after all tables exist)
# ═══════════════════════════════════════════════════════════════════════

def _create_composite_indexes() -> None:
    pass  # All composite indexes already created inline above


# ═══════════════════════════════════════════════════════════════════════
# VIEWS
# ═══════════════════════════════════════════════════════════════════════

def _create_views(conn) -> None:
    # ── Admin Dashboard KPIs ─────────────────────────────────────
    conn.execute(sa.text("""
        CREATE VIEW vw_admin_dashboard_kpis AS
        SELECT
            COUNT(*)                                                         AS total_companies,
            COUNT(*) FILTER (WHERE is_active = TRUE)                        AS active_companies,
            COUNT(*) FILTER (WHERE current_risk_band = 'BLACK')             AS black_band_count,
            COUNT(*) FILTER (WHERE current_risk_band = 'RED')               AS red_band_count,
            COUNT(*) FILTER (WHERE current_risk_band = 'YELLOW')            AS yellow_band_count,
            COUNT(*) FILTER (WHERE current_risk_band = 'GREEN')             AS green_band_count,
            COUNT(*) FILTER (WHERE rescue_required = TRUE)                  AS rescue_required_count,
            ROUND(AVG(current_compliance_score), 1)                         AS avg_compliance_score,
            COUNT(*) FILTER (WHERE last_evaluated_at < NOW() - INTERVAL '7 days'
                             OR last_evaluated_at IS NULL)                  AS stale_evaluations
        FROM companies;
    """))

    # ── Risk Distribution ─────────────────────────────────────────
    conn.execute(sa.text("""
        CREATE VIEW vw_risk_distribution AS
        SELECT
            current_risk_band                           AS risk_band,
            COUNT(*)                                    AS company_count,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) AS percentage
        FROM companies
        WHERE is_active = TRUE
        GROUP BY current_risk_band
        ORDER BY
            CASE current_risk_band
                WHEN 'BLACK'  THEN 1
                WHEN 'RED'    THEN 2
                WHEN 'YELLOW' THEN 3
                WHEN 'GREEN'  THEN 4
                ELSE 5
            END;
    """))

    # ── Company Flag Summary ──────────────────────────────────────
    conn.execute(sa.text("""
        CREATE VIEW vw_company_flag_summary AS
        SELECT
            c.id                                AS company_id,
            c.company_name,
            c.registration_number,
            c.current_risk_band,
            c.current_compliance_score,
            COUNT(f.id)                         AS total_active_flags,
            COUNT(f.id) FILTER (WHERE f.severity = 'BLACK') AS black_flags,
            COUNT(f.id) FILTER (WHERE f.severity = 'RED')   AS red_flags,
            COUNT(f.id) FILTER (WHERE f.severity = 'YELLOW') AS yellow_flags,
            c.rescue_required,
            c.last_evaluated_at
        FROM companies c
        LEFT JOIN compliance_flags f
            ON f.company_id = c.id AND f.flag_status = 'ACTIVE'
        WHERE c.is_active = TRUE
        GROUP BY c.id, c.company_name, c.registration_number,
                 c.current_risk_band, c.current_compliance_score,
                 c.rescue_required, c.last_evaluated_at;
    """))

    # ── Revenue Pipeline ──────────────────────────────────────────
    conn.execute(sa.text("""
        CREATE VIEW vw_revenue_pipeline AS
        SELECT
            revenue_tier,
            engagement_status,
            COUNT(*)                                    AS engagement_count,
            SUM(estimated_fee_bdt)                      AS total_estimated_bdt,
            SUM(quoted_fee_bdt)                         AS total_quoted_bdt,
            SUM(confirmed_fee_bdt)                      AS total_confirmed_bdt,
            SUM(invoiced_bdt)                           AS total_invoiced_bdt,
            SUM(collected_bdt)                          AS total_collected_bdt
        FROM engagements
        WHERE is_active = TRUE
        GROUP BY revenue_tier, engagement_status
        ORDER BY revenue_tier, engagement_status;
    """))

    # ── Upcoming Deadlines ────────────────────────────────────────
    conn.execute(sa.text("""
        CREATE VIEW vw_upcoming_deadlines AS
        SELECT
            c.id            AS company_id,
            c.company_name,
            c.registration_number,
            'AGM'           AS deadline_type,
            a.agm_deadline  AS deadline_date,
            (a.agm_deadline - CURRENT_DATE) AS days_remaining,
            c.current_risk_band
        FROM companies c
        JOIN agms a ON a.company_id = c.id
        WHERE c.is_active = TRUE
          AND a.agm_held = FALSE
          AND a.agm_deadline IS NOT NULL
          AND a.agm_deadline >= CURRENT_DATE
        UNION ALL
        SELECT
            c.id,
            c.company_name,
            c.registration_number,
            'ANNUAL_RETURN'     AS deadline_type,
            ar.filing_deadline  AS deadline_date,
            (ar.filing_deadline - CURRENT_DATE) AS days_remaining,
            c.current_risk_band
        FROM companies c
        JOIN annual_returns ar ON ar.company_id = c.id
        WHERE c.is_active = TRUE
          AND ar.is_default = FALSE
          AND ar.filed_date IS NULL
          AND ar.filing_deadline IS NOT NULL
          AND ar.filing_deadline >= CURRENT_DATE
        ORDER BY days_remaining ASC;
    """))


# ═══════════════════════════════════════════════════════════════════════
# ROW-LEVEL SECURITY
# ═══════════════════════════════════════════════════════════════════════

def _enable_rls(conn) -> None:
    """
    Enable RLS on company-scoped tables.
    Policy: users can only see companies they have access to
    via company_user_access.
    Bypassed for: SUPER_ADMIN and ADMIN_STAFF roles (set via set_admin_context).
    """
    rls_tables = [
        "companies", "directors", "shareholders", "share_transfers",
        "agms", "audits", "annual_returns", "compliance_flags",
        "compliance_score_history", "rescue_plans", "rescue_steps",
        "tasks", "documents", "notifications",
        "statutory_registers", "registered_office_history",
    ]

    for table in rls_tables:
        conn.execute(sa.text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))

    # Policy: allow all for admin context (background jobs, SUPER_ADMIN)
    # Policy: allow per company_user_access for all other users
    conn.execute(sa.text("""
        CREATE POLICY companies_access_policy ON companies
        USING (
            current_setting('app.current_user_id', TRUE) = 'ADMIN'
            OR id IN (
                SELECT company_id FROM company_user_access
                WHERE user_id = current_setting('app.current_user_id', TRUE)::uuid
                  AND is_active = TRUE
            )
        );
    """))

    # For child tables — policy through company_id
    child_tables = [
        "directors", "shareholders", "share_transfers",
        "agms", "audits", "annual_returns", "compliance_flags",
        "compliance_score_history", "rescue_plans", "rescue_steps",
        "tasks", "documents", "notifications",
        "statutory_registers", "registered_office_history",
    ]
    for table in child_tables:
        conn.execute(sa.text(f"""
            CREATE POLICY {table}_company_policy ON {table}
            USING (
                current_setting('app.current_user_id', TRUE) = 'ADMIN'
                OR company_id IN (
                    SELECT company_id FROM company_user_access
                    WHERE user_id = current_setting('app.current_user_id', TRUE)::uuid
                      AND is_active = TRUE
                )
            );
        """))

    # Engagements — admin-only (revenue data)
    conn.execute(sa.text("ALTER TABLE engagements ENABLE ROW LEVEL SECURITY"))
    conn.execute(sa.text("""
        CREATE POLICY engagements_admin_only ON engagements
        USING (current_setting('app.current_user_id', TRUE) = 'ADMIN');
    """))


# ═══════════════════════════════════════════════════════════════════════
# DOWNGRADE
# ═══════════════════════════════════════════════════════════════════════
def downgrade() -> None:
    """
    Complete rollback — drops everything.
    WARNING: All data is permanently lost.
    NEVER run on production without explicit written approval.
    """
    conn = op.get_bind()

    # Drop views first
    for view in ["vw_upcoming_deadlines", "vw_revenue_pipeline",
                 "vw_company_flag_summary", "vw_risk_distribution",
                 "vw_admin_dashboard_kpis"]:
        conn.execute(sa.text(f"DROP VIEW IF EXISTS {view} CASCADE"))

    # Drop tables in reverse dependency order
    tables = [
        "user_activity_logs", "ai_output_log", "ai_prompt_templates",
        "registered_office_history", "statutory_registers", "sro_registry",
        "notifications", "document_access_log", "documents",
        "quotations", "engagements", "tasks",
        "rescue_steps", "rescue_plans",
        "legal_rule_versions", "legal_rules",
        "compliance_score_history", "compliance_flags", "compliance_events",
        "annual_returns", "audits", "agms",
        "share_transfers", "shareholders", "directors",
        "company_user_access", "companies", "users",
    ]
    for table in tables:
        conn.execute(sa.text(f"DROP TABLE IF EXISTS {table} CASCADE"))

    # Drop trigger functions
    conn.execute(sa.text("DROP FUNCTION IF EXISTS update_updated_at() CASCADE"))
    conn.execute(sa.text("DROP FUNCTION IF EXISTS update_company_search_vector() CASCADE"))

    # Drop ENUMs
    enum_names = [
        "risk_band", "severity_level", "exposure_band", "revenue_tier",
        "company_status", "lifecycle_stage", "company_type", "user_role",
        "flag_status", "task_priority", "task_status", "document_type",
        "event_action", "notification_channel", "notification_status",
        "transfer_status", "director_status", "engagement_status",
        "rescue_step_status", "complexity_level", "rule_type",
        "ai_model", "sro_type",
    ]
    for name in enum_names:
        conn.execute(sa.text(f"DROP TYPE IF EXISTS {name} CASCADE"))

