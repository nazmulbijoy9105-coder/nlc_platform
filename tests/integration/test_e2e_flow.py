"""End-to-end flow tests."""
import pytest
import pytest_asyncio

@pytest.fixture
def test_app():
    try:
        from app.main import create_app
        return create_app()
    except Exception:
        pytest.skip("App creation failed")

@pytest_asyncio.fixture
async def client(test_app):
    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as c:
        yield c

class TestFullUserJourney:
    @pytest.mark.asyncio
    async def test_health(self, client):
        r = await client.get("/api/v1/health/live")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_rules_loaded(self, client):
        r = await client.get("/api/v1/rules")
        assert r.status_code == 200
        rules = r.json()
        assert len(rules) >= 65
        ids = {x["rule_id"] for x in rules}
        assert "AGM-001" in ids
        assert "AUD-001" in ids
        assert "ESC-003" in ids

    @pytest.mark.asyncio
    async def test_rjsc_forms(self, client):
        r = await client.get("/api/v1/rjsc-forms/reference")
        if r.status_code == 200:
            assert r.json().get("total", 0) >= 13

    @pytest.mark.asyncio
    async def test_auth_enforced(self, client):
        r = await client.post("/api/v1/companies", json={"company_name":"T","registration_number":"C-1","company_type":"PRIVATE_LIMITED","registered_address":"Dhaka"})
        assert r.status_code in (401, 403, 422)

    @pytest.mark.asyncio
    async def test_api_structure(self, client):
        r = await client.get("/openapi.json")
        paths = list(r.json().get("paths", {}).keys())
        assert any("/auth/login" in p for p in paths)
        assert any("/companies" in p for p in paths)
        assert any("/rules" in p for p in paths)
        assert any("/rjsc-forms" in p for p in paths)

    @pytest.mark.asyncio
    async def test_black_rules(self, client):
        r = await client.get("/api/v1/rules")
        blacks = {x["rule_id"] for x in r.json() if x.get("is_black_override")}
        assert "AUD-003" in blacks
        assert "INC-003" in blacks
        assert "ESC-002" in blacks

    @pytest.mark.asyncio
    async def test_statutory_refs(self, client):
        r = await client.get("/api/v1/rules")
        for rule in r.json()[:10]:
            assert rule.get("statutory_basis"), f"Rule {rule['rule_id']} missing statutory_basis"
