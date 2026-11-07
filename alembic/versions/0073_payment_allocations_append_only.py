"""Make posted payment allocations append-only at the database boundary.

Revision ID: 0073_payment_allocations_append_only
Revises: 0072_allocation_mutation_reconciliation
"""
from alembic import op

revision = "0073_payment_allocations_append_only"
down_revision = "0072_allocation_mutation_reconciliation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_reject_payment_allocation_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $function$
        BEGIN
            RAISE EXCEPTION
                'posted payment allocations are append-only; use a separately evidenced adjustment workflow'
                USING ERRCODE = '55000';
        END
        $function$
    """)
    op.execute("""
        REVOKE ALL ON FUNCTION
        public.nlc_reject_payment_allocation_mutation() FROM PUBLIC
    """)
    op.execute("""
        CREATE TRIGGER payment_allocations_append_only
        BEFORE UPDATE OR DELETE ON public.payment_allocations
        FOR EACH ROW
        EXECUTE FUNCTION public.nlc_reject_payment_allocation_mutation()
    """)
    op.execute("""
        REVOKE UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER
        ON TABLE public.payment_allocations FROM nlc_app_role
    """)


def downgrade() -> None:
    # Forward-only: posted allocations are permanent financial evidence.
    pass
