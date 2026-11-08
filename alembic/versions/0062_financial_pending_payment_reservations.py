"""Reserve invoice balances across pending payment submissions.

Revision ID: 0062_financial_pending_payment_reservations
Revises: 0061_financial_allocation_integrity
"""
from alembic import op

revision = "0062_financial_pending_payment_reservations"
down_revision = "0061_financial_allocation_integrity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Lock the invoice so concurrent submissions cannot each reserve the same
    # outstanding balance independently.
    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_guard_pending_payment_submission_insert()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $function$
        DECLARE
            invoice_row record;
            pending_total numeric(15,2);
        BEGIN
            IF NEW.status <> 'PENDING_REVIEW' THEN
                RAISE EXCEPTION 'new payment submissions must enter pending review'
                    USING ERRCODE = '23514';
            END IF;

            SELECT id, company_id, status, balance_bdt
              INTO invoice_row
              FROM public.invoices
             WHERE id = NEW.invoice_id
               AND company_id = NEW.company_id
             FOR UPDATE;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'payment submission invoice is unavailable for this company'
                    USING ERRCODE = '23503';
            END IF;
            IF invoice_row.status NOT IN ('ISSUED','PARTIALLY_PAID','OVERDUE') THEN
                RAISE EXCEPTION 'invoice is not open for payment submissions'
                    USING ERRCODE = '23514';
            END IF;

            SELECT COALESCE(SUM(ps.amount_bdt), 0)
              INTO pending_total
              FROM public.payment_submissions ps
             WHERE ps.invoice_id = NEW.invoice_id
               AND ps.company_id = NEW.company_id
               AND ps.status = 'PENDING_REVIEW';

            IF pending_total + NEW.amount_bdt > invoice_row.balance_bdt THEN
                RAISE EXCEPTION 'pending payment submissions exceed the invoice outstanding balance'
                    USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END
        $function$
    """)
    op.execute("REVOKE ALL ON FUNCTION public.nlc_guard_pending_payment_submission_insert() FROM PUBLIC")
    op.execute("""
        CREATE TRIGGER payment_submissions_reserve_balance
        BEFORE INSERT ON public.payment_submissions
        FOR EACH ROW
        EXECUTE FUNCTION public.nlc_guard_pending_payment_submission_insert()
    """)


def downgrade() -> None:
    # Forward-only: removing reservation checks permits pending claims to
    # overbook the same invoice balance.
    pass
