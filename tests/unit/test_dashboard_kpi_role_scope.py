"""Dashboard KPI role scope must match the authenticated staff role."""

from types import SimpleNamespace
import uuid

import pytest

from app.api import companies as companies_api
from app.models.enums import UserRole


class _KPIService:
    received_user_ids = []

    def __init__(self, db):
        self.db = db

    async def get_dashboard_kpis(self, user_id=None):
        self.received_user_ids.append(user_id)
        return {"total_companies": 0}


@pytest.mark.asyncio
@pytest.mark.parametrize("role", [UserRole.SUPER_ADMIN, UserRole.ADMIN_STAFF])
async def test_administrator_kpis_use_authorized_portfolio_scope(monkeypatch, role):
    user_id = uuid.uuid4()
    _KPIService.received_user_ids = []
    monkeypatch.setattr(companies_api, "ComplianceService", _KPIService)
    monkeypatch.setattr(companies_api, "_require_legal_dashboard_release", lambda: None)

    result = await companies_api.get_dashboard_kpis(
        current_user=SimpleNamespace(id=user_id, role=role),
        db=object(),
    )

    assert result == {"total_companies": 0}
    assert _KPIService.received_user_ids == [None]


@pytest.mark.asyncio
async def test_legal_staff_kpis_remain_scoped_to_their_assignment(monkeypatch):
    user_id = uuid.uuid4()
    _KPIService.received_user_ids = []
    monkeypatch.setattr(companies_api, "ComplianceService", _KPIService)
    monkeypatch.setattr(companies_api, "_require_legal_dashboard_release", lambda: None)

    result = await companies_api.get_dashboard_kpis(
        current_user=SimpleNamespace(id=user_id, role=UserRole.LEGAL_STAFF),
        db=object(),
    )

    assert result == {"total_companies": 0}
    assert _KPIService.received_user_ids == [user_id]
