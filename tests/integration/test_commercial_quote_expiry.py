"""Regression coverage for quotation expiry and inaccessible engagement handling."""
from datetime import date, timedelta
from uuid import UUID

import pytest

from app.models.commercial import Engagement, Quotation


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _create_quote(api_client, token: str, company_id):
    engagement_response = await api_client.post(
        "/api/v1/commercial/engagements",
        headers=_auth(token),
        json={
            "company_id": str(company_id),
            "engagement_type": "COMPLIANCE_PACKAGE",
            "revenue_tier": "COMPLIANCE_PACKAGE",
            "description": "Quotation expiry regression",
        },
    )
    assert engagement_response.status_code == 201, engagement_response.text
    engagement = engagement_response.json()
    quotation_response = await api_client.post(
        "/api/v1/commercial/quotations",
        headers=_auth(token),
        json={
            "engagement_id": engagement["engagement_id"],
            "company_id": str(company_id),
            "professional_fee_bdt": "10000.00",
            "valid_days": 30,
        },
    )
    assert quotation_response.status_code == 201, quotation_response.text
    return engagement, quotation_response.json()


@pytest.mark.asyncio
async def test_expired_quotation_cannot_be_accepted(
    api_client, admin_token, db_company, db
):
    engagement, quotation = await _create_quote(
        api_client, admin_token, db_company.id
    )
    stored = await db.get(Quotation, UUID(quotation["quotation_id"]))
    assert stored is not None
    stored.valid_until = date.today() - timedelta(days=1)
    await db.flush()

    response = await api_client.patch(
        f"/api/v1/commercial/quotations/{quotation['quotation_id']}/accept",
        headers=_auth(admin_token),
    )
    assert response.status_code == 409, response.text
    assert "expired" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_inactive_engagement_quotation_is_tenant_safe_not_found(
    api_client, admin_token, db_company, db
):
    engagement, quotation = await _create_quote(
        api_client, admin_token, db_company.id
    )
    stored = await db.get(Engagement, UUID(engagement["engagement_id"]))
    assert stored is not None
    stored.is_active = False
    await db.flush()

    response = await api_client.patch(
        f"/api/v1/commercial/quotations/{quotation['quotation_id']}/accept",
        headers=_auth(admin_token),
    )
    assert response.status_code == 404, response.text
