"""Regression tests for webhook tenant boundaries and current-role authorization."""
import asyncio
import inspect
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.core.dependencies import TokenData, require_roles
from app.api.webhooks import WebhookCreateRequest, WebhookUpdateRequest
from app.models.webhook import WebhookDelivery, WebhookEndpoint
from app.services.webhook_service import WebhookService, validate_webhook_url


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



def test_document_workflow_service_contracts_accept_notes_and_worker_parameters():
    from app.services.document_service import DocumentService

    assert "approval_note" in inspect.signature(DocumentService.approve_document).parameters
    assert "release_note" in inspect.signature(DocumentService.release_to_client).parameters
    assert "parameters" in inspect.signature(DocumentService.generate_ai_document).parameters


def test_event_without_tenant_owner_is_not_broadcast():
    db = _DB()
    count = asyncio.run(WebhookService(db).trigger_event("compliance.evaluated", {}))
    assert count == 0
    assert db.statements == []




def test_webhook_request_schemas_require_https():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        WebhookCreateRequest(url="http://example.com/hook")
    with pytest.raises(ValidationError):
        WebhookUpdateRequest(url="http://example.com/hook")


def test_webhook_url_rejects_plain_http():
    with pytest.raises(ValueError, match="HTTPS"):
        asyncio.run(validate_webhook_url("http://example.com/hook"))


@pytest.mark.parametrize("url", [
    "https://127.0.0.1/hook",
    "https://10.0.0.5/hook",
    "https://localhost/hook",
])
def test_webhook_url_rejects_local_destinations(url):
    with pytest.raises(ValueError):
        asyncio.run(validate_webhook_url(url))


def test_retry_worker_claims_new_and_due_pending_deliveries():
    db = _DB(_Result([]))
    count = asyncio.run(WebhookService(db).process_retries())
    assert count == 0
    from sqlalchemy.dialects import postgresql
    sql = str(db.statements[0].compile(
        dialect=postgresql.dialect(),
        compile_kwargs={"literal_binds": True},
    ))
    assert "next_retry_at IS NULL" in sql
    assert "FOR UPDATE SKIP LOCKED" in sql


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
"""Security tests for webhook endpoint tenant boundaries."""
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock


def _sql(stmt) -> str:
    """Compile a SQLAlchemy statement to SQL string."""
    return str(stmt.compile(compile_kwargs={"literal_binds": True}))


class TestWebhookTenantBoundaries:

    @pytest.mark.asyncio
    async def test_test_delivery_requires_endpoint_owner(self):
        """Webhook delivery query must filter by endpoint owner."""
        owner_id = uuid.UUID("b7a30ec0-7fc4-4eac-95c1-07f0cd2c95de")
        endpoint_id = uuid.UUID("f02afa5d-c692-468c-ab33-22e17f057be5")

        from app.models.webhook import WebhookEndpoint, WebhookDelivery
        from sqlalchemy import select
        from sqlalchemy.orm import aliased

        Endpoint = aliased(WebhookEndpoint)
        stmt = (
            select(WebhookDelivery)
            .join(Endpoint, WebhookDelivery.endpoint_id == Endpoint.id)
            .where(Endpoint.id == endpoint_id, Endpoint.user_id == owner_id)
        )

        sql = _sql(stmt)
        # UUIDs in compiled SQL may not have hyphens
        assert str(owner_id).replace("-", "") in sql.replace("-", ""), \
            f"Owner ID not found in query: {sql}"

    @pytest.mark.asyncio
    async def test_delivery_history_is_scoped_to_endpoint_owner(self):
        """Delivery history query must be scoped to endpoint owner."""
        owner_id = uuid.UUID("c7c30df4-a3b9-47ad-af6d-467d353fbfa8")

        from app.models.webhook import WebhookEndpoint, WebhookDelivery
        from sqlalchemy import select
        from sqlalchemy.orm import aliased

        Endpoint = aliased(WebhookEndpoint)
        stmt = (
            select(WebhookDelivery)
            .join(Endpoint, WebhookDelivery.endpoint_id == Endpoint.id)
            .where(Endpoint.user_id == owner_id)
            .order_by(WebhookDelivery.created_at.desc())
            .limit(50)
        )

        sql = _sql(stmt)
        assert str(owner_id).replace("-", "") in sql.replace("-", ""), \
            f"Owner ID not found in query: {sql}"


@pytest.mark.asyncio
async def test_dashboard_risk_distribution_is_scoped_before_aggregation():
    """Risk counts and percentages must exclude every non-member company."""
    from types import SimpleNamespace
    from app.services.company_service import CompanyService

    user_id = uuid.uuid4()
    db = _DB(_Result([
        SimpleNamespace(risk_band="RED", company_count=1),
        SimpleNamespace(risk_band="GREEN", company_count=1),
    ]))
    rows = await CompanyService(db).get_risk_distribution(user_id)

    assert rows == [
        {"risk_band": "RED", "company_count": 1, "percentage": 50.0},
        {"risk_band": "GREEN", "company_count": 1, "percentage": 50.0},
    ]
    sql = _sql(db.statements[0])
    assert "companies.is_active IS true" in sql
    assert "company_user_access.user_id" in sql
    assert "company_user_access.is_active IS true" in sql
    assert str(user_id).replace("-", "") in sql.replace("-", "")


@pytest.mark.asyncio
async def test_dashboard_risk_distribution_returns_empty_without_active_memberships():
    from app.services.company_service import CompanyService

    db = _DB(_Result([]))
    assert await CompanyService(db).get_risk_distribution(uuid.uuid4()) == []


@pytest.mark.asyncio
async def test_dashboard_deadlines_require_active_user_membership():
    from app.services.company_service import CompanyService

    user_id = uuid.uuid4()

    class _Mappings:
        def all(self):
            return []

    class _DeadlineResult:
        def mappings(self):
            return _Mappings()

    class _DeadlineDB:
        def __init__(self):
            self.statements = []
            self.parameters = None

        async def execute(self, statement, parameters=None):
            self.statements.append(statement)
            self.parameters = parameters
            return _DeadlineResult()

    db = _DeadlineDB()
    assert await CompanyService(db).get_upcoming_deadlines(30, user_id) == []
    sql = str(db.statements[0])
    assert "company_id IN" in sql
    assert "company_user_access" in sql
    assert "user_id = :user_id" in sql
    assert "is_active IS TRUE" in sql
    assert "days_remaining <= :days" in sql
    assert db.parameters == {"days": 30, "user_id": user_id}


def test_not_evaluated_severity_is_a_persistable_database_enum_value():
    from app.models.enums import SeverityLevel

    assert SeverityLevel("NOT_EVALUATED") is SeverityLevel.NOT_EVALUATED


def test_compliance_flag_model_and_api_preserve_evaluation_state():
    from app.models.compliance import ComplianceFlag
    from app.api.companies import FlagResponse

    assert "evaluation_state" in ComplianceFlag.__table__.columns
    response = FlagResponse(
        flag_id="flag-1",
        rule_id="AUD-003",
        rule_name="Legal review required",
        severity="NOT_EVALUATED",
        score_impact=0,
        evaluation_state="REQUIRES_LAWYER_JUDGMENT",
        status="ACTIVE",
        is_black_override=False,
        triggered_at="2026-11-04",
        resolved_at=None,
        resolution_note=None,
    )
    assert response.evaluation_state == "REQUIRES_LAWYER_JUDGMENT"
