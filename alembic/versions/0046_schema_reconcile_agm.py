"""Forward-reconcile company ORM fields and AGM held evidence.

Revision ID: 0046_schema_reconcile_agm
Revises: 0045_agm_held_fields

The production Alembic marker may be ahead of physical DDL. This migration
repairs missing columns from historical 0031-0033 revisions and the AGM
held-record contract. It is additive and preserves unknown evidence as NULL.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects.postgresql import UUID

revision = "0046_schema_reconcile_agm"
down_revision = "0045_agm_held_fields"
branch_labels = None
depends_on = None

COMPANY_COLUMNS = [
    # 0031
    ("last_board_meeting_date", sa.Date()),
    ("board_meeting_notice_given", sa.Boolean()),
    ("board_minutes_prepared", sa.Boolean()),
    ("financial_statements_presented", sa.Boolean()),
    ("financial_statements_filed", sa.Boolean()),
    ("books_of_account_kept", sa.Boolean()),
    ("director_consent_filed", sa.Boolean()),
    ("director_office_of_profit", sa.Boolean()),
    ("managing_director_appointment_date", sa.Date()),
    ("member_count", sa.Integer()),
    ("articles_quorum_verified", sa.Boolean()),
    ("articles_quorum_required", sa.Integer()),
    ("articles_quorum_verified_by", sa.String(length=100)),
    ("articles_quorum_verified_at", sa.Date()),
    ("articles_quorum_evidence_ref", sa.String(length=500)),
    ("business_commencement_declaration_filed", sa.Boolean()),
    # 0032
    ("on_rjsc_strike_off_list", sa.Boolean()),
    ("rjsc_strike_off_notice_date", sa.Date()),
    ("rjsc_status", sa.String(length=50)),
    ("last_rjsc_compliance_date", sa.Date()),
    # 0033
    ("form_iii_filed_date", sa.Date()),
    ("form_iv_filed_date", sa.Date()),
    ("form_vi_filed", sa.Boolean()),
    ("form_vi_filed_date", sa.Date()),
    ("form_xv_filed_date", sa.Date()),
    ("special_resolution_filed_date", sa.Date()),
    ("paid_up_ge_authorized", sa.Boolean()),
    ("register_of_members_maintained", sa.Boolean()),
    ("register_of_directors_maintained", sa.Boolean()),
    ("register_of_charges_maintained", sa.Boolean()),
    ("minutes_book_agm_maintained", sa.Boolean()),
    ("minutes_book_board_maintained", sa.Boolean()),
    ("agm_scheduled_date", sa.Date()),
    ("notice_sent_date", sa.Date()),
    ("members_present_at_agm", sa.Integer()),
    ("auditor_reappointed_at_agm", sa.Boolean()),
    ("accounts_adopted_at_agm", sa.Boolean()),
    ("audit_in_progress", sa.Boolean()),
    ("first_auditor_appointment_date", sa.Date()),
    ("auditor_name", sa.String(length=255)),
    ("auditor_firm_reg_no", sa.String(length=100)),
    ("registered_office_address", sa.Text()),
    ("registered_office_change_date", sa.Date()),
    ("last_tax_return_filed_year", sa.Integer()),
    ("share_certificates_issued", sa.Boolean()),
    ("share_certificates_issued_date", sa.Date()),
    ("last_allotment_date", sa.Date()),
    ("shareholder_change_date", sa.Date()),
    ("is_dormant", sa.Boolean()),
    ("aoa_transfer_restriction", sa.Boolean()),
    ("capital_increase_date", sa.Date()),
    ("capital_increase_special_resolution", sa.Boolean()),
    ("minimum_directors_met", sa.Boolean()),
]

AGM_COLUMNS = [
    ("scheduled_date", sa.Date()),
    ("venue", sa.String(length=255)),
    ("accounts_adopted", sa.Boolean()),
    ("agm_held_without_audit", sa.Boolean()),
    ("quorum_basis", sa.String(length=64)),
    ("members_present_evidence_ref", sa.String(length=500)),
    ("members_total_at_agm", sa.Integer()),
    ("members_total_evidence_ref", sa.String(length=500)),
    ("articles_quorum_verified", sa.Boolean()),
    ("articles_quorum_required", sa.Integer()),
    ("articles_quorum_verified_by", sa.String(length=100)),
    ("articles_quorum_verified_at", sa.Date()),
    ("articles_quorum_evidence_ref", sa.String(length=500)),
]

AUDIT_COLUMNS = [
    ("first_auditor_appointed", sa.Boolean()),
    ("first_auditor_appointment_date", sa.Date()),
]

LEGAL_RULE_COLUMNS = [
    ("verified_by", sa.String(length=100)),
    ("verified_at", sa.Date()),
    ("verification_notes", sa.Text()),
]

QUOTATION_COLUMNS = [
    ("rejected_by", UUID(as_uuid=True)),
]

# Historical 0036 semantics: NULL means unknown; False means confirmed absent.
NULLABLE_EVIDENCE_COLUMNS = [
    "first_auditor_appointed",
    "trade_license_obtained",
    "factory_license_obtained",
    "worker_compensation_filed",
    "bsec_quarterly_report_filed",
    "cg_certificate_obtained",
    "board_independent_director",
    "audit_committee_established",
    "moa_aoa_filed",
]


def _ensure_rescue_audit_log():
    op.execute("""
        CREATE TABLE IF NOT EXISTS rescue_audit_log (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            rescue_plan_id UUID NOT NULL REFERENCES rescue_plans(id) ON DELETE CASCADE,
            finding_id UUID NULL REFERENCES compliance_flags(id) ON DELETE SET NULL,
            rule_id VARCHAR(50) NOT NULL,
            rule_version VARCHAR(20) NOT NULL,
            action_performed VARCHAR(200) NOT NULL,
            actor_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            evidence_ref VARCHAR(500) NULL,
            outcome VARCHAR(50) NOT NULL,
            notes TEXT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    for name, column in (
        ("ix_rescue_audit_log_plan_id", "rescue_plan_id"),
        ("ix_rescue_audit_log_actor_id", "actor_user_id"),
        ("ix_rescue_audit_log_finding_id", "finding_id"),
        ("ix_rescue_audit_log_created_at", "created_at"),
    ):
        op.execute(
            f"CREATE INDEX IF NOT EXISTS {name} ON rescue_audit_log ({column})"
        )


def _add_missing_columns(table_name, definitions):
    bind = op.get_bind()
    inspector = inspect(bind)
    if not inspector.has_table(table_name):
        raise RuntimeError(f"Cannot reconcile schema: missing table {table_name}")
    existing = {column["name"] for column in inspect(bind).get_columns(table_name)}
    for name, column_type in definitions:
        if name not in existing:
            # NULL means unknown; do not fabricate compliance facts with
            # defaults such as TRUE or a made-up membership count.
            op.add_column(table_name, sa.Column(name, column_type, nullable=True))
            existing.add(name)


def upgrade():
    _add_missing_columns("companies", COMPANY_COLUMNS)
    _add_missing_columns("agms", AGM_COLUMNS)
    _add_missing_columns("audits", AUDIT_COLUMNS)

    # A missing appointment record is unknown, not proof that no auditor was appointed.
    op.alter_column(
        "audits", "first_auditor_appointed",
        existing_type=sa.Boolean(),
        nullable=True,
        server_default=None,
    )

    # NULL means quorum not established; historical defaults of TRUE/2 would
    # fabricate a legal conclusion before Articles and membership are checked.
    op.alter_column(
        "agms", "quorum_met",
        existing_type=sa.Boolean(),
        nullable=True,
        server_default=None,
    )
    op.alter_column(
        "agms", "quorum_required",
        existing_type=sa.Integer(),
        nullable=True,
        server_default=None,
    )

    _add_missing_columns("legal_rules", LEGAL_RULE_COLUMNS)
    _add_missing_columns("quotations", QUOTATION_COLUMNS)

    # Historical 0035 requires PENDING, not VERIFIED, for unreviewed rules.
    bind = op.get_bind()
    legal_rule_columns = {c["name"]: c for c in inspect(bind).get_columns("legal_rules")}
    if "verification_status" not in legal_rule_columns:
        op.add_column(
            "legal_rules",
            sa.Column("verification_status", sa.String(length=20), nullable=False,
                      server_default="PENDING"),
        )

    # Correct the historical AGM-005 citation/description. Earlier migration
    # 0030 incorrectly grouped AGM-005 quorum with AGM-006 minutes under s.89.
    # Keep legal verification PENDING: correcting a citation is not counsel approval.
    op.execute("""
        UPDATE legal_rules
        SET statutory_basis = 'Section 85(2)(b), Companies Act 1994 (Bangladesh)',
            description = 'AGM quorum for a private company: statutory default is two members where total membership is up to six and three members where total membership exceeds six, unless the current Articles provide otherwise. Verify the current Articles, register of members and attendance record before evaluation.',
            verification_status = 'PENDING',
            verified_by = NULL,
            verified_at = NULL,
            verification_notes = 'Citation corrected; counsel validation and current Articles evidence review remain pending.'
        WHERE rule_id = 'AGM-005'
    """)

    # Correct the legacy AUD-001 seed/identity migration's fixed-30-day wording.
    # The current evaluator uses the actual appointment date and calendar-month arithmetic.
    op.execute("""
        UPDATE legal_rules
        SET rule_name = 'First Auditor Not Appointed Within One Calendar Month',
            statutory_basis = 'Section 210(6), Companies Act 1994 (Bangladesh)',
            description = 'The Board must appoint the first auditor within one calendar month of registration under Section 210(6). The deadline is a calendar month, not a fixed 30 days. Timeliness requires the actual appointment date.',
            verification_status = 'PENDING',
            verified_by = NULL,
            verified_at = NULL,
            verification_notes = 'Wording and evaluator aligned; counsel verification of statutory source and interpretation remains pending.'
        WHERE rule_id = 'AUD-001'
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_quotations_rejected_by "
        "ON quotations (rejected_by)"
    )

    # Historical 0038 rescue audit evidence table, created idempotently.
    _ensure_rescue_audit_log()

    # Reapply 0036's fail-closed tri-state semantics where branches retained
    # NOT NULL/default values. Existing values are preserved; defaults removed.
    company_columns = {c["name"] for c in inspect(bind).get_columns("companies")}
    for column_name in NULLABLE_EVIDENCE_COLUMNS:
        if column_name in company_columns:
            op.alter_column(
                "companies",
                column_name,
                existing_type=sa.Boolean(),
                nullable=True,
                server_default=None,
            )

    # A quorum result must not be silently inferred for legacy rows.
    op.alter_column("agms", "quorum_met", existing_type=sa.Boolean(), nullable=True)
    op.alter_column("agms", "quorum_required", existing_type=sa.Integer(), nullable=True)
    op.alter_column("agms", "quorum_met", existing_type=sa.Boolean(), server_default=None)
    op.alter_column("agms", "quorum_required", existing_type=sa.Integer(), server_default=None)


def downgrade():
    # Forward-only. Do not discard compliance evidence or reverse schema
    # reconciliation on databases where some columns pre-existed.
    pass
