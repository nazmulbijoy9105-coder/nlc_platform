"""
NLC — GATE E2: Tenant & Object Authorization (IDOR) Adversarial Tests
Proves that User A (Company A) cannot access Company B's resources by manipulating IDs.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import create_app

@pytest.fixture(scope="module")
def client():
    app = create_app()
    with TestClient(app) as c:
        yield c

# Mock tokens for two different companies
TOKEN_A = "mock_company_a_token"  # User belongs to Company A
TOKEN_B = "mock_company_b_token"  # User belongs to Company B

COMPANY_A_ID = "00000000-0000-0000-0000-000000000001"
COMPANY_B_ID = "00000000-0000-0000-0000-000000000002"

def test_company_a_cannot_get_company_b(client):
    """User A tries to GET Company B's profile."""
    headers = {"Authorization": f"Bearer {TOKEN_A}"}
    response = client.get(f"/api/v1/companies/{COMPANY_B_ID}", headers=headers)
    assert response.status_code in (403, 404), "Tenant boundary breached: User A accessed Company B"

def test_company_a_cannot_access_company_b_documents(client):
    """User A tries to GET documents for Company B."""
    headers = {"Authorization": f"Bearer {TOKEN_A}"}
    response = client.get(f"/api/v1/documents/{COMPANY_B_ID}", headers=headers)
    assert response.status_code in (403, 404), "Tenant boundary breached: User A accessed Company B documents"

def test_company_a_cannot_access_company_b_filings(client):
    """User A tries to GET filings for Company B."""
    headers = {"Authorization": f"Bearer {TOKEN_A}"}
    response = client.get(f"/api/v1/filings/agm/{COMPANY_B_ID}", headers=headers)
    assert response.status_code in (403, 404), "Tenant boundary breached: User A accessed Company B filings"

def test_company_a_cannot_access_company_b_rescue(client):
    """User A tries to GET rescue plan for Company B."""
    headers = {"Authorization": f"Bearer {TOKEN_A}"}
    response = client.get(f"/api/v1/rescue/plans/{COMPANY_B_ID}/active", headers=headers)
    assert response.status_code in (403, 404), "Tenant boundary breached: User A accessed Company B rescue plan"
