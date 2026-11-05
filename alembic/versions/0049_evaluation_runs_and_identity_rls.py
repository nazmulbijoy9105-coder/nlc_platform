"""Create immutable evaluation snapshots and fail-closed RLS transition.

Revision ID: 0049_evaluation_runs_and_identity_rls
Revises: 0048_merge_legal_evidence_heads

This revision deliberately removes legacy/raw-GUC policies and leaves the
managed tables closed until 0050 installs signed identity policies. If 0050
fails, access remains denied rather than falling back to caller-settable
ADMIN/AUTH sentinels.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0049_evaluation_runs_and_identity_rls"
down_revision: Union[str, Sequence[str], None] = "0048_merge_legal_evidence_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

RLS_TABLES = (
    "companies",
    "agms",
    "annual_returns",
    "audits",
    "compliance_flags",
    "compliance_score_history",
    "directors",
    "documents",
    "notifications",
    "registered_office_history",
    "rescue_plans",
    "rescue_steps",
    "rjsc_form_filings",
    "share_transfers",
    "shareholders",
    "statutory_registers",
    "tasks",
    "users",
    "company_user_access",
    "compliance_calendar_events",
    "compliance_events",
    "quotations",
    "document_access_log",
    "user_activity_logs",
    "legal_rules",
    "legal_rule_versions",
    "sro_registry",
    "regulatory_rules",
    "ai_output_log",
    "ai_prompt_templates",
    "engagements",
    "compliance_evaluation_runs",
)


def upgrade() -> None:
    op.create_table(
        "compliance_evaluation_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "company_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column(
            "risk_band",
            postgresql.ENUM(
                "GREEN", "YELLOW", "RED", "BLACK", "NOT_EVALUATED",
                name="risk_band", create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("engine_version", sa.String(length=50), nullable=False),
        sa.Column("score_hash", sa.String(length=64), nullable=False),
        sa.Column("previous_hash", sa.String(length=64), nullable=True),
        sa.Column("evaluation_status", sa.String(length=20), nullable=False, server_default="COMPLETED"),
        sa.Column("trigger_source", sa.String(length=100), nullable=False, server_default="MANUAL"),
        sa.Column("active_flags_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("black_flags_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("flags_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("score_breakdown_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.UniqueConstraint("company_id", "calculated_at", name="uq_eval_run_company_time"),
    )

    # Remove all legacy permissive/raw-GUC policies first. Enable and force
    # RLS without replacement policies: this intermediate state is fail-closed.
    table_sql = ", ".join("'" + name + "'" for name in RLS_TABLES)
    op.execute(f"""
        DO $policies$
        DECLARE p record;
        BEGIN
            FOR p IN
                SELECT schemaname, tablename, policyname
                FROM pg_policies
                WHERE schemaname = 'public'
                  AND tablename = ANY (ARRAY[{table_sql}])
            LOOP
                EXECUTE format(
                    'DROP POLICY %I ON %I.%I',
                    p.policyname, p.schemaname, p.tablename
                );
            END LOOP;
        END
        $policies$;
    """)
    for table in RLS_TABLES:
        op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE public.{table} FORCE ROW LEVEL SECURITY")

    # The CI parity principal receives only this narrow rule-ID view.
    op.execute("CREATE SCHEMA IF NOT EXISTS audit")
    op.execute("""
        CREATE OR REPLACE VIEW audit.active_legal_rule_ids
        WITH (security_barrier = true)
        AS SELECT rule_id FROM public.legal_rules WHERE is_active = true
    """)
    op.execute("REVOKE ALL ON SCHEMA audit FROM PUBLIC")
    op.execute("REVOKE ALL ON audit.active_legal_rule_ids FROM PUBLIC")

    op.execute("""
        CREATE FUNCTION public.prevent_compliance_evaluation_run_mutation()
        RETURNS trigger AS $function$
        BEGIN
            RAISE EXCEPTION 'compliance_evaluation_runs is append-only';
        END;
        $function$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER trg_compliance_evaluation_runs_append_only
        BEFORE UPDATE OR DELETE ON public.compliance_evaluation_runs
        FOR EACH ROW EXECUTE FUNCTION public.prevent_compliance_evaluation_run_mutation()
    """)


def downgrade() -> None:
    # Forward-only: restoring raw-GUC policies would re-open tenant access.
    pass
