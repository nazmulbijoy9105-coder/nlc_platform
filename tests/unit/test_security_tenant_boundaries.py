"""Regression tests for webhook tenant boundaries and current-role authorization."""
import asyncio
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.core.dependencies import TokenData, require_roles
from app.models.webhook import WebhookDelivery, WebhookEndpoint
from app.services.webhook_service import WebhookService


class _Result:
    def __init__(self, value=None):
        self.value = value

    def scalar_one_or_none(self):
        return self.value

    def scalars(self):
        return self

    def all(self):
        return self.value or []


class _DB:
    def __init__(self, *results):
        self.results = list(results)
        self.statements = []
        self.execute = self._execute
        self.flush = AsyncMock()
        self.add = lambda obj: None
        self.delete = AsyncMock()

    async def _execute(self, statement):
        self.statements.append(statement)
        return self.results.pop(0) if self.results else _Result(None)


def _sql(statement):
    return str(statement.compile(compile_kwargs={"literal_binds": True}))


def test_update_endpoint_is_scoped_to_owner():
    endpoint_id, owner_id = uuid.uuid4(), uuid.uuid4()
    db = _DB(_Result(None))
    result = asyncio.run(WebhookService(db).update_endpoint(endpoint_id, owner_id, is_active=False))
    assert result is None
    sql = _sql(db.statements[0])
    assert "webhook_endpoints.user_id" in sql
    assert str(owner_id).replace("-", "") in sql


def test_delete_endpoint_cannot_delete_another_users_endpoint():
    endpoint_id, owner_id = uuid.uuid4(), uuid.uuid4()
    db = _DB(_Result(None))
    deleted = asyncio.run(WebhookService(db).delete_endpoint(endpoint_id, owner_id))
    assert deleted is False
    assert str(owner_id).replace("-", "") in _sql(db.statements[0])
    db.delete.assert_not_awaited()


def test_test_delivery_requires_endpoint_owner():
    endpoint_id, owner_id = uuid.uuid4(), uuid.uuid4()
    db = _DB(_Result(None))
    result = asyncio.run(WebhookService(db).send_test_event(endpoint_id, owner_id))
    assert result == {"error": "Endpoint not found"}
    assert str(owner_id).replace("-", "") in _sql(db.statements[0])


def test_delivery_history_is_scoped_to_endpoint_owner():
    endpoint_id, owner_id = uuid.uuid4(), uuid.uuid4()
    db = _DB(_Result([]))
    rows = asyncio.run(WebhookService(db).get_deliveries(endpoint_id, owner_id))
    assert rows == []
    sql = _sql(db.statements[0])
    assert "JOIN webhook_endpoints" in sql
    assert str(owner_id).replace("-", "") in sql



def test_company_access_query_requires_active_membership():
    company_id, user_id = uuid.uuid4(), uuid.uuid4()
    db = _DB(_Result(SimpleNamespace(role="CLIENT_DIRECTOR")), _Result(None))
    token = TokenData(user_id=str(user_id), email="client@example.test", role="CLIENT_DIRECTOR")
    checker = __import__("app.core.dependencies", fromlist=["require_company_access"]).require_company_access()
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr("app.core.dependencies.set_rls_context", AsyncMock())
    try:
        with pytest.raises(HTTPException) as exc:
            asyncio.run(checker(company_id, token, db))
        assert exc.value.status_code == 403
        membership_sql = _sql(db.statements[1])
        assert "company_user_access.is_active IS true" in membership_sql
    finally:
        monkeypatch.undo()


def test_company_list_filter_uses_live_active_memberships(monkeypatch):
    from app.core.dependencies import get_client_company_filter

    user_id, allowed_id, stale_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    user = SimpleNamespace(role="CLIENT_DIRECTOR", is_active=True)
    db = _DB(_Result(user), _Result([allowed_id]))
    monkeypatch.setattr("app.core.dependencies.set_rls_context", AsyncMock())
    token = TokenData(
        user_id=str(user_id),
        email="client@example.test",
        role="CLIENT_DIRECTOR",
        company_ids=[str(allowed_id), str(stale_id)],
    )
    result = asyncio.run(get_client_company_filter(token, db))
    assert result == [str(allowed_id)]
    membership_sql = _sql(db.statements[1])
    assert "company_user_access.is_active IS true" in membership_sql


def test_event_without_tenant_owner_is_not_broadcast():
    db = _DB()
    count = asyncio.run(WebhookService(db).trigger_event("compliance.evaluated", {}))
    assert count == 0
    assert db.statements == []


def test_privileged_role_is_rechecked_against_database(monkeypatch):
    user_id = uuid.uuid4()
    monkeypatch.setattr("app.core.dependencies.set_rls_context", AsyncMock())
    db = _DB(_Result(SimpleNamespace(role="CLIENT_VIEW_ONLY")))
    token = TokenData(user_id=str(user_id), email="user@example.test", role="SUPER_ADMIN")
    checker = require_roles("SUPER_ADMIN")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(checker(token, db))
    assert exc.value.status_code == 401


def test_privileged_role_accepts_current_database_role(monkeypatch):
    user_id = uuid.uuid4()
    monkeypatch.setattr("app.core.dependencies.set_rls_context", AsyncMock())
    db = _DB(_Result(SimpleNamespace(role="SUPER_ADMIN")))
    token = TokenData(user_id=str(user_id), email="admin@example.test", role="SUPER_ADMIN")
    checker = require_roles("SUPER_ADMIN")
    assert asyncio.run(checker(token, db)) is token
