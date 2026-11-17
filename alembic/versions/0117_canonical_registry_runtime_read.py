"""Grant signed application principals read-only access to canonical legal registry.

Revision ID: 0117_canonical_registry_runtime_read
Revises: 0116_canonical_rule_identity_registry

The registry contains jurisdiction-wide legal definitions, not tenant records.
Only signed user principals and the trusted ADMIN/CATALOG service principals
may read it. The runtime role receives SELECT only; no write or audit-role
access is granted.
"""
from alembic import op

revision = "0117_canonical_registry_runtime_read"
down_revision = "0116_canonical_rule_identity_registry"
branch_labels = None
depends_on = None

_TABLES = (
    "legal_rule_identities",
    "legal_rule_aliases",
    "legal_rule_revisions",
)


def upgrade() -> None:
    for table in _TABLES:
        op.execute(
            f"REVOKE ALL PRIVILEGES ON TABLE public.{table} "
            "FROM PUBLIC, nlc_app_role, nlc_ci_audit_role"
        )
        op.execute(
            f"DROP POLICY IF EXISTS {table}_signed_runtime_read "
            f"ON public.{table}"
        )
        op.execute(
            f"CREATE POLICY {table}_signed_runtime_read ON public.{table} "
            "FOR SELECT TO nlc_app_role USING ("
            "public.nlc_current_user_context_valid() "
            "AND (public.nlc_current_user_id() IS NOT NULL "
            "OR public.nlc_current_user_principal() IN ('ADMIN', 'CATALOG'))"
            ")"
        )
        op.execute(
            f"GRANT SELECT ON TABLE public.{table} TO nlc_app_role"
        )


def downgrade() -> None:
    raise RuntimeError(
        "0117 is forward-only: remove runtime registry access through a "
        "separately reviewed forward migration, not a destructive downgrade."
    )
