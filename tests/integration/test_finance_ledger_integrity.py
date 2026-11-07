"""PostgreSQL contract checks for financial allocation integrity guards."""
from __future__ import annotations

import pytest
from sqlalchemy import text

from app.models.database import set_rls_context


@pytest.mark.asyncio
async def test_invoice_update_guard_reconciles_paid_amount_to_allocations(db):
    result = await db.execute(
        text("SELECT pg_get_functiondef('public.nlc_guard_invoice_update()'::regprocedure)")
    )
    definition = result.scalar_one()

    assert "invoice paid amount must equal posted payment allocations" in definition
    assert "invoice balance must reconcile to posted payment allocations" in definition
    assert "FROM public.payment_allocations" in definition


@pytest.mark.asyncio
async def test_payment_allocation_guard_serializes_and_caps_allocations(db):
    result = await db.execute(
        text("SELECT pg_get_functiondef('public.nlc_guard_payment_allocation_insert()'::regprocedure)")
    )
    definition = result.scalar_one()

    assert definition.count("FOR UPDATE") >= 2  # invoice and payment rows are both serialized
    assert "payment allocations exceed the verified receipt amount" in definition
    assert "allocation requires a verified settled BDT payment" in definition


@pytest.mark.asyncio
async def test_payment_allocation_insert_trigger_is_installed(db):
    result = await db.execute(
        text("""
            SELECT EXISTS (
                SELECT 1
                  FROM pg_trigger t
                  JOIN pg_class c ON c.oid = t.tgrelid
                  JOIN pg_namespace n ON n.oid = c.relnamespace
                 WHERE n.nspname = 'public'
                   AND c.relname = 'payment_allocations'
                   AND t.tgname = 'payment_allocations_guard_insert'
                   AND NOT t.tgisinternal
            )
        """)
    )
    assert result.scalar_one() is True


@pytest.mark.asyncio
async def test_review_status_requires_matching_ledger_evidence_at_commit(db):
    result = await db.execute(
        text("SELECT pg_get_functiondef('public.nlc_assert_payment_submission_ledger_integrity()'::regprocedure)")
    )
    definition = result.scalar_one()

    assert "approved payment submission requires reviewer-bound verified payment" in definition
    assert "rejected payment submission requires reviewer-bound rejection ledger evidence" in definition
    assert "payment.verified_by = NEW.reviewed_by" in definition
    assert "payment.verified_at = NEW.reviewed_at" in definition
    assert "verified.actor_id = NEW.reviewed_by" in definition
    assert "allocated.actor_id = NEW.reviewed_by" in definition
    assert "event.actor_id = NEW.reviewed_by" in definition
    assert "NEW.reviewed_by = public.nlc_current_user_id()" in definition
    assert "public.nlc_current_user_is_finance_staff()" in definition
    assert "event.event_metadata->>'reason' = NEW.review_note" in definition
    assert "PAYMENT_VERIFIED" in definition
    assert "PAYMENT_ALLOCATED" in definition
    assert "SUBMISSION_REJECTED" in definition


