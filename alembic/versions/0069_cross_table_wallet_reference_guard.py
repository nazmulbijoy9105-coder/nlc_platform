"""Enforce manual wallet-reference uniqueness across claims and receipts.

Revision ID: 0069_cross_table_wallet_reference_guard
Revises: 0068_repair_aggregate_view_and_revenue_rls
"""
from alembic import op

revision = "0069_cross_table_wallet_reference_guard"
down_revision = "0068_repair_aggregate_view_and_revenue_rls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Do not silently bless an already-corrupt ledger. Require operators to
    # reconcile any historical cross-table collisions before this guard lands.
    op.execute("""
        DO $preflight$
        BEGIN
            IF EXISTS (
                SELECT 1
                  FROM public.payment_submissions ps
                  JOIN public.payments p
                    ON p.method = ps.method
                   AND lower(btrim(p.payer_reference)) =
                       lower(btrim(ps.payer_reference))
                 WHERE ps.method IN ('BKASH_MANUAL', 'NAGAD_MANUAL')
                   AND NULLIF(BTRIM(ps.payer_reference), '') IS NOT NULL
                   AND NULLIF(BTRIM(p.payer_reference), '') IS NOT NULL
            ) THEN
                RAISE EXCEPTION
                    'cross-table manual wallet reference collision exists; reconcile finance evidence before migration 0069'
                    USING ERRCODE = '23505',
                          CONSTRAINT = 'uq_wallet_reference_across_finance_tables';
            END IF;
        END
        $preflight$
    """)

    # The per-table unique indexes in 0067 cannot prevent one reference from
    # existing once in payment_submissions and once in payments. Serialize
    # writes to the normalized provider reference and check the opposite table
    # in a SECURITY DEFINER trigger, so direct SQL cannot bypass the invariant.
    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_guard_cross_table_wallet_reference()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $function$
        DECLARE
            normalized_reference text;
            lock_key text;
            duplicate_exists boolean;
        BEGIN
            IF NEW.method NOT IN ('BKASH_MANUAL', 'NAGAD_MANUAL')
               OR NULLIF(BTRIM(NEW.payer_reference), '') IS NULL THEN
                RETURN NEW;
            END IF;

            normalized_reference := lower(btrim(NEW.payer_reference));
            lock_key := 'nlc:wallet-reference:' || NEW.method || ':' || normalized_reference;

            -- This is intentionally the same transaction-scoped lock key used
            -- by FinanceService.submit_offline_payment/approve_offline_payment.
            PERFORM pg_advisory_xact_lock(hashtextextended(lock_key, 0));

            IF TG_TABLE_NAME = 'payment_submissions' THEN
                SELECT EXISTS (
                    SELECT 1
                    FROM public.payments p
                    WHERE p.method = NEW.method
                      AND lower(btrim(p.payer_reference)) = normalized_reference
                ) INTO duplicate_exists;
            ELSIF TG_TABLE_NAME = 'payments' THEN
                SELECT EXISTS (
                    SELECT 1
                    FROM public.payment_submissions ps
                    WHERE ps.method = NEW.method
                      AND lower(btrim(ps.payer_reference)) = normalized_reference
                ) INTO duplicate_exists;
            ELSE
                RAISE EXCEPTION 'wallet-reference guard attached to unsupported table %',
                    TG_TABLE_NAME USING ERRCODE = '55000';
            END IF;

            IF duplicate_exists THEN
                RAISE EXCEPTION
                    'manual wallet transaction reference already exists across finance claims and receipts'
                    USING ERRCODE = '23505',
                          CONSTRAINT = 'uq_wallet_reference_across_finance_tables';
            END IF;

            RETURN NEW;
        END
        $function$
    """)
    op.execute(
        "REVOKE ALL ON FUNCTION public.nlc_guard_cross_table_wallet_reference() FROM PUBLIC"
    )
    op.execute("""
        CREATE TRIGGER payment_submissions_cross_table_wallet_reference
        BEFORE INSERT OR UPDATE OF method, payer_reference
        ON public.payment_submissions
        FOR EACH ROW
        EXECUTE FUNCTION public.nlc_guard_cross_table_wallet_reference()
    """)
    op.execute("""
        CREATE TRIGGER payments_cross_table_wallet_reference
        BEFORE INSERT OR UPDATE OF method, payer_reference
        ON public.payments
        FOR EACH ROW
        EXECUTE FUNCTION public.nlc_guard_cross_table_wallet_reference()
    """)


def downgrade() -> None:
    # Forward-only: dropping this guard would permit a provider transfer to be
    # claimed against one invoice and independently credited to another.
    pass
