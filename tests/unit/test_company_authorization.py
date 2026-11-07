import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.core.company_authorization import ensure_staff_company_scope


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["SUPER_ADMIN", "ADMIN_STAFF"])
async def test_platform_admin_has_portfolio_company_scope(role):
    db = MagicMock()
    db.execute = AsyncMock()
    await ensure_staff_company_scope(
        uuid.uuid4(), SimpleNamespace(id=uuid.uuid4(), role=role), db
    )
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_legal_staff_scope_queries_explicit_company_assignment():
    user_id = uuid.uuid4()
    company_id = uuid.uuid4()
    result = MagicMock()
    result.scalar_one_or_none.return_value = company_id
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)

    await ensure_staff_company_scope(
        company_id, SimpleNamespace(id=user_id, role="LEGAL_STAFF"), db
    )

    db.execute.assert_awaited_once()
    statement = db.execute.await_args.args[0]
    sql = str(statement)
    assert "assigned_staff_id" in sql
    assert "company_user_access" in sql
    assert "is_active" in sql


@pytest.mark.asyncio
async def test_unassigned_legal_staff_is_denied():
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)

    with pytest.raises(HTTPException) as exc:
        await ensure_staff_company_scope(
            uuid.uuid4(),
            SimpleNamespace(id=uuid.uuid4(), role="LEGAL_STAFF"),
            db,
        )

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_non_staff_cannot_use_staff_company_scope_guard():
    db = MagicMock()
    db.execute = AsyncMock()

    with pytest.raises(HTTPException) as exc:
        await ensure_staff_company_scope(
            uuid.uuid4(),
            SimpleNamespace(id=uuid.uuid4(), role="CLIENT_DIRECTOR"),
            db,
        )

    assert exc.value.status_code == 403
    db.execute.assert_not_awaited()