@pytest.mark.asyncio
async def test_unsupported_payment_and_intent_transitions_are_blocked(db, db_company, db_user):
    payment_result = await db.execute(
        text("SELECT pg_get_functiondef('public.nlc_guard_payment_update()'::regprocedure)")
    )
    intent_result = await db.execute(
        text("SELECT pg_get_functiondef('public.nlc_guard_payment_intent_update()'::regprocedure)")
    )

    assert "payment reversals, refunds and disputes require a dedicated verified workflow" in payment_result.scalar_one()
    assert "online payment intents are immutable until verified provider integration is enabled" in intent_result.scalar_one()

    import uuid
    from datetime import UTC, datetime, timedelta
    from decimal import Decimal

    from sqlalchemy.exc import DBAPIError
    from app.models.finance import PaymentIntent
    from app.services.finance_service import FinanceService

    await set_rls_context(db, str(db_user.id))
    service = FinanceService(db)
    invoice = await service.create_invoice(
        company_id=db_company.id,
        engagement_id=None,
        lines=[{
            "description": "Provider intent transition guard",
            "quantity": "1",
            "unit_price_bdt": "100.00",
        }],
        tax_bdt=Decimal("0.00"),
        due_at=None,
        notes=None,
        actor_id=db_user.id,
    )
    await service.issue_invoice(invoice.id)
    intent = PaymentIntent(
        company_id=db_company.id,
        invoice_id=invoice.id,
        provider_name="SSLCOMMERZ",
        idempotency_key=f"test-{uuid.uuid4().hex}",
        provider_order_id=f"order-{uuid.uuid4().hex}",
        amount_bdt=Decimal("100.00"),
        currency="BDT",
        status="CREATED",
        expires_at=datetime.now(UTC) + timedelta(minutes=15),
        created_by=db_user.id,
    )
    db.add(intent)
    await db.flush()

    with pytest.raises(DBAPIError):
        async with db.begin_nested():
            intent.status = "SUCCEEDED"
            intent.provider_transaction_id = f"txn-{uuid.uuid4().hex}"
            intent.verified_at = datetime.now(UTC)
            await db.flush()


@pytest.mark.asyncio
async def test_provider_event_history_is_append_only(db):
    result = await db.execute(
        text("SELECT pg_get_functiondef('public.nlc_reject_payment_provider_event_mutation()'::regprocedure)")
    )
    assert "payment provider events are append-only" in result.scalar_one()


@pytest.mark.asyncio
async def test_overdue_invoices_remain_eligible_for_payment_submission(db):
    result = await db.execute(
        text("SELECT pg_get_expr(polwithcheck, polrelid) FROM pg_policy WHERE polname = 'payment_submissions_submit_insert'")
    )
    policy = result.scalar_one()
    assert "OVERDUE" in policy


@pytest.mark.asyncio
async def test_database_rejects_status_only_payment_submission_approval(db, db_company, db_user):
    """A direct status update cannot approve a claim without payment evidence."""
    from datetime import UTC, datetime
    from decimal import Decimal

    from sqlalchemy.exc import DBAPIError

    from app.services.finance_service import FinanceService

    await set_rls_context(db, str(db_user.id))
    service = FinanceService(db)
    invoice = await service.create_invoice(
        company_id=db_company.id,
        engagement_id=None,
        lines=[{
            "description": "Ledger integrity test",
            "quantity": "1",
            "unit_price_bdt": "100.00",
        }],
        tax_bdt=Decimal("0.00"),
        due_at=None,
        notes=None,
        actor_id=db_user.id,
    )
    invoice = await service.issue_invoice(invoice.id)
    submission = await service.submit_offline_payment(
        company_id=db_company.id,
        invoice_id=invoice.id,
        submitted_by=db_user.id,
        method="CASH",
        amount_bdt=Decimal("25.00"),
        payer_reference=None,
        paid_at=None,
        evidence_document_id=None,
    )

    with pytest.raises(DBAPIError):
        async with db.begin_nested():
            submission.status = "APPROVED"
            submission.reviewed_by = db_user.id
            submission.reviewed_at = datetime.now(UTC)
            await db.flush()
            # Force the deferred constraint trigger now, inside the savepoint.
            await db.execute(text("SET CONSTRAINTS payment_submissions_ledger_integrity IMMEDIATE"))

