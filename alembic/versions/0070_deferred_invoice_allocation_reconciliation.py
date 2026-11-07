"""Require invoice/allocation reconciliation at transaction commit.

Revision ID: 0070_deferred_invoice_allocation_reconciliation
Revises: 0069_cross_table_wallet_reference_guard
"""
from alembic import op

revision = "0070_deferred_invoice_allocation_reconciliation"
down_revision = "0069_cross_table_wallet_reference_guard"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Migration must not bless historical drift. Reconcile every invoice before
    # installing the deferred guard; ambiguous financial history blocks upgrade.
    op.execute("""
        DO $preflight$
        BEGIN
            IF EXISTS (
                SELECT 1
                  FROM public.invoices i
                  LEFT JOIN (
                      SELECT company_id, invoice_id, SUM(amount_bdt) AS allocated_total
                        FROM public.payment_allocations
                       GROUP BY company_id, invoice_id
                  ) a
                    ON a.company_id = i.company_id
                   AND a.invoice_id = i.id
                 WHERE i.paid_bdt IS DISTINCT FROM COALESCE(a.allocated_total, 0)
                    OR i.balance_bdt IS DISTINCT FROM
                       (i.total_bdt - COALESCE(a.allocated_total, 0))
            ) THEN
                RAISE EXCEPTION
                    'invoice paid/balance values do not reconcile to payment allocations; reconcile finance history before migration 0070'
                    USING ERRCODE = '23514';
            END IF;
        END
        $preflight$
    """)

    # The invoice UPDATE guard in 0061 prevents fabricated paid totals, but by
    # itself it does not stop an app-role caller inserting an allocation and
    # omitting the matching invoice update. Validate the final transaction state.
    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_assert_invoice_allocation_reconciliation()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        SET row_security = off
        AS $function$
        DECLARE
            invoice_paid numeric(15,2);
            invoice_balance numeric(15,2);
            invoice_total numeric(15,2);
            allocated_total numeric(15,2);
        BEGIN
            SELECT paid_bdt, balance_bdt, total_bdt
              INTO invoice_paid, invoice_balance, invoice_total
              FROM public.invoices
             WHERE id = NEW.invoice_id
               AND company_id = NEW.company_id;

            IF NOT FOUND THEN
                RAISE EXCEPTION 'allocation invoice disappeared before reconciliation'
                    USING ERRCODE = '23503';
            END IF;

            SELECT COALESCE(SUM(pa.amount_bdt), 0)
              INTO allocated_total
              FROM public.payment_allocations pa
             WHERE pa.invoice_id = NEW.invoice_id
               AND pa.company_id = NEW.company_id;

            IF invoice_paid IS DISTINCT FROM allocated_total
               OR invoice_balance IS DISTINCT FROM (invoice_total - allocated_total) THEN
                RAISE EXCEPTION
                    'invoice paid/balance values must reconcile to posted payment allocations'
                    USING ERRCODE = '23514';
            END IF;
            RETURN NULL;
        END
        $function$
    """)
    op.execute("""
        REVOKE ALL ON FUNCTION
        public.nlc_assert_invoice_allocation_reconciliation() FROM PUBLIC
    """)
    op.execute("""
        CREATE CONSTRAINT TRIGGER payment_allocations_invoice_reconciliation
        AFTER INSERT ON public.payment_allocations
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW
        EXECUTE FUNCTION public.nlc_assert_invoice_allocation_reconciliation()
    """)


def downgrade() -> None:
    # Forward-only: removing the deferred check would allow unbalanced ledger writes.
    pass
