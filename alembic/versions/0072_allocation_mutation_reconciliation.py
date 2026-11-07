"""Enforce invoice/allocation reconciliation on allocation mutations.

Revision ID: 0072_allocation_mutation_reconciliation
Revises: 0071_immutable_payment_submission_link
"""
from alembic import op

revision = "0072_allocation_mutation_reconciliation"
down_revision = "0071_immutable_payment_submission_link"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_assert_invoice_allocation_reconciliation()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        SET row_security = off
        AS $function$
        DECLARE
            target_invoice_id uuid;
            target_company_id uuid;
            invoice_paid numeric(15,2);
            invoice_balance numeric(15,2);
            invoice_total numeric(15,2);
            allocated_total numeric(15,2);
        BEGIN
            -- UPDATE can move an allocation between invoices. Both the old
            -- and new invoice must reconcile at commit; DELETE checks OLD.
            IF TG_OP <> 'INSERT' THEN
                target_invoice_id := OLD.invoice_id;
                target_company_id := OLD.company_id;
                SELECT paid_bdt, balance_bdt, total_bdt
                  INTO invoice_paid, invoice_balance, invoice_total
                  FROM public.invoices
                 WHERE id = target_invoice_id
                   AND company_id = target_company_id;
                IF NOT FOUND THEN
                    RAISE EXCEPTION 'allocation source invoice missing during reconciliation'
                        USING ERRCODE = '23503';
                END IF;
                SELECT COALESCE(SUM(pa.amount_bdt), 0)
                  INTO allocated_total
                  FROM public.payment_allocations pa
                 WHERE pa.invoice_id = target_invoice_id
                   AND pa.company_id = target_company_id;
                IF invoice_paid IS DISTINCT FROM allocated_total
                   OR invoice_balance IS DISTINCT FROM (invoice_total - allocated_total) THEN
                    RAISE EXCEPTION 'invoice paid/balance values must reconcile to posted payment allocations'
                        USING ERRCODE = '23514';
                END IF;
            END IF;

            IF TG_OP <> 'DELETE'
               AND (TG_OP <> 'UPDATE'
                    OR (NEW.invoice_id, NEW.company_id)
                       IS DISTINCT FROM (OLD.invoice_id, OLD.company_id)) THEN
                target_invoice_id := NEW.invoice_id;
                target_company_id := NEW.company_id;
                SELECT paid_bdt, balance_bdt, total_bdt
                  INTO invoice_paid, invoice_balance, invoice_total
                  FROM public.invoices
                 WHERE id = target_invoice_id
                   AND company_id = target_company_id;
                IF NOT FOUND THEN
                    RAISE EXCEPTION 'allocation destination invoice missing during reconciliation'
                        USING ERRCODE = '23503';
                END IF;
                SELECT COALESCE(SUM(pa.amount_bdt), 0)
                  INTO allocated_total
                  FROM public.payment_allocations pa
                 WHERE pa.invoice_id = target_invoice_id
                   AND pa.company_id = target_company_id;
                IF invoice_paid IS DISTINCT FROM allocated_total
                   OR invoice_balance IS DISTINCT FROM (invoice_total - allocated_total) THEN
                    RAISE EXCEPTION 'invoice paid/balance values must reconcile to posted payment allocations'
                        USING ERRCODE = '23514';
                END IF;
            ELSIF TG_OP = 'INSERT' THEN
                -- INSERT has only a destination invoice to validate.
                target_invoice_id := NEW.invoice_id;
                target_company_id := NEW.company_id;
                SELECT paid_bdt, balance_bdt, total_bdt
                  INTO invoice_paid, invoice_balance, invoice_total
                  FROM public.invoices
                 WHERE id = target_invoice_id
                   AND company_id = target_company_id;
                IF NOT FOUND THEN
                    RAISE EXCEPTION 'allocation destination invoice missing during reconciliation'
                        USING ERRCODE = '23503';
                END IF;
                SELECT COALESCE(SUM(pa.amount_bdt), 0)
                  INTO allocated_total
                  FROM public.payment_allocations pa
                 WHERE pa.invoice_id = target_invoice_id
                   AND pa.company_id = target_company_id;
                IF invoice_paid IS DISTINCT FROM allocated_total
                   OR invoice_balance IS DISTINCT FROM (invoice_total - allocated_total) THEN
                    RAISE EXCEPTION 'invoice paid/balance values must reconcile to posted payment allocations'
                        USING ERRCODE = '23514';
                END IF;
            END IF;
            RETURN NULL;
        END
        $function$
    """)
    op.execute("""
        DROP TRIGGER IF EXISTS payment_allocations_invoice_reconciliation
        ON public.payment_allocations
    """)
    op.execute("""
        CREATE CONSTRAINT TRIGGER payment_allocations_invoice_reconciliation
        AFTER INSERT OR UPDATE OR DELETE ON public.payment_allocations
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW
        EXECUTE FUNCTION public.nlc_assert_invoice_allocation_reconciliation()
    """)


def downgrade() -> None:
    # Forward-only: the prior trigger is weaker and must not be restored.
    pass
