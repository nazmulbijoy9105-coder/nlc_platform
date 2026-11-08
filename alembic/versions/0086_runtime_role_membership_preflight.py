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

    membership_exists = bind.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT 1
                  FROM pg_auth_members membership
                  JOIN pg_roles granted_role ON granted_role.oid = membership.roleid
                  JOIN pg_roles member_role ON member_role.oid = membership.member
                 WHERE member_role.rolname IN ('nlc_app_role', 'nlc_ci_audit_role')
                    OR granted_role.rolname IN ('nlc_app_role', 'nlc_ci_audit_role')
            )
            """
        )
    ).scalar_one()
    if membership_exists:
        raise RuntimeError(
            "nlc_app_role and nlc_ci_audit_role must have no role memberships in either direction"
        )


def downgrade() -> None:
    # Forward-only security preflight.
    pass
