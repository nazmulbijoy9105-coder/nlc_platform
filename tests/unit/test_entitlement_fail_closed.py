"""Entitlement checks fail closed and always bind access to a tenant."""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from starlette.requests import Request

import app.core.entitlement as entitlement


def _request(
    company_id: uuid.UUID | None = None,
    *,
    path: str = "/api/v1/companies",
    method: str = "GET",
    document_id: uuid.UUID | None = None,
) -> Request:
    path_params = {}
    if company_id is not None:
        path_params["company_id"] = str(company_id)
    if document_id is not None:
        path_params["document_id"] = str(document_id)
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": method,
            "scheme": "https",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 443),
            "path_params": path_params,
        }
    )


def _membership_result(company_id):
    result = MagicMock()
    result.scalar_one_or_none.return_value = company_id
    return result


def _company_list_result(company_ids):
    result = MagicMock()
    result.scalars.return_value.all.return_value = list(company_ids)
    return result


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["SUPER_ADMIN", "ADMIN_STAFF"])
async def test_privileged_staff_bypass_customer_subscription_lookup(role):
    dependency = entitlement.require_entitlement("compliance_package")
    db = MagicMock()
    user = SimpleNamespace(id=uuid.uuid4(), role=role)

    assert await dependency(request=_request(), db=db, current_user=user) is True
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_assigned_legal_staff_uses_explicit_company_scope(monkeypatch):
    company_id = uuid.uuid4()
    user = SimpleNamespace(id=uuid.uuid4(), role="LEGAL_STAFF")
    calls = []

    async def ensure_scope(requested_company_id, current_user, db):
        calls.append((requested_company_id, current_user.id))
        assert requested_company_id == company_id

    from app.core import company_authorization

    monkeypatch.setattr(company_authorization, "ensure_staff_company_scope", ensure_scope)
    dependency = entitlement.require_entitlement("compliance_package")

    assert await dependency(
        request=_request(company_id), db=MagicMock(), current_user=user
    ) is True
    assert calls == [(company_id, user.id)]


@pytest.mark.asyncio
async def test_legal_staff_can_read_shared_templates_without_customer_subscription():
    dependency = entitlement.require_entitlement("document_management")
    user = SimpleNamespace(id=uuid.uuid4(), role="LEGAL_STAFF")
    db = MagicMock()

    assert await dependency(
        request=_request(path="/api/v1/documents/templates"),
        db=db,
        current_user=user,
    ) is True
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_legal_staff_without_company_context_is_denied():
    dependency = entitlement.require_entitlement("compliance_package")
    user = SimpleNamespace(id=uuid.uuid4(), role="LEGAL_STAFF")

    with pytest.raises(HTTPException) as exc:
        await dependency(request=_request(), db=MagicMock(), current_user=user)

    assert exc.value.status_code == 403
    assert "assigned company context" in exc.value.detail


@pytest.mark.asyncio
async def test_customer_without_company_membership_is_denied_before_billing_lookup(monkeypatch):
    dependency = entitlement.require_entitlement("compliance_package")
    user = SimpleNamespace(id=uuid.uuid4(), role="CLIENT_DIRECTOR")
    db = MagicMock()
    db.execute = AsyncMock(return_value=_company_list_result([]))

    class MustNotCheckSubscription:
        def __init__(self, db):
            raise AssertionError("Subscription lookup must follow membership authorization")

    monkeypatch.setattr(entitlement, "SubscriptionService", MustNotCheckSubscription)
    with pytest.raises(HTTPException) as exc:
        await dependency(request=_request(), db=db, current_user=user)

    assert exc.value.status_code == 403
    assert "active company membership" in exc.value.detail


@pytest.mark.asyncio
async def test_customer_without_paid_company_entitlement_gets_payment_required(monkeypatch):
    company_id = uuid.uuid4()
    user = SimpleNamespace(id=uuid.uuid4(), role="CLIENT_DIRECTOR")
    db = MagicMock()
    db.execute = AsyncMock(return_value=_membership_result(company_id))

    class NoEntitlement:
        def __init__(self, db):
            pass

        async def has_entitlement(self, *, company_id, feature_code):
            assert company_id == expected_company
            assert feature_code == "compliance_package"
            return False

    expected_company = company_id
    monkeypatch.setattr(entitlement, "SubscriptionService", NoEntitlement)

    with pytest.raises(HTTPException) as exc:
        await entitlement.require_entitlement("compliance_package")(
            request=_request(company_id), db=db, current_user=user
        )

    assert exc.value.status_code == 402
    assert "does not include" in exc.value.detail


@pytest.mark.asyncio
async def test_customer_with_paid_company_entitlement_is_allowed(monkeypatch):
    company_id = uuid.uuid4()
    user = SimpleNamespace(id=uuid.uuid4(), role="CLIENT_VIEW_ONLY")
    db = MagicMock()
    db.execute = AsyncMock(return_value=_membership_result(company_id))

    class PaidEntitlement:
        def __init__(self, db):
            pass

        async def has_entitlement(self, *, company_id, feature_code):
            return company_id == expected_company and feature_code == "document_management"

    expected_company = company_id
    monkeypatch.setattr(entitlement, "SubscriptionService", PaidEntitlement)
    request = _request(company_id)

    assert await entitlement.require_entitlement("document_management")(
        request=request, db=db, current_user=user
    ) is True
    assert request.state.entitled_company_ids == [str(company_id)]


@pytest.mark.asyncio
async def test_invalid_company_context_is_rejected():
    dependency = entitlement.require_entitlement("compliance_package")
    user = SimpleNamespace(id=uuid.uuid4(), role="CLIENT_DIRECTOR")
    request = Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "https",
            "path": "/api/v1/companies/not-a-uuid",
            "raw_path": b"/api/v1/companies/not-a-uuid",
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 443),
            "path_params": {"company_id": "not-a-uuid"},
        }
    )

    with pytest.raises(HTTPException) as exc:
        await dependency(request=request, db=MagicMock(), current_user=user)

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_unknown_account_role_does_not_receive_entitlement():
    dependency = entitlement.require_entitlement("compliance_package")
    user = SimpleNamespace(id=uuid.uuid4(), role="AUDITOR")

    with pytest.raises(HTTPException) as exc:
        await dependency(request=_request(), db=MagicMock(), current_user=user)

    assert exc.value.status_code == 403