@pytest.mark.asyncio
async def test_offline_payment_approval_posts_reconciled_ledger_once(db, db_company, db_user):
    """Exercise the supported approval path and its idempotent retry."""
    from decimal import Decimal

    from sqlalchemy import select
    from app.models.finance import (
        Invoice,
        Payment,
        PaymentAllocation,
        PaymentLedgerEvent,
        PaymentSubmission,
    )
    from app.services.finance_service import FinanceService

    await set_rls_context(db, str(db_user.id))
    service = FinanceService(db)
    invoice = await service.create_invoice(
        company_id=db_company.id,
        engagement_id=None,
        lines=[{
            "description": "Successful payment approval",
            "quantity": "1",
            "unit_price_bdt": "100.00",
        }],
        tax_bdt=Decimal("0.00"),
        due_at=None,
        notes=None,
        actor_id=db_user.id,
    )
    await service.issue_invoice(invoice.id)
    submission = await service.submit_offline_payment(
        company_id=db_company.id,
        invoice_id=invoice.id,
        submitted_by=db_user.id,
        method="CASH",
        amount_bdt=Decimal("40.00"),
        payer_reference=None,
        paid_at=None,
        evidence_document_id=None,
    )

    payment = await service.approve_offline_payment(
        submission_id=submission.id,
        reviewer_id=db_user.id,
        review_note="Cash receipt verified",
        cheque_cleared_at=None,
    )
    retry_payment = await service.approve_offline_payment(
        submission_id=submission.id,
        reviewer_id=db_user.id,
        review_note="Retry must not duplicate the receipt",
        cheque_cleared_at=None,
    )
    assert retry_payment.id == payment.id

    await db.refresh(submission)
    await db.refresh(invoice)
    assert submission.status == "APPROVED"
    assert submission.reviewed_by == db_user.id
    assert invoice.paid_bdt == Decimal("40.00")
    assert invoice.balance_bdt == Decimal("60.00")
    assert invoice.status == "PARTIALLY_PAID"

    allocations = list((await db.execute(
        select(PaymentAllocation).where(PaymentAllocation.payment_id == payment.id)
    )).scalars().all())
    events = list((await db.execute(
        select(PaymentLedgerEvent).where(PaymentLedgerEvent.submission_id == submission.id)
    )).scalars().all())
    payments = list((await db.execute(
        select(Payment).where(Payment.company_id == db_company.id)
    )).scalars().all())
    assert len(allocations) == 1
    assert allocations[0].invoice_id == invoice.id
    assert allocations[0].amount_bdt == Decimal("40.00")
    assert {event.event_type for event in events} == {"PAYMENT_VERIFIED", "PAYMENT_ALLOCATED"}
    assert len(events) == 2
    assert len(payments) == 1

    # Refund/reversal/dispute transitions remain blocked until their
    # dedicated evidence and reconciliation workflow is implemented.
    from sqlalchemy.exc import DBAPIError
    with pytest.raises(DBAPIError):
        async with db.begin_nested():
            payment.status = "REFUNDED"
            await db.flush()


@pytest.mark.asyncio
async def test_offline_payment_rejection_requires_reason_and_posts_audit_event(db, db_company, db_user):
    """Exercise a rejection with mandatory reason and immutable ledger evidence."""
    from decimal import Decimal

    from sqlalchemy import select
    from app.models.finance import PaymentLedgerEvent, PaymentSubmission
    from app.services.finance_service import FinanceConflictError, FinanceService

    await set_rls_context(db, str(db_user.id))
    service = FinanceService(db)
    invoice = await service.create_invoice(
        company_id=db_company.id,
        engagement_id=None,
        lines=[{
            "description": "Rejected payment submission",
            "quantity": "1",
            "unit_price_bdt": "100.00",
        }],
        tax_bdt=Decimal("0.00"),
        due_at=None,
        notes=None,
        actor_id=db_user.id,
    )
    await service.issue_invoice(invoice.id)
    submission = await service.submit_offline_payment(
        company_id=db_company.id,
        invoice_id=invoice.id,
        submitted_by=db_user.id,
        method="CASH",
        amount_bdt=Decimal("25.00"),
        payer_reference=None,
        paid_at=None,
        evidence_document_id=None,
    )

    with pytest.raises(FinanceConflictError, match="rejection reason"):
        await service.reject_offline_payment(
            submission_id=submission.id,
            reviewer_id=db_user.id,
            reason="   ",
        )

    rejected = await service.reject_offline_payment(
        submission_id=submission.id,
        reviewer_id=db_user.id,
        reason="Receipt evidence does not match",
    )
    assert rejected.status == "REJECTED"
    assert rejected.reviewed_by == db_user.id
    event = (await db.execute(
        select(PaymentLedgerEvent).where(
            PaymentLedgerEvent.submission_id == submission.id,
            PaymentLedgerEvent.event_type == "SUBMISSION_REJECTED",
        )
    )).scalar_one()
    assert event.amount_bdt == Decimal("25.00")
    assert event.event_metadata["reason"] == "Receipt evidence does not match"

    await db.refresh(invoice)
    assert invoice.paid_bdt == Decimal("0.00")
    assert invoice.balance_bdt == Decimal("100.00")

