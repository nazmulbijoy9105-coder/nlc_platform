"""Regression tests for normalized cross-table manual manual payment references."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.models.database import set_rls_context


async def _issued_invoice(db, company, actor):
    from app.services.finance_service import FinanceService

    service = FinanceService(db)
    invoice = await service.create_invoice(
        company_id=company.id,
        engagement_id=None,
        lines=[{
            "description": "Wallet reference integrity",
            "quantity": "1",
            "unit_price_bdt": Decimal("100.00"),
        }],
        tax_bdt=Decimal("0.00"),
        due_at=None,
        notes=None,
        actor_id=actor.id,
    )
    return await service.issue_invoice(invoice.id)


@pytest.mark.asyncio
async def test_manual_reference_duplicate_submission_is_case_and_space_insensitive(
    db, db_company, db_user
):
    from app.services.finance_service import FinanceConflictError, FinanceService

    await set_rls_context(db, str(db_user.id))
    service = FinanceService(db)
    invoice = await _issued_invoice(db, db_company, db_user)
    await service.submit_offline_payment(
        company_id=db_company.id,
        invoice_id=invoice.id,
        submitted_by=db_user.id,
        method="BANK_TRANSFER",
        amount_bdt=Decimal("25.00"),
        payer_reference="  Txn-AbC-123  ",
        paid_at=None,
        evidence_document_id=None,
    )

    with pytest.raises(FinanceConflictError, match="already been submitted or credited"):
        await service.submit_offline_payment(
            company_id=db_company.id,
            invoice_id=invoice.id,
            submitted_by=db_user.id,
            method="BANK_TRANSFER",
            amount_bdt=Decimal("25.00"),
            payer_reference="txn-abc-123",
            paid_at=None,
            evidence_document_id=None,
        )


@pytest.mark.asyncio
async def test_manual_payment_submission_rejects_reference_already_present_in_payments(
    db, db_company, db_user
):
    from app.models.finance import Payment
    from app.services.finance_service import FinanceConflictError, FinanceService

    await set_rls_context(db, str(db_user.id))
    invoice = await _issued_invoice(db, db_company, db_user)
    now = datetime.now(UTC)
    reference = f"orphan-{uuid.uuid4().hex}"

    # Simulate a legacy/imported receipt which has no matching submission row.
    # The application must still reject a new claim using the same provider ID.
    db.add(Payment(
        company_id=db_company.id,
        payment_number=f"PAY-TEST-{uuid.uuid4().hex[:12]}",
        method="CHEQUE",
        channel="OFFLINE",
        amount_bdt=Decimal("25.00"),
        currency="BDT",
        payer_reference=reference,
        status="SETTLED",
        received_at=now,
        verified_by=db_user.id,
        verified_at=now,
        created_by=db_user.id,
    ))
    await db.flush()

    service = FinanceService(db)
    with pytest.raises(FinanceConflictError, match="already been submitted or credited"):
        await service.submit_offline_payment(
            company_id=db_company.id,
            invoice_id=invoice.id,
            submitted_by=db_user.id,
            method="CHEQUE",
            amount_bdt=Decimal("25.00"),
            payer_reference=reference.upper(),
            paid_at=None,
            evidence_document_id=None,
        )

@pytest.mark.parametrize("method", ["BKASH_MANUAL", "NAGAD_MANUAL"])
async def test_manual_mobile_wallet_reference_is_unique_across_claims_and_receipts(
    db, db_company, db_user, method
):
    from app.services.finance_service import FinanceConflictError, FinanceService

    await set_rls_context(db, str(db_user.id))
    service = FinanceService(db)
    invoice = await _issued_invoice(db, db_company, db_user)
    reference = f"{method}-TXN-{uuid.uuid4().hex}"

    submission = await service.submit_offline_payment(
        company_id=db_company.id,
        invoice_id=invoice.id,
        submitted_by=db_user.id,
        method=method,
        amount_bdt=Decimal("25.00"),
        payer_reference=reference,
        paid_at=None,
        evidence_document_id=None,
    )
    payment = await service.approve_offline_payment(
        submission_id=submission.id,
        reviewer_id=db_user.id,
        review_note="Manual wallet receipt verified",
        cheque_cleared_at=None,
    )
    assert payment.method == method
    assert payment.payer_reference == reference

    with pytest.raises(FinanceConflictError, match="already been submitted or credited"):
        await service.submit_offline_payment(
            company_id=db_company.id,
            invoice_id=invoice.id,
            submitted_by=db_user.id,
            method=method,
            amount_bdt=Decimal("25.00"),
            payer_reference=reference.lower(),
            paid_at=None,
            evidence_document_id=None,
        )
