"""Least-privilege regression tests for the production rule-parity principal.

The historical role name includes "ci", but this role is also used by the
manual production-parity workflow. It must be connectable while remaining
read-only and isolated from tenant/application tables.
"""
from __future__ import annotations

import os

import asyncpg
import pytest


pytestmark = [pytest.mark.integration]


@pytest.mark.asyncio
async def test_rule_parity_role_is_login_and_can_read_only_the_audit_view():
    database_url = os.environ["DATABASE_URL"].replace("+asyncpg", "", 1)
    connection = await asyncpg.connect(database_url)
    try:
        role = await connection.fetchrow(
            """
            SELECT rolcanlogin, rolsuper, rolcreatedb, rolcreaterole,
                   rolinherit, rolreplication, rolbypassrls
            FROM pg_roles
            WHERE rolname = 'nlc_ci_audit_role'
            """
        )
        assert role is not None
        assert role["rolcanlogin"] is True
        assert role["rolsuper"] is False
        assert role["rolcreatedb"] is False
        assert role["rolcreaterole"] is False
        assert role["rolinherit"] is False
        assert role["rolreplication"] is False
        assert role["rolbypassrls"] is False

        # The CI database administrator can assume the dedicated role to
        # verify its effective grants without exposing its password.
        await connection.execute("SET ROLE nlc_ci_audit_role")
        visible_rule_count = await connection.fetchval(
            "SELECT count(*) FROM audit.active_legal_rule_ids"
        )
        assert visible_rule_count is not None
        assert await connection.fetchval(
            "SELECT has_schema_privilege(current_user, 'audit', 'CREATE')"
        ) is False

        # The audit principal is read-only even on its one permitted view.
        for privilege in ("INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER"):
            allowed = await connection.fetchval(
                "SELECT has_table_privilege(current_user, 'audit.active_legal_rule_ids', $1)",
                privilege,
            )
            assert allowed is False, f"audit role unexpectedly has {privilege} on the audit view"

        # PUBLIC EXECUTE on a SECURITY DEFINER routine would silently widen
        # the audit role's authority. None may be executable by this principal.
        executable_definers = await connection.fetch(
            """
            SELECT p.oid::regprocedure::text AS signature
            FROM pg_proc p
            JOIN pg_namespace n ON n.oid = p.pronamespace
            WHERE n.nspname = 'public'
              AND p.prosecdef IS TRUE
              AND has_function_privilege(current_user, p.oid, 'EXECUTE')
            ORDER BY signature
            """
        )
        assert executable_definers == []

        for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER"):
            allowed = await connection.fetchval(
                "SELECT has_table_privilege(current_user, 'public.companies', $1)",
                privilege,
            )
            assert allowed is False, f"audit role unexpectedly has {privilege} on public.companies"

        # NOINHERIT alone does not prevent SET ROLE. Reject memberships
        # both from and to this principal.
        memberships = await connection.fetch(
            """
            SELECT parent.rolname AS granted_role, member.rolname AS member_role
            FROM pg_auth_members membership
            JOIN pg_roles parent ON parent.oid = membership.roleid
            JOIN pg_roles member ON member.oid = membership.member
            WHERE member.rolname = current_user
               OR parent.rolname = current_user
            """
        )
        assert memberships == []
    finally:
        await connection.close()
