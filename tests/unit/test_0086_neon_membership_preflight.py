"""Regression checks for the 0086 Neon membership preflight contract."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = (
    ROOT
    / "alembic"
    / "versions"
    / "0086_runtime_role_membership_preflight.py"
).read_text(encoding="utf-8")


def test_0086_requires_postgresql_16_before_membership_option_columns():
    version_guard = SOURCE.index("if server_version_num < 160000:")
    membership_query = SOURCE.index("FROM pg_auth_members")
    assert version_guard < membership_query
    assert "pg_auth_members.inherit_option/set_option" in SOURCE


def test_0086_allows_only_the_exact_neon_control_plane_membership():
    assert "member_role.rolname = 'neondb_owner'" in SOURCE
    assert "granted_role.rolname IN ('nlc_app_role', 'nlc_ci_audit_role')" in SOURCE
    assert "grantor_role.rolname = 'cloud_admin'" in SOURCE
    assert "membership.admin_option IS TRUE" in SOURCE
    assert "membership.inherit_option IS FALSE" in SOURCE
    assert "membership.set_option IS FALSE" in SOURCE
    assert "AND NOT (" in SOURCE


def test_0086_still_fails_closed_for_every_other_membership():
    assert "member_role.rolname IN ('nlc_app_role', 'nlc_ci_audit_role')" in SOURCE
    assert "granted_role.rolname IN ('nlc_app_role', 'nlc_ci_audit_role')" in SOURCE
    assert "have an unapproved role membership" in SOURCE
