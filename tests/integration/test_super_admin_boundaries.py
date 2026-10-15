"""
NLC — GATE E3: Super Admin Control Plane Boundary Tests
Proves that Super Admins cannot alter immutable legal evaluation results directly.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.core.dependencies import get_current_user, TokenData
from contextlib import asynccontextmanager

# Mock Super Admin Token
MOCK_SUPER_ADMIN = TokenData(sub="admin-uuid", role="SUPER_ADMIN", company_ids=[], user_id="admin-uuid", email="admin@test.com")

COMPANY_A_ID = "00000000-0000-0000-0000-000000000001"

@pytest.fixture(scope="module")
def client():
    app = create_app()
    
    @asynccontextmanager
    async def empty_lifespan(app):
        yield
    app.router.lifespan_context = empty_lifespan
    
    async def override_get_current_user():
        return MOCK_SUPER_ADMIN
        
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    with TestClient(app) as c:
        yield c

def test_super_admin_cannot_alter_score_directly(client):
    """Super Admin tries to POST to a non-existent backdoor endpoint to change a score."""
    response = client.post(f"/api/v1/admin/companies/{COMPANY_A_ID}/score", json={"score": 100})
    # Expect 404 or 405 because the endpoint does not exist
    assert response.status_code in (404, 405), "Super Admin backdoor detected: endpoint should not exist"

def test_super_admin_cannot_resolve_flag_directly_via_admin(client):
    """Super Admin tries to POST to a non-existent admin endpoint to resolve a flag."""
    flag_id = "00000000-0000-0000-0000-000000000099"
    response = client.post(f"/api/v1/admin/flags/{flag_id}/resolve", json={"note": "admin override"})
    assert response.status_code in (404, 405), "Super Admin backdoor detected: endpoint should not exist"
