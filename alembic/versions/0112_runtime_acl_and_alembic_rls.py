"""Tighten runtime DML grants and force RLS on Alembic metadata.

Revision ID: 0112_runtime_acl_and_alembic_rls
Revises: 0111_rule_outcome_ledger

The API role must not hard-delete ordinary business or audit records. The
only currently identified runtime DELETE workflows are webhook endpoint
removal and post-archive activity-log retention cleanup. Dashboard views are
read-only projections and must never carry DML grants. alembic_version is
not readable or writable by the runtime role and is forced through RLS for
consistent owner semantics; the controlled migration owner has BYPASSRLS.
"""
from alembic import op

revision = "0112_runtime_acl_and_alembic_rls"
down_revision = "0111_rule_outcome_ledger"
branch_labels = None
depends_on = None

_READ_ONLY_VIEWS = (
    "vw_admin_dashboard_kpis",
    "vw_company_flag_summary",
    "vw_risk_distribution",
    "vw_upcoming_deadlines",
    "vw_revenue_pipeline",
)


def upgrade() -> None:
    # Remove broad DELETE grants, including any inherited by views. Preserve
    # the two code-confirmed workflows: user-owned webhook endpoint removal
    # and activity-log deletion only after successful archival.
    op.execute(
        "REVOKE DELETE ON ALL TABLES IN SCHEMA public FROM nlc_app_role"
    )
    op.execute(
        "GRANT DELETE ON TABLE public.webhook_endpoints TO nlc_app_role"
    )
    op.execute(
        "GRANT DELETE ON TABLE public.user_activity_logs TO nlc_app_role"
    )

    # Views are read-only API projections. Keep SELECT; remove all DML.
    for view in _READ_ONLY_VIEWS:
        op.execute(
            f"REVOKE INSERT, UPDATE, DELETE ON TABLE public.{view} "
            "FROM nlc_app_role"
        )

    # The application role already has no privileges on this table. FORCE
    # RLS makes the catalog state consistent; the migration owner is
    # BYPASSRLS and remains able to maintain Alembic metadata.
    op.execute(
        "ALTER TABLE public.alembic_version FORCE ROW LEVEL SECURITY"
    )


def downgrade() -> None:
    # Forward-only security migration. Restoring broad DELETE/DML grants
    # would reintroduce the privilege exposure this revision removes.
    pass
