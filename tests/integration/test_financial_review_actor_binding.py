"""Database regression tests for reviewer-bound finance ledger evidence."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.models.database import set_rls_context


@pytest.mark.asyncio
@pytest.mark.parametrize("allocation_event_matches_invoice", [True, False])
async def test_approval_requires_allocation_event_for_submission_invoice(
    db, db_company, db_user, allocation_event_matches_invoice
):
    """The deferred DB trigger rejects an allocation event naming another invoice."""
    from app.models.finance import (
        Payment,
        PaymentAllocation,
        PaymentLedgerEvent,
        PaymentSubmission,
    )
    from app.services.finance_service import FinanceService

    await set_rls_context(db, str(db_user.id))
    service = FinanceService(db)
    invoices = []
    for description in ("Primary payment invoice", "Other valid company invoice"):
        invoice = await service.create_invoice(
            company_id=db_company.id,
            engagement_id=None,
            lines=[{
                "description": description,
                "quantity": Decimal("1.00"),
                "unit_price_bdt": Decimal("100.00"),
            }],
            tax_bdt=Decimal("0.00"),
            due_at=None,
            notes=None,
            actor_id=db_user.id,
        )
        invoices.append(await service.issue_invoice(invoice.id))

    submission_invoice, other_invoice = invoices
    now = datetime.now(UTC)
    amount = Decimal("100.00")
    submission = PaymentSubmission(
        id=uuid.uuid4(),
        company_id=db_company.id,
        invoice_id=submission_invoice.id,
        submitted_by=db_user.id,
        method="BANK_TRANSFER",
        amount_bdt=amount,
        currency="BDT",
        payer_reference=f"TEST-{uuid.uuid4().hex}",
        paid_at=now,
        status="PENDING_REVIEW",
    )
    payment = Payment(
        company_id=db_company.id,
        payment_number=f"PAY-TEST-{uuid.uuid4().hex[:12]}",
        method="BANK_TRANSFER",
        channel="OFFLINE",
        amount_bdt=amount,
        currency="BDT",
        payer_reference=submission.payer_reference,
        source_submission_id=submission.id,
        status="SETTLED",
        received_at=now,
        verified_by=db_user.id,
        verified_at=now,
        created_by=db_user.id,
    )
    # A new claim must enter PENDING_REVIEW. The production approval path
    # then updates that existing row to APPROVED before inserting its linked
    # receipt; the deferred ledger constraint is checked after evidence exists.
    db.add(submission)
    await db.flush()
    submission.status = "APPROVED"
    submission.reviewed_by = db_user.id
    submission.reviewed_at = now
    submission.review_note = "Regression test approval"
    await db.flush()
    db.add(payment)
    await db.flush()

    db.add(PaymentAllocation(
        company_id=db_company.id,
        payment_id=payment.id,
        invoice_id=submission_invoice.id,
        amount_bdt=amount,
        currency="BDT",
        created_by=db_user.id,
    ))
    allocation_event_invoice_id = (
        submission_invoice.id if allocation_event_matches_invoice else other_invoice.id
    )
    db.add_all([
        PaymentLedgerEvent(
            company_id=db_company.id,
            payment_id=payment.id,
            invoice_id=submission_invoice.id,
            submission_id=submission.id,
            event_type="PAYMENT_VERIFIED",
            amount_bdt=amount,
            currency="BDT",
            reference=submission.payer_reference,
            actor_id=db_user.id,
            event_metadata={"method": "BANK_TRANSFER", "channel": "OFFLINE"},
        ),
        PaymentLedgerEvent(
            company_id=db_company.id,
            payment_id=payment.id,
            invoice_id=allocation_event_invoice_id,
            submission_id=submission.id,
            event_type="PAYMENT_ALLOCATED",
            amount_bdt=amount,
            currency="BDT",
            reference=submission_invoice.invoice_number,
            actor_id=db_user.id,
            event_metadata={"allocation": "FULL_SUBMISSION"},
        ),
    ])
    await db.flush()

    # The trigger checks the signed actor, not an unsigned session GUC.
    await set_rls_context(db, str(db_user.id))

    async def approve_and_force_deferred_constraint():
        await db.execute(
            text("SET CONSTRAINTS payment_submissions_ledger_integrity IMMEDIATE")
        )

    if allocation_event_matches_invoice:
        async with db.begin_nested():
            await approve_and_force_deferred_constraint()
        # Provenance cannot be detached after approval, even for non-wallet
        # methods that are outside the cross-table wallet-reference trigger.
        with pytest.raises(DBAPIError):
            async with db.begin_nested():
                await db.execute(
                    text("""
                        UPDATE public.payments
                           SET source_submission_id = NULL
                         WHERE id = :payment_id
                    """),
                    {"payment_id": payment.id},
                )
    else:
        with pytest.raises(DBAPIError):
            async with db.begin_nested():
                await approve_and_force_deferred_constraint()
