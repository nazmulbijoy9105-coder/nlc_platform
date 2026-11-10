"""Focused authorization tests for the company access dependency factory."""
from types import SimpleNamespace
from unittest.mock import AsyncMock
import uuid

import pytest
from fastapi import HTTPException

from app.core.company_access import require_company_access


@pytest.mark.asyncio
async def test_super_admin_bypasses_company_membership_lookup():
    user = SimpleNamespace(id=uuid.uuid4(), role="SUPER_ADMIN")
    db = SimpleNamespace(execute=AsyncMock())
    dependency = await require_company_access()

    result = await dependency(
        SimpleNamespace(path_params={}),
        current_user=user,
        db=db,
    )

    assert result is user
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_company_path_parameter_is_bad_request():
    user = SimpleNamespace(id=uuid.uuid4(), role="ADMIN_STAFF")
    dependency = await require_company_access()

    with pytest.raises(HTTPException) as exc:
        await dependency(
            SimpleNamespace(path_params={}),
            current_user=user,
            db=SimpleNamespace(execute=AsyncMock()),
        )

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_invalid_company_uuid_is_bad_request():
    user = SimpleNamespace(id=uuid.uuid4(), role="ADMIN_STAFF")
    dependency = await require_company_access()

    with pytest.raises(HTTPException) as exc:
        await dependency(
            SimpleNamespace(path_params={"company_id": "not-a-uuid"}),
            current_user=user,
            db=SimpleNamespace(execute=AsyncMock()),
        )

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_missing_active_membership_is_forbidden():
    user = SimpleNamespace(id=uuid.uuid4(), role="ADMIN_STAFF")
    result = SimpleNamespace(scalar_one_or_none=lambda: None)
    db = SimpleNamespace(execute=AsyncMock(return_value=result))
    dependency = await require_company_access()
    company_id = uuid.uuid4()

    with pytest.raises(HTTPException) as exc:
        await dependency(
            SimpleNamespace(path_params={"company_id": str(company_id)}),
            current_user=user,
            db=db,
        )

    assert exc.value.status_code == 403
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_active_membership_returns_authenticated_user():
    user = SimpleNamespace(id=uuid.uuid4(), role="ADMIN_STAFF")
    membership = SimpleNamespace(company_id=uuid.uuid4(), is_active=True)
    result = SimpleNamespace(scalar_one_or_none=lambda: membership)
    db = SimpleNamespace(execute=AsyncMock(return_value=result))
    dependency = await require_company_access()

    returned = await dependency(
        SimpleNamespace(path_params={"company_id": str(membership.company_id)}),
        current_user=user,
        db=db,
    )

    assert returned is user
    db.execute.assert_awaited_once()
