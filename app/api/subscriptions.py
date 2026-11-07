"""Company subscriptions and server-managed plan catalogue.

A customer can request a priced plan for a company they can edit and view
financials for. NLC finance staff issue the invoice. Activation is automatic
only after the linked invoice is fully reconciled to settled payment allocations.
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    get_current_user,
    get_db_for_user,
    require_company_access,
    require_roles,
)
from app.models.finance import ClientSubscription, Invoice
from app.models.user import User
from app.services.subscription_service import (
    SubscriptionConflictError,
    SubscriptionNotFoundError,
    SubscriptionService,
)

router = APIRouter()

FINANCE_ROLES = ("SUPER_ADMIN", "ADMIN_STAFF")
CUSTOMER_READ_ROLES = ("CLIENT_DIRECTOR", "CLIENT_VIEW_ONLY", "SUPER_ADMIN", "ADMIN_STAFF")


class SubscriptionPriceInput(BaseModel):
    billing_interval: Literal["MONTHLY", "QUARTERLY", "ANNUAL", "ONE_TIME"]
    amount_bdt: Decimal = Field(gt=0, max_digits=15, decimal_places=2, allow_inf_nan=False)


class SubscriptionFeatureInput(BaseModel):
    feature_code: str = Field(min_length=2, max_length=80)
    limits: dict | None = None


class SubscriptionPlanUpsertRequest(BaseModel):
    plan_name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    grace_days: int = Field(default=0, ge=0, le=30)
    is_active: bool = True
    prices: list[SubscriptionPriceInput] = Field(min_length=1, max_length=4)
    features: list[SubscriptionFeatureInput] = Field(min_length=1, max_length=20)


class SubscriptionRequest(BaseModel):
    plan_code: str = Field(min_length=2, max_length=60)
    billing_interval: Literal["MONTHLY", "QUARTERLY", "ANNUAL", "ONE_TIME"]


class SuspensionRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)


class SubscriptionResponse(BaseModel):
    subscription_id: str
    company_id: str
    plan_code: str
    plan_name: str
    billing_interval: str
    amount_bdt: Decimal
    currency: str
    status: str
    starts_at: str | None
    ends_at: str | None
    renews_at: str | None
    grace_ends_at: str | None
    grace_days: int
    invoice_id: str | None
    cancel_at_period_end: bool
    cancelled_at: str | None
    suspended_at: str | None
    suspension_reason: str | None


class SubscriptionInvoiceResponse(BaseModel):
    subscription_id: str
    invoice_id: str
    invoice_number: str
    total_bdt: Decimal
    balance_bdt: Decimal
    status: str


def _subscription_response(item: ClientSubscription) -> SubscriptionResponse:
    return SubscriptionResponse(
        subscription_id=str(item.id),
        company_id=str(item.company_id),
        plan_code=item.plan_code,
        plan_name=item.plan_name,
        billing_interval=item.billing_interval,
        amount_bdt=item.amount_bdt,
        currency=item.currency,
        status=item.status,
        starts_at=item.starts_at.isoformat() if item.starts_at else None,
        ends_at=item.ends_at.isoformat() if item.ends_at else None,
        renews_at=item.renews_at.isoformat() if item.renews_at else None,
        grace_ends_at=item.grace_ends_at.isoformat() if item.grace_ends_at else None,
        grace_days=item.grace_days,
        invoice_id=str(item.invoice_id) if item.invoice_id else None,
        cancel_at_period_end=item.cancel_at_period_end,
        cancelled_at=item.cancelled_at.isoformat() if item.cancelled_at else None,
        suspended_at=item.suspended_at.isoformat() if item.suspended_at else None,
        suspension_reason=item.suspension_reason,
    )


def _raise_subscription_error(exc: Exception) -> None:
    if isinstance(exc, SubscriptionNotFoundError):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if isinstance(exc, SubscriptionConflictError):
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    raise exc


@router.get("/plans", response_model=list[dict])
async def list_subscription_plans(
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_db_for_user),
    current_user: User = Depends(get_current_user),
):
    staff = current_user.role in ("SUPER_ADMIN", "ADMIN_STAFF")
    return await SubscriptionService(db).list_plans(include_inactive=staff and include_inactive)


@router.put("/plans/{plan_code}", response_model=dict)
async def upsert_subscription_plan(
    plan_code: str,
    body: SubscriptionPlanUpsertRequest,
    db: AsyncSession = Depends(get_db_for_user),
    current_user: User = Depends(get_current_user),
    _role: None = Depends(require_roles(*FINANCE_ROLES)),
):
    try:
        plan = await SubscriptionService(db).upsert_plan(
            plan_code=plan_code,
            plan_name=body.plan_name,
            description=body.description,
            grace_days=body.grace_days,
            is_active=body.is_active,
            prices=[item.model_dump() for item in body.prices],
            features=[item.model_dump() for item in body.features],
            actor_id=current_user.id,
        )
    except (SubscriptionNotFoundError, SubscriptionConflictError) as exc:
        _raise_subscription_error(exc)
    return {
        "plan_code": plan.plan_code,
        "plan_name": plan.plan_name,
        "description": plan.description,
        "grace_days": plan.grace_days,
        "is_active": plan.is_active,
    }


@router.post(
    "/companies/{company_id}",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def request_company_subscription(
    company_id: uuid.UUID,
    body: SubscriptionRequest,
    db: AsyncSession = Depends(get_db_for_user),
    current_user: User = Depends(get_current_user),
    _access: uuid.UUID = Depends(require_company_access()),
    _role: None = Depends(require_roles("CLIENT_DIRECTOR")),
):
    try:
        item = await SubscriptionService(db).request_subscription(
            company_id=company_id,
            plan_code=body.plan_code,
            billing_interval=body.billing_interval,
            actor_id=current_user.id,
        )
    except (SubscriptionNotFoundError, SubscriptionConflictError) as exc:
        _raise_subscription_error(exc)
    return _subscription_response(item)


@router.get(
    "/companies/{company_id}/current",
    response_model=SubscriptionResponse | None,
)
async def get_company_subscription(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_for_user),
    _access: uuid.UUID = Depends(require_company_access()),
    _role: None = Depends(require_roles(*CUSTOMER_READ_ROLES)),
):
    item = await SubscriptionService(db).get_current(company_id)
    return _subscription_response(item) if item else None


@router.get(
    "/companies/{company_id}/history",
    response_model=list[SubscriptionResponse],
)
async def get_company_subscription_history(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_for_user),
    _access: uuid.UUID = Depends(require_company_access()),
    _role: None = Depends(require_roles(*CUSTOMER_READ_ROLES)),
):
    items = await SubscriptionService(db).list_history(company_id)
    return [_subscription_response(item) for item in items]


@router.post(
    "/{subscription_id}/invoice",
    response_model=SubscriptionInvoiceResponse,
)
async def issue_subscription_invoice(
    subscription_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db_for_user),
    current_user: User = Depends(get_current_user),
    _role: None = Depends(require_roles(*FINANCE_ROLES)),
):
    try:
        invoice = await SubscriptionService(db).issue_invoice(
            subscription_id=subscription_id,
            actor_id=current_user.id,
        )
        subscription = await db.get(ClientSubscription, subscription_id)
    except (SubscriptionNotFoundError, SubscriptionConflictError) as exc:
        _raise_subscription_error(exc)
    if subscription is None:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return SubscriptionInvoiceResponse(
        subscription_id=str(subscription.id),
        invoice_id=str(invoice.id),
        invoice_number=invoice.invoice_number,
        total_bdt=invoice.total_bdt,
        balance_bdt=invoice.balance_bdt,
        status=invoice.status,
    )


@router.get(
    "/companies/{company_id}/{subscription_id}/events",
    response_model=list[dict],
)
async def get_company_subscription_events(
    company_id: uuid.UUID,
    subscription_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_for_user),
    _access: uuid.UUID = Depends(require_company_access()),
    _role: None = Depends(require_roles(*CUSTOMER_READ_ROLES)),
):
    events = await SubscriptionService(db).list_events(
        company_id=company_id,
        subscription_id=subscription_id,
    )
    return [
        {
            "event_id": str(item.id),
            "event_type": item.event_type,
            "actor_id": str(item.actor_id) if item.actor_id else None,
            "invoice_id": str(item.invoice_id) if item.invoice_id else None,
            "payment_id": str(item.payment_id) if item.payment_id else None,
            "metadata": item.event_metadata,
            "created_at": item.created_at.isoformat(),
        }
        for item in events
    ]


@router.post(
    "/companies/{company_id}/{subscription_id}/cancel",
    response_model=SubscriptionResponse,
)
async def cancel_company_subscription(
    company_id: uuid.UUID,
    subscription_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_for_user),
    current_user: User = Depends(get_current_user),
    _access: uuid.UUID = Depends(require_company_access()),
    _role: None = Depends(require_roles("CLIENT_DIRECTOR")),
):
    try:
        item = await SubscriptionService(db).request_cancel_at_period_end(
            company_id=company_id,
            subscription_id=subscription_id,
            actor_id=current_user.id,
        )
    except (SubscriptionNotFoundError, SubscriptionConflictError) as exc:
        _raise_subscription_error(exc)
    return _subscription_response(item)


@router.post("/{subscription_id}/suspend", response_model=SubscriptionResponse)
async def suspend_subscription(
    subscription_id: uuid.UUID,
    body: SuspensionRequest,
    db: AsyncSession = Depends(get_db_for_user),
    current_user: User = Depends(get_current_user),
    _role: None = Depends(require_roles(*FINANCE_ROLES)),
):
    try:
        item = await SubscriptionService(db).suspend(
            subscription_id=subscription_id,
            actor_id=current_user.id,
            reason=body.reason,
        )
    except (SubscriptionNotFoundError, SubscriptionConflictError) as exc:
        _raise_subscription_error(exc)
    return _subscription_response(item)


@router.post("/maintenance/process-due", response_model=dict)
async def process_due_subscriptions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
    _role: None = Depends(require_roles(*FINANCE_ROLES)),
):
    """Daily finance/operations maintenance; safe to retry and row-locks each term."""
    return await SubscriptionService(db).process_due_subscriptions(actor_id=current_user.id)


@router.post("/{subscription_id}/resume", response_model=SubscriptionResponse)
async def resume_subscription(
    subscription_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_for_user),
    current_user: User = Depends(get_current_user),
    _role: None = Depends(require_roles(*FINANCE_ROLES)),
):
    try:
        item = await SubscriptionService(db).resume(
            subscription_id=subscription_id,
            actor_id=current_user.id,
        )
    except (SubscriptionNotFoundError, SubscriptionConflictError) as exc:
        _raise_subscription_error(exc)
    return _subscription_response(item)
