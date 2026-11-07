"""Prevent duplicate manual bKash/Nagad transaction references.

Revision ID: 0067_unique_manual_wallet_references
Revises: 0066_verified_revenue_pipeline
"""
from alembic import op

revision = "0067_unique_manual_wallet_references"
down_revision = "0066_verified_revenue_pipeline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Do not install uniqueness over ambiguous legacy data. Require explicit
    # reconciliation rather than selecting an arbitrary claim or receipt.
    op.execute("""
        DO $preflight$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM public.payment_submissions
                WHERE method IN ('BANK_TRANSFER', 'CHEQUE', 'BKASH_MANUAL', 'NAGAD_MANUAL')
                  AND NULLIF(BTRIM(payer_reference), '') IS NULL
            ) THEN
                RAISE EXCEPTION
                    'payment_submissions contains a reference-required method without a reference; reconcile before migration';
            END IF;

            IF EXISTS (
                SELECT 1
                FROM public.payments
                WHERE method IN ('BANK_TRANSFER', 'CHEQUE', 'BKASH_MANUAL', 'NAGAD_MANUAL')
                  AND NULLIF(BTRIM(payer_reference), '') IS NULL
            ) THEN
                RAISE EXCEPTION
                    'payments contains a reference-required method without a reference; reconcile before migration';
            END IF;

            IF EXISTS (
                SELECT 1
                FROM public.payment_submissions
                WHERE payer_reference IS NOT NULL
                  AND method IN ('BKASH_MANUAL', 'NAGAD_MANUAL')
                  GROUP BY method, lower(btrim(payer_reference))
                HAVING count(*) > 1
            ) THEN
                RAISE EXCEPTION
                    'duplicate active manual wallet references exist in payment_submissions; reconcile before migration';
            END IF;

            IF EXISTS (
                SELECT 1
                FROM public.payments
                WHERE payer_reference IS NOT NULL
                  AND method IN ('BKASH_MANUAL', 'NAGAD_MANUAL')
                GROUP BY method, lower(btrim(payer_reference))
                HAVING count(*) > 1
            ) THEN
                RAISE EXCEPTION
                    'duplicate manual wallet references exist in payments; reconcile before migration';
            END IF;
        END
        $preflight$;
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

    op.execute("""
        CREATE UNIQUE INDEX uq_payment_submission_wallet_reference
            ON public.payment_submissions (
                method,
                lower(btrim(payer_reference))
            )
            WHERE payer_reference IS NOT NULL
              AND method IN ('BKASH_MANUAL', 'NAGAD_MANUAL')
    """)
    op.execute("""
        CREATE UNIQUE INDEX uq_payment_wallet_reference
            ON public.payments (
                method,
                lower(btrim(payer_reference))
            )
            WHERE payer_reference IS NOT NULL
              AND method IN ('BKASH_MANUAL', 'NAGAD_MANUAL')
    """)


def downgrade() -> None:
    # Forward-only: removing these constraints would permit duplicate manual
    # wallet receipts to be credited against multiple invoices.
    pass
