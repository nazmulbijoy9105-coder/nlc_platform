"""Regression guards for schema-recovery and signed-RLS migration preflights."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _migration(name: str) -> str:
    return (ROOT / "alembic" / "versions" / name).read_text(encoding="utf-8")


def test_webhook_and_rescue_reconciliation_is_explicitly_schema_only():
    source = _migration("0044_webhook_schema_reconcile.py")

    assert '"webhook_endpoints"' in source
    assert '"webhook_deliveries"' in source
    assert '"rescue_audit_log"' in source
    assert "op.create_table(" in source
    assert "SCHEMA-ONLY RECONSTRUCTION" in source
    assert "Historical endpoint rows were not restored" in source
    assert "Historical rescue audit rows were not restored" in source
    # SQLAlchemy renders this FK option into PostgreSQL DDL during migration.
    assert 'sa.ForeignKey("rescue_plans.id", ondelete="RESTRICT")' in source
    assert "ENABLE ROW LEVEL SECURITY" in source
    assert "FORCE ROW LEVEL SECURITY" in source


def test_signed_rls_migration_restricts_memberships_to_trusted_admins():
    source = _migration("0050_signed_rls_identity_hardening.py")

    assert "nlc_app_role" in source
    assert "nlc_ci_audit_role" in source
    assert "rolcanlogin" in source
    assert "rolinherit" in source
    assert "rolbypassrls" in source
    assert "pg_auth_members" in source
    assert "current_setting('server_version_num')::int < 160000" in source
    assert "0050 requires PostgreSQL 16+ (pg_auth_members.inherit_option/set_option)" in source
    assert "member_role.rolname IN ('nlc_app_role', 'nlc_ci_audit_role')" in source
    assert "granted_role.rolname IN ('nlc_app_role', 'nlc_ci_audit_role')" in source
    assert "member_role.rolname = 'neondb_owner'" in source
    assert "grantor_role.rolname = 'cloud_admin'" in source
    assert "membership.admin_option IS TRUE" in source
    assert "membership.inherit_option IS FALSE" in source
    assert "membership.set_option IS FALSE" in source
    assert "AND NOT (" in source
    assert "nlc_app_role and nlc_ci_audit_role have an unapproved role membership" in source
    assert "NOT (member_role.rolsuper OR member_role.rolbypassrls)" not in source

def test_out_of_band_role_provisioning_enforces_noinherit():
    source = (ROOT / "scripts" / "provision_nlc_roles.sql").read_text(encoding="utf-8")

    assert "ALTER ROLE nlc_app_role" in source
    assert "ALTER ROLE nlc_ci_audit_role" in source
    assert source.count("NOINHERIT") == 2
    assert "BYPASSRLS" in source
    assert "CREATEROLE" in source


def test_signed_rls_inventory_preflight_runs_before_schema_mutations():
    source = _migration("0050_signed_rls_identity_hardening.py")

    role_preflight = source.index("DO $role_preflight$")
    table_inventory = source.index("missing_rls_tables =")
    view_inventory = source.index("missing_rls_views =")
    first_schema_mutation = source.index("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    assert role_preflight < table_inventory < view_inventory < first_schema_mutation
    assert "to_regclass(:qualified_name)" in source
    assert "RLS migration preflight found missing expected public tables:" in source
    assert "RLS migration preflight found missing expected public views:" in source
    assert "SCHEMA-ONLY RECONSTRUCTION" in _migration(
        "0044_webhook_schema_reconcile.py"
    )
