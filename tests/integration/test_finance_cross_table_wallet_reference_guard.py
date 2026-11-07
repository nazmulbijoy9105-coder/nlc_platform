"""Database enforcement for cross-table manual wallet reference uniqueness."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.models.database import set_rls_context
from app.services.finance_service import FinanceService


async def _invoice(db, company, actor):
    service = FinanceService(db)
    invoice = await service.create_invoice(
        company_id=company.id,
        engagement_id=None,
        lines=[{
            "description": "Cross-table wallet guard",
            "quantity": Decimal("1.00"),
            "unit_price_bdt": Decimal("100.00"),
        }],
        tax_bdt=Decimal("0.00"),
        due_at=None,
        notes=None,
        actor_id=actor.id,
    )
    return await service.issue_invoice(invoice.id)


async def _insert_payment(db, company_id, actor_id, reference):
    now = datetime.now(UTC)
    await db.execute(
        text("""
            INSERT INTO public.payments
                (id, company_id, payment_number, method, channel, amount_bdt,
                 currency, payer_reference, status, received_at, verified_by,
                 verified_at, created_by)
            VALUES
                (:id, :company_id, :payment_number, 'BKASH_MANUAL', 'OFFLINE',
                 25.00, 'BDT', :reference, 'SETTLED', :received_at, :actor_id,
                 :verified_at, :actor_id)
        """),
        {
            "id": uuid.uuid4(),
            "company_id": company_id,
            "payment_number": f"PAY-XTABLE-{uuid.uuid4().hex[:12]}",
            "reference": reference,
            "received_at": now,
            "verified_at": now,
            "actor_id": actor_id,
        },
    )


@pytest.mark.asyncio
async def test_direct_payment_insert_cannot_reuse_existing_submission_reference(
    db, db_company, db_user
):
    await set_rls_context(db, str(db_user.id))
    invoice = await _invoice(db, db_company, db_user)
    await FinanceService(db).submit_offline_payment(
        company_id=db_company.id,
        invoice_id=invoice.id,
        submitted_by=db_user.id,
        method="BKASH_MANUAL",
        amount_bdt=Decimal("25.00"),
        payer_reference="Txn-Cross-Table-01",
        paid_at=None,
        evidence_document_id=None,
    )

    with pytest.raises(DBAPIError, match="uq_wallet_reference_across_finance_tables"):
        async with db.begin_nested():
            await _insert_payment(db, db_company.id, db_user.id, " txn-cross-table-01 ")


@pytest.mark.asyncio
async def test_direct_submission_insert_cannot_reuse_existing_payment_reference(
    db, db_company, db_user
):
    await set_rls_context(db, str(db_user.id))
    invoice = await _invoice(db, db_company, db_user)
    reference = f"Txn-Cross-Table-{uuid.uuid4().hex}"
    await _insert_payment(db, db_company.id, db_user.id, reference)

    with pytest.raises(DBAPIError, match="uq_wallet_reference_across_finance_tables"):
        async with db.begin_nested():
            await db.execute(
                text("""
                    INSERT INTO public.payment_submissions
                        (id, company_id, invoice_id, submitted_by, method,
                         amount_bdt, currency, payer_reference, status)
                    VALUES
                        (:id, :company_id, :invoice_id, :submitted_by,
                         'BKASH_MANUAL', 25.00, 'BDT', :reference,
                         'PENDING_REVIEW')
                """),
                {
                    "id": uuid.uuid4(),
                    "company_id": db_company.id,
                    "invoice_id": invoice.id,
                    "submitted_by": db_user.id,
                    "reference": reference.upper(),
                },
            )
