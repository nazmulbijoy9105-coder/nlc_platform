"""Transactional billing and offline payment service.

The service is the only supported writer for invoices, allocations and payment
receipts. It locks invoices/submissions, uses Decimal arithmetic and posts the
payment receipt, allocation, invoice balance and immutable events atomically.
"""
from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.commercial import Engagement
from app.models.documents import Document
from app.models.finance import (
    Invoice,
    InvoiceLine,
    Payment,
    PaymentAllocation,
    PaymentLedgerEvent,
    PaymentSubmission,
)

CENT = Decimal("0.01")
OFFLINE_METHODS = {"BANK_TRANSFER", "CASH", "CHEQUE", "BKASH_MANUAL", "NAGAD_MANUAL"}
PAYMENTABLE_INVOICE_STATES = {"ISSUED", "PARTIALLY_PAID", "OVERDUE"}


class FinanceNotFoundError(LookupError):
    """Requested finance record is not visible or does not exist."""


class FinanceConflictError(ValueError):
    """Requested finance action conflicts with the current financial state."""


def _require_aware_datetime(value: datetime | None, field_name: str) -> None:
    if value is not None and (value.tzinfo is None or value.utcoffset() is None):
        raise FinanceConflictError(f"{field_name} must include an explicit timezone offset")


def _integrity_constraint_name(error: IntegrityError) -> str | None:
    original = error.orig
    diagnostic = getattr(original, "diag", None)
    return (
        getattr(diagnostic, "constraint_name", None)
        or getattr(original, "constraint_name", None)
    )


def _money(value: Decimal | int | str) -> Decimal:
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


class FinanceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_invoice(
        self,
        *,
        company_id: uuid.UUID,
        engagement_id: uuid.UUID | None,
        lines: list[dict[str, Any]],
        tax_bdt: Decimal,
        due_at: date | None,
        notes: str | None,
        actor_id: uuid.UUID,
    ) -> Invoice:
        if not lines:
            raise FinanceConflictError("An invoice must contain at least one line item")
        if engagement_id is not None:
            engagement_result = await self.db.execute(
                select(Engagement.id).where(
                    Engagement.id == engagement_id,
                    Engagement.company_id == company_id,
                )
            )
            if engagement_result.scalar_one_or_none() is None:
                raise FinanceNotFoundError("Engagement not found for this company")

        prepared_lines: list[tuple[str, Decimal, Decimal, Decimal, int]] = []
        subtotal = Decimal("0.00")
        for index, line in enumerate(lines):
            description = str(line["description"]).strip()
            if not description:
                raise FinanceConflictError("Invoice line description is required")
            quantity = Decimal(str(line["quantity"]))
            unit_price = _money(line["unit_price_bdt"])
            if quantity <= 0 or unit_price < 0:
                raise FinanceConflictError("Invoice line quantity and price are invalid")
            line_total = _money(quantity * unit_price)
            subtotal += line_total
            prepared_lines.append((description, quantity, unit_price, line_total, index))

        subtotal = _money(subtotal)
        tax = _money(tax_bdt)
        if tax < 0:
            raise FinanceConflictError("Tax amount cannot be negative")
        total = _money(subtotal + tax)
        invoice_number = await self._next_number("INV", "invoices", "invoice_number")
        invoice = Invoice(
            company_id=company_id,
            engagement_id=engagement_id,
            invoice_number=invoice_number,
            currency="BDT",
            subtotal_bdt=subtotal,
            tax_bdt=tax,
            total_bdt=total,
            paid_bdt=Decimal("0.00"),
            balance_bdt=total,
            status="DRAFT",
            due_at=due_at,
            notes=notes,
            created_by=actor_id,
        )
        self.db.add(invoice)
        await self.db.flush()

        for description, quantity, unit_price, line_total, sort_order in prepared_lines:
            self.db.add(
                InvoiceLine(
                    invoice_id=invoice.id,
                    company_id=company_id,
                    description=description,
                    quantity=quantity,
                    unit_price_bdt=unit_price,
                    line_total_bdt=line_total,
                    sort_order=sort_order,
                )
            )
        await self.db.flush()
        return await self.get_invoice(invoice.id)  # type: ignore[return-value]

    async def issue_invoice(self, invoice_id: uuid.UUID) -> Invoice:
        invoice = await self._locked_invoice(invoice_id)
        if invoice is None:
            raise FinanceNotFoundError("Invoice not found")
        if invoice.status != "DRAFT":
            raise FinanceConflictError(f"Only a draft invoice can be issued; current state is {invoice.status}")
        lines_result = await self.db.execute(
            select(InvoiceLine).where(
                InvoiceLine.invoice_id == invoice.id,
                InvoiceLine.company_id == invoice.company_id,
            )
        )
        lines = list(lines_result.scalars().all())
        if not lines:
            raise FinanceConflictError("An invoice without line items cannot be issued")
        subtotal = _money(sum((line.line_total_bdt for line in lines), Decimal("0.00")))
        if subtotal != invoice.subtotal_bdt or invoice.total_bdt != _money(subtotal + invoice.tax_bdt):
            raise FinanceConflictError("Invoice line totals do not reconcile to the invoice total")
        invoice.status = "ISSUED"
        invoice.issued_at = datetime.now(UTC)
        await self.db.flush()
        return await self.get_invoice(invoice.id)  # type: ignore[return-value]

    async def get_invoice(self, invoice_id: uuid.UUID) -> Invoice | None:
        result = await self.db.execute(
            select(Invoice)
            .options(selectinload(Invoice.lines))
            .where(Invoice.id == invoice_id)
        )
        return result.scalar_one_or_none()

    async def list_invoices(self, company_id: uuid.UUID) -> list[Invoice]:
        result = await self.db.execute(
            select(Invoice)
            .options(selectinload(Invoice.lines))
            .where(Invoice.company_id == company_id)
            .order_by(Invoice.created_at.desc())
        )
        return list(result.scalars().all())

    async def submit_offline_payment(
        self,
        *,
        company_id: uuid.UUID,
        invoice_id: uuid.UUID,
        submitted_by: uuid.UUID,
        method: str,
        amount_bdt: Decimal,
        payer_reference: str | None,
        paid_at: datetime | None,
        evidence_document_id: uuid.UUID | None,
    ) -> PaymentSubmission:
        if method not in OFFLINE_METHODS:
            raise FinanceConflictError("Unsupported offline payment method")
        _require_aware_datetime(paid_at, "paid_at")
        if method in {"BANK_TRANSFER", "CHEQUE", "BKASH_MANUAL", "NAGAD_MANUAL"} and not (payer_reference and payer_reference.strip()):
            raise FinanceConflictError("A transaction or instrument reference is required for this payment method")
        if paid_at is not None and paid_at > datetime.now(UTC):
            raise FinanceConflictError("Payment date cannot be in the future")

        # bKash/Nagad transaction IDs identify a single transfer. Serialize
        # submissions on the normalized provider reference, then check both
        # pending/approved claims and already-posted receipts. The unique
        # database indexes remain the final integrity boundary.
        if method in {"BKASH_MANUAL", "NAGAD_MANUAL"}:
            assert payer_reference is not None  # required by the method check above
            normalized_reference = payer_reference.strip().lower()
            reference_lock_key = f"nlc:wallet-reference:{method}:{normalized_reference}"
            await self.db.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
                {"lock_key": reference_lock_key},
            )
            duplicate_submission = await self.db.execute(
                select(PaymentSubmission.id)
                .where(
                    PaymentSubmission.method == method,
                    func.lower(func.btrim(PaymentSubmission.payer_reference)) == normalized_reference,
                )
                .limit(1)
            )
            duplicate_payment = await self.db.execute(
                select(Payment.id)
                .where(
                    Payment.method == method,
                    func.lower(func.btrim(Payment.payer_reference)) == normalized_reference,
                )
                .limit(1)
            )
            if (
                duplicate_submission.scalar_one_or_none() is not None
                or duplicate_payment.scalar_one_or_none() is not None
            ):
                raise FinanceConflictError(
                    "This manual wallet transaction reference has already been submitted or credited"
                )

        invoice = await self._locked_invoice(invoice_id, company_id)
        if invoice is None:
            raise FinanceNotFoundError("Invoice not found for this company")
        if invoice.status not in PAYMENTABLE_INVOICE_STATES:
            raise FinanceConflictError(f"Invoice cannot accept payment in {invoice.status} state")
        amount = _money(amount_bdt)
        if amount <= 0 or amount > invoice.balance_bdt:
            raise FinanceConflictError("Payment amount must be positive and cannot exceed the invoice balance")
        pending_result = await self.db.execute(
            select(func.coalesce(func.sum(PaymentSubmission.amount_bdt), 0)).where(
                PaymentSubmission.company_id == company_id,
                PaymentSubmission.invoice_id == invoice_id,
                PaymentSubmission.status == "PENDING_REVIEW",
            )
        )
        pending_total = _money(pending_result.scalar_one())
        if pending_total + amount > invoice.balance_bdt:
            raise FinanceConflictError(
                "Pending payment submissions already reserve the remaining invoice balance"
            )
        if evidence_document_id is not None:
            evidence = await self.db.execute(
                select(Document.id).where(
                    Document.id == evidence_document_id,
                    Document.company_id == company_id,
                )
            )
            if evidence.scalar_one_or_none() is None:
                raise FinanceNotFoundError("Payment evidence document not found for this company")

        submission = PaymentSubmission(
            company_id=company_id,
            invoice_id=invoice_id,
            submitted_by=submitted_by,
            method=method,
            amount_bdt=amount,
            currency="BDT",
            payer_reference=(payer_reference.strip() if payer_reference else None),
            paid_at=paid_at,
            evidence_document_id=evidence_document_id,
            status="PENDING_REVIEW",
        )
        try:
            async with self.db.begin_nested():
                self.db.add(submission)
                await self.db.flush()
        except IntegrityError as exc:
            if _integrity_constraint_name(exc) == "uq_payment_submission_wallet_reference":
                raise FinanceConflictError(
                    "This manual wallet transaction reference has already been submitted or credited"
                ) from exc
            raise
        return submission

    async def list_payment_submissions(self, company_id: uuid.UUID) -> list[PaymentSubmission]:
        result = await self.db.execute(
            select(PaymentSubmission)
            .where(PaymentSubmission.company_id == company_id)
            .order_by(PaymentSubmission.created_at.desc())
        )
        return list(result.scalars().all())

    async def approve_offline_payment(
        self,
        *,
        submission_id: uuid.UUID,
        reviewer_id: uuid.UUID,
        review_note: str | None,
        cheque_cleared_at: datetime | None,
    ) -> Payment:
        submission_result = await self.db.execute(
            select(PaymentSubmission)
            .where(PaymentSubmission.id == submission_id)
            .with_for_update()
        )
        submission = submission_result.scalar_one_or_none()
        if submission is None:
            raise FinanceNotFoundError("Payment submission not found")

        if submission.status == "APPROVED":
            event_result = await self.db.execute(
                select(PaymentLedgerEvent.payment_id).where(
                    PaymentLedgerEvent.submission_id == submission.id,
                    PaymentLedgerEvent.event_type == "PAYMENT_VERIFIED",
                )
            )
            payment_id = event_result.scalar_one_or_none()
            if payment_id is None:
                raise FinanceConflictError("Approved submission has no matching payment ledger event")
            payment_result = await self.db.execute(select(Payment).where(Payment.id == payment_id))
            payment = payment_result.scalar_one_or_none()
            if payment is None:
                raise FinanceConflictError("Approved submission payment record is missing")
            return payment

        if submission.status != "PENDING_REVIEW":
            raise FinanceConflictError(f"Payment submission is already {submission.status}")
        _require_aware_datetime(submission.paid_at, "paid_at")
        _require_aware_datetime(cheque_cleared_at, "cheque_cleared_at")
        if submission.method == "CHEQUE" and cheque_cleared_at is None:
            raise FinanceConflictError("Cheque must be cleared before approval")
        if submission.method != "CHEQUE" and cheque_cleared_at is not None:
            raise FinanceConflictError("Cheque clearance time is valid only for cheque payments")
        if cheque_cleared_at is not None and cheque_cleared_at > datetime.now(UTC):
            raise FinanceConflictError("Cheque clearance time cannot be in the future")
        if (
            submission.method == "CHEQUE"
            and submission.paid_at is not None
            and cheque_cleared_at is not None
            and cheque_cleared_at < submission.paid_at
        ):
            raise FinanceConflictError("Cheque clearance time cannot precede the payment date")

        if submission.method in {"BKASH_MANUAL", "NAGAD_MANUAL"}:
            assert submission.payer_reference is not None
            normalized_reference = submission.payer_reference.strip().lower()
            reference_lock_key = (
                f"nlc:wallet-reference:{submission.method}:{normalized_reference}"
            )
            await self.db.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:lock_key, 0))"),
                {"lock_key": reference_lock_key},
            )
            existing_payment = await self.db.execute(
                select(Payment.id)
                .where(
                    Payment.method == submission.method,
                    func.lower(func.btrim(Payment.payer_reference)) == normalized_reference,
                )
                .limit(1)
            )
            if existing_payment.scalar_one_or_none() is not None:
                raise FinanceConflictError(
                    "This manual wallet transaction reference has already been credited"
                )

        invoice = await self._locked_invoice(submission.invoice_id, submission.company_id)
        if invoice is None:
            raise FinanceNotFoundError("Payment invoice not found")
        if invoice.status not in PAYMENTABLE_INVOICE_STATES:
            raise FinanceConflictError(f"Invoice cannot accept payment in {invoice.status} state")
        amount = _money(submission.amount_bdt)
        if amount > invoice.balance_bdt:
            raise FinanceConflictError("Invoice balance changed; payment must be reconciled before approval")

        now = datetime.now(UTC)
        # Mark the source claim approved in this transaction before inserting
        # its linked receipt. The deferred ledger-integrity constraint validates
        # the reviewer-bound evidence at commit; the DB guard only exempts this
        # exact approved source claim from cross-table duplicate detection.
        submission.status = "APPROVED"
        submission.reviewed_by = reviewer_id
        submission.reviewed_at = now
        submission.review_note = review_note
        if submission.method == "CHEQUE":
            submission.cheque_cleared_at = cheque_cleared_at
        await self.db.flush()

        payment_number = await self._next_number("PAY", "payments", "payment_number")
        payment = Payment(
            company_id=submission.company_id,
            payment_number=payment_number,
            method=submission.method,
            channel="OFFLINE",
            amount_bdt=amount,
            currency="BDT",
            payer_reference=submission.payer_reference,
            source_submission_id=submission.id,
            status="SETTLED",
            received_at=submission.paid_at or now,
            verified_by=reviewer_id,
            verified_at=now,
            created_by=submission.submitted_by,
        )
        try:
            async with self.db.begin_nested():
                self.db.add(payment)
                await self.db.flush()
        except IntegrityError as exc:
            if _integrity_constraint_name(exc) == "uq_payment_wallet_reference":
                raise FinanceConflictError(
                    "This manual wallet transaction reference has already been credited"
                ) from exc
            raise

        allocation = PaymentAllocation(
            company_id=submission.company_id,
            payment_id=payment.id,
            invoice_id=invoice.id,
            amount_bdt=amount,
            currency="BDT",
            created_by=reviewer_id,
        )
        self.db.add(allocation)
        # Flush the allocation while the invoice still has its pre-payment
        # balance; the database RLS policy verifies allocation <= current balance.
        await self.db.flush()

        invoice.paid_bdt = _money(invoice.paid_bdt + amount)
        invoice.balance_bdt = _money(invoice.total_bdt - invoice.paid_bdt)
        invoice.status = "PAID" if invoice.balance_bdt == 0 else "PARTIALLY_PAID"

        self.db.add_all([
            PaymentLedgerEvent(
                company_id=submission.company_id,
                payment_id=payment.id,
                invoice_id=invoice.id,
                submission_id=submission.id,
                event_type="PAYMENT_VERIFIED",
                amount_bdt=amount,
                currency="BDT",
                reference=submission.payer_reference,
                actor_id=reviewer_id,
                event_metadata={"method": submission.method, "channel": "OFFLINE"},
            ),
            PaymentLedgerEvent(
                company_id=submission.company_id,
                payment_id=payment.id,
                invoice_id=invoice.id,
                submission_id=submission.id,
                event_type="PAYMENT_ALLOCATED",
                amount_bdt=amount,
                currency="BDT",
                reference=invoice.invoice_number,
                actor_id=reviewer_id,
                event_metadata={"allocation": "FULL_SUBMISSION"},
            ),
        ])
        await self.db.flush()
        return payment

    async def reject_offline_payment(
        self,
        *,
        submission_id: uuid.UUID,
        reviewer_id: uuid.UUID,
        reason: str,
    ) -> PaymentSubmission:
        reason = reason.strip()
        if not reason:
            raise FinanceConflictError("A rejection reason is required")
        submission_result = await self.db.execute(
            select(PaymentSubmission)
            .where(PaymentSubmission.id == submission_id)
            .with_for_update()
        )
        submission = submission_result.scalar_one_or_none()
        if submission is None:
            raise FinanceNotFoundError("Payment submission not found")
        if submission.status != "PENDING_REVIEW":
            raise FinanceConflictError(f"Payment submission is already {submission.status}")
        now = datetime.now(UTC)
        submission.status = "REJECTED"
        submission.reviewed_by = reviewer_id
        submission.reviewed_at = now
        submission.review_note = reason
        self.db.add(
            PaymentLedgerEvent(
                company_id=submission.company_id,
                invoice_id=submission.invoice_id,
                submission_id=submission.id,
                event_type="SUBMISSION_REJECTED",
                amount_bdt=_money(submission.amount_bdt),
                currency="BDT",
                reference=submission.payer_reference,
                actor_id=reviewer_id,
                event_metadata={"reason": reason},
            )
        )
        await self.db.flush()
        return submission

    async def list_payments(self, company_id: uuid.UUID) -> list[Payment]:
        result = await self.db.execute(
            select(Payment)
            .where(Payment.company_id == company_id)
            .order_by(Payment.received_at.desc())
        )
        return list(result.scalars().all())

    async def _locked_invoice(
        self, invoice_id: uuid.UUID, company_id: uuid.UUID | None = None
    ) -> Invoice | None:
        query = select(Invoice).where(Invoice.id == invoice_id)
        if company_id is not None:
            query = query.where(Invoice.company_id == company_id)
        result = await self.db.execute(query.with_for_update())
        return result.scalar_one_or_none()

    async def _next_number(self, prefix: str, table: str, column: str) -> str:
        if table not in {"invoices", "payments"} or column not in {"invoice_number", "payment_number"}:
            raise ValueError("Unsupported financial numbering target")
        year = date.today().year
        key_prefix = f"{prefix}-{year}-"
        await self.db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"),
            {"lock_key": key_prefix},
        )
        result = await self.db.execute(
            text(
                f"SELECT COALESCE(MAX(CAST(SPLIT_PART({column}, '-', 3) AS INTEGER)), 0) "
                f"FROM {table} WHERE {column} LIKE :prefix"
            ),
            {"prefix": f"{key_prefix}%"},
        )
        sequence = int(result.scalar_one()) + 1
        return f"{key_prefix}{sequence:06d}"
