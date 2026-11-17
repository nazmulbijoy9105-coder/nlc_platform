"""Revoke inherited broad ACLs from the legal provenance application tables.

Revision ID: 0110_legal_provenance_acl
Revises: 0109_product_owner_legal_provenance

The registries are append-only. The application needs SELECT and INSERT only;
RLS and actor guards control which authenticated users may read or insert.
"""
from alembic import op

revision = "0110_legal_provenance_acl"
down_revision = "0109_product_owner_legal_provenance"
branch_labels = None
depends_on = None

_TABLES = (
    "legal_sources",
    "legal_rule_source_mappings",
    "legal_deadline_definitions",
    "legal_rule_release_events",
)


def upgrade() -> None:
    for table in _TABLES:
        # REVOKE ALL is deliberate: Neon/database default privileges can grant
        # broader ACLs to nlc_app_role when the table is created by neondb_owner.
        op.execute(f"REVOKE ALL PRIVILEGES ON TABLE public.{table} FROM PUBLIC")
        op.execute(f"REVOKE ALL PRIVILEGES ON TABLE public.{table} FROM nlc_app_role")
        op.execute(f"GRANT SELECT, INSERT ON TABLE public.{table} TO nlc_app_role")


def downgrade() -> None:
    # Forward-only security hardening. Re-granting broad mutation rights is unsafe.
    pass
