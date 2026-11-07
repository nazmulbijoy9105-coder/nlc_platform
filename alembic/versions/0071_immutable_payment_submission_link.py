"""Bind every approved offline receipt to its immutable source claim.

Revision ID: 0071_immutable_payment_submission_link
Revises: 0070_deferred_invoice_allocation_reconciliation
"""
from alembic import op

revision = "0071_immutable_payment_submission_link"
down_revision = "0070_deferred_invoice_allocation_reconciliation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 0069 introduced source_submission_id after the original payment UPDATE
    # guard was installed. Without this guard, a non-wallet receipt could have
    # its provenance link nulled or redirected after approval.
    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_guard_payment_source_submission_immutable()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $function$
        BEGIN
            IF NEW.source_submission_id IS DISTINCT FROM OLD.source_submission_id THEN
                RAISE EXCEPTION 'payment source submission provenance is immutable'
                    USING ERRCODE = '55000';
            END IF;
            RETURN NEW;
        END
        $function$
    """)
    op.execute("""
        REVOKE ALL ON FUNCTION
        public.nlc_guard_payment_source_submission_immutable() FROM PUBLIC
    """)
    op.execute("""
        CREATE TRIGGER payments_source_submission_immutable
        BEFORE UPDATE OF source_submission_id ON public.payments
        FOR EACH ROW
        EXECUTE FUNCTION public.nlc_guard_payment_source_submission_immutable()
    """)

    # Strengthen the deferred approval assertion: the verified receipt itself
    # must carry the exact source_submission_id, not merely ledger events that
    # happen to reference the same submission and payment IDs.
    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_assert_payment_submission_ledger_integrity()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = pg_catalog, public
        AS $function$
        DECLARE evidence_exists boolean;
        BEGIN
            IF NEW.status = 'APPROVED' THEN
                SELECT EXISTS (
                    SELECT 1
                      FROM public.payment_ledger_events verified
                      JOIN public.payment_ledger_events allocated
                        ON allocated.payment_id = verified.payment_id
                       AND allocated.submission_id = verified.submission_id
                       AND allocated.company_id = verified.company_id
                      JOIN public.payments payment
                        ON payment.id = verified.payment_id
                       AND payment.company_id = verified.company_id
                      JOIN public.payment_allocations allocation
                        ON allocation.payment_id = payment.id
                       AND allocation.company_id = payment.company_id
                     WHERE verified.submission_id = NEW.id
                       AND verified.company_id = NEW.company_id
                       AND verified.invoice_id = NEW.invoice_id
                       AND allocated.invoice_id = NEW.invoice_id
                       AND verified.event_type = 'PAYMENT_VERIFIED'
                       AND allocated.event_type = 'PAYMENT_ALLOCATED'
                       AND verified.amount_bdt = NEW.amount_bdt
                       AND allocated.amount_bdt = NEW.amount_bdt
                       AND payment.amount_bdt = NEW.amount_bdt
                       AND payment.method = NEW.method
                       AND payment.source_submission_id = NEW.id
                       AND payment.payer_reference IS NOT DISTINCT FROM NEW.payer_reference
                       AND payment.channel = 'OFFLINE'
                       AND payment.status = 'SETTLED'
                       AND payment.verified_by = NEW.reviewed_by
                       AND payment.verified_at = NEW.reviewed_at
                       AND NEW.reviewed_by = public.nlc_current_user_id()
                       AND public.nlc_current_user_is_finance_staff()
                       AND NEW.reviewed_by IS NOT NULL
                       AND NEW.reviewed_at IS NOT NULL
                       AND verified.actor_id = NEW.reviewed_by
                       AND allocated.actor_id = NEW.reviewed_by
                       AND allocation.invoice_id = NEW.invoice_id
                       AND allocation.amount_bdt = NEW.amount_bdt
                ) INTO evidence_exists;
                IF NOT evidence_exists THEN
                    RAISE EXCEPTION 'approved payment submission requires its exact source-linked, reviewer-bound verified receipt, allocation and ledger evidence'
                        USING ERRCODE = '23514';
                END IF;
            ELSIF NEW.status = 'REJECTED' THEN
                SELECT EXISTS (
                    SELECT 1
                      FROM public.payment_ledger_events event
                     WHERE event.submission_id = NEW.id
                       AND event.company_id = NEW.company_id
                       AND event.invoice_id = NEW.invoice_id
                       AND event.event_type = 'SUBMISSION_REJECTED'
                       AND event.amount_bdt = NEW.amount_bdt
                       AND event.actor_id = NEW.reviewed_by
                       AND NEW.reviewed_by = public.nlc_current_user_id()
                       AND public.nlc_current_user_is_finance_staff()
                       AND NEW.reviewed_by IS NOT NULL
                       AND NEW.reviewed_at IS NOT NULL
                       AND length(trim(COALESCE(NEW.review_note, ''))) > 0
                       AND event.event_metadata->>'reason' = NEW.review_note
                ) INTO evidence_exists;
                IF NOT evidence_exists THEN
                    RAISE EXCEPTION 'rejected payment submission requires reviewer-bound rejection ledger evidence'
                        USING ERRCODE = '23514';
                END IF;
            END IF;
            RETURN NULL;
        END
        $function$
    """)
    op.execute("""
        REVOKE ALL ON FUNCTION
        public.nlc_assert_payment_submission_ledger_integrity() FROM PUBLIC
    """)


def downgrade() -> None:
    # Forward-only: dropping source-link immutability would make approval
    # provenance mutable and weaken the finance evidence chain.
    pass
