"""Negative database tests for invoice/allocation financial integrity."""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.models.database import set_rls_context
from app.models.finance import Payment, PaymentAllocation, PaymentSubmission
from app.services.finance_service import FinanceConflictError, FinanceService


async def _issued_invoice(db, company, actor):
    service = FinanceService(db)
    invoice = await service.create_invoice(
        company_id=company.id,
        engagement_id=None,
        lines=[{
            "description": "Annual compliance retainer",
            "quantity": "1",
            "unit_price_bdt": "100.00",
        }],
        tax_bdt=Decimal("0.00"),
        due_at=None,
        notes=None,
        actor_id=actor.id,
    )
    return await service.issue_invoice(invoice.id)


@pytest.mark.asyncio
async def test_database_rejects_invoice_paid_balance_without_allocations(db, db_company, db_user):
    await set_rls_context(db, str(db_user.id))
    invoice = await _issued_invoice(db, db_company, db_user)

    with pytest.raises(DBAPIError):
        async with db.begin_nested():
            invoice.paid_bdt = Decimal("10.00")
            invoice.balance_bdt = Decimal("90.00")
            await db.flush()


@pytest.mark.asyncio
async def test_database_rejects_allocations_above_verified_payment_amount(db, db_company, db_user):
    await set_rls_context(db, str(db_user.id))
    invoice = await _issued_invoice(db, db_company, db_user)
    now = datetime.now(UTC)
    payment = Payment(
        company_id=db_company.id,
        payment_number=f"PAY-TEST-{invoice.id.hex[:12]}",
        method="CASH",
        channel="OFFLINE",
        amount_bdt=Decimal("50.00"),
        currency="BDT",
        status="SETTLED",
        received_at=now,
        verified_by=db_user.id,
        verified_at=now,
        created_by=db_user.id,
    )
    db.add(payment)
    await db.flush()

    with pytest.raises(DBAPIError):
        async with db.begin_nested():
            db.add(PaymentAllocation(
                company_id=db_company.id,
                payment_id=payment.id,
                invoice_id=invoice.id,
                amount_bdt=Decimal("60.00"),
                currency="BDT",
                created_by=db_user.id,
            ))
            await db.flush()


@pytest.mark.asyncio
async def test_service_rejects_pending_submissions_that_overbook_invoice(db, db_company, db_user):
    await set_rls_context(db, str(db_user.id))
    invoice = await _issued_invoice(db, db_company, db_user)
    service = FinanceService(db)

    await service.submit_offline_payment(
        company_id=db_company.id,
        invoice_id=invoice.id,
        submitted_by=db_user.id,
        method="CASH",
        amount_bdt=Decimal("60.00"),
        payer_reference=None,
        paid_at=None,
        evidence_document_id=None,
    )
    with pytest.raises(FinanceConflictError, match="already reserve"):
        await service.submit_offline_payment(
            company_id=db_company.id,
            invoice_id=invoice.id,
            submitted_by=db_user.id,
            method="CASH",
            amount_bdt=Decimal("50.00"),
            payer_reference=None,
            paid_at=None,
            evidence_document_id=None,
        )


@pytest.mark.asyncio
async def test_database_rejects_pending_submission_overbooking(db, db_company, db_user):
    await set_rls_context(db, str(db_user.id))
    invoice = await _issued_invoice(db, db_company, db_user)
    service = FinanceService(db)
    await service.submit_offline_payment(
        company_id=db_company.id,
        invoice_id=invoice.id,
        submitted_by=db_user.id,
        method="CASH",
        amount_bdt=Decimal("60.00"),
        payer_reference=None,
        paid_at=None,
        evidence_document_id=None,
    )

    with pytest.raises(DBAPIError):
        async with db.begin_nested():
            db.add(PaymentSubmission(
                company_id=db_company.id,
                invoice_id=invoice.id,
                submitted_by=db_user.id,
                method="CASH",
                amount_bdt=Decimal("50.00"),
                currency="BDT",
                status="PENDING_REVIEW",
            ))
            await db.flush()


@pytest.mark.asyncio
async def test_rejected_manual_wallet_reference_cannot_be_reused(db, db_company, db_user):
    """A rejected claim does not make a real wallet transaction reference reusable."""
    from decimal import Decimal

    from app.services.finance_service import FinanceConflictError, FinanceService

    await set_rls_context(db, str(db_user.id))
    service = FinanceService(db)
    invoice = await _issued_invoice(db, db_company, db_user)
    reference = f"TXN-{invoice.id.hex[:16].upper()}"

    submission = await service.submit_offline_payment(
        company_id=db_company.id,
        invoice_id=invoice.id,
        submitted_by=db_user.id,
        method="BKASH_MANUAL",
        amount_bdt=Decimal("25.00"),
        payer_reference=reference,
        paid_at=None,
        evidence_document_id=None,
    )
    await service.reject_offline_payment(
        submission_id=submission.id,
        reviewer_id=db_user.id,
        reason="Reference evidence did not match the claimed amount",
    )

    with pytest.raises(FinanceConflictError, match="already been submitted"):
        await service.submit_offline_payment(
            company_id=db_company.id,
            invoice_id=invoice.id,
            submitted_by=db_user.id,
            method="BKASH_MANUAL",
            amount_bdt=Decimal("25.00"),
            payer_reference=reference,
            paid_at=None,
            evidence_document_id=None,
        )

@pytest.mark.asyncio
async def test_database_rejects_allocation_without_invoice_balance_reconciliation(
    db, db_company, db_user
):
    """An allocation cannot commit unless invoice paid/balance totals also change."""
    await set_rls_context(db, str(db_user.id))
    invoice = await _issued_invoice(db, db_company, db_user)
    now = datetime.now(UTC)
    payment = Payment(
        company_id=db_company.id,
        payment_number=f"PAY-TEST-{invoice.id.hex[:12]}",
        method="CASH",
        channel="OFFLINE",
        amount_bdt=Decimal("25.00"),
        currency="BDT",
        status="SETTLED",
        received_at=now,
        verified_by=db_user.id,
        verified_at=now,
        created_by=db_user.id,
    )
    db.add(payment)
    await db.flush()

    with pytest.raises(DBAPIError):
        async with db.begin_nested():
            db.add(PaymentAllocation(
                company_id=db_company.id,
                payment_id=payment.id,
                invoice_id=invoice.id,
                amount_bdt=Decimal("25.00"),
                currency="BDT",
                created_by=db_user.id,
            ))
            await db.flush()
            await db.execute(
                text(
                    "SET CONSTRAINTS payment_allocations_invoice_reconciliation IMMEDIATE"
                )
            )

