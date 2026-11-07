"""Enforce payment allocation and invoice balance reconciliation in PostgreSQL.

Revision ID: 0061_financial_allocation_integrity
Revises: 0060_financial_billing_core
"""
from alembic import op

revision = "0061_financial_allocation_integrity"
down_revision = "0060_financial_billing_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The invoice's paid amount must be the sum of immutable payment allocations.
    # This closes the gap where a finance-scoped SQL session could alter paid_bdt
    # while keeping the arithmetic CHECK(balance = total - paid) satisfied.
    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_guard_invoice_update()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $function$
        DECLARE allocated_total numeric(15,2);
        BEGIN
            IF OLD.status <> 'DRAFT' AND (
                NEW.company_id IS DISTINCT FROM OLD.company_id
                OR NEW.engagement_id IS DISTINCT FROM OLD.engagement_id
                OR NEW.invoice_number IS DISTINCT FROM OLD.invoice_number
                OR NEW.currency IS DISTINCT FROM OLD.currency
                OR NEW.subtotal_bdt IS DISTINCT FROM OLD.subtotal_bdt
                OR NEW.tax_bdt IS DISTINCT FROM OLD.tax_bdt
                OR NEW.total_bdt IS DISTINCT FROM OLD.total_bdt
                OR NEW.due_at IS DISTINCT FROM OLD.due_at
                OR NEW.notes IS DISTINCT FROM OLD.notes
                OR NEW.created_by IS DISTINCT FROM OLD.created_by
            ) THEN
                RAISE EXCEPTION 'issued invoice terms are immutable' USING ERRCODE = '55000';
            END IF;

            IF NEW.status IS DISTINCT FROM OLD.status AND NOT (
                (OLD.status = 'DRAFT' AND NEW.status IN ('ISSUED','VOID'))
                OR (OLD.status = 'ISSUED' AND NEW.status IN ('PARTIALLY_PAID','PAID','OVERDUE','VOID'))
                OR (OLD.status = 'OVERDUE' AND NEW.status IN ('PARTIALLY_PAID','PAID','VOID'))
                OR (OLD.status = 'PARTIALLY_PAID' AND NEW.status IN ('PAID','OVERDUE'))
            ) THEN
                RAISE EXCEPTION 'invalid invoice state transition: % -> %', OLD.status, NEW.status
                    USING ERRCODE = '55000';
            END IF;

            SELECT COALESCE(SUM(pa.amount_bdt), 0)
              INTO allocated_total
              FROM public.payment_allocations pa
             WHERE pa.invoice_id = NEW.id
               AND pa.company_id = NEW.company_id;

            IF NEW.paid_bdt IS DISTINCT FROM allocated_total THEN
                RAISE EXCEPTION 'invoice paid amount must equal posted payment allocations'
                    USING ERRCODE = '23514';
            END IF;
            IF NEW.balance_bdt IS DISTINCT FROM (NEW.total_bdt - allocated_total) THEN
                RAISE EXCEPTION 'invoice balance must reconcile to posted payment allocations'
                    USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END
        $function$
    """)
    op.execute("REVOKE ALL ON FUNCTION public.nlc_guard_invoice_update() FROM PUBLIC")

    # Serialize allocation attempts against both the invoice and payment.
    # Prevent a payment from being allocated beyond its receipt amount and
    # prevent allocations against unverified/non-settled receipts.
    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_guard_payment_allocation_insert()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $function$
        DECLARE
            invoice_row record;
            payment_row record;
            already_allocated numeric(15,2);
        BEGIN
            SELECT id, company_id, status, currency, balance_bdt
              INTO invoice_row
              FROM public.invoices
             WHERE id = NEW.invoice_id
               AND company_id = NEW.company_id
             FOR UPDATE;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'allocation invoice is unavailable for this company'
                    USING ERRCODE = '23503';
            END IF;

            SELECT id, company_id, status, currency, amount_bdt, verified_by, verified_at
              INTO payment_row
              FROM public.payments
             WHERE id = NEW.payment_id
               AND company_id = NEW.company_id
             FOR UPDATE;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'allocation payment is unavailable for this company'
                    USING ERRCODE = '23503';
            END IF;

            IF payment_row.status <> 'SETTLED'
               OR payment_row.verified_by IS NULL
               OR payment_row.verified_at IS NULL
               OR payment_row.currency <> NEW.currency
               OR invoice_row.currency <> NEW.currency THEN
                RAISE EXCEPTION 'allocation requires a verified settled BDT payment'
                    USING ERRCODE = '23514';
            END IF;

            IF invoice_row.status NOT IN ('ISSUED','PARTIALLY_PAID','OVERDUE')
               OR NEW.amount_bdt > invoice_row.balance_bdt THEN
                RAISE EXCEPTION 'allocation exceeds the invoice outstanding balance'
                    USING ERRCODE = '23514';
            END IF;

            SELECT COALESCE(SUM(pa.amount_bdt), 0)
              INTO already_allocated
              FROM public.payment_allocations pa
             WHERE pa.payment_id = NEW.payment_id
               AND pa.company_id = NEW.company_id;

            IF already_allocated + NEW.amount_bdt > payment_row.amount_bdt THEN
                RAISE EXCEPTION 'payment allocations exceed the verified receipt amount'
                    USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END
        $function$
    """)
    op.execute("REVOKE ALL ON FUNCTION public.nlc_guard_payment_allocation_insert() FROM PUBLIC")
    op.execute("""
        CREATE TRIGGER payment_allocations_guard_insert
        BEFORE INSERT ON public.payment_allocations
        FOR EACH ROW
        EXECUTE FUNCTION public.nlc_guard_payment_allocation_insert()
    """)


def downgrade() -> None:
    # Forward-only: removing these guards would weaken financial integrity.
    pass
