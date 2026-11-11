"""Authorization regressions for the company-access dependency used by API routes."""
from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

import app.core.dependencies as dependencies
from app.core.dependencies import TokenData, require_company_access


def _result(value):
    return SimpleNamespace(scalar_one_or_none=lambda: value)


def _user(user_id, role, *, active=True):
    return SimpleNamespace(id=user_id, role=role, is_active=active)


def _token(user_id, role):
    return TokenData(
        user_id=str(user_id),
        email="test@example.invalid",
        role=role,
        company_ids=[],
    )


@pytest.mark.asyncio
async def test_inactive_user_is_rejected_with_401(monkeypatch):
    user_id = uuid.uuid4()
    db = SimpleNamespace(execute=AsyncMock(return_value=_result(None)))
    set_rls = AsyncMock()
    monkeypatch.setattr(dependencies, "set_rls_context", set_rls)

    with pytest.raises(HTTPException) as exc:
        await require_company_access()(uuid.uuid4(), token=_token(user_id, "CLIENT_VIEW_ONLY"), db=db)

    assert exc.value.status_code == 401
    set_rls.assert_awaited_once_with(db, str(user_id))
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_database_role_mismatch_is_rejected_with_401(monkeypatch):
    user_id = uuid.uuid4()
    db = SimpleNamespace(execute=AsyncMock(return_value=_result(_user(user_id, "ADMIN_STAFF"))))
    monkeypatch.setattr(dependencies, "set_rls_context", AsyncMock())

    with pytest.raises(HTTPException) as exc:
        await require_company_access()(uuid.uuid4(), token=_token(user_id, "CLIENT_VIEW_ONLY"), db=db)

    assert exc.value.status_code == 401
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["SUPER_ADMIN", "ADMIN_STAFF"])
async def test_platform_admin_roles_bypass_company_membership(role, monkeypatch):
    user_id = uuid.uuid4()
    company_id = uuid.uuid4()
    db = SimpleNamespace(execute=AsyncMock(return_value=_result(_user(user_id, role))))
    monkeypatch.setattr(dependencies, "set_rls_context", AsyncMock())

    result = await require_company_access()(company_id, token=_token(user_id, role), db=db)

    assert result == company_id
    # Only the active-user/current-role lookup runs; no tenant membership lookup.
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_legal_staff_uses_company_scope_authorization(monkeypatch):
    user_id = uuid.uuid4()
    company_id = uuid.uuid4()
    user = _user(user_id, "LEGAL_STAFF")
    db = SimpleNamespace(execute=AsyncMock(return_value=_result(user)))
    scope_check = AsyncMock()
    monkeypatch.setattr(dependencies, "set_rls_context", AsyncMock())
    import app.core.company_authorization as company_authorization
    monkeypatch.setattr(company_authorization, "ensure_staff_company_scope", scope_check)

    result = await require_company_access()(company_id, token=_token(user_id, "LEGAL_STAFF"), db=db)

    assert result == company_id
    scope_check.assert_awaited_once_with(company_id, user, db)
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_client_with_active_membership_is_authorized(monkeypatch):
    user_id = uuid.uuid4()
    company_id = uuid.uuid4()
    user = _user(user_id, "CLIENT_DIRECTOR")
    membership_id = uuid.uuid4()
    db = SimpleNamespace(
        execute=AsyncMock(side_effect=[_result(user), _result(membership_id)])
    )
    monkeypatch.setattr(dependencies, "set_rls_context", AsyncMock())

    result = await require_company_access()(company_id, token=_token(user_id, "CLIENT_DIRECTOR"), db=db)

    assert result == company_id
    assert db.execute.await_count == 2
    membership_query = db.execute.await_args_list[1].args[0]
    sql = str(membership_query)
    assert "company_user_access.user_id" in sql
    assert "company_user_access.company_id" in sql
    assert "company_user_access.is_active" in sql
    bound_values = membership_query.compile().params.values()
    assert user_id in bound_values
    assert company_id in bound_values


@pytest.mark.asyncio
async def test_client_without_active_membership_is_forbidden(monkeypatch):
    user_id = uuid.uuid4()
    company_id = uuid.uuid4()
    user = _user(user_id, "CLIENT_VIEW_ONLY")
    db = SimpleNamespace(
        execute=AsyncMock(side_effect=[_result(user), _result(None)])
    )
    monkeypatch.setattr(dependencies, "set_rls_context", AsyncMock())

    with pytest.raises(HTTPException) as exc:
        await require_company_access()(company_id, token=_token(user_id, "CLIENT_VIEW_ONLY"), db=db)

    assert exc.value.status_code == 403
    assert "do not have access" in exc.value.detail
    assert db.execute.await_count == 2
