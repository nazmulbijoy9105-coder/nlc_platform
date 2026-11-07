import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from starlette.requests import Request

import app.core.entitlement as entitlement


def _request(company_id: uuid.UUID | None = None) -> Request:
    path_params = {"company_id": str(company_id)} if company_id else {}
    return Request({
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "https",
        "path": "/api/v1/companies",
        "raw_path": b"/api/v1/companies",
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 443),
        "path_params": path_params,
    })


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["SUPER_ADMIN", "ADMIN_STAFF"])
async def test_authorized_staff_roles_bypass_customer_subscription_lookup(role):
    dependency = entitlement.require_entitlement("compliance_package")
    db = MagicMock()
    user = SimpleNamespace(id=uuid.uuid4(), role=role)

    assert await dependency(request=_request(), db=db, current_user=user) is True
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_legal_staff_does_not_receive_implicit_subscription_bypass():
    dependency = entitlement.require_entitlement("compliance_package")
    user = SimpleNamespace(id=uuid.uuid4(), role="LEGAL_STAFF")

    with pytest.raises(HTTPException) as exc:
        await dependency(request=_request(), db=MagicMock(), current_user=user)

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_customer_without_company_entitlement_receives_payment_required(monkeypatch):
    company_id = uuid.uuid4()

    class FakeSubscriptionService:
        def __init__(self, db):
            pass

        async def has_entitlement(self, *, company_id, feature_code):
            assert feature_code == "compliance_package"
            return False

    monkeypatch.setattr(entitlement, "SubscriptionService", FakeSubscriptionService)
    dependency = entitlement.require_entitlement("compliance_package")
    user = SimpleNamespace(id=uuid.uuid4(), role="CLIENT_DIRECTOR")

    membership = MagicMock()
    membership.scalar_one_or_none.return_value = company_id
    db = MagicMock()
    db.execute = AsyncMock(return_value=membership)

    with pytest.raises(HTTPException) as exc:
        await dependency(request=_request(company_id), db=db, current_user=user)

    assert exc.value.status_code == 402
    assert "does not include" in exc.value.detail


@pytest.mark.asyncio
async def test_customer_with_verified_company_entitlement_is_allowed(monkeypatch):
    company_id = uuid.uuid4()

    class FakeSubscriptionService:
        def __init__(self, db):
            pass

        async def has_entitlement(self, *, company_id, feature_code):
            return company_id == expected_company and feature_code == "document_management"

    expected_company = company_id
    monkeypatch.setattr(entitlement, "SubscriptionService", FakeSubscriptionService)
    dependency = entitlement.require_entitlement("document_management")
    user = SimpleNamespace(id=uuid.uuid4(), role="CLIENT_DIRECTOR")
    request = _request(company_id)
    membership = MagicMock()
    membership.scalar_one_or_none.return_value = company_id
    db = MagicMock()
    db.execute = AsyncMock(return_value=membership)

    assert await dependency(request=request, db=db, current_user=user) is True
    assert request.state.entitled_company_ids == [str(company_id)]


@pytest.mark.asyncio
async def test_customer_without_live_financial_company_membership_is_denied():
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    dependency = entitlement.require_entitlement("document_management")
    user = SimpleNamespace(id=uuid.uuid4(), role="CLIENT_VIEW_ONLY")

    with pytest.raises(HTTPException) as exc:
        await dependency(request=_request(), db=db, current_user=user)

    assert exc.value.status_code == 403
    assert "active company membership" in exc.value.detail


@pytest.mark.asyncio
async def test_unknown_account_role_does_not_receive_entitlement():
    dependency = entitlement.require_entitlement("compliance_package")
    user = SimpleNamespace(id=uuid.uuid4(), role="AUDITOR")

    with pytest.raises(HTTPException) as exc:
        await dependency(request=_request(), db=MagicMock(), current_user=user)

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_known_company_id_without_financial_membership_is_denied(monkeypatch):
    company_id = uuid.uuid4()

    class MustNotCheckEntitlement:
        def __init__(self, db):
            pass

        async def has_entitlement(self, *, company_id, feature_code):
            raise AssertionError("Entitlement lookup must not run before membership authorization")

    monkeypatch.setattr(entitlement, "SubscriptionService", MustNotCheckEntitlement)
    membership = MagicMock()
    membership.scalar_one_or_none.return_value = None
    db = MagicMock()
    db.execute = AsyncMock(return_value=membership)
    dependency = entitlement.require_entitlement("document_management")
    user = SimpleNamespace(id=uuid.uuid4(), role="CLIENT_DIRECTOR")

    with pytest.raises(HTTPException) as exc:
        await dependency(request=_request(company_id), db=db, current_user=user)

    assert exc.value.status_code == 403
    assert "financial access" in exc.value.detail


@pytest.mark.asyncio
async def test_active_company_member_without_financial_permission_can_use_paid_feature(monkeypatch):
    company_id = uuid.uuid4()

    class PaidSubscription:
        def __init__(self, db):
            pass

        async def has_entitlement(self, *, company_id, feature_code):
            return feature_code == "document_management"

    monkeypatch.setattr(entitlement, "SubscriptionService", PaidSubscription)
    membership = MagicMock()
    membership.scalar_one_or_none.return_value = company_id
    db = MagicMock()
    db.execute = AsyncMock(return_value=membership)
    request = _request(company_id)
    dependency = entitlement.require_entitlement("document_management")
    user = SimpleNamespace(id=uuid.uuid4(), role="CLIENT_VIEW_ONLY")

    assert await dependency(request=request, db=db, current_user=user) is True
    assert request.state.entitled_company_ids == [str(company_id)]


@pytest.mark.asyncio
async def test_multi_company_account_requires_explicit_company_context():
    result = MagicMock()
    result.scalars.return_value.all.return_value = [uuid.uuid4(), uuid.uuid4()]
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    dependency = entitlement.require_entitlement("document_management")
    user = SimpleNamespace(id=uuid.uuid4(), role="CLIENT_DIRECTOR")

    with pytest.raises(HTTPException) as exc:
        await dependency(request=_request(), db=db, current_user=user)

    assert exc.value.status_code == 400
    assert "company context is required" in exc.value.detail.lower()
