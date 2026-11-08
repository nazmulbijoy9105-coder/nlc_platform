"""Close unsupported provider transitions and bind submission review to ledger evidence.

Revision ID: 0063_financial_review_and_provider_guards
Revises: 0062_financial_pending_payment_reservations
"""
from alembic import op

revision = "0063_financial_review_and_provider_guards"
down_revision = "0062_financial_pending_payment_reservations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The current product has no verified online-provider callback or reversal
    # workflow. Do not allow SQL callers to manufacture those state transitions.
    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_guard_payment_update()
        RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, public AS $function$
        BEGIN
            IF (
                NEW.company_id IS DISTINCT FROM OLD.company_id
                OR NEW.payment_number IS DISTINCT FROM OLD.payment_number
                OR NEW.method IS DISTINCT FROM OLD.method
                OR NEW.channel IS DISTINCT FROM OLD.channel
                OR NEW.amount_bdt IS DISTINCT FROM OLD.amount_bdt
                OR NEW.currency IS DISTINCT FROM OLD.currency
                OR NEW.provider_name IS DISTINCT FROM OLD.provider_name
                OR NEW.provider_transaction_id IS DISTINCT FROM OLD.provider_transaction_id
                OR NEW.payer_reference IS DISTINCT FROM OLD.payer_reference
                OR NEW.received_at IS DISTINCT FROM OLD.received_at
                OR NEW.verified_by IS DISTINCT FROM OLD.verified_by
                OR NEW.verified_at IS DISTINCT FROM OLD.verified_at
                OR NEW.created_by IS DISTINCT FROM OLD.created_by
            ) THEN
                RAISE EXCEPTION 'payment receipt facts are immutable' USING ERRCODE = '55000';
            END IF;
            IF NEW.status IS DISTINCT FROM OLD.status THEN
                RAISE EXCEPTION 'payment reversals, refunds and disputes require a dedicated verified workflow'
                    USING ERRCODE = '55000';
            END IF;
            RETURN NEW;
        END
        $function$
    """)

    # No provider checkout/callback implementation exists yet. Keep intents
    # immutable after creation instead of allowing staff SQL to mark them paid.
    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_guard_payment_intent_update()
        RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, public AS $function$
        BEGIN
            RAISE EXCEPTION 'online payment intents are immutable until verified provider integration is enabled'
                USING ERRCODE = '55000';
        END
        $function$
    """)

    # These functions are invoked by attached triggers, not directly by
    # application callers. Revoke PUBLIC EXECUTE so SECURITY DEFINER routines
    # cannot widen the read-only audit role's callable surface.
    op.execute("REVOKE ALL ON FUNCTION public.nlc_guard_payment_update() FROM PUBLIC")
    op.execute("REVOKE ALL ON FUNCTION public.nlc_guard_payment_intent_update() FROM PUBLIC")

    # Provider events are evidence records, not editable staff notes.
    op.execute("""
        CREATE OR REPLACE FUNCTION public.nlc_reject_payment_provider_event_mutation()
        RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, public AS $function$
        BEGIN
            RAISE EXCEPTION 'payment provider events are append-only'
                USING ERRCODE = '55000';
        END
        $function$
    """)
    op.execute("REVOKE ALL ON FUNCTION public.nlc_reject_payment_provider_event_mutation() FROM PUBLIC")
    op.execute("""
        CREATE TRIGGER payment_provider_events_append_only
        BEFORE UPDATE OR DELETE ON public.payment_provider_events
        FOR EACH ROW EXECUTE FUNCTION public.nlc_reject_payment_provider_event_mutation()
    """)
    op.execute("""
        REVOKE UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER
        ON TABLE public.payment_provider_events FROM nlc_app_role
    """)
    op.execute("GRANT SELECT, INSERT ON TABLE public.payment_provider_events TO nlc_app_role")

    # An approval/rejection is not valid unless the matching ledger evidence
    # exists by transaction commit. This prevents direct SQL status-only review.
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
                       AND payment.verified_by IS NOT NULL
                       AND payment.verified_at IS NOT NULL
                       AND allocation.invoice_id = NEW.invoice_id
                       AND allocation.amount_bdt = NEW.amount_bdt
                ) INTO evidence_exists;
                IF NOT evidence_exists THEN
                    RAISE EXCEPTION 'approved payment submission requires matching verified payment, allocation and ledger events'
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
                ) INTO evidence_exists;
                IF NOT evidence_exists THEN
                    RAISE EXCEPTION 'rejected payment submission requires a matching rejection ledger event'
                        USING ERRCODE = '23514';
                END IF;
            END IF;
            RETURN NULL;
        END
        $function$
    """)
    op.execute("REVOKE ALL ON FUNCTION public.nlc_assert_payment_submission_ledger_integrity() FROM PUBLIC")
    op.execute("""
        CREATE CONSTRAINT TRIGGER payment_submissions_ledger_integrity
        AFTER INSERT OR UPDATE ON public.payment_submissions
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW
        EXECUTE FUNCTION public.nlc_assert_payment_submission_ledger_integrity()
    """)

    # Overdue invoices remain payable. Align row policy with service and DB guards.
    op.execute("DROP POLICY IF EXISTS payment_submissions_submit_insert ON public.payment_submissions")
    op.execute("""
        CREATE POLICY payment_submissions_submit_insert ON public.payment_submissions
        FOR INSERT WITH CHECK (
            public.nlc_can_submit_payment_company(company_id)
            AND (
                public.nlc_current_user_is_finance_staff()
                OR submitted_by = public.nlc_current_user_id()
            )
            AND status = 'PENDING_REVIEW'
            AND reviewed_by IS NULL
            AND reviewed_at IS NULL
            AND review_note IS NULL
            AND cheque_cleared_at IS NULL
            AND (
                evidence_document_id IS NULL
                OR EXISTS (
                    SELECT 1 FROM public.documents d
                    WHERE d.id = payment_submissions.evidence_document_id
                      AND d.company_id = payment_submissions.company_id
                )
            )
            AND EXISTS (
                SELECT 1 FROM public.invoices i
                WHERE i.id = payment_submissions.invoice_id
                  AND i.company_id = payment_submissions.company_id
                  AND i.status IN ('ISSUED','PARTIALLY_PAID','OVERDUE')
                  AND payment_submissions.amount_bdt <= i.balance_bdt
            )
        )
    """)
    op.execute("DROP POLICY IF EXISTS payment_intents_submit_insert ON public.payment_intents")
    op.execute("""
        CREATE POLICY payment_intents_submit_insert ON public.payment_intents
        FOR INSERT WITH CHECK (
            public.nlc_can_submit_payment_company(company_id)
            AND (
                public.nlc_current_user_is_finance_staff()
                OR created_by = public.nlc_current_user_id()
            )
            AND status = 'CREATED'
            AND provider_transaction_id IS NULL
            AND verified_at IS NULL
            AND checkout_url IS NULL
            AND EXISTS (
                SELECT 1 FROM public.invoices i
                WHERE i.id = payment_intents.invoice_id
                  AND i.company_id = payment_intents.company_id
                  AND i.status IN ('ISSUED','PARTIALLY_PAID','OVERDUE')
                  AND payment_intents.amount_bdt <= i.balance_bdt
            )
        )
    """)


def downgrade() -> None:
    # Forward-only: re-enabling unverified provider/reversal transitions or
    # removing ledger evidence requirements would weaken financial integrity.
    pass
