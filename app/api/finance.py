"""Customer and finance-staff billing API.

Customer routes are tenant-scoped and RLS-backed. Only ADMIN_STAFF and
SUPER_ADMIN may issue invoices or approve/reject payment claims.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    get_current_user,
    get_db_for_user,
    require_company_access,
    require_roles,
)
from app.models.finance import Invoice, Payment, PaymentSubmission
from app.models.user import User
from app.services.finance_service import (
    FinanceConflictError,
    FinanceNotFoundError,
    FinanceService,
)
from app.services.notification_service import ActivityService

logger = structlog.get_logger(__name__)
router = APIRouter()

FINANCE_ROLES = ["ADMIN_STAFF", "SUPER_ADMIN"]
CUSTOMER_BILLING_READ_ROLES = [
    "CLIENT_DIRECTOR", "CLIENT_VIEW_ONLY", "ADMIN_STAFF", "SUPER_ADMIN"
]
CUSTOMER_BILLING_WRITE_ROLES = [
    "CLIENT_DIRECTOR", "ADMIN_STAFF", "SUPER_ADMIN"
]
OFFLINE_METHOD = Literal["BANK_TRANSFER", "CASH", "CHEQUE", "BKASH_MANUAL", "NAGAD_MANUAL"]


def _require_timezone_offset(value: datetime | None, field_name: str) -> datetime | None:
    if value is not None and (value.tzinfo is None or value.utcoffset() is None):
        raise ValueError(f"{field_name} must include an explicit timezone offset")
    return value


class InvoiceLineInput(BaseModel):
    description: str = Field(min_length=1, max_length=500)
    quantity: Decimal = Field(default=Decimal("1.00"), gt=0, max_digits=12, decimal_places=2, allow_inf_nan=False)
    unit_price_bdt: Decimal = Field(ge=0, max_digits=15, decimal_places=2, allow_inf_nan=False)


class InvoiceCreateRequest(BaseModel):
    company_id: uuid.UUID
    engagement_id: uuid.UUID | None = None
    lines: list[InvoiceLineInput] = Field(min_length=1, max_length=100)
    tax_bdt: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=15, decimal_places=2, allow_inf_nan=False)
    due_at: date | None = None
    notes: str | None = Field(default=None, max_length=4000)


class InvoiceLineResponse(BaseModel):
    id: str
    description: str
    quantity: Decimal
    unit_price_bdt: Decimal
    line_total_bdt: Decimal
    sort_order: int


class InvoiceResponse(BaseModel):
    invoice_id: str
    company_id: str
    engagement_id: str | None
    invoice_number: str
    currency: str
    subtotal_bdt: Decimal
    tax_bdt: Decimal
    total_bdt: Decimal
    paid_bdt: Decimal
    balance_bdt: Decimal
    status: str
    issued_at: str | None
    due_at: str | None
    lines: list[InvoiceLineResponse]


class OfflinePaymentSubmissionRequest(BaseModel):
    invoice_id: uuid.UUID
    method: OFFLINE_METHOD
    amount_bdt: Decimal = Field(gt=0, max_digits=15, decimal_places=2, allow_inf_nan=False)
    payer_reference: str | None = Field(default=None, max_length=160)
    paid_at: datetime | None = None
    evidence_document_id: uuid.UUID | None = None

    @field_validator("paid_at")
    @classmethod
    def paid_at_requires_timezone(cls, value: datetime | None) -> datetime | None:
        return _require_timezone_offset(value, "paid_at")


class PaymentSubmissionResponse(BaseModel):
    submission_id: str
    company_id: str
    invoice_id: str
    method: str
    amount_bdt: Decimal
    currency: str
    payer_reference: str | None
    paid_at: str | None
    evidence_document_id: str | None
    status: str
    reviewed_at: str | None
    review_note: str | None
    cheque_cleared_at: str | None


class PaymentApprovalRequest(BaseModel):
    review_note: str | None = Field(default=None, max_length=2000)
    cheque_cleared_at: datetime | None = None

    @field_validator("cheque_cleared_at")
    @classmethod
    def cheque_clearance_requires_timezone(cls, value: datetime | None) -> datetime | None:
        return _require_timezone_offset(value, "cheque_cleared_at")


class PaymentRejectionRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)


class PaymentResponse(BaseModel):
    payment_id: str
    company_id: str
    payment_number: str
    method: str
    channel: str
    amount_bdt: Decimal
    currency: str
    status: str
    received_at: str
    verified_at: str | None


def _invoice_response(invoice: Invoice) -> InvoiceResponse:
    lines = sorted(invoice.lines or [], key=lambda line: line.sort_order)
    return InvoiceResponse(
        invoice_id=str(invoice.id),
        company_id=str(invoice.company_id),
        engagement_id=str(invoice.engagement_id) if invoice.engagement_id else None,
        invoice_number=invoice.invoice_number,
        currency=invoice.currency,
        subtotal_bdt=invoice.subtotal_bdt,
        tax_bdt=invoice.tax_bdt,
        total_bdt=invoice.total_bdt,
        paid_bdt=invoice.paid_bdt,
        balance_bdt=invoice.balance_bdt,
        status=invoice.status,
        issued_at=invoice.issued_at.isoformat() if invoice.issued_at else None,
        due_at=invoice.due_at.isoformat() if invoice.due_at else None,
        lines=[
            InvoiceLineResponse(
                id=str(line.id),
                description=line.description,
                quantity=line.quantity,
                unit_price_bdt=line.unit_price_bdt,
                line_total_bdt=line.line_total_bdt,
                sort_order=line.sort_order,
            )
            for line in lines
        ],
    )


def _submission_response(submission: PaymentSubmission) -> PaymentSubmissionResponse:
    return PaymentSubmissionResponse(
        submission_id=str(submission.id),
        company_id=str(submission.company_id),
        invoice_id=str(submission.invoice_id),
        method=submission.method,
        amount_bdt=submission.amount_bdt,
        currency=submission.currency,
        payer_reference=submission.payer_reference,
        paid_at=submission.paid_at.isoformat() if submission.paid_at else None,
        evidence_document_id=str(submission.evidence_document_id) if submission.evidence_document_id else None,
        status=submission.status,
        reviewed_at=submission.reviewed_at.isoformat() if submission.reviewed_at else None,
        review_note=submission.review_note,
        cheque_cleared_at=submission.cheque_cleared_at.isoformat() if submission.cheque_cleared_at else None,
    )


def _payment_response(payment: Payment) -> PaymentResponse:
    return PaymentResponse(
        payment_id=str(payment.id),
        company_id=str(payment.company_id),
        payment_number=payment.payment_number,
        method=payment.method,
        channel=payment.channel,
        amount_bdt=payment.amount_bdt,
        currency=payment.currency,
        status=payment.status,
        received_at=payment.received_at.isoformat(),
        verified_at=payment.verified_at.isoformat() if payment.verified_at else None,
    )


def _raise_finance_error(exc: Exception) -> None:
    if isinstance(exc, FinanceNotFoundError):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if isinstance(exc, FinanceConflictError):
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    raise exc


@router.post("/invoices", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    body: InvoiceCreateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_for_user),
    current_user: User = Depends(get_current_user),
    _role: None = Depends(require_roles(*FINANCE_ROLES)),
):
    svc = FinanceService(db)
    try:
        invoice = await svc.create_invoice(
            company_id=body.company_id,
            engagement_id=body.engagement_id,
            lines=[line.model_dump() for line in body.lines],
            tax_bdt=body.tax_bdt,
            due_at=body.due_at,
            notes=body.notes,
            actor_id=current_user.id,
        )
    except (FinanceNotFoundError, FinanceConflictError) as exc:
        _raise_finance_error(exc)
    await ActivityService(db).log(
        action="INVOICE_CREATED",
        resource_type="invoice",
        resource_id=str(invoice.id),
        description=f"Draft invoice {invoice.invoice_number} created",
        ip_address=request.client.host if request.client else None,
        actor_user_id=current_user.id,
        company_id=invoice.company_id,
    )
    return _invoice_response(invoice)


@router.post("/invoices/{invoice_id}/issue", response_model=InvoiceResponse)
async def issue_invoice(
    invoice_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db_for_user),
    current_user: User = Depends(get_current_user),
    _role: None = Depends(require_roles(*FINANCE_ROLES)),
):
    try:
        invoice = await FinanceService(db).issue_invoice(invoice_id)
    except (FinanceNotFoundError, FinanceConflictError) as exc:
        _raise_finance_error(exc)
    await ActivityService(db).log(
        action="INVOICE_ISSUED",
        resource_type="invoice",
        resource_id=str(invoice.id),
        description=f"Invoice {invoice.invoice_number} issued",
        ip_address=request.client.host if request.client else None,
        actor_user_id=current_user.id,
        company_id=invoice.company_id,
    )
    return _invoice_response(invoice)


@router.get("/companies/{company_id}/invoices", response_model=list[InvoiceResponse])
async def list_company_invoices(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_for_user),
    _access: None = Depends(require_company_access()),
    _role: None = Depends(require_roles(*CUSTOMER_BILLING_READ_ROLES)),
):
    invoices = await FinanceService(db).list_invoices(company_id)
    return [_invoice_response(invoice) for invoice in invoices]


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_for_user),
    _role: None = Depends(require_roles(*CUSTOMER_BILLING_READ_ROLES)),
):
    invoice = await FinanceService(db).get_invoice(invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return _invoice_response(invoice)


@router.post(
    "/companies/{company_id}/payments/offline",
    response_model=PaymentSubmissionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_offline_payment(
    company_id: uuid.UUID,
    body: OfflinePaymentSubmissionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_for_user),
    current_user: User = Depends(get_current_user),
    _access: None = Depends(require_company_access()),
    _role: None = Depends(require_roles(*CUSTOMER_BILLING_WRITE_ROLES)),
):
    try:
        submission = await FinanceService(db).submit_offline_payment(
            company_id=company_id,
            invoice_id=body.invoice_id,
            submitted_by=current_user.id,
            method=body.method,
            amount_bdt=body.amount_bdt,
            payer_reference=body.payer_reference,
            paid_at=body.paid_at,
            evidence_document_id=body.evidence_document_id,
        )
    except (FinanceNotFoundError, FinanceConflictError) as exc:
        _raise_finance_error(exc)
    await ActivityService(db).log(
        action="OFFLINE_PAYMENT_SUBMITTED",
        resource_type="payment_submission",
        resource_id=str(submission.id),
        description=f"Offline payment submission received for invoice {submission.invoice_id}",
        ip_address=request.client.host if request.client else None,
        actor_user_id=current_user.id,
        company_id=company_id,
    )
    return _submission_response(submission)


@router.get(
    "/companies/{company_id}/payment-submissions",
    response_model=list[PaymentSubmissionResponse],
)
async def list_company_payment_submissions(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_for_user),
    _access: None = Depends(require_company_access()),
    _role: None = Depends(require_roles(*CUSTOMER_BILLING_READ_ROLES)),
):
    submissions = await FinanceService(db).list_payment_submissions(company_id)
    return [_submission_response(item) for item in submissions]


@router.post("/payment-submissions/{submission_id}/approve", response_model=PaymentResponse)
async def approve_offline_payment(
    submission_id: uuid.UUID,
    body: PaymentApprovalRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_for_user),
    current_user: User = Depends(get_current_user),
    _role: None = Depends(require_roles(*FINANCE_ROLES)),
):
    try:
        payment = await FinanceService(db).approve_offline_payment(
            submission_id=submission_id,
            reviewer_id=current_user.id,
            review_note=body.review_note,
            cheque_cleared_at=body.cheque_cleared_at,
        )
    except (FinanceNotFoundError, FinanceConflictError) as exc:
        _raise_finance_error(exc)
    await ActivityService(db).log(
        action="OFFLINE_PAYMENT_APPROVED",
        resource_type="payment",
        resource_id=str(payment.id),
        description=f"Payment {payment.payment_number} verified and allocated",
        ip_address=request.client.host if request.client else None,
        actor_user_id=current_user.id,
        company_id=payment.company_id,
    )
    return _payment_response(payment)


@router.post("/payment-submissions/{submission_id}/reject", response_model=PaymentSubmissionResponse)
async def reject_offline_payment(
    submission_id: uuid.UUID,
    body: PaymentRejectionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_for_user),
    current_user: User = Depends(get_current_user),
    _role: None = Depends(require_roles(*FINANCE_ROLES)),
):
    try:
        submission = await FinanceService(db).reject_offline_payment(
            submission_id=submission_id,
            reviewer_id=current_user.id,
            reason=body.reason,
        )
    except (FinanceNotFoundError, FinanceConflictError) as exc:
        _raise_finance_error(exc)
    await ActivityService(db).log(
        action="OFFLINE_PAYMENT_REJECTED",
        resource_type="payment_submission",
        resource_id=str(submission.id),
        description=f"Payment submission rejected: {body.reason}",
        ip_address=request.client.host if request.client else None,
        actor_user_id=current_user.id,
        company_id=submission.company_id,
    )
    return _submission_response(submission)


@router.get("/companies/{company_id}/payments", response_model=list[PaymentResponse])
async def list_company_payments(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_for_user),
    _access: None = Depends(require_company_access()),
    _role: None = Depends(require_roles(*CUSTOMER_BILLING_READ_ROLES)),
):
    payments = await FinanceService(db).list_payments(company_id)
    return [_payment_response(payment) for payment in payments]
