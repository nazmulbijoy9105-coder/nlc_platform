"""Add immutable per-evaluation snapshots and core signed-identity RLS policies."""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0049_evaluation_runs_and_identity_rls"
down_revision: Union[str, Sequence[str], None] = "0048_merge_legal_evidence_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "compliance_evaluation_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "company_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("score", sa.Integer(), nullable=True),
        sa.Column(
            "risk_band",
            postgresql.ENUM("GREEN", "YELLOW", "RED", "BLACK", "NOT_EVALUATED", name="risk_band", create_type=False),
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
    # A non-owner application role must be able to read its own identity and
    # company mappings. Writes to these access-control tables remain admin-only.
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE company_user_access ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY users_self_or_admin_select
        ON users FOR SELECT
        USING (
            id::text = current_setting('app.current_user_id', true)
            OR current_setting('app.current_user_id', true) = 'ADMIN'
        )
        """
    )
    op.execute(
        """
        CREATE POLICY users_admin_write
        ON users FOR ALL
        USING (current_setting('app.current_user_id', true) = 'ADMIN')
        WITH CHECK (current_setting('app.current_user_id', true) = 'ADMIN')
        """
    )
    op.execute(
        """
        CREATE POLICY company_user_access_self_or_admin_select
        ON company_user_access FOR SELECT
        USING (
            user_id::text = current_setting('app.current_user_id', true)
            OR current_setting('app.current_user_id', true) = 'ADMIN'
        )
        """
    )
    op.execute(
        """
        CREATE POLICY company_user_access_admin_write
        ON company_user_access FOR ALL
        USING (current_setting('app.current_user_id', true) = 'ADMIN')
        WITH CHECK (current_setting('app.current_user_id', true) = 'ADMIN')
        """
    )

    op.execute("ALTER TABLE compliance_evaluation_runs ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY evaluation_runs_company_scope
        ON compliance_evaluation_runs FOR ALL
        USING (
            current_setting('app.current_user_id', true) = 'ADMIN'
            OR EXISTS (
                SELECT 1
                FROM company_user_access access
                WHERE access.company_id = compliance_evaluation_runs.company_id
                  AND access.user_id::text = current_setting('app.current_user_id', true)
                  AND access.is_active = true
            )
        )
        WITH CHECK (
            current_setting('app.current_user_id', true) = 'ADMIN'
            OR EXISTS (
                SELECT 1
                FROM company_user_access access
                WHERE access.company_id = compliance_evaluation_runs.company_id
                  AND access.user_id::text = current_setting('app.current_user_id', true)
                  AND access.is_active = true
            )
        )
        """
    )

    # Tenant-scoped tables that previously had no policy or no RLS.
    op.execute("ALTER TABLE compliance_calendar_events ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY calendar_events_company_scope
        ON compliance_calendar_events FOR ALL
        USING (
            current_setting('app.current_user_id', true) = 'ADMIN'
            OR EXISTS (
                SELECT 1 FROM company_user_access access
                WHERE access.company_id = compliance_calendar_events.company_id
                  AND access.user_id::text = current_setting('app.current_user_id', true)
                  AND access.is_active = true
            )
        )
        WITH CHECK (
            current_setting('app.current_user_id', true) = 'ADMIN'
            OR EXISTS (
                SELECT 1 FROM company_user_access access
                WHERE access.company_id = compliance_calendar_events.company_id
                  AND access.user_id::text = current_setting('app.current_user_id', true)
                  AND access.is_active = true
            )
        )
        """
    )

    op.execute(
        """
        CREATE POLICY compliance_events_company_scope
        ON compliance_events FOR ALL
        USING (
            current_setting('app.current_user_id', true) = 'ADMIN'
            OR EXISTS (
                SELECT 1 FROM company_user_access access
                WHERE access.company_id = compliance_events.company_id
                  AND access.user_id::text = current_setting('app.current_user_id', true)
                  AND access.is_active = true
            )
        )
        WITH CHECK (
            current_setting('app.current_user_id', true) = 'ADMIN'
            OR EXISTS (
                SELECT 1 FROM company_user_access access
                WHERE access.company_id = compliance_events.company_id
                  AND access.user_id::text = current_setting('app.current_user_id', true)
                  AND access.is_active = true
            )
        )
        """
    )

    op.execute(
        """
        CREATE POLICY quotations_company_scope
        ON quotations FOR ALL
        USING (
            current_setting('app.current_user_id', true) = 'ADMIN'
            OR (
                company_id IS NOT NULL
                AND EXISTS (
                    SELECT 1 FROM company_user_access access
                    WHERE access.company_id = quotations.company_id
                      AND access.user_id::text = current_setting('app.current_user_id', true)
                      AND access.is_active = true
                )
            )
        )
        WITH CHECK (
            current_setting('app.current_user_id', true) = 'ADMIN'
            OR (
                company_id IS NOT NULL
                AND EXISTS (
                    SELECT 1 FROM company_user_access access
                    WHERE access.company_id = quotations.company_id
                      AND access.user_id::text = current_setting('app.current_user_id', true)
                      AND access.is_active = true
                )
            )
        )
        """
    )

    op.execute(
        """
        CREATE POLICY document_access_log_company_scope
        ON document_access_log FOR SELECT
        USING (
            current_setting('app.current_user_id', true) = 'ADMIN'
            OR accessed_by::text = current_setting('app.current_user_id', true)
            OR EXISTS (
                SELECT 1
                FROM documents d
                JOIN company_user_access access ON access.company_id = d.company_id
                WHERE d.id = document_access_log.document_id
                  AND access.user_id::text = current_setting('app.current_user_id', true)
                  AND access.is_active = true
            )
        )
        """
    )
    op.execute(
        """
        CREATE POLICY document_access_log_insert
        ON document_access_log FOR INSERT
        WITH CHECK (
            current_setting('app.current_user_id', true) = 'ADMIN'
            OR (
                accessed_by::text = current_setting('app.current_user_id', true)
                AND EXISTS (
                    SELECT 1
                    FROM documents d
                    JOIN company_user_access access ON access.company_id = d.company_id
                    WHERE d.id = document_access_log.document_id
                      AND access.user_id::text = current_setting('app.current_user_id', true)
                      AND access.is_active = true
                )
            )
        )
        """
    )

    op.execute(
        """
        CREATE POLICY user_activity_logs_self_or_company_read
        ON user_activity_logs FOR SELECT
        USING (
            current_setting('app.current_user_id', true) = 'ADMIN'
            OR user_id::text = current_setting('app.current_user_id', true)
            OR (
                company_id IS NOT NULL
                AND EXISTS (
                    SELECT 1 FROM company_user_access access
                    WHERE access.company_id = user_activity_logs.company_id
                      AND access.user_id::text = current_setting('app.current_user_id', true)
                      AND access.is_active = true
                )
            )
        )
        """
    )
    op.execute(
        """
        CREATE POLICY user_activity_logs_self_insert
        ON user_activity_logs FOR INSERT
        WITH CHECK (
            current_setting('app.current_user_id', true) = 'ADMIN'
            OR user_id::text = current_setting('app.current_user_id', true)
        )
        """
    )

    # Global legal/reference catalogues are readable by authenticated users;
    # mutation and internal audit logs remain admin-only.
    for table in ("legal_rules", "sro_registry", "regulatory_rules"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY {table}_authenticated_read
            ON {table} FOR SELECT
            USING (current_setting('app.current_user_id', true) IS NOT NULL)
            """
        )
        op.execute(
            f"""
            CREATE POLICY {table}_admin_write
            ON {table} FOR ALL
            USING (current_setting('app.current_user_id', true) = 'ADMIN')
            WITH CHECK (current_setting('app.current_user_id', true) = 'ADMIN')
            """
        )

    for table in ("legal_rule_versions", "ai_output_log", "ai_prompt_templates"):
        op.execute(
            f"""
            CREATE POLICY {table}_admin_only
            ON {table} FOR ALL
            USING (current_setting('app.current_user_id', true) = 'ADMIN')
            WITH CHECK (current_setting('app.current_user_id', true) = 'ADMIN')
            """
        )

    # Evaluation records are append-only. No API role can rewrite/delete evidence.
    op.execute(
        """
        CREATE FUNCTION prevent_compliance_evaluation_run_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'compliance_evaluation_runs is append-only';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_compliance_evaluation_runs_append_only
        BEFORE UPDATE OR DELETE ON compliance_evaluation_runs
        FOR EACH ROW EXECUTE FUNCTION prevent_compliance_evaluation_run_mutation()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_compliance_evaluation_runs_append_only ON compliance_evaluation_runs")
    op.execute("DROP FUNCTION IF EXISTS prevent_compliance_evaluation_run_mutation()")
    op.execute("DROP POLICY IF EXISTS evaluation_runs_company_scope ON compliance_evaluation_runs")
    op.execute("DROP TABLE IF EXISTS compliance_evaluation_runs")
    op.execute("DROP POLICY IF EXISTS company_user_access_admin_write ON company_user_access")
    op.execute("DROP POLICY IF EXISTS company_user_access_self_or_admin_select ON company_user_access")
    op.execute("DROP POLICY IF EXISTS users_admin_write ON users")
    op.execute("DROP POLICY IF EXISTS users_self_or_admin_select ON users")
