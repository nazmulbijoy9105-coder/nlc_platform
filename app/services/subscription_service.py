"""Company-scoped subscription lifecycle and server-side feature entitlement service."""
from __future__ import annotations

import calendar
import re
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company, CompanyUserAccess
from app.models.finance import (
    ClientSubscription,
    Invoice,
    Payment,
    PaymentAllocation,
    PaymentSubmission,
)
from app.models.subscription import (
    ClientSubscriptionFeature,
    SubscriptionEvent,
    SubscriptionPlan,
    SubscriptionPlanFeature,
    SubscriptionPlanPrice,
)

SUPPORTED_FEATURES = frozenset({
    "compliance_package",
    "document_management",
    "corporate_rescue",
})
BILLING_INTERVALS = frozenset({"MONTHLY", "QUARTERLY", "ANNUAL", "ONE_TIME"})


class SubscriptionNotFoundError(LookupError):
    """A subscription, plan, price, or invoice is not visible or does not exist."""


class SubscriptionConflictError(ValueError):
    """A subscription lifecycle operation conflicts with verified billing state."""


def _add_months(value: datetime, months: int) -> datetime:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


class SubscriptionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_plans(self, *, include_inactive: bool = False) -> list[dict[str, Any]]:
        query = select(SubscriptionPlan).order_by(SubscriptionPlan.plan_name)
        if not include_inactive:
            query = query.where(SubscriptionPlan.is_active.is_(True))
        plans = list((await self.db.execute(query)).scalars().all())
        output: list[dict[str, Any]] = []
        for plan in plans:
            price_query = select(SubscriptionPlanPrice).where(
                SubscriptionPlanPrice.plan_code == plan.plan_code
            )
            feature_query = select(SubscriptionPlanFeature).where(
                SubscriptionPlanFeature.plan_code == plan.plan_code
            )
            if not include_inactive:
                price_query = price_query.where(SubscriptionPlanPrice.is_active.is_(True))
                feature_query = feature_query.where(SubscriptionPlanFeature.enabled.is_(True))
            prices = await self.db.execute(price_query.order_by(SubscriptionPlanPrice.billing_interval))
            features = await self.db.execute(feature_query.order_by(SubscriptionPlanFeature.feature_code))
            output.append({
                "plan_code": plan.plan_code,
                "plan_name": plan.plan_name,
                "description": plan.description,
                "grace_days": plan.grace_days,
                "is_active": plan.is_active,
                "prices": [
                    {
                        "billing_interval": item.billing_interval,
                        "amount_bdt": item.amount_bdt,
                        "tax_bdt": item.tax_bdt,
                        "tax_policy_reference": item.tax_policy_reference,
                        "currency": item.currency,
                        "is_active": item.is_active,
                    }
                    for item in prices.scalars().all()
                ],
                "features": [
                    {"feature_code": item.feature_code, "enabled": item.enabled}
                    for item in features.scalars().all()
                ],
            })
        return output

    async def upsert_plan(
        self,
        *,
        plan_code: str,
        plan_name: str,
        description: str | None,
        grace_days: int,
        is_active: bool,
        prices: list[dict[str, Any]],
        features: list[dict[str, Any]],
        actor_id: uuid.UUID,
    ) -> SubscriptionPlan:
        code = plan_code.strip().upper()
        if not re.fullmatch(r"[A-Z][A-Z0-9_-]{1,59}", code):
            raise SubscriptionConflictError("Plan code must use 2-60 uppercase letters, digits, '_' or '-'")
        if not plan_name.strip() or len(plan_name.strip()) > 120:
            raise SubscriptionConflictError("Plan name is required and must not exceed 120 characters")
        if not 0 <= grace_days <= 30:
            raise SubscriptionConflictError("Grace days must be between 0 and 30")
        if not prices:
            raise SubscriptionConflictError("At least one active billing price is required")

        intervals: set[str] = set()
        for price in prices:
            interval = str(price["billing_interval"]).upper()
            amount = Decimal(str(price["amount_bdt"]))
            tax = Decimal(str(price["tax_bdt"]))
            tax_reference = str(price["tax_policy_reference"]).strip()
            if interval not in BILLING_INTERVALS or interval in intervals:
                raise SubscriptionConflictError("Billing intervals must be supported and unique")
            if amount <= 0 or amount != amount.quantize(Decimal("0.01")):
                raise SubscriptionConflictError("Subscription price must be a positive BDT amount with two decimals")
            if tax < 0 or tax != tax.quantize(Decimal("0.01")):
                raise SubscriptionConflictError("Subscription tax amount must be nonnegative BDT with two decimals")
            if len(tax_reference) < 3 or len(tax_reference) > 500:
                raise SubscriptionConflictError("A tax policy reference is required for every subscription price")
            intervals.add(interval)

        requested_features: dict[str, dict[str, Any]] = {}
        for feature in features:
            code_value = str(feature["feature_code"]).strip().lower()
            if code_value not in SUPPORTED_FEATURES:
                raise SubscriptionConflictError(f"Unsupported subscription feature: {code_value}")
            if code_value in requested_features:
                raise SubscriptionConflictError(f"Duplicate feature mapping: {code_value}")
            requested_features[code_value] = feature

        plan_result = await self.db.execute(
            select(SubscriptionPlan)
            .where(SubscriptionPlan.plan_code == code)
            .with_for_update()
        )
        plan = plan_result.scalar_one_or_none()
        if plan is None:
            plan = SubscriptionPlan(
                plan_code=code,
                plan_name=plan_name.strip(),
                description=description,
                grace_days=grace_days,
                is_active=is_active,
                created_by=actor_id,
                updated_by=actor_id,
            )
            self.db.add(plan)
        else:
            plan.plan_name = plan_name.strip()
            plan.description = description
            plan.grace_days = grace_days
            plan.is_active = is_active
            plan.updated_by = actor_id

        existing_prices_result = await self.db.execute(
            select(SubscriptionPlanPrice).where(SubscriptionPlanPrice.plan_code == code)
        )
        existing_prices = {item.billing_interval: item for item in existing_prices_result.scalars().all()}
        for interval, item in existing_prices.items():
            item.is_active = interval in intervals
        for price in prices:
            interval = str(price["billing_interval"]).upper()
            amount = Decimal(str(price["amount_bdt"])).quantize(Decimal("0.01"))
            tax = Decimal(str(price["tax_bdt"])).quantize(Decimal("0.01"))
            tax_reference = str(price["tax_policy_reference"]).strip()
            item = existing_prices.get(interval)
            if item is None:
                self.db.add(SubscriptionPlanPrice(
                    plan_code=code, billing_interval=interval,
                    amount_bdt=amount, tax_bdt=tax,
                    tax_policy_reference=tax_reference,
                    currency="BDT", is_active=True,
                ))
            else:
                item.amount_bdt = amount
                item.tax_bdt = tax
                item.tax_policy_reference = tax_reference
                item.currency = "BDT"
                item.is_active = True

        existing_features_result = await self.db.execute(
            select(SubscriptionPlanFeature).where(SubscriptionPlanFeature.plan_code == code)
        )
        existing_features = {item.feature_code: item for item in existing_features_result.scalars().all()}
        for feature_code, item in existing_features.items():
            item.enabled = feature_code in requested_features
        for feature_code, feature in requested_features.items():
            if feature_code not in existing_features:
                self.db.add(SubscriptionPlanFeature(
                    plan_code=code,
                    feature_code=feature_code,
                    enabled=True,
                ))
        await self.db.flush()
        return plan

    async def request_subscription(
        self,
        *,
        company_id: uuid.UUID,
        plan_code: str,
        billing_interval: str,
        actor_id: uuid.UUID,
    ) -> ClientSubscription:
        # Serialize requests per company; concurrent requests cannot create two
        # pending subscriptions for the same tenant.
        company_result = await self.db.execute(
            select(Company.id).where(Company.id == company_id).with_for_update()
        )
        if company_result.scalar_one_or_none() is None:
            raise SubscriptionNotFoundError("Company not found")

        now = datetime.now(UTC)
        existing_result = await self.db.execute(
            select(ClientSubscription)
            .where(
                ClientSubscription.company_id == company_id,
                ClientSubscription.status.in_(("PENDING", "ACTIVE", "PAST_DUE", "SUSPENDED")),
            )
            .with_for_update()
        )
        for existing in existing_result.scalars().all():
            if existing.status == "PENDING":
                raise SubscriptionConflictError("This company already has a pending subscription request")
            if existing.status == "SUSPENDED":
                raise SubscriptionConflictError("This company has a suspended subscription that must be resolved by NLC finance staff")
            if (
                existing.ends_at is None
                or existing.ends_at > now
                or (
                    not existing.cancel_at_period_end
                    and existing.grace_ends_at is not None
                    and existing.grace_ends_at > now
                )
            ):
                raise SubscriptionConflictError("This company already has a current subscription term")

        interval = billing_interval.upper()
        if interval not in BILLING_INTERVALS:
            raise SubscriptionConflictError("Unsupported billing interval")
        plan_result = await self.db.execute(
            select(SubscriptionPlan, SubscriptionPlanPrice)
            .join(SubscriptionPlanPrice, SubscriptionPlanPrice.plan_code == SubscriptionPlan.plan_code)
            .where(
                SubscriptionPlan.plan_code == plan_code.upper(),
                SubscriptionPlan.is_active.is_(True),
                SubscriptionPlanPrice.billing_interval == interval,
                SubscriptionPlanPrice.is_active.is_(True),
            )
        )
        row = plan_result.one_or_none()
        if row is None:
            raise SubscriptionNotFoundError("Active plan price not found")
        plan, price = row

        feature_result = await self.db.execute(
            select(SubscriptionPlanFeature).where(
                SubscriptionPlanFeature.plan_code == plan.plan_code,
                SubscriptionPlanFeature.enabled.is_(True),
            )
        )
        enabled_features = list(feature_result.scalars().all())
        if not enabled_features:
            raise SubscriptionConflictError("The selected plan has no enabled features")
        if price.amount_bdt <= 0:
            raise SubscriptionConflictError("Zero-price plans require a separately approved free-tier activation workflow")

        subscription = ClientSubscription(
            company_id=company_id,
            plan_code=plan.plan_code,
            plan_name=plan.plan_name,
            billing_interval=interval,
            amount_bdt=price.amount_bdt,
            tax_bdt=price.tax_bdt,
            tax_policy_reference=price.tax_policy_reference,
            currency="BDT",
            status="PENDING",
            grace_days=plan.grace_days,
            auto_renew=False,
            created_by=actor_id,
        )
        self.db.add(subscription)
        await self.db.flush()
        for feature in enabled_features:
            self.db.add(ClientSubscriptionFeature(
                subscription_id=subscription.id,
                company_id=company_id,
                feature_code=feature.feature_code,
                enabled=True,
            ))
        self.db.add(SubscriptionEvent(
            subscription_id=subscription.id,
            company_id=company_id,
            event_type="REQUESTED",
            actor_id=actor_id,
            event_metadata={
                "plan_code": plan.plan_code,
                "billing_interval": interval,
                "amount_bdt": str(price.amount_bdt),
                "tax_bdt": str(price.tax_bdt),
                "tax_policy_reference": price.tax_policy_reference,
                "currency": "BDT",
                "feature_snapshot": [item.feature_code for item in enabled_features],
            },
        ))
        await self.db.flush()
        return subscription

    async def issue_invoice(
        self, *, subscription_id: uuid.UUID, actor_id: uuid.UUID
    ) -> Invoice:
        subscription_result = await self.db.execute(
            select(ClientSubscription)
            .where(ClientSubscription.id == subscription_id)
            .with_for_update()
        )
        subscription = subscription_result.scalar_one_or_none()
        if subscription is None:
            raise SubscriptionNotFoundError("Subscription not found")
        if subscription.invoice_id is not None:
            invoice = await self.db.get(Invoice, subscription.invoice_id)
            if invoice is None or invoice.company_id != subscription.company_id:
                raise SubscriptionConflictError("Linked subscription invoice is missing or belongs to another company")
            return invoice
        if subscription.status != "PENDING":
            raise SubscriptionConflictError("Only a pending subscription can be invoiced")

        from app.services.finance_service import FinanceService

        finance = FinanceService(self.db)
        invoice = await finance.create_invoice(
            company_id=subscription.company_id,
            engagement_id=None,
            lines=[{
                "description": f"NLC subscription: {subscription.plan_name} ({subscription.billing_interval})",
                "quantity": Decimal("1.00"),
                "unit_price_bdt": subscription.amount_bdt,
            }],
            tax_bdt=subscription.tax_bdt,
            due_at=datetime.now(UTC).date() + timedelta(days=7),
            notes=f"Subscription ID: {subscription.id}",
            actor_id=actor_id,
        )
        invoice = await finance.issue_invoice(invoice.id)
        subscription.invoice_id = invoice.id
        self.db.add(SubscriptionEvent(
            subscription_id=subscription.id,
            company_id=subscription.company_id,
            event_type="INVOICE_ISSUED",
            actor_id=actor_id,
            invoice_id=invoice.id,
            event_metadata={
                "invoice_number": invoice.invoice_number,
                "subtotal_bdt": str(invoice.subtotal_bdt),
                "tax_bdt": str(invoice.tax_bdt),
                "total_bdt": str(invoice.total_bdt),
                "tax_policy_reference": subscription.tax_policy_reference,
            },
        ))
        await self.db.flush()
        return invoice

    async def activate_for_paid_invoice(
        self,
        *,
        invoice_id: uuid.UUID,
        payment_id: uuid.UUID,
        actor_id: uuid.UUID,
    ) -> ClientSubscription | None:
        result = await self.db.execute(
            select(ClientSubscription)
            .where(ClientSubscription.invoice_id == invoice_id)
            .with_for_update()
        )
        subscription = result.scalar_one_or_none()
        if subscription is None:
            return None
        if subscription.status == "ACTIVE":
            return subscription
        if subscription.status != "PENDING":
            raise SubscriptionConflictError("Only a pending subscription can be activated")

        invoice = await self.db.get(Invoice, invoice_id)
        if invoice is None or invoice.company_id != subscription.company_id:
            raise SubscriptionConflictError("Subscription invoice is missing or belongs to another company")
        # Partial settlement is valid finance workflow, but it never activates
        # paid features. The final verified allocation will call this again.
        if invoice.status != "PAID" or invoice.balance_bdt != 0:
            return None
        if invoice.paid_bdt != invoice.total_bdt:
            raise SubscriptionConflictError("Paid subscription invoice does not reconcile to its total")

        allocation_total_result = await self.db.execute(
            select(func.coalesce(func.sum(PaymentAllocation.amount_bdt), 0))
            .join(Payment, Payment.id == PaymentAllocation.payment_id)
            .where(
                PaymentAllocation.invoice_id == invoice_id,
                PaymentAllocation.company_id == subscription.company_id,
                Payment.company_id == subscription.company_id,
                Payment.status == "SETTLED",
            )
        )
        allocated = Decimal(str(allocation_total_result.scalar_one() or 0)).quantize(Decimal("0.01"))
        if allocated != invoice.total_bdt:
            raise SubscriptionConflictError("Verified settled payment allocations do not reconcile to subscription invoice")
        payment_allocation = await self.db.execute(
            select(PaymentAllocation.id)
            .join(Payment, Payment.id == PaymentAllocation.payment_id)
            .where(
                PaymentAllocation.invoice_id == invoice_id,
                PaymentAllocation.payment_id == payment_id,
                PaymentAllocation.company_id == subscription.company_id,
                Payment.status == "SETTLED",
            )
            .limit(1)
        )
        if payment_allocation.scalar_one_or_none() is None:
            raise SubscriptionConflictError("Activation payment is not a settled allocation to the subscription invoice")

        now = datetime.now(UTC)
        interval_months = {"MONTHLY": 1, "QUARTERLY": 3, "ANNUAL": 12}
        ends_at = _add_months(now, interval_months[subscription.billing_interval]) if subscription.billing_interval in interval_months else None
        grace_ends_at = ends_at + timedelta(days=subscription.grace_days) if ends_at and subscription.grace_days else ends_at
        subscription.status = "ACTIVE"
        subscription.starts_at = now
        subscription.ends_at = ends_at
        subscription.renews_at = ends_at
        subscription.grace_ends_at = grace_ends_at
        subscription.activated_by = actor_id
        self.db.add(SubscriptionEvent(
            subscription_id=subscription.id,
            company_id=subscription.company_id,
            event_type="ACTIVATED",
            actor_id=actor_id,
            invoice_id=invoice.id,
            payment_id=payment_id,
            event_metadata={
                "starts_at": now.isoformat(),
                "ends_at": ends_at.isoformat() if ends_at else None,
                "grace_ends_at": grace_ends_at.isoformat() if grace_ends_at else None,
                "verified_allocation_bdt": str(allocated),
            },
        ))
        await self.db.flush()
        return subscription

    async def has_entitlement(self, *, company_id: uuid.UUID, feature_code: str) -> bool:
        now = datetime.now(UTC)
        result = await self.db.execute(
            select(ClientSubscription, Invoice)
            .join(
                ClientSubscriptionFeature,
                and_(
                    ClientSubscriptionFeature.subscription_id == ClientSubscription.id,
                    ClientSubscriptionFeature.company_id == ClientSubscription.company_id,
                ),
            )
            .join(
                Invoice,
                and_(
                    Invoice.id == ClientSubscription.invoice_id,
                    Invoice.company_id == ClientSubscription.company_id,
                ),
            )
            .where(
                ClientSubscription.company_id == company_id,
                ClientSubscriptionFeature.feature_code == feature_code,
                ClientSubscriptionFeature.enabled.is_(True),
                ClientSubscription.status.in_(("ACTIVE", "PAST_DUE")),
                ClientSubscription.starts_at.is_not(None),
                ClientSubscription.starts_at <= now,
                or_(
                    ClientSubscription.ends_at.is_(None),
                    ClientSubscription.ends_at > now,
                    and_(
                        ClientSubscription.cancel_at_period_end.is_(False),
                        ClientSubscription.grace_ends_at > now,
                    ),
                ),
                or_(
                    ClientSubscription.status == "ACTIVE",
                    and_(
                        ClientSubscription.status == "PAST_DUE",
                        ClientSubscription.grace_ends_at > now,
                    ),
                ),
                Invoice.status == "PAID",
                Invoice.balance_bdt == 0,
                Invoice.paid_bdt == Invoice.total_bdt,
            )
        )
        candidates = result.all()
        for subscription, invoice in candidates:
            allocated_result = await self.db.execute(
                select(func.coalesce(func.sum(PaymentAllocation.amount_bdt), 0))
                .join(Payment, Payment.id == PaymentAllocation.payment_id)
                .where(
                    PaymentAllocation.invoice_id == invoice.id,
                    PaymentAllocation.company_id == company_id,
                    Payment.status == "SETTLED",
                )
            )
            allocated = Decimal(str(allocated_result.scalar_one() or 0)).quantize(Decimal("0.01"))
            if allocated == invoice.total_bdt:
                return True
        return False

    async def entitled_company_ids(
        self, *, user_id: uuid.UUID, feature_code: str
    ) -> list[uuid.UUID]:
        result = await self.db.execute(
            select(CompanyUserAccess.company_id).where(
                CompanyUserAccess.user_id == user_id,
                CompanyUserAccess.is_active.is_(True),
            )
        )
        company_ids = list(result.scalars().all())
        entitled: list[uuid.UUID] = []
        for company_id in company_ids:
            if await self.has_entitlement(company_id=company_id, feature_code=feature_code):
                entitled.append(company_id)
        return entitled

    async def list_admin_subscriptions(
        self,
        *,
        status_filter: str | None = None,
        company_id: uuid.UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ClientSubscription]:
        allowed = {"PENDING", "ACTIVE", "PAST_DUE", "CANCELLED", "EXPIRED", "SUSPENDED"}
        if status_filter is not None:
            status_filter = status_filter.upper()
            if status_filter not in allowed:
                raise SubscriptionConflictError("Unsupported subscription status filter")
        if not 1 <= limit <= 200 or offset < 0:
            raise SubscriptionConflictError("Invalid subscription pagination")
        query = select(ClientSubscription)
        if status_filter is not None:
            query = query.where(ClientSubscription.status == status_filter)
        if company_id is not None:
            query = query.where(ClientSubscription.company_id == company_id)
        result = await self.db.execute(
            query.order_by(ClientSubscription.created_at.desc(), ClientSubscription.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_current(self, company_id: uuid.UUID) -> ClientSubscription | None:
        result = await self.db.execute(
            select(ClientSubscription)
            .where(
                ClientSubscription.company_id == company_id,
                ClientSubscription.status.in_(("PENDING", "ACTIVE", "PAST_DUE", "SUSPENDED")),
            )
            .order_by(ClientSubscription.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_history(self, company_id: uuid.UUID) -> list[ClientSubscription]:
        result = await self.db.execute(
            select(ClientSubscription)
            .where(ClientSubscription.company_id == company_id)
            .order_by(ClientSubscription.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_events(
        self, *, company_id: uuid.UUID, subscription_id: uuid.UUID
    ) -> list[SubscriptionEvent]:
        result = await self.db.execute(
            select(SubscriptionEvent)
            .where(
                SubscriptionEvent.company_id == company_id,
                SubscriptionEvent.subscription_id == subscription_id,
            )
            .order_by(SubscriptionEvent.created_at.asc(), SubscriptionEvent.id.asc())
        )
        return list(result.scalars().all())

    async def request_cancel_at_period_end(
        self, *, company_id: uuid.UUID, subscription_id: uuid.UUID, actor_id: uuid.UUID
    ) -> ClientSubscription:
        result = await self.db.execute(
            select(ClientSubscription)
            .where(
                ClientSubscription.id == subscription_id,
                ClientSubscription.company_id == company_id,
            )
            .with_for_update()
        )
        subscription = result.scalar_one_or_none()
        if subscription is None:
            raise SubscriptionNotFoundError("Subscription not found for this company")
        if subscription.created_by != actor_id:
            raise SubscriptionNotFoundError("Subscription not found for this company")
        if subscription.status == "CANCELLED" and subscription.invoice_id is None:
            return subscription
        if subscription.status == "PENDING":
            if subscription.invoice_id is not None:
                raise SubscriptionConflictError("A subscription invoice has already been issued; contact NLC finance staff to resolve it before cancellation")
            now = datetime.now(UTC)
            subscription.status = "CANCELLED"
            subscription.cancelled_at = now
            self.db.add(SubscriptionEvent(
                subscription_id=subscription.id,
                company_id=company_id,
                event_type="CANCELLED",
                actor_id=actor_id,
                event_metadata={"reason": "customer_cancelled_before_invoice", "cancelled_at": now.isoformat()},
            ))
            await self.db.flush()
            return subscription
        if (
            subscription.status != "ACTIVE"
            or subscription.ends_at is None
            or subscription.ends_at <= datetime.now(UTC)
        ):
            raise SubscriptionConflictError("Only an active recurring subscription before its period end can be cancelled at period end")
        if subscription.cancel_at_period_end:
            return subscription
        subscription.cancel_at_period_end = True
        self.db.add(SubscriptionEvent(
            subscription_id=subscription.id,
            company_id=company_id,
            event_type="CANCEL_AT_PERIOD_END",
            actor_id=actor_id,
            invoice_id=subscription.invoice_id,
            event_metadata={"effective_at": subscription.ends_at.isoformat()},
        ))
        await self.db.flush()
        return subscription

    async def process_due_subscriptions(self, *, actor_id: uuid.UUID | None) -> dict[str, int]:
        """Advance expired terms and cancellation/grace transitions in a daily staff job."""
        now = datetime.now(UTC)
        active_result = await self.db.execute(
            select(ClientSubscription)
            .where(
                ClientSubscription.status == "ACTIVE",
                ClientSubscription.ends_at.is_not(None),
                ClientSubscription.ends_at <= now,
            )
            .order_by(ClientSubscription.company_id, ClientSubscription.id)
            .with_for_update(skip_locked=True)
        )
        counts = {"past_due": 0, "expired": 0, "cancelled": 0}
        for subscription in active_result.scalars().all():
            if subscription.cancel_at_period_end:
                subscription.status = "CANCELLED"
                subscription.cancelled_at = subscription.ends_at or now
                event_type = "CANCELLED"
                counts["cancelled"] += 1
            elif subscription.grace_ends_at is not None and subscription.grace_ends_at > now:
                subscription.status = "PAST_DUE"
                event_type = "PAST_DUE"
                counts["past_due"] += 1
            else:
                subscription.status = "EXPIRED"
                event_type = "EXPIRED"
                counts["expired"] += 1
            self.db.add(SubscriptionEvent(
                subscription_id=subscription.id,
                company_id=subscription.company_id,
                event_type=event_type,
                actor_id=actor_id,
                invoice_id=subscription.invoice_id,
                event_metadata={"processed_at": now.isoformat()},
            ))

        grace_result = await self.db.execute(
            select(ClientSubscription)
            .where(
                ClientSubscription.status == "PAST_DUE",
                ClientSubscription.grace_ends_at.is_not(None),
                ClientSubscription.grace_ends_at <= now,
            )
            .order_by(ClientSubscription.company_id, ClientSubscription.id)
            .with_for_update(skip_locked=True)
        )
        for subscription in grace_result.scalars().all():
            subscription.status = "EXPIRED"
            self.db.add(SubscriptionEvent(
                subscription_id=subscription.id,
                company_id=subscription.company_id,
                event_type="EXPIRED",
                actor_id=actor_id,
                invoice_id=subscription.invoice_id,
                event_metadata={"grace_expired_at": now.isoformat()},
            ))
            counts["expired"] += 1
        suspended_result = await self.db.execute(
            select(ClientSubscription)
            .where(
                ClientSubscription.status == "SUSPENDED",
                ClientSubscription.ends_at.is_not(None),
                ClientSubscription.ends_at <= now,
            )
            .order_by(ClientSubscription.company_id, ClientSubscription.id)
            .with_for_update(skip_locked=True)
        )
        for subscription in suspended_result.scalars().all():
            if subscription.cancel_at_period_end:
                subscription.status = "CANCELLED"
                subscription.cancelled_at = subscription.ends_at or now
                event_type = "CANCELLED"
                counts["cancelled"] += 1
            elif subscription.grace_ends_at is None or subscription.grace_ends_at <= now:
                subscription.status = "EXPIRED"
                event_type = "EXPIRED"
                counts["expired"] += 1
            else:
                continue
            self.db.add(SubscriptionEvent(
                subscription_id=subscription.id,
                company_id=subscription.company_id,
                event_type=event_type,
                actor_id=actor_id,
                invoice_id=subscription.invoice_id,
                event_metadata={"processed_at": now.isoformat(), "while_suspended": True},
            ))
        await self.db.flush()
        return counts

    async def cancel_pending_by_staff(
        self, *, subscription_id: uuid.UUID, actor_id: uuid.UUID, reason: str
    ) -> ClientSubscription:
        reason = reason.strip()
        if not reason:
            raise SubscriptionConflictError("A cancellation reason is required")
        result = await self.db.execute(
            select(ClientSubscription)
            .where(ClientSubscription.id == subscription_id)
            .with_for_update()
        )
        subscription = result.scalar_one_or_none()
        if subscription is None:
            raise SubscriptionNotFoundError("Subscription not found")
        if subscription.status != "PENDING":
            raise SubscriptionConflictError("Only a pending subscription request can be cancelled by finance")
        if subscription.invoice_id is not None:
            invoice = await self.db.execute(
                select(Invoice)
                .where(
                    Invoice.id == subscription.invoice_id,
                    Invoice.company_id == subscription.company_id,
                )
                .with_for_update()
            )
            invoice = invoice.scalar_one_or_none()
            if invoice is None:
                raise SubscriptionConflictError("Linked subscription invoice is missing")
            if invoice.status not in ("ISSUED", "OVERDUE") or invoice.paid_bdt != 0 or invoice.balance_bdt != invoice.total_bdt:
                raise SubscriptionConflictError("Subscription invoice has payment activity or is not voidable")
            pending_claim = await self.db.execute(
                select(PaymentSubmission.id)
                .where(
                    PaymentSubmission.invoice_id == invoice.id,
                    PaymentSubmission.company_id == subscription.company_id,
                    PaymentSubmission.status == "PENDING_REVIEW",
                )
                .limit(1)
            )
            if pending_claim.scalar_one_or_none() is not None:
                raise SubscriptionConflictError("Reject or resolve pending payment submissions before voiding this subscription invoice")
            invoice.status = "VOID"
        now = datetime.now(UTC)
        subscription.status = "CANCELLED"
        subscription.cancelled_at = now
        self.db.add(SubscriptionEvent(
            subscription_id=subscription.id,
            company_id=subscription.company_id,
            event_type="CANCELLED",
            actor_id=actor_id,
            invoice_id=subscription.invoice_id,
            event_metadata={"reason": reason, "cancelled_at": now.isoformat(), "voided_invoice": subscription.invoice_id is not None},
        ))
        await self.db.flush()
        return subscription

    async def suspend(
        self, *, subscription_id: uuid.UUID, actor_id: uuid.UUID, reason: str
    ) -> ClientSubscription:
        reason = reason.strip()
        if not reason:
            raise SubscriptionConflictError("A suspension reason is required")
        result = await self.db.execute(
            select(ClientSubscription).where(ClientSubscription.id == subscription_id).with_for_update()
        )
        subscription = result.scalar_one_or_none()
        if subscription is None:
            raise SubscriptionNotFoundError("Subscription not found")
        if subscription.status not in ("ACTIVE", "PAST_DUE"):
            raise SubscriptionConflictError("Only active or past-due subscriptions can be suspended")
        subscription.status = "SUSPENDED"
        subscription.suspended_at = datetime.now(UTC)
        subscription.suspension_reason = reason
        self.db.add(SubscriptionEvent(
            subscription_id=subscription.id,
            company_id=subscription.company_id,
            event_type="SUSPENDED",
            actor_id=actor_id,
            invoice_id=subscription.invoice_id,
            event_metadata={"reason": reason},
        ))
        await self.db.flush()
        return subscription

    async def resume(
        self, *, subscription_id: uuid.UUID, actor_id: uuid.UUID
    ) -> ClientSubscription:
        result = await self.db.execute(
            select(ClientSubscription).where(ClientSubscription.id == subscription_id).with_for_update()
        )
        subscription = result.scalar_one_or_none()
        if subscription is None:
            raise SubscriptionNotFoundError("Subscription not found")
        now = datetime.now(UTC)
        if subscription.status != "SUSPENDED":
            raise SubscriptionConflictError("Only suspended subscriptions can be resumed")
        if subscription.ends_at is not None and subscription.ends_at <= now and (
            subscription.grace_ends_at is None or subscription.grace_ends_at <= now
        ):
            raise SubscriptionConflictError("Subscription term and grace period have expired; a new paid term is required")
        subscription.status = "ACTIVE"
        subscription.suspended_at = None
        subscription.suspension_reason = None
        self.db.add(SubscriptionEvent(
            subscription_id=subscription.id,
            company_id=subscription.company_id,
            event_type="RESUMED",
            actor_id=actor_id,
            invoice_id=subscription.invoice_id,
        ))
        await self.db.flush()
        return subscription
