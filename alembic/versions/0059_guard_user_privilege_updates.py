"""Prevent self-service mutation of privileged user account attributes.

Revision ID: 0059_guard_user_privilege_updates
Revises: 0058_suppress_unreleased_rule_notifications
"""
from alembic import op

revision = "0059_guard_user_privilege_updates"
down_revision = "0058_suppress_unreleased_rule_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # RLS is row-scoped, not column-scoped. The existing users_self_update
    # policy permits a user to update their own row, so guard authorization
    # attributes independently of API request schemas.
    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_guard_user_privilege_updates()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $function$
        BEGIN
            IF (
                NEW.role IS DISTINCT FROM OLD.role
                OR NEW.is_active IS DISTINCT FROM OLD.is_active
            )
            AND NOT (
                public.nlc_current_user_is_super_admin()
                OR public.nlc_current_user_principal() = 'ADMIN'
            ) THEN
                RAISE EXCEPTION
                    'Only a verified SUPER_ADMIN or trusted ADMIN service principal may change user role or active status'
                    USING ERRCODE = '42501';
            END IF;
            RETURN NEW;
        END
        $function$
    """)
    op.execute(
        "REVOKE ALL ON FUNCTION public.nlc_guard_user_privilege_updates() FROM PUBLIC"
    )
    op.execute("DROP TRIGGER IF EXISTS users_guard_privilege_updates ON public.users")
    op.execute("""
        CREATE TRIGGER users_guard_privilege_updates
        BEFORE UPDATE OF role, is_active ON public.users
        FOR EACH ROW
        EXECUTE FUNCTION public.nlc_guard_user_privilege_updates()
    """)


def downgrade() -> None:
    # Forward-only: removing this guard would restore privilege escalation
    # through the broad row-level self-update policy.
    pass
