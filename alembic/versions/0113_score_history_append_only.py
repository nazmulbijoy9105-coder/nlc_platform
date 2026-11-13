"""Make monthly compliance score history append-only at the database layer.

Revision ID: 0113_score_history_append_only
Revises: 0112_runtime_acl_and_alembic_rls
"""
from alembic import op

revision = "0113_score_history_append_only"
down_revision = "0112_runtime_acl_and_alembic_rls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Monthly snapshots are evidential records. The runtime role may append
    # and read them, but must never rewrite or remove an existing snapshot.
    op.execute(
        "REVOKE UPDATE, DELETE ON TABLE public.compliance_score_history "
        "FROM nlc_app_role"
    )
    op.execute(
        "DROP POLICY IF EXISTS compliance_score_history_tenant_update "
        "ON public.compliance_score_history"
    )
    op.execute(
        "DROP POLICY IF EXISTS compliance_score_history_tenant_delete "
        "ON public.compliance_score_history"
    )
    op.execute("""
        CREATE FUNCTION public.prevent_compliance_score_history_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $function$
        BEGIN
            RAISE EXCEPTION
                'compliance_score_history is append-only: % is forbidden',
                TG_OP
                USING ERRCODE = '55000';
        END;
        $function$
    """)
    op.execute("""
        CREATE TRIGGER trg_compliance_score_history_append_only
        BEFORE UPDATE OR DELETE ON public.compliance_score_history
        FOR EACH ROW
        EXECUTE FUNCTION public.prevent_compliance_score_history_mutation()
    """)
    op.execute(
        "REVOKE ALL ON FUNCTION "
        "public.prevent_compliance_score_history_mutation() FROM PUBLIC"
    )


def downgrade() -> None:
    raise RuntimeError(
        "0113 is forward-only: score-history immutability must not be "
        "silently removed by an Alembic downgrade."
    )
