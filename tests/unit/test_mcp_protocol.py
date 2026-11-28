"""Contract tests for the authenticated NLC MCP HTTP endpoint."""
import json
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api import mcp
from app.core.dependencies import get_catalog_db, get_current_user
from app.main import create_app


def _client():
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id="11111111-1111-4111-8111-111111111111"
    )

    async def fake_catalog_db():
        yield object()

    app.dependency_overrides[get_catalog_db] = fake_catalog_db
    return TestClient(app)


def _headers():
    return {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": "2025-11-25",
    }


def test_initialize_negotiates_supported_protocol_version():
    client = _client()
    response = client.post(
        "/api/v1/mcp",
        headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-11-25",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0"},
            },
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["result"]["protocolVersion"] == "2025-11-25"
    assert body["result"]["capabilities"]["tools"]["listChanged"] is False
    assert response.headers["mcp-protocol-version"] == "2025-11-25"


def test_tools_list_returns_only_read_only_catalogue_tools():
    client = _client()
    response = client.post(
        "/api/v1/mcp",
        headers=_headers(),
        json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    )
    assert response.status_code == 200
    tools = response.json()["result"]["tools"]
    assert {tool["name"] for tool in tools} == {"nlc.list_rules", "nlc.get_rule"}
    assert all(tool["inputSchema"]["additionalProperties"] is False for tool in tools)


def test_tools_call_rejects_unknown_arguments_without_touching_database(monkeypatch):
    async def should_not_run(*args, **kwargs):
        raise AssertionError("Invalid arguments must be rejected before querying rules.")

    monkeypatch.setattr(mcp, "RulesService", lambda db: SimpleNamespace(get_all=should_not_run))
    client = _client()
    response = client.post(
        "/api/v1/mcp",
        headers=_headers(),
        json={
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "nlc.list_rules",
                "arguments": {"unexpected": "value"},
            },
        },
    )
    result = response.json()["result"]
    assert result["isError"] is True
    assert "Unsupported argument" in result["content"][0]["text"]


def test_tools_call_returns_rule_metadata_with_explicit_legal_limitations(monkeypatch):
    rule = SimpleNamespace(
        rule_id="AGM-001",
        rule_name="Sample AGM rule",
        rule_type="GOVERNANCE",
        statutory_basis="Sample statutory reference",
        description="Sample description",
        verification_status="PENDING",
        statutory_effective_date=None,
        is_active=True,
        rule_version="1.0",
        score_impact=0,
    )

    class FakeRulesService:
        def __init__(self, db):
            self.db = db

        async def get_by_rule_id(self, rule_id):
            assert rule_id == "AGM-001"
            return rule

    monkeypatch.setattr(mcp, "RulesService", FakeRulesService)
    client = _client()
    response = client.post(
        "/api/v1/mcp",
        headers=_headers(),
        json={
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "nlc.get_rule",
                "arguments": {"rule_id": "AGM-001"},
            },
        },
    )
    result = response.json()["result"]
    assert result["isError"] is False
    payload = json.loads(result["content"][0]["text"])
    assert payload["rule_id"] == "AGM-001"
    assert payload["verification_status"] == "PENDING"
    assert "not independent legal verification" in payload["disclaimer"]


def test_non_initialize_requests_require_protocol_version():
    client = _client()
    response = client.post(
        "/api/v1/mcp",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        json={"jsonrpc": "2.0", "id": 5, "method": "tools/list", "params": {}},
    )
    assert response.status_code == 200
    assert response.json()["error"]["code"] == -32600


def test_get_transport_is_not_supported():
    client = _client()
    response = client.get("/api/v1/mcp")
    assert response.status_code == 405
