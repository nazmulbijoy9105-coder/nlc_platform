"""Regression tests for tenant-scoped dashboard aggregates."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.company_service import CompanyService


@pytest.mark.asyncio
async def test_dashboard_risk_distribution_fails_closed_without_user():
    db = MagicMock()
    db.execute = AsyncMock()
    result = await CompanyService(db).get_risk_distribution()
    assert result == []
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_dashboard_deadlines_fails_closed_without_user():
    db = MagicMock()
    db.execute = AsyncMock()
    result = await CompanyService(db).get_upcoming_deadlines()
    assert result == []
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_risk_distribution_query_requires_active_membership():
    user_id = uuid.uuid4()
    db = MagicMock()
    db.execute = AsyncMock(return_value=MagicMock(
        mappings=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
    ))
    await CompanyService(db).get_risk_distribution(user_id=user_id)
    statement = str(db.execute.await_args.args[0])
    assert "JOIN company_user_access cua" in statement
    assert "cua.user_id = :user_id" in statement
    assert "cua.is_active = TRUE" in statement


@pytest.mark.asyncio
async def test_deadlines_query_requires_active_membership_and_bounded_window():
    user_id = uuid.uuid4()
    db = MagicMock()
    db.execute = AsyncMock(return_value=MagicMock(
        mappings=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
    ))
    await CompanyService(db).get_upcoming_deadlines(days_ahead=21, user_id=user_id)
    statement = str(db.execute.await_args.args[0])
    params = db.execute.await_args.args[1]
    assert "JOIN company_user_access cua" in statement
    assert "cua.user_id = :user_id" in statement
    assert "cua.is_active = TRUE" in statement
    assert "BETWEEN 0 AND :days" in statement
    assert params == {"user_id": user_id, "days": 21}


@pytest.mark.asyncio
async def test_system_deadline_feed_is_explicit_and_separate():
    db = MagicMock()
    db.execute = AsyncMock(return_value=MagicMock(
        mappings=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
    ))
    await CompanyService(db).get_upcoming_deadlines_for_system(days_ahead=45)
    statement = str(db.execute.await_args.args[0])
    assert "vw_upcoming_deadlines" in statement
    assert "company_user_access" not in statement
    assert db.execute.await_args.args[1] == {"days": 45}
