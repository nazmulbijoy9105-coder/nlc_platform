"""Prevent overlapping resolved historical legal-rule aliases.

Revision ID: 0118_legal_rule_alias_overlap_guard
Revises: 0117_canonical_registry_runtime_read
"""
from alembic import op

revision = "0118_legal_rule_alias_overlap_guard"
down_revision = "0117_canonical_registry_runtime_read"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Serialize competing claims for the same source identifier. Under the
    # application's READ COMMITTED transaction isolation, the post-lock
    # statement sees a preceding transaction's committed alias row.
    op.execute("""
        CREATE FUNCTION public.prevent_legal_rule_alias_overlap()
        RETURNS trigger LANGUAGE plpgsql VOLATILE AS $alias_overlap$
        BEGIN
            IF NEW.resolution_status <> 'RESOLVED' THEN
                RETURN NEW;
            END IF;

            IF current_setting('transaction_isolation') <> 'read committed' THEN
                RAISE EXCEPTION
                    'Alias overlap guard requires READ COMMITTED isolation'
                    USING ERRCODE = '25000';
            END IF;

            PERFORM pg_advisory_xact_lock(
                hashtextextended(
                    jsonb_build_array(
                        NEW.source_namespace, NEW.historical_rule_id
                    )::text,
                    0
                )
            );

            IF EXISTS (
                SELECT 1
                  FROM public.legal_rule_aliases existing
                 WHERE existing.source_namespace = NEW.source_namespace
                   AND existing.historical_rule_id = NEW.historical_rule_id
                   AND existing.resolution_status = 'RESOLVED'
                   AND daterange(
                       existing.valid_from, existing.valid_to, '[)'
                   ) && daterange(
                       NEW.valid_from, NEW.valid_to, '[)'
                   )
            ) THEN
                RAISE EXCEPTION
                    'Overlapping resolved alias interval for source % / historical ID %',
                    NEW.source_namespace, NEW.historical_rule_id
                    USING ERRCODE = '23P01';
            END IF;
            RETURN NEW;
        END;
        $alias_overlap$
    """)
    op.execute("""
        CREATE TRIGGER trg_legal_rule_alias_no_overlap
        BEFORE INSERT ON public.legal_rule_aliases
        FOR EACH ROW
        EXECUTE FUNCTION public.prevent_legal_rule_alias_overlap()
    """)
    op.execute(
        "REVOKE ALL ON FUNCTION public.prevent_legal_rule_alias_overlap() "
        "FROM PUBLIC, nlc_app_role, nlc_ci_audit_role"
    )


def downgrade() -> None:
    raise RuntimeError(
        "0118 is forward-only: remove the alias overlap guard only through "
        "a separately reviewed forward migration."
    )
