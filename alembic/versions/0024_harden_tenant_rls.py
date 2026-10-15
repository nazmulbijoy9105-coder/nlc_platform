"""Harden tenant RLS coverage.

Revision ID: 0024_harden_tenant_rls
Revises: 0023_is_manufacturing
"""

from alembic import op
import sqlalchemy as sa


revision = "0024_harden_tenant_rls"
down_revision = "0023_is_manufacturing"
branch_labels = None
depends_on = None


COMPANY_SCOPED_TABLES = (
    "compliance_events",
    "quotations",
    "rjsc_form_filings",
)


NULLABLE_COMPANY_TABLES = (
    "ai_output_log",
    "user_activity_logs",
)


def _company_access_policy(table: str) -> str:
    return f"""
        CREATE POLICY {table}_company_policy
        ON {table}
        USING (
            current_setting('app.current_user_id', TRUE) = 'ADMIN'
            OR (
                company_id IS NOT NULL
                AND current_setting('app.current_user_id', TRUE)
                    ~* '^[0-9a-f]{{8}}-[0-9a-f]{{4}}-[0-9a-f]{{4}}-[0-9a-f]{{4}}-[0-9a-f]{{12}}$'
                AND company_id IN (
                    SELECT company_id
                    FROM company_user_access
                    WHERE user_id =
                        current_setting('app.current_user_id', TRUE)::uuid
                      AND is_active = TRUE
                )
            )
        )
        WITH CHECK (
            current_setting('app.current_user_id', TRUE) = 'ADMIN'
            OR (
                company_id IS NOT NULL
                AND current_setting('app.current_user_id', TRUE)
                    ~* '^[0-9a-f]{{8}}-[0-9a-f]{{4}}-[0-9a-f]{{4}}-[0-9a-f]{{4}}-[0-9a-f]{{12}}$'
                AND company_id IN (
                    SELECT company_id
                    FROM company_user_access
                    WHERE user_id =
                        current_setting('app.current_user_id', TRUE)::uuid
                      AND is_active = TRUE
                )
            )
        )
    """


def upgrade() -> None:
    conn = op.get_bind()

    # Required company-scoped tables.
    for table in COMPANY_SCOPED_TABLES:
        conn.execute(
            sa.text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        )
        conn.execute(sa.text(_company_access_policy(table)))

    # Nullable company_id audit tables.
    # Rows without a company are intentionally not visible to ordinary
    # tenant contexts; only the explicit ADMIN database context can access
    # them.
    for table in NULLABLE_COMPANY_TABLES:
        conn.execute(
            sa.text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        )
        conn.execute(sa.text(_company_access_policy(table)))


def downgrade() -> None:
    conn = op.get_bind()

    for table in COMPANY_SCOPED_TABLES + NULLABLE_COMPANY_TABLES:
        conn.execute(
            sa.text(
                f"DROP POLICY IF EXISTS {table}_company_policy ON {table}"
            )
        )
        conn.execute(
            sa.text(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
        )
