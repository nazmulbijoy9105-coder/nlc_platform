"""Revalidate restricted PostgreSQL role membership on upgraded databases.

Revision ID: 0086_runtime_role_membership_preflight
Revises: 0085_task_completion_note
"""
from alembic import op
import sqlalchemy as sa

revision = "0086_runtime_role_membership_preflight"
down_revision = "0085_task_completion_note"
branch_labels = None
depends_on = None

RESTRICTED_ROLES = ("nlc_app_role", "nlc_ci_audit_role")


def upgrade() -> None:
    bind = op.get_bind()
    server_version_num = bind.execute(
        sa.text("SELECT current_setting('server_version_num')::int")
    ).scalar_one()
    if server_version_num < 160000:
        raise RuntimeError(
            "0086 requires PostgreSQL 16+ "
            "(pg_auth_members.inherit_option/set_option)"
        )

    missing = [
        role
        for role in RESTRICTED_ROLES
        if bind.execute(
            sa.text("SELECT 1 FROM pg_roles WHERE rolname = :role"),
            {"role": role},
        ).scalar_one_or_none() is None
    ]
    if missing:
        raise RuntimeError(
            "Required restricted runtime roles are missing: " + ", ".join(missing)
        )

    # Match the narrowly-scoped Neon control-plane exception introduced in
    # 0050. Neon grants these two roles to neondb_owner via cloud_admin with
    # ADMIN OPTION only; the owner cannot revoke a grant it did not make.
    # Every other membership involving either restricted NLC role fails closed.
    membership_exists = bind.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT 1
                  FROM pg_auth_members membership
                  JOIN pg_roles granted_role ON granted_role.oid = membership.roleid
                  JOIN pg_roles member_role ON member_role.oid = membership.member
                  JOIN pg_roles grantor_role ON grantor_role.oid = membership.grantor
                 WHERE (
                        member_role.rolname IN ('nlc_app_role', 'nlc_ci_audit_role')
                     OR granted_role.rolname IN ('nlc_app_role', 'nlc_ci_audit_role')
                 )
                   AND NOT (
                        member_role.rolname = 'neondb_owner'
                    AND granted_role.rolname IN ('nlc_app_role', 'nlc_ci_audit_role')
                    AND grantor_role.rolname = 'cloud_admin'
                    AND membership.admin_option IS TRUE
                    AND membership.inherit_option IS FALSE
                    AND membership.set_option IS FALSE
                   )
            )
            """
        )
    ).scalar_one()
    if membership_exists:
        raise RuntimeError(
            "nlc_app_role and nlc_ci_audit_role have an unapproved role membership"
        )


def downgrade() -> None:
    # Forward-only security preflight.
    pass
