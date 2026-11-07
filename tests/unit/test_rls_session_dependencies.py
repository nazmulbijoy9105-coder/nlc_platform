import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.core import dependencies
from app.core.dependencies import TokenData
from app.models.enums import UserRole


class _Result:
    def __init__(self, user):
        self._user = user

    def scalar_one_or_none(self):
        return self._user


class _Session:
    def __init__(self, user):
        self.user = user
        self.committed = False
        self.rolled_back = False
        self.closed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def execute(self, statement):
        return _Result(self.user)

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True

    async def close(self):
        self.closed = True


@pytest.mark.asyncio
async def test_client_session_sets_verified_user_rls_context(monkeypatch):
    user_id = uuid.uuid4()
    session = _Session(SimpleNamespace(role=UserRole.CLIENT_VIEW_ONLY, is_active=True))
    calls = []

    monkeypatch.setattr(dependencies, "AsyncSessionLocal", lambda: session)

    async def set_user_context(db, value):
        calls.append(("user", value))

    async def set_admin_context(db):
        calls.append(("admin", None))

    monkeypatch.setattr(dependencies, "set_rls_context", set_user_context)
    monkeypatch.setattr(dependencies, "set_admin_context", set_admin_context)

    token = TokenData(user_id=str(user_id), email="client@example.test", role="CLIENT_VIEW_ONLY")
    generator = dependencies.get_db_for_user(token)
    yielded = await generator.__anext__()
    assert yielded is session
    with pytest.raises(StopAsyncIteration):
        await generator.__anext__()

    assert calls == [("user", str(user_id))]
    assert session.committed is True
    assert session.closed is True


@pytest.mark.parametrize("role", [UserRole.SUPER_ADMIN, UserRole.ADMIN_STAFF])
@pytest.mark.asyncio
async def test_human_admin_sessions_keep_signed_user_identity(monkeypatch, role):
    user_id = uuid.uuid4()
    session = _Session(SimpleNamespace(role=role, is_active=True))
    calls = []

    monkeypatch.setattr(dependencies, "AsyncSessionLocal", lambda: session)

    async def set_user_context(db, value):
        calls.append(("user", value))

    async def set_admin_context(db):
        calls.append(("admin", None))

    monkeypatch.setattr(dependencies, "set_rls_context", set_user_context)
    monkeypatch.setattr(dependencies, "set_admin_context", set_admin_context)

    token = TokenData(user_id=str(user_id), email="admin@example.test", role=role.value)
    generator = dependencies.get_db_for_user(token)
    yielded = await generator.__anext__()
    assert yielded is session
    with pytest.raises(StopAsyncIteration):
        await generator.__anext__()

    assert calls == [("user", str(user_id))]
    assert session.committed is True
    assert session.closed is True


@pytest.mark.asyncio
async def test_stale_token_role_is_rejected_before_session_is_yielded(monkeypatch):
    user_id = uuid.uuid4()
    session = _Session(SimpleNamespace(role=UserRole.CLIENT_VIEW_ONLY, is_active=True))
    monkeypatch.setattr(dependencies, "AsyncSessionLocal", lambda: session)

    async def set_user_context(db, value):
        return None

    async def set_admin_context(db):
        return None

    monkeypatch.setattr(dependencies, "set_rls_context", set_user_context)
    monkeypatch.setattr(dependencies, "set_admin_context", set_admin_context)

    token = TokenData(user_id=str(user_id), email="old@example.test", role="SUPER_ADMIN")
    generator = dependencies.get_db_for_user(token)
    with pytest.raises(HTTPException) as exc:
        await generator.__anext__()

    assert exc.value.status_code == 401
    assert session.rolled_back is True
    assert session.closed is True

@pytest.mark.asyncio
async def test_legal_staff_keeps_signed_user_identity(monkeypatch):
    user_id = uuid.uuid4()
    session = _Session(SimpleNamespace(role=UserRole.LEGAL_STAFF, is_active=True))
    calls = []

    monkeypatch.setattr(dependencies, "AsyncSessionLocal", lambda: session)

    async def set_user_context(db, value):
        calls.append(("user", value))

    async def set_admin_context(db):
        calls.append(("admin", None))

    monkeypatch.setattr(dependencies, "set_rls_context", set_user_context)
    monkeypatch.setattr(dependencies, "set_admin_context", set_admin_context)

    token = TokenData(user_id=str(user_id), email="legal@example.test", role="LEGAL_STAFF")
    generator = dependencies.get_db_for_user(token)
    yielded = await generator.__anext__()
    assert yielded is session
    with pytest.raises(StopAsyncIteration):
        await generator.__anext__()

    assert calls == [("user", str(user_id))]
    assert session.committed is True
    assert session.closed is True
