from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.subscription_service import (
    SubscriptionService,
    _add_months,
)


def _result_with_rows(rows):
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows
    return result


@pytest.mark.parametrize(
    ("source", "months", "expected"),
    [
        (datetime(2026, 1, 31, 10, tzinfo=UTC), 1, datetime(2026, 2, 28, 10, tzinfo=UTC)),
        (datetime(2026, 11, 30, 10, tzinfo=UTC), 3, datetime(2027, 2, 28, 10, tzinfo=UTC)),
        (datetime(2024, 2, 29, 10, tzinfo=UTC), 12, datetime(2025, 2, 28, 10, tzinfo=UTC)),
    ],
)
def test_subscription_calendar_month_arithmetic(source, months, expected):
    assert _add_months(source, months) == expected


@pytest.mark.asyncio
async def test_request_subscription_snapshots_price_and_enabled_features():
    company_id = __import__("uuid").uuid4()
    actor_id = __import__("uuid").uuid4()
    plan = SimpleNamespace(
        plan_code="COMPLIANCE_PRO",
        plan_name="Compliance Pro",
        grace_days=5,
    )
    price = SimpleNamespace(
        amount_bdt=Decimal("12000.00"),
        tax_bdt=Decimal("1800.00"),
        tax_policy_reference="BD VAT policy review reference",
        billing_interval="MONTHLY",
    )
    feature = SimpleNamespace(feature_code="compliance_package")

    company_result = MagicMock()
    company_result.scalar_one_or_none.return_value = company_id
    existing_result = _result_with_rows([])
    plan_result = MagicMock()
    plan_result.one_or_none.return_value = (plan, price)
    feature_result = _result_with_rows([feature])

    db = MagicMock()
    db.execute = AsyncMock(side_effect=[
        company_result,
        existing_result,
        plan_result,
        feature_result,
    ])
    db.flush = AsyncMock()
    db.add = MagicMock()

    subscription = await SubscriptionService(db).request_subscription(
        company_id=company_id,
        plan_code="compliance_pro",
        billing_interval="MONTHLY",
        actor_id=actor_id,
    )

    assert subscription.company_id == company_id
    assert subscription.plan_code == "COMPLIANCE_PRO"
    assert subscription.amount_bdt == Decimal("12000.00")
    assert subscription.tax_bdt == Decimal("1800.00")
    assert subscription.tax_policy_reference == "BD VAT policy review reference"
    assert subscription.status == "PENDING"
    assert subscription.grace_days == 5
    added = [call.args[0] for call in db.add.call_args_list]
    snapshot = next(item for item in added if item.__class__.__name__ == "ClientSubscriptionFeature")
    event = next(item for item in added if item.__class__.__name__ == "SubscriptionEvent")
    assert snapshot.feature_code == "compliance_package"
    assert event.event_type == "REQUESTED"
    assert event.actor_id == actor_id
    db.flush.assert_awaited()


