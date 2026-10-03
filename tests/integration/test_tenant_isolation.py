"""
NLC — GATE E2: Tenant & Object Authorization (IDOR) Adversarial Tests
Proves that User A (Company A) cannot access Company B's resources by manipulating IDs.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.core.dependencies import get_current_user, TokenData

# Mock User A (belongs only to Company A)
MOCK_TOKEN_A = TokenData(sub="user-a-uuid", role="CLIENT_DIRECTOR", company_ids=["00000000-0000-0000-0000-000000000001"])

COMPANY_A_ID = "00000000-0000-0000-0000-000000000001"
COMPANY_B_ID = "00000000-0000-0000-0000-000000000002"

@pytest.fixture(scope="module")
def client():
    app = create_app()
    
    # Override the authentication dependency to simulate User A
    async def override_get_current_user():
        return MOCK_TOKEN_A
        
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    with TestClient(app) as c:
        yield c

def test_company_a_cannot_get_company_b(client):
    """User A tries to GET Company B's profile."""
    response = client.get(f"/api/v1/companies/{COMPANY_B_ID}")
    assert response.status_code in (403, 404), "Tenant boundary breached: User A accessed Company B"

def test_company_a_cannot_access_company_b_documents(client):
    """User A tries to GET documents for Company B."""
    response = client.get(f"/api/v1/documents/{COMPANY_B_ID}")
    assert response.status_code in (403, 404), "Tenant boundary breached: User A accessed Company B documents"

def test_company_a_cannot_access_company_b_filings(client):
    """User A tries to GET filings for Company B."""
    response = client.get(f"/api/v1/filings/agm/{COMPANY_B_ID}")
    assert response.status_code in (403, 404), "Tenant boundary breached: User A accessed Company B filings"

def test_company_a_cannot_access_company_b_rescue(client):
    """User A tries to GET rescue plan for Company B."""
    response = client.get(f"/api/v1/rescue/plans/{COMPANY_B_ID}/active")
    assert response.status_code in (403, 404), "Tenant boundary breached: User A accessed Company B rescue plan"
