import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, call

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


@pytest.mark.asyncio
async def test_company_portfolio_query_uses_assignment_only_for_legal_staff():
    from sqlalchemy.dialects import postgresql

    from app.services.company_service import CompanyService

    user_id = uuid.uuid4()
    count_result = MagicMock()
    count_result.scalar_one.return_value = 1
    rows_result = MagicMock()
    rows_result.scalars.return_value.all.return_value = []
    db = MagicMock()
    db.execute = AsyncMock(side_effect=[count_result, rows_result])

    await CompanyService(db).list_companies(
        user_id=user_id, include_assigned_staff=True
    )

    statements = [call.args[0] for call in db.execute.await_args_list]
    sql = str(statements[0].compile(dialect=postgresql.dialect()))
    assert "assigned_staff_id" in sql
    assert "company_user_access" in sql
