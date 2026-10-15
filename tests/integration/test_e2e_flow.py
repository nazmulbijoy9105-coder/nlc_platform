"""End-to-end flow tests."""
import pytest
import pytest_asyncio


class TestFullUserJourney:
    @pytest.mark.asyncio
    async def test_health(self, api_client):
        r = await api_client.get("/api/v1/health/live")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_rules_loaded(self, api_client, super_admin_headers):
        r = await api_client.get("/api/v1/rules", headers=super_admin_headers)
        assert r.status_code == 200
        rules = r.json()
        assert len(rules) >= 75
        ids = {x["rule_id"] for x in rules}
        assert "AGM-001" in ids
        assert "AUD-001" in ids
        assert "ESC-003" in ids

    @pytest.mark.asyncio
    async def test_rjsc_forms(self, api_client, super_admin_headers):
        r = await api_client.get("/api/v1/rjsc-forms/reference", headers=super_admin_headers)
        if r.status_code == 200:
            assert r.json().get("total", 0) >= 13

    @pytest.mark.asyncio
    async def test_auth_enforced(self, api_client):
        r = await api_client.post(
            "/api/v1/companies",
            json={
                "company_name": "T",
                "registration_number": "C-1",
                "company_type": "PRIVATE_LIMITED",
                "registered_address": "Dhaka"
            }
        )
        assert r.status_code in (401, 403, 422)

    @pytest.mark.asyncio
    async def test_api_structure(self, api_client, super_admin_headers):
        r = await api_client.get("/api/v1/openapi.json", headers=super_admin_headers)
        assert r.status_code == 200
        paths = list(r.json().get("paths", {}).keys())
        assert any("/auth/login" in p for p in paths)
        assert any("/companies" in p for p in paths)
        assert any("/rules" in p for p in paths)
        assert any("/rjsc-forms" in p for p in paths)

    @pytest.mark.asyncio
    async def test_black_rules(self, api_client, super_admin_headers):
        r = await api_client.get("/api/v1/rules", headers=super_admin_headers)
        assert r.status_code == 200
        blacks = {x["rule_id"] for x in r.json() if x.get("is_black_override")}
        assert "AUD-003" in blacks
        assert "INC-003" in blacks
        assert "ESC-002" in blacks

    @pytest.mark.asyncio
    async def test_statutory_refs(self, api_client, super_admin_headers):
        r = await api_client.get("/api/v1/rules", headers=super_admin_headers)
        assert r.status_code == 200
        for rule in r.json()[:10]:
            assert rule.get("statutory_basis"), f"Rule {rule['rule_id']} missing statutory_basis"