@pytest.mark.asyncio
async def test_partial_subscription_invoice_never_activates():
    from app.models.finance import ClientSubscription

    subscription = SimpleNamespace(
        id=__import__("uuid").uuid4(),
        company_id=__import__("uuid").uuid4(),
        invoice_id=__import__("uuid").uuid4(),
        status="PENDING",
    )
    invoice = SimpleNamespace(
        id=subscription.invoice_id,
        company_id=subscription.company_id,
        status="PARTIALLY_PAID",
        balance_bdt=Decimal("500.00"),
        paid_bdt=Decimal("500.00"),
        total_bdt=Decimal("1000.00"),
    )
    result = MagicMock()
    result.scalar_one_or_none.return_value = subscription
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    db.get = AsyncMock(return_value=invoice)

    activated = await SubscriptionService(db).activate_for_paid_invoice(
        invoice_id=subscription.invoice_id,
        payment_id=__import__("uuid").uuid4(),
        actor_id=__import__("uuid").uuid4(),
    )

    assert activated is None
    assert subscription.status == "PENDING"
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_due_subscription_processing_records_terminal_and_grace_transitions():
    now = datetime.now(UTC)
    cancelled = SimpleNamespace(
        id=__import__("uuid").uuid4(), company_id=__import__("uuid").uuid4(),
        status="ACTIVE", ends_at=now - timedelta(days=1),
        grace_ends_at=now + timedelta(days=3), cancel_at_period_end=True,
        cancelled_at=None, invoice_id=None,
    )
    grace = SimpleNamespace(
        id=__import__("uuid").uuid4(), company_id=__import__("uuid").uuid4(),
        status="ACTIVE", ends_at=now - timedelta(days=1),
        grace_ends_at=now + timedelta(days=3), cancel_at_period_end=False,
        cancelled_at=None, invoice_id=None,
    )
    expired = SimpleNamespace(
        id=__import__("uuid").uuid4(), company_id=__import__("uuid").uuid4(),
        status="ACTIVE", ends_at=now - timedelta(days=4),
        grace_ends_at=now - timedelta(days=1), cancel_at_period_end=False,
        cancelled_at=None, invoice_id=None,
    )
    grace_expired = SimpleNamespace(
        id=__import__("uuid").uuid4(), company_id=__import__("uuid").uuid4(),
        status="PAST_DUE", grace_ends_at=now - timedelta(seconds=1),
        invoice_id=None,
    )
    suspended_expired = SimpleNamespace(
        id=__import__("uuid").uuid4(), company_id=__import__("uuid").uuid4(),
        status="SUSPENDED", ends_at=now - timedelta(days=5),
        grace_ends_at=now - timedelta(days=1), cancel_at_period_end=False,
        cancelled_at=None, invoice_id=None,
    )
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[
        _result_with_rows([cancelled, grace, expired]),
        _result_with_rows([grace_expired]),
        _result_with_rows([suspended_expired]),
    ])
    db.add = MagicMock()
    db.flush = AsyncMock()

    counts = await SubscriptionService(db).process_due_subscriptions(
        actor_id=__import__("uuid").uuid4()
    )

    assert counts == {"past_due": 1, "expired": 3, "cancelled": 1}
    assert cancelled.status == "CANCELLED"
    assert grace.status == "PAST_DUE"
    assert expired.status == "EXPIRED"
    assert grace_expired.status == "EXPIRED"
    assert suspended_expired.status == "EXPIRED"
    event_types = [call.args[0].event_type for call in db.add.call_args_list]
    assert event_types.count("CANCELLED") == 1
    assert event_types.count("PAST_DUE") == 1
    assert event_types.count("EXPIRED") == 3
    db.flush.assert_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("settled_amount", "expected"),
    [
        (Decimal("1000.00"), True),
        (Decimal("999.99"), False),
        (Decimal("0.00"), False),
    ],
)
async def test_entitlement_requires_fully_reconciled_settled_allocations(settled_amount, expected):
    company_id = __import__("uuid").uuid4()
    invoice = SimpleNamespace(
        id=__import__("uuid").uuid4(),
        total_bdt=Decimal("1000.00"),
    )
    subscription = SimpleNamespace(id=__import__("uuid").uuid4())
    candidates = MagicMock()
    candidates.all.return_value = [(subscription, invoice)]
    allocation = MagicMock()
    allocation.scalar_one.return_value = settled_amount
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[candidates, allocation])

    allowed = await SubscriptionService(db).has_entitlement(
        company_id=company_id,
        feature_code="document_management",
    )

    assert allowed is expected


