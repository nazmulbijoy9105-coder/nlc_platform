"""Exercise the real FastAPI company-access dependency against live-style DB results."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.core import dependencies
from app.core.dependencies import TokenData
from app.models.enums import UserRole


class _ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _Session:
    def __init__(self, *results):
        self.results = list(results)
        self.statements = []

    async def execute(self, statement):
        self.statements.append(statement)
        if not self.results:
            raise AssertionError("Unexpected additional database query")
        return self.results.pop(0)


async def _invoke_company_access(
    monkeypatch,
    *,
    db_user,
    token_role,
    membership_id,
    company_id=None,
    token_company_ids=None,
):
    company_id = company_id or uuid.uuid4()
    user_id = uuid.uuid4()
    session = _Session(_ScalarResult(db_user), *(
        [_ScalarResult(membership_id)] if db_user is not None and token_role not in {
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN_STAFF.value,
        } else []
    ))

    async def set_rls_context(_db, _user_id):
        return None

    monkeypatch.setattr(dependencies, "set_rls_context", set_rls_context)
    token = TokenData(
        user_id=str(user_id),
        email="dependency-test@example.test",
        role=str(getattr(token_role, "value", token_role)),
        company_ids=token_company_ids or [],
    )
    dependency = dependencies.require_company_access()
    result = await dependency(company_id=company_id, token=token, db=session)
    return result, company_id, session


@pytest.mark.asyncio
async def test_client_with_active_database_membership_is_authorized(monkeypatch):
    company_id = uuid.uuid4()
    membership_id = uuid.uuid4()
    user = SimpleNamespace(role=UserRole.CLIENT_VIEW_ONLY, is_active=True)

    result, expected_company_id, session = await _invoke_company_access(
        monkeypatch,
        db_user=user,
        token_role=UserRole.CLIENT_VIEW_ONLY,
        membership_id=membership_id,
        company_id=company_id,
    )

    assert result == expected_company_id == company_id
    assert len(session.statements) == 2


@pytest.mark.asyncio
async def test_client_without_active_membership_receives_403(monkeypatch):
    user = SimpleNamespace(role=UserRole.CLIENT_VIEW_ONLY, is_active=True)

    with pytest.raises(HTTPException) as exc:
        await _invoke_company_access(
            monkeypatch,
            db_user=user,
            token_role=UserRole.CLIENT_VIEW_ONLY,
            membership_id=None,
        )

    assert exc.value.status_code == 403
    assert exc.value.detail == "You do not have access to this company."


@pytest.mark.asyncio
async def test_stale_jwt_company_ids_do_not_replace_database_membership(monkeypatch):
    company_id = uuid.uuid4()
    user = SimpleNamespace(role=UserRole.CLIENT_DIRECTOR, is_active=True)

    with pytest.raises(HTTPException) as exc:
        await _invoke_company_access(
            monkeypatch,
            db_user=user,
            token_role=UserRole.CLIENT_DIRECTOR,
            membership_id=None,
            company_id=company_id,
            token_company_ids=[str(company_id)],
        )

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_inactive_database_user_receives_401_before_membership_query(monkeypatch):
    with pytest.raises(HTTPException) as exc:
        await _invoke_company_access(
            monkeypatch,
            db_user=None,
            token_role=UserRole.CLIENT_VIEW_ONLY,
            membership_id=None,
        )

    assert exc.value.status_code == 401
    assert exc.value.detail == "User account is inactive or unavailable."


@pytest.mark.asyncio
async def test_stale_token_role_receives_401_before_membership_query(monkeypatch):
    user = SimpleNamespace(role=UserRole.CLIENT_VIEW_ONLY, is_active=True)

    with pytest.raises(HTTPException) as exc:
        await _invoke_company_access(
            monkeypatch,
            db_user=user,
            token_role=UserRole.SUPER_ADMIN,
            membership_id=None,
        )

    assert exc.value.status_code == 401
    assert exc.value.detail == "Account permissions changed. Please sign in again."


@pytest.mark.asyncio
async def test_platform_admin_has_company_access_without_client_membership(monkeypatch):
    user = SimpleNamespace(role=UserRole.SUPER_ADMIN, is_active=True)

    result, company_id, session = await _invoke_company_access(
        monkeypatch,
        db_user=user,
        token_role=UserRole.SUPER_ADMIN,
        membership_id=None,
    )

    assert result == company_id
    assert len(session.statements) == 1
