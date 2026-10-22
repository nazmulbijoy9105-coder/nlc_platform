"""Behavior + IDOR tests for PATCH /api/v1/rjsc-forms/{form_id}/filed."""
from __future__ import annotations

import uuid
from datetime import date

import pytest


@pytest.fixture
async def db_company(db):
    from app.models.company import Company
    company = Company(
        id=str(uuid.uuid4()),
        registration_number=f"REG-{uuid.uuid4().hex[:8].upper()}",
        company_name=f"Test Co {uuid.uuid4().hex[:6]}",
        company_type="PRIVATE_LIMITED",
        incorporation_date=date(2020, 1, 1),
        financial_year_end=date(2020, 12, 31),
    )
    db.add(company)
    await db.flush()
    return company


@pytest.fixture
async def db_filing(db, db_company):
    from app.models.rjsc_forms import RJSCFormFiling
    filing = RJSCFormFiling(
        id=str(uuid.uuid4()),
        company_id=db_company.id,
        form_code="FORM_XII",
        form_number="XII",
        form_name="Annual Return",
        section_reference="Section 36",
        related_rule_id="AR-001",
        filing_status="PENDING",
        due_date=date.today(),
        financial_year="2024-2025",
    )
    db.add(filing)
    await db.flush()
    return filing




@pytest.fixture
def client_view_headers(client_view_token) -> dict[str, str]:
    return {"Authorization": f"Bearer {client_view_token}"}

class TestMarkFormFiledBasics:
    @pytest.mark.asyncio
    async def test_401_without_auth_token(self, api_client, db_filing):
        resp = await api_client.patch(
            f"/api/v1/rjsc-forms/{db_filing.id}/filed",
            json={"filed_date": "2024-12-01"},
        )
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}: {resp.text}"

    @pytest.mark.asyncio
    async def test_403_for_client_view_only_role(self, api_client, db_filing, client_view_headers):
        resp = await api_client.patch(
            f"/api/v1/rjsc-forms/{db_filing.id}/filed",
            json={"filed_date": "2024-12-01"},
            headers=client_view_headers,
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"

    @pytest.mark.asyncio
    async def test_403_for_client_director_role(self, api_client, db_filing, client_headers):
        resp = await api_client.patch(
            f"/api/v1/rjsc-forms/{db_filing.id}/filed",
            json={"filed_date": "2024-12-01"},
            headers=client_headers,
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"

    @pytest.mark.asyncio
    async def test_404_for_nonexistent_form_id(self, api_client, admin_headers):
        fake_id = str(uuid.uuid4())
        resp = await api_client.patch(
            f"/api/v1/rjsc-forms/{fake_id}/filed",
            json={"filed_date": "2024-12-01"},
            headers=admin_headers,
        )
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}: {resp.text}"

    @pytest.mark.asyncio
    async def test_422_for_invalid_form_id_format(self, api_client, admin_headers):
        """PATCH with a non-UUID string → 422 (FastAPI validates path param type)."""
        resp = await api_client.patch(
            "/api/v1/rjsc-forms/not-a-uuid/filed",
            json={"filed_date": "2024-12-01"},
            headers=admin_headers,
        )
        assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"

    @pytest.mark.asyncio
    async def test_200_for_authorized_staff(self, api_client, db_filing, admin_headers):
        resp = await api_client.patch(
            f"/api/v1/rjsc-forms/{db_filing.id}/filed",
            json={
                "filed_date": "2024-12-01",
                "rjsc_receipt_number": "RJSC-RECEIPT-001",
                "notes": "Filed via test",
            },
            headers=admin_headers,
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        body = resp.json()
        assert body["filing_status"] == "FILED"
        assert body["filed_date"] == "2024-12-01"
        assert body["rjsc_receipt_number"] == "RJSC-RECEIPT-001"

    @pytest.mark.asyncio
    async def test_filed_by_audit_trail_is_recorded(
        self, api_client, db_filing, admin_headers, admin_token, db
    ):
        from app.core.security import decode_token
        payload = decode_token(admin_token)
        expected_user_id = payload.get("user_id") or payload.get("sub")

        resp = await api_client.patch(
            f"/api/v1/rjsc-forms/{db_filing.id}/filed",
            json={"filed_date": "2024-12-01"},
            headers=admin_headers,
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

        await db.refresh(db_filing)
        assert str(db_filing.filed_by) == expected_user_id, (
            f"filed_by should be {expected_user_id}, got {db_filing.filed_by}"
        )


class TestMarkFormFiledIDOR:
    @pytest.mark.asyncio
    async def test_user_cannot_mark_other_companys_filing(
        self, api_client, db_filing, client_headers
    ):
        resp = await api_client.patch(
            f"/api/v1/rjsc-forms/{db_filing.id}/filed",
            json={"filed_date": "2024-12-01"},
            headers=client_headers,
        )
        assert resp.status_code in (403, 404), (
            f"Expected 403/404 for cross-tenant access, got {resp.status_code}"
        )
