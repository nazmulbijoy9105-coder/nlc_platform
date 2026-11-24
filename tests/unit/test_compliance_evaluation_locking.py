"""Evaluations lock before reading and refresh previously loaded company graphs."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.dialects import postgresql

from app.services.company_service import CompanyService
from app.services.compliance_service import ComplianceService


@pytest.mark.asyncio
async def test_evaluation_locks_before_building_fresh_profile(monkeypatch):
    events = []
    company_id = uuid.uuid4()

    class FakeCompanyService:
        def __init__(self, db):
            pass

        async def build_company_profile(self, company_id, *, refresh=False):
            events.append(("build_company_profile", refresh))
            return None

    async def execute(statement):
        sql = str(statement.compile(dialect=postgresql.dialect()))
        events.append("company lock")
        assert "companies" in sql and "FOR UPDATE" in sql
        return MagicMock()

    monkeypatch.setattr(
        "app.services.company_service.CompanyService", FakeCompanyService,
    )
    db = MagicMock()
    db.execute = AsyncMock(side_effect=execute)

    with pytest.raises(ValueError, match="not found or inactive"):
        await ComplianceService(db).evaluate_company(company_id)

    assert events == ["company lock", ("build_company_profile", True)]


@pytest.mark.asyncio
@pytest.mark.parametrize("refresh", [True, False])
async def test_get_with_relations_refresh_option(refresh):
    db = MagicMock()
    db.execute = AsyncMock(return_value=MagicMock())
    service = CompanyService(db)
    company_id = uuid.uuid4()

    if refresh:
        await service.get_with_relations(company_id, refresh=True)
    else:
        await service.get_with_relations(company_id)

    statement = db.execute.await_args.args[0]
    option = statement.get_execution_options().get("populate_existing")
    assert option is (True if refresh else None)


@pytest.mark.asyncio
@pytest.mark.parametrize("refresh", [True, False])
async def test_build_profile_forwards_refresh(monkeypatch, refresh):
    service = CompanyService(MagicMock())
    get_with_relations = AsyncMock(return_value=None)
    monkeypatch.setattr(service, "get_with_relations", get_with_relations)
    company_id = uuid.uuid4()

    if refresh:
        result = await service.build_company_profile(company_id, refresh=True)
    else:
        result = await service.build_company_profile(company_id)

    assert result is None
    get_with_relations.assert_awaited_once_with(company_id, refresh=refresh)
