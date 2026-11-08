"""Install the legal-rule version guard after all historical rule updates.

Revision ID: 0084_install_legal_rule_version_guard
Revises: 0083_merge_all_release_heads

Historical rule corrections run on independent Alembic branches. Install the
version-snapshot trigger only after those branches are joined. The database
owner remains the only trusted migration principal allowed to bypass the
application-level SUPER_ADMIN snapshot requirement; the runtime role must
never own the database.
"""
from alembic import op
import sqlalchemy as sa

revision = "0084_install_legal_rule_version_guard"
down_revision = "0083_merge_all_release_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    runtime_role_exists = bind.execute(
        sa.text("SELECT 1 FROM pg_roles WHERE rolname = 'nlc_app_role'")
    ).scalar_one_or_none()
    if runtime_role_exists is None:
        raise RuntimeError(
            "Legal-rule guard requires the nlc_app_role runtime database role"
        )

    runtime_is_database_owner = bind.execute(
        sa.text(
            "SELECT pg_has_role("
            "'nlc_app_role', 'pg_database_owner', 'USAGE'"
            ")"
        )
    ).scalar_one()
    if runtime_is_database_owner:
        raise RuntimeError(
            "SECURITY: nlc_app_role must not own the database; "
            "migration-owner bypass would otherwise be available to the runtime"
        )

    migration_is_database_owner = bind.execute(
        sa.text(
            "SELECT pg_has_role(session_user, 'pg_database_owner', 'USAGE')"
        )
    ).scalar_one()
    if not migration_is_database_owner:
        raise RuntimeError(
            "Legal-rule guard migration must run under the database-owner migration principal"
        )

    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_require_legal_rule_version_snapshot()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $function$
        DECLARE
            actor_id uuid;
        BEGIN
            -- Trusted database-owner sessions are migration principals, not
            -- application users. The runtime role is explicitly rejected
            -- above if it owns the database.
            IF pg_has_role(session_user, 'pg_database_owner', 'USAGE') THEN
                RETURN NEW;
            END IF;

            actor_id := public.nlc_current_user_id();
            IF actor_id IS NULL OR NOT public.nlc_current_user_is_super_admin() THEN
                RAISE EXCEPTION 'Only an active SUPER_ADMIN may modify legal rules'
                    USING ERRCODE = '42501';
            END IF;

            IF NEW.rule_id IS DISTINCT FROM OLD.rule_id THEN
                RAISE EXCEPTION 'legal_rules.rule_id is immutable'
                    USING ERRCODE = '55000';
            END IF;

            IF NOT EXISTS (
                SELECT 1
                FROM public.legal_rule_versions v
                WHERE v.rule_id = OLD.rule_id
                  AND v.changed_by = actor_id
                  AND v.changed_at >= transaction_timestamp() - INTERVAL '15 minutes'
                  AND v.previous_definition->>'id' = OLD.id::text
                  AND v.previous_definition->>'rule_version' = COALESCE(OLD.rule_version, '1.0')
                  AND v.previous_definition->>'rule_name' IS NOT DISTINCT FROM OLD.rule_name
                  AND v.previous_definition->>'statutory_basis' IS NOT DISTINCT FROM OLD.statutory_basis
                  AND NULLIF(BTRIM(v.change_reason), '') IS NOT NULL
            ) THEN
                RAISE EXCEPTION 'A matching legal_rule_versions snapshot is required before changing a rule'
                    USING ERRCODE = '55000';
            END IF;

            RETURN NEW;
        END
        $function$
    """)
    op.execute(
        "REVOKE ALL ON FUNCTION public.nlc_require_legal_rule_version_snapshot() FROM PUBLIC"
    )
    op.execute(
        "DROP TRIGGER IF EXISTS legal_rules_require_version_snapshot ON public.legal_rules"
    )
    op.execute("""
        CREATE TRIGGER legal_rules_require_version_snapshot
        BEFORE UPDATE ON public.legal_rules
        FOR EACH ROW EXECUTE FUNCTION public.nlc_require_legal_rule_version_snapshot()
    """)


def downgrade() -> None:
    # Forward-only: removing the version-snapshot guard would weaken the
    # legal-rule audit boundary.
    pass
