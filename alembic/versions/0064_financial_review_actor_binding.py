"""Bind payment review decisions to the verified ledger actors.

Revision ID: 0064_financial_review_actor_binding
Revises: 0063_financial_review_and_provider_guards
"""
from alembic import op

revision = "0064_financial_review_actor_binding"
down_revision = "0063_financial_review_and_provider_guards"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Evidence must prove not only that a payment exists, but that the
    # reviewer recorded on the submission is the same actor who verified
    # the receipt and posted both immutable ledger events.
    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_assert_payment_submission_ledger_integrity()
        RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, public AS $function$
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
                       AND verified.event_type = 'PAYMENT_VERIFIED'
                       AND allocated.event_type = 'PAYMENT_ALLOCATED'
                       AND verified.amount_bdt = NEW.amount_bdt
                       AND allocated.amount_bdt = NEW.amount_bdt
                       AND payment.amount_bdt = NEW.amount_bdt
                       AND payment.method = NEW.method
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
                    RAISE EXCEPTION 'approved payment submission requires reviewer-bound verified payment, allocation and ledger evidence'
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
    op.execute("REVOKE ALL ON FUNCTION public.nlc_assert_payment_submission_ledger_integrity() FROM PUBLIC")


def downgrade() -> None:
    # Forward-only: restoring weaker reviewer attribution would weaken
    # financial evidence integrity after deployment.
    pass
