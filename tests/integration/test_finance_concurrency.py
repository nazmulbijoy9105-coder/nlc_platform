"""Real PostgreSQL multi-session race tests for finance invariants.

These tests intentionally use committed, uniquely identified fixtures and independent
connections. The CI integration job provisions a disposable nlc_test database; rows
from the approval test include append-only ledger evidence and are not deleted.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.company import Company
from app.models.database import set_rls_context
from app.models.enums import CompanyStatus, RiskBand, UserRole
from app.models.finance import (
    Invoice,
    Payment,
    PaymentAllocation,
    PaymentLedgerEvent,
    PaymentSubmission,
)
from app.models.user import User
from app.services.finance_service import FinanceConflictError, FinanceService


async def _committed_finance_fixture(test_engine, *, with_submission: bool):
    """Create and commit a unique tenant, reviewer, issued invoice and optional claim."""
    sessions = async_sessionmaker(test_engine, expire_on_commit=False)
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()

    async with sessions() as session:
        company = Company(
            id=company_id,
            company_name=f"Concurrent Finance {company_id.hex[:8]} Ltd",
            registration_number=f"CF-{company_id.hex[:12].upper()}",
            incorporation_date=date(2023, 1, 1),
            registered_address="Test address, Dhaka, Bangladesh",
            company_type="PRIVATE_LIMITED",
            member_count=5,
            financial_year_end=date(2025, 12, 31),
            current_compliance_score=85,
            current_risk_band=RiskBand.GREEN,
            company_status=CompanyStatus.ACTIVE,
            is_active=True,
            is_dormant=False,
            is_fdi_registered=False,
        )
        user = User(
            id=user_id,
            email=f"concurrent-{user_id.hex}@nlctest.com",
            full_name="Concurrent Finance Test",
            password_hash="!test-only-no-login",
            role=UserRole.ADMIN_STAFF,
            is_active=True,
            totp_enabled=False,
        )
        session.add_all([company, user])
        await session.flush()
        await set_rls_context(session, str(user_id))

        service = FinanceService(session)
        invoice = await service.create_invoice(
            company_id=company_id,
            engagement_id=None,
            lines=[{
                "description": "Concurrent finance integrity test",
                "quantity": "1",
                "unit_price_bdt": Decimal("100.00"),
            }],
            tax_bdt=Decimal("0.00"),
            due_at=None,
            notes="Automated integration test",
            actor_id=user_id,
        )
        invoice = await service.issue_invoice(invoice.id)
        invoice_id = invoice.id

        submission_id = None
        if with_submission:
            submission = await service.submit_offline_payment(
                company_id=company_id,
                invoice_id=invoice_id,
                submitted_by=user_id,
                method="CASH",
                amount_bdt=Decimal("100.00"),
                payer_reference=None,
                paid_at=None,
                evidence_document_id=None,
            )
            submission_id = submission.id

        await session.commit()

    return sessions, company_id, user_id, invoice_id, submission_id


@pytest.mark.asyncio
async def test_concurrent_pending_submissions_cannot_overbook_invoice(test_engine):
    """Two independent transactions racing for 60 on a 100 invoice: exactly one wins."""
    sessions, company_id, user_id, invoice_id, _ = await _committed_finance_fixture(
        test_engine, with_submission=False
    )
    start = asyncio.Barrier(2)

    async def submit_once():
        async with sessions() as session:
            await set_rls_context(session, str(user_id))
            await start.wait()
            try:
                submission = await FinanceService(session).submit_offline_payment(
                    company_id=company_id,
                    invoice_id=invoice_id,
                    submitted_by=user_id,
                    method="CASH",
                    amount_bdt=Decimal("60.00"),
                    payer_reference=None,
                    paid_at=None,
                    evidence_document_id=None,
                )
                await session.commit()
                return ("accepted", submission.id)
            except FinanceConflictError:
                await session.rollback()
                return ("rejected", None)

    outcomes = await asyncio.gather(submit_once(), submit_once())
    assert sorted(result for result, _ in outcomes) == ["accepted", "rejected"]

    async with sessions() as verify:
        accepted = await verify.execute(
            select(func.count(PaymentSubmission.id)).where(
                PaymentSubmission.invoice_id == invoice_id,
                PaymentSubmission.status == "PENDING_REVIEW",
            )
        )
        reserved = await verify.execute(
            select(func.coalesce(func.sum(PaymentSubmission.amount_bdt), 0)).where(
                PaymentSubmission.invoice_id == invoice_id,
                PaymentSubmission.status == "PENDING_REVIEW",
            )
        )
        assert accepted.scalar_one() == 1
        assert reserved.scalar_one() == Decimal("60.00")


@pytest.mark.asyncio
async def test_concurrent_approval_posts_one_payment_and_one_allocation(test_engine):
    """Two independent reviewers racing to approve one claim must return one receipt."""
    sessions, company_id, user_id, invoice_id, submission_id = (
        await _committed_finance_fixture(test_engine, with_submission=True)
    )
    assert submission_id is not None
    start = asyncio.Barrier(2)

    async def approve_once():
        async with sessions() as session:
            await set_rls_context(session, str(user_id))
            await start.wait()
            payment = await FinanceService(session).approve_offline_payment(
                submission_id=submission_id,
                reviewer_id=user_id,
                review_note="Concurrent approval regression test",
                cheque_cleared_at=None,
            )
            payment_id = payment.id
            await session.commit()
            return payment_id

    payment_ids = await asyncio.gather(approve_once(), approve_once())
    assert payment_ids[0] == payment_ids[1]

    async with sessions() as verify:
        payments = await verify.execute(
            select(func.count(Payment.id)).where(
                Payment.source_submission_id == submission_id
            )
        )
        allocations = await verify.execute(
            select(func.count(PaymentAllocation.id)).where(
                PaymentAllocation.invoice_id == invoice_id
            )
        )
        verified_events = await verify.execute(
            select(func.count(PaymentLedgerEvent.id)).where(
                PaymentLedgerEvent.submission_id == submission_id,
                PaymentLedgerEvent.event_type == "PAYMENT_VERIFIED",
            )
        )
        invoice = await verify.get(Invoice, invoice_id)
        assert payments.scalar_one() == 1
        assert allocations.scalar_one() == 1
        assert verified_events.scalar_one() == 1
        assert invoice is not None
        assert invoice.paid_bdt == Decimal("100.00")
        assert invoice.balance_bdt == Decimal("0.00")
        assert invoice.status == "PAID"
