"""Regression tests for the existing commercial API/service contract."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.core.security import create_access_token


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def commercial_admin_token(db_user):
    return create_access_token({
        "sub": str(db_user.id),
        "user_id": str(db_user.id),
        "type": "access",
        "role": "ADMIN_STAFF",
        "email": db_user.email,
        "company_ids": [],
    })


async def _create_engagement(api_client, token, company_id):
    response = await api_client.post(
        "/api/v1/commercial/engagements",
        headers=_auth(token),
        json={
            "company_id": str(company_id),
            "engagement_type": "COMPLIANCE_PACKAGE",
            "revenue_tier": "COMPLIANCE_PACKAGE",
            "description": "Commercial API contract regression",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _create_quotation(api_client, token, company_id, engagement_id):
    response = await api_client.post(
        "/api/v1/commercial/quotations",
        headers=_auth(token),
        json={
            "engagement_id": engagement_id,
            "company_id": str(company_id),
            "professional_fee_bdt": "100000.00",
            "government_fee_bdt": "5000.00",
            "vat_bdt": "15000.00",
            "valid_days": 30,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio
async def test_quotation_creation_uses_decimal_totals_and_validity(
    api_client, commercial_admin_token, db_company
):
    engagement = await _create_engagement(
        api_client, commercial_admin_token, db_company.id
    )
    quotation = await _create_quotation(
        api_client,
        commercial_admin_token,
        db_company.id,
        engagement["engagement_id"],
    )

    assert Decimal(str(quotation["total_fee_bdt"])) == Decimal("120000.00")
    assert quotation["valid_until"] == (
        date.today() + timedelta(days=30)
    ).isoformat()


@pytest.mark.asyncio
async def test_quotation_accept_and_reject_routes_match_service_contract(
    api_client, commercial_admin_token, db_company
):
    engagement = await _create_engagement(
        api_client, commercial_admin_token, db_company.id
    )
    accepted = await _create_quotation(
        api_client, commercial_admin_token, db_company.id, engagement["engagement_id"]
    )
    accept_response = await api_client.patch(
        f"/api/v1/commercial/quotations/{accepted['quotation_id']}/accept",
        headers=_auth(commercial_admin_token),
    )
    assert accept_response.status_code == 200, accept_response.text
    assert accept_response.json()["status"] == "ACCEPTED"

    rejected = await _create_quotation(
        api_client, commercial_admin_token, db_company.id, engagement["engagement_id"]
    )
    reject_response = await api_client.patch(
        f"/api/v1/commercial/quotations/{rejected['quotation_id']}/reject",
        headers=_auth(commercial_admin_token),
        json={"reason": "Client declined the proposed scope"},
    )
    assert reject_response.status_code == 200, reject_response.text
    assert reject_response.json()["status"] == "REJECTED"


@pytest.mark.asyncio
async def test_engagement_status_transition_accepts_note(
    api_client, commercial_admin_token, db_company
):
    engagement = await _create_engagement(
        api_client, commercial_admin_token, db_company.id
    )
    response = await api_client.patch(
        f"/api/v1/commercial/engagements/{engagement['engagement_id']}/status",
        headers=_auth(commercial_admin_token),
        json={"new_status": "QUOTED", "note": "Quotation prepared"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "QUOTED"


@pytest.mark.asyncio
async def test_task_completion_accepts_completion_note(
    api_client, commercial_admin_token, db_company
):
    created = await api_client.post(
        "/api/v1/commercial/tasks",
        headers=_auth(commercial_admin_token),
        json={
            "company_id": str(db_company.id),
            "title": "Complete API contract test task",
            "description": "Exercise task completion endpoint",
        },
    )
    assert created.status_code == 201, created.text

    response = await api_client.patch(
        f"/api/v1/commercial/tasks/{created.json()['task_id']}/complete",
        headers=_auth(commercial_admin_token),
        json={"completion_note": "Verified complete"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "COMPLETED"