@pytest.mark.asyncio
async def test_plan_upsert_rejects_unimplemented_feature_before_database_write():
    db = MagicMock()
    db.get = AsyncMock()
    db.execute = AsyncMock()
    service = SubscriptionService(db)

    with pytest.raises(ValueError, match="Unsupported subscription feature"):
        await service.upsert_plan(
            plan_code="CUSTOM",
            plan_name="Custom",
            description=None,
            grace_days=0,
            is_active=True,
            prices=[{
                "billing_interval": "MONTHLY",
                "amount_bdt": Decimal("1000.00"),
                "tax_bdt": Decimal("150.00"),
                "tax_policy_reference": "BD tax review reference",
            }],
            features=[{"feature_code": "unimplemented_feature"}],
            actor_id=__import__("uuid").uuid4(),
        )

    db.get.assert_not_awaited()
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_customer_can_cancel_pending_request_before_invoice_issuance():
    company_id = __import__("uuid").uuid4()
    actor_id = __import__("uuid").uuid4()
    subscription = SimpleNamespace(
        id=__import__("uuid").uuid4(),
        company_id=company_id,
        created_by=actor_id,
        status="PENDING",
        invoice_id=None,
        cancelled_at=None,
    )
    result = MagicMock()
    result.scalar_one_or_none.return_value = subscription
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    db.add = MagicMock()
    db.flush = AsyncMock()

    cancelled = await SubscriptionService(db).request_cancel_at_period_end(
        company_id=company_id,
        subscription_id=subscription.id,
        actor_id=actor_id,
    )

    assert cancelled.status == "CANCELLED"
    assert cancelled.cancelled_at is not None
    event = db.add.call_args.args[0]
    assert event.event_type == "CANCELLED"
    assert event.event_metadata["reason"] == "customer_cancelled_before_invoice"
    db.flush.assert_awaited()


@pytest.mark.asyncio
async def test_finance_can_void_unpaid_subscription_invoice_and_cancel_request():
    company_id = __import__("uuid").uuid4()
    actor_id = __import__("uuid").uuid4()
    invoice = SimpleNamespace(
        id=__import__("uuid").uuid4(),
        company_id=company_id,
        status="ISSUED",
        paid_bdt=Decimal("0.00"),
        balance_bdt=Decimal("1000.00"),
        total_bdt=Decimal("1000.00"),
    )
    subscription = SimpleNamespace(
        id=__import__("uuid").uuid4(),
        company_id=company_id,
        status="PENDING",
        invoice_id=invoice.id,
        cancelled_at=None,
    )
    subscription_result = MagicMock()
    subscription_result.scalar_one_or_none.return_value = subscription
    invoice_result = MagicMock()
    invoice_result.scalar_one_or_none.return_value = invoice
    claims_result = MagicMock()
    claims_result.scalar_one_or_none.return_value = None
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[subscription_result, invoice_result, claims_result])
    db.add = MagicMock()
    db.flush = AsyncMock()

    cancelled = await SubscriptionService(db).cancel_pending_by_staff(
        subscription_id=subscription.id,
        actor_id=actor_id,
        reason="Customer request withdrawn",
    )

    assert cancelled.status == "CANCELLED"
    assert invoice.status == "VOID"
    assert cancelled.cancelled_at is not None
    event = db.add.call_args.args[0]
    assert event.event_type == "CANCELLED"
    assert event.invoice_id == invoice.id
    assert event.event_metadata["voided_invoice"] is True
    db.flush.assert_awaited()


@pytest.mark.asyncio
async def test_finance_cannot_void_subscription_invoice_with_pending_payment_claim():
    company_id = __import__("uuid").uuid4()
    invoice = SimpleNamespace(
        id=__import__("uuid").uuid4(),
        company_id=company_id,
        status="ISSUED",
        paid_bdt=Decimal("0.00"),
        balance_bdt=Decimal("1000.00"),
        total_bdt=Decimal("1000.00"),
    )
    subscription = SimpleNamespace(
        id=__import__("uuid").uuid4(),
        company_id=company_id,
        status="PENDING",
        invoice_id=invoice.id,
        cancelled_at=None,
    )
    subscription_result = MagicMock()
    subscription_result.scalar_one_or_none.return_value = subscription
    invoice_result = MagicMock()
    invoice_result.scalar_one_or_none.return_value = invoice
    claims_result = MagicMock()
    claims_result.scalar_one_or_none.return_value = __import__("uuid").uuid4()
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[subscription_result, invoice_result, claims_result])

    with pytest.raises(ValueError, match="pending payment submissions"):
        await SubscriptionService(db).cancel_pending_by_staff(
            subscription_id=subscription.id,
            actor_id=__import__("uuid").uuid4(),
            reason="Customer request withdrawn",
        )

    assert invoice.status == "ISSUED"
    assert subscription.status == "PENDING"
    db.add.assert_not_called()