@pytest.mark.asyncio
async def test_database_rejects_status_only_payment_submission_rejection(db, db_company, db_user):
    """A direct rejection cannot bypass the required rejection ledger event."""
    from datetime import UTC, datetime
    from decimal import Decimal

    from sqlalchemy.exc import DBAPIError
    from app.services.finance_service import FinanceService

    await set_rls_context(db, str(db_user.id))
    service = FinanceService(db)
    invoice = await service.create_invoice(
        company_id=db_company.id,
        engagement_id=None,
        lines=[{
            "description": "Rejection ledger integrity test",
            "quantity": "1",
            "unit_price_bdt": "100.00",
        }],
        tax_bdt=Decimal("0.00"),
        due_at=None,
        notes=None,
        actor_id=db_user.id,
    )
    await service.issue_invoice(invoice.id)
    submission = await service.submit_offline_payment(
        company_id=db_company.id,
        invoice_id=invoice.id,
        submitted_by=db_user.id,
        method="CASH",
        amount_bdt=Decimal("25.00"),
        payer_reference=None,
        paid_at=None,
        evidence_document_id=None,
    )

    with pytest.raises(DBAPIError):
        async with db.begin_nested():
            submission.status = "REJECTED"
            submission.reviewed_by = db_user.id
            submission.reviewed_at = datetime.now(UTC)
            submission.review_note = "Attempted status-only rejection"
            await db.flush()
            await db.execute(text("SET CONSTRAINTS payment_submissions_ledger_integrity IMMEDIATE"))


@pytest.mark.asyncio
async def test_manual_wallet_transaction_reference_cannot_be_submitted_twice(db, db_company, db_user):
    from decimal import Decimal

    from app.services.finance_service import FinanceConflictError, FinanceService

    await set_rls_context(db, str(db_user.id))
    service = FinanceService(db)
    invoices = []
    for description in ("First wallet claim", "Second wallet claim"):
        invoice = await service.create_invoice(
            company_id=db_company.id,
            engagement_id=None,
            lines=[{
                "description": description,
                "quantity": "1",
                "unit_price_bdt": "100.00",
            }],
            tax_bdt=Decimal("0.00"),
            due_at=None,
            notes=None,
            actor_id=db_user.id,
        )
        invoices.append(await service.issue_invoice(invoice.id))

    await service.submit_offline_payment(
        company_id=db_company.id,
        invoice_id=invoices[0].id,
        submitted_by=db_user.id,
        method="BANK_TRANSFER",
        amount_bdt=Decimal("25.00"),
        payer_reference="Trx-CaseSensitive-123",
        paid_at=None,
        evidence_document_id=None,
    )

    with pytest.raises(FinanceConflictError, match="already been submitted or credited"):
        await service.submit_offline_payment(
            company_id=db_company.id,
            invoice_id=invoices[1].id,
            submitted_by=db_user.id,
            method="BANK_TRANSFER",
            amount_bdt=Decimal("25.00"),
            payer_reference="  trx-casesensitive-123  ",
            paid_at=None,
            evidence_document_id=None,
        )
