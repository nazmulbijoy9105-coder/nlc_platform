"""Add reference-protected manual bKash and Nagad payment methods.

Revision ID: 0076_manual_mobile_wallet_methods
Revises: 0075_director_transfer_evidence

Only manual claim/receipt methods are enabled here. This does not claim an
online bKash/Nagad provider integration or verify provider callbacks.
"""
from alembic import op

revision = "0076_manual_mobile_wallet_methods"
down_revision = "0075_director_transfer_evidence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Serialize the preflight and index/trigger replacement against finance writes.
    op.execute(
        "LOCK TABLE public.payment_submissions, public.payments IN SHARE ROW EXCLUSIVE MODE"
    )
    op.execute("""
        DO $preflight$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM public.payment_submissions
                 WHERE method IN ('BKASH_MANUAL', 'NAGAD_MANUAL')
                   AND NULLIF(BTRIM(payer_reference), '') IS NULL
            ) OR EXISTS (
                SELECT 1 FROM public.payments
                 WHERE method IN ('BKASH_MANUAL', 'NAGAD_MANUAL')
                   AND NULLIF(BTRIM(payer_reference), '') IS NULL
            ) THEN
                RAISE EXCEPTION
                    'manual mobile-wallet records require a non-empty provider reference'
                    USING ERRCODE = '23514';
            END IF;

            IF EXISTS (
                SELECT 1 FROM public.payment_submissions
                 WHERE method IN ('BANK_TRANSFER', 'CHEQUE', 'BKASH_MANUAL', 'NAGAD_MANUAL')
                 GROUP BY method, lower(btrim(payer_reference))
                HAVING count(*) > 1
            ) OR EXISTS (
                SELECT 1 FROM public.payments
                 WHERE method IN ('BANK_TRANSFER', 'CHEQUE', 'BKASH_MANUAL', 'NAGAD_MANUAL')
                 GROUP BY method, lower(btrim(payer_reference))
                HAVING count(*) > 1
            ) THEN
                RAISE EXCEPTION
                    'duplicate normalized manual payment references exist; reconcile before migration 0076'
                    USING ERRCODE = '23505',
                          CONSTRAINT = 'uq_manual_reference_across_finance_tables';
            END IF;

            IF EXISTS (
                SELECT 1
                  FROM public.payment_submissions ps
                  JOIN public.payments p
                    ON p.method = ps.method
                   AND lower(btrim(p.payer_reference)) = lower(btrim(ps.payer_reference))
                 WHERE ps.method IN ('BKASH_MANUAL', 'NAGAD_MANUAL')
                   AND NULLIF(BTRIM(ps.payer_reference), '') IS NOT NULL
                   AND NULLIF(BTRIM(p.payer_reference), '') IS NOT NULL
                   AND NOT EXISTS (
                       SELECT 1 FROM public.payment_ledger_events e
                        WHERE e.payment_id = p.id
                          AND e.submission_id = ps.id
                          AND e.event_type = 'PAYMENT_VERIFIED'
                   )
            ) THEN
                RAISE EXCEPTION
                    'unmatched cross-table mobile-wallet reference collision exists; reconcile before migration 0076'
                    USING ERRCODE = '23505',
                          CONSTRAINT = 'uq_manual_reference_across_finance_tables';
            END IF;
        END
        $preflight$;
    """)

    op.execute("ALTER TABLE public.payment_submissions DROP CONSTRAINT ck_payment_submission_method")
    op.execute("ALTER TABLE public.payments DROP CONSTRAINT ck_payment_method")
    op.execute("ALTER TABLE public.payment_submissions DROP CONSTRAINT ck_payment_submission_reference_required")
    op.execute("ALTER TABLE public.payments DROP CONSTRAINT ck_payment_reference_required")

    op.execute("""
        ALTER TABLE public.payment_submissions
        ADD CONSTRAINT ck_payment_submission_method
        CHECK (method IN ('BANK_TRANSFER','CASH','CHEQUE','BKASH_MANUAL','NAGAD_MANUAL'))
    """)
    op.execute("""
        ALTER TABLE public.payments
        ADD CONSTRAINT ck_payment_method
        CHECK (method IN ('BANK_TRANSFER','CASH','CHEQUE','SSLCOMMERZ','BKASH_MANUAL','NAGAD_MANUAL'))
    """)
    op.execute("""
        ALTER TABLE public.payment_submissions
        ADD CONSTRAINT ck_payment_submission_reference_required
        CHECK (
            method NOT IN ('BANK_TRANSFER','CHEQUE','BKASH_MANUAL','NAGAD_MANUAL')
            OR NULLIF(BTRIM(payer_reference), '') IS NOT NULL
        )
    """)
    op.execute("""
        ALTER TABLE public.payments
        ADD CONSTRAINT ck_payment_reference_required
        CHECK (
            method NOT IN ('BANK_TRANSFER','CHEQUE','BKASH_MANUAL','NAGAD_MANUAL')
            OR NULLIF(BTRIM(payer_reference), '') IS NOT NULL
        )
    """)

    op.execute("DROP INDEX public.uq_payment_submission_manual_reference")
    op.execute("DROP INDEX public.uq_payment_manual_reference")
    op.execute("""
        CREATE UNIQUE INDEX uq_payment_submission_manual_reference
        ON public.payment_submissions (method, lower(btrim(payer_reference)))
        WHERE payer_reference IS NOT NULL
          AND method IN ('BANK_TRANSFER', 'CHEQUE', 'BKASH_MANUAL', 'NAGAD_MANUAL')
    """)
    op.execute("""
        CREATE UNIQUE INDEX uq_payment_manual_reference
        ON public.payments (method, lower(btrim(payer_reference)))
        WHERE payer_reference IS NOT NULL
          AND method IN ('BANK_TRANSFER', 'CHEQUE', 'BKASH_MANUAL', 'NAGAD_MANUAL')
    """)

    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_guard_cross_table_manual_reference()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        SET row_security = off
        AS $function$
        DECLARE
            normalized_reference text;
            lock_key text;
            duplicate_exists boolean;
        BEGIN
            IF NEW.method NOT IN ('BANK_TRANSFER', 'CHEQUE', 'BKASH_MANUAL', 'NAGAD_MANUAL')
               OR NULLIF(BTRIM(NEW.payer_reference), '') IS NULL THEN
                RETURN NEW;
            END IF;

            normalized_reference := lower(btrim(NEW.payer_reference));
            lock_key := 'nlc:manual-reference:' || NEW.method || ':' || normalized_reference;

            -- This is intentionally the same transaction-scoped lock key used
            -- by FinanceService.submit_offline_payment/approve_offline_payment.
            PERFORM pg_advisory_xact_lock(hashtextextended(lock_key, 0));

            IF TG_TABLE_NAME = 'payment_submissions' THEN
                SELECT EXISTS (
                    SELECT 1
                    FROM public.payments p
                    WHERE p.method = NEW.method
                      AND lower(btrim(p.payer_reference)) = normalized_reference
                      AND (
                          p.source_submission_id IS DISTINCT FROM NEW.id
                          OR NOT EXISTS (
                              SELECT 1
                                FROM public.payment_submissions source
                               WHERE source.id = NEW.id
                                 AND source.company_id = p.company_id
                                 AND source.status = 'APPROVED'
                                 AND source.method = p.method
                                 AND lower(btrim(source.payer_reference)) =
                                     lower(btrim(p.payer_reference))
                          )
                      )
                ) INTO duplicate_exists;
            ELSIF TG_TABLE_NAME = 'payments' THEN
                -- A receipt may reuse the reference of exactly one source
                -- claim, but only when that claim is approved and every
                -- tenant/payment identity field matches the receipt.
                IF NEW.source_submission_id IS NOT NULL AND NOT EXISTS (
                    SELECT 1
                    FROM public.payment_submissions source
                    WHERE source.id = NEW.source_submission_id
                      AND source.company_id = NEW.company_id
                      AND source.status = 'APPROVED'
                      AND source.method = NEW.method
                      AND lower(btrim(source.payer_reference)) = normalized_reference
                ) THEN
                    RAISE EXCEPTION
                        'linked payment source must be an approved matching claim'
                        USING ERRCODE = '23514';
                END IF;

                SELECT EXISTS (
                    SELECT 1
                    FROM public.payment_submissions ps
                    WHERE ps.method = NEW.method
                      AND lower(btrim(ps.payer_reference)) = normalized_reference
                      AND ps.id IS DISTINCT FROM NEW.source_submission_id
                ) INTO duplicate_exists;
            ELSE
                RAISE EXCEPTION 'manual-reference guard attached to unsupported table %',
                    TG_TABLE_NAME USING ERRCODE = '55000';
            END IF;

            IF duplicate_exists THEN
                RAISE EXCEPTION
                    'uq_manual_reference_across_finance_tables: manual payment reference already exists across finance claims and receipts'
                    USING ERRCODE = '23505',
                          CONSTRAINT = 'uq_manual_reference_across_finance_tables';
            END IF;

            RETURN NEW;
        END
        $function$
    """)

def downgrade() -> None:
    # Forward-only: narrowing accepted payment methods would invalidate
    # existing wallet claims and receipts, while dropping reference guards
    # would reopen duplicate-credit paths.
    pass
