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


class _ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one(self):
        return self.value


class _MappingResult:
    def __init__(self, rows):
        self.rows = rows

    def mappings(self):
        return self

    def all(self):
        return self.rows


class _EvidenceKPIDB:
    def __init__(self):
        self.calls = []

    async def execute(self, query, params=None):
        sql = str(query)
        self.calls.append((sql, params))
        if "COUNT(DISTINCT c.id)" in sql:
            return _ScalarResult(1)
        if "GROUP BY cf.evaluation_state" in sql:
            return _MappingResult([
                {"evaluation_state": "UNKNOWN", "item_count": 3, "company_count": 1},
                {"evaluation_state": "VIOLATION", "item_count": 1, "company_count": 1},
            ])
        return _ScalarResult(2)


@pytest.mark.asyncio
async def test_unreleased_kpis_return_evidence_metrics_without_legal_risk_bands(monkeypatch):
    import app.rule_engine.engine as engine_module
    from app.services.compliance_service import ComplianceService

    monkeypatch.setattr(engine_module, "legal_score_is_released", lambda: False)
    db = _EvidenceKPIDB()

    result = await ComplianceService(db).get_dashboard_kpis()

    assert result["dashboard_mode"] == "EVIDENCE_REVIEW"
    assert result["statutory_score_release_status"] == "NOT_RELEASED"
    assert result["statutory_risk_aggregates_available"] is False
    assert result["total_companies"] == 2
    assert result["not_evaluated_count"] == 2
    assert result["companies_with_review_items"] == 1
    assert result["active_review_items"] == 4
    assert result["evaluation_state_counts"] == {"UNKNOWN": 3, "VIOLATION": 1}
    assert result["green_count"] is None
    assert result["yellow_count"] is None
    assert result["red_black_count"] is None
    assert result["upcoming_deadlines"] is None
    assert all("current_risk_band" not in sql for sql, _ in db.calls)


@pytest.mark.asyncio
async def test_unreleased_legal_staff_evidence_kpis_apply_assignment_scope(monkeypatch):
    import app.rule_engine.engine as engine_module
    from app.services.compliance_service import ComplianceService

    monkeypatch.setattr(engine_module, "legal_score_is_released", lambda: False)
    db = _EvidenceKPIDB()
    user_id = uuid.uuid4()

    result = await ComplianceService(db).get_dashboard_kpis(user_id=user_id)

    assert result["total_companies"] == 2
    assert result["active_review_items"] == 4
    assert all("assigned_staff_id = CAST(:uid AS uuid)" in sql for sql, _ in db.calls)
    assert all(params == {"uid": str(user_id)} for _, params in db.calls)
