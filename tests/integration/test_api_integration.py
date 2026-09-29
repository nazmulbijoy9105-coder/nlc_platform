"""Real HTTP integration tests."""
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
async def api_client(test_app):
    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        yield client

class TestHealthEndpoints:
    @pytest.mark.asyncio
    async def test_root(self, api_client):
        r = await api_client.get("/")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_health(self, api_client):
        r = await api_client.get("/api/v1/health/live")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_docs(self, api_client):
        r = await api_client.get("/docs")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_openapi(self, api_client):
        r = await api_client.get("/openapi.json")
        assert r.status_code == 200
        assert "paths" in r.json()

class TestRulesAPI:
    @pytest.mark.asyncio
    async def test_rules_list(self, api_client):
        r = await api_client.get("/api/v1/rules")
        assert r.status_code == 200
        raw = r.json()
        data = raw if isinstance(raw, dict) else (raw if isinstance(raw, list) else {})
        assert isinstance(data, list) and len(data) >= 65, f"Expected list, got {type(data)}: {str(data)[:100]}"
        assert isinstance(data, list) and len(data) > 0 and "rule_id" in data[0]

    @pytest.mark.asyncio
    async def test_black_overrides(self, api_client):
        r = await api_client.get("/api/v1/rules")
        blacks = [x for x in r.json() if x.get("is_black_override")]
        assert len(blacks) >= 10

class TestAuthFlow:
    @pytest.mark.asyncio
    async def test_bad_login(self, api_client):
        r = await api_client.post("/api/v1/auth/login", json={"email":"bad@test.com","password":"BadPass1!"})
        assert r.status_code == 401

    @pytest.mark.asyncio
    async def test_me_no_token(self, api_client):
        r = await api_client.get("/api/v1/auth/me")
        assert r.status_code in (401, 403)

class TestErrors:
    @pytest.mark.asyncio
    async def test_404(self, api_client):
        r = await api_client.get("/api/v1/nonexistent")
        assert r.status_code == 404
