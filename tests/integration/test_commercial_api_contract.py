"""Regression tests for the existing commercial API/service contract."""
from __future__ import annotations

import asyncio

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
    premature_start = await api_client.patch(
        f"/api/v1/commercial/engagements/{engagement['engagement_id']}/status",
        headers=_auth(commercial_admin_token),
        json={"new_status": "IN_PROGRESS"},
    )
    assert premature_start.status_code == 409, premature_start.text

    accept_response = await api_client.patch(
        f"/api/v1/commercial/quotations/{accepted['quotation_id']}/accept",
        headers=_auth(commercial_admin_token),
    )
    assert accept_response.status_code == 200, accept_response.text
    assert accept_response.json()["status"] == "ACCEPTED"

    start_response = await api_client.patch(
        f"/api/v1/commercial/engagements/{engagement['engagement_id']}/status",
        headers=_auth(commercial_admin_token),
        json={"new_status": "IN_PROGRESS", "note": "Service delivery started"},
    )
    assert start_response.status_code == 200, start_response.text
    assert start_response.json()["status"] == "IN_PROGRESS"

    rejection_engagement = await _create_engagement(
        api_client, commercial_admin_token, db_company.id
    )
    rejected = await _create_quotation(
        api_client,
        commercial_admin_token,
        db_company.id,
        rejection_engagement["engagement_id"],
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
        json={"new_status": "CANCELLED", "note": "Engagement cancelled"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "CANCELLED"


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

    repeated = await api_client.patch(
        f"/api/v1/commercial/tasks/{created.json()['task_id']}/complete",
        headers=_auth(commercial_admin_token),
        json={"completion_note": "Should not complete twice"},
    )
    assert repeated.status_code == 409, repeated.text

@pytest.mark.asyncio
async def test_quotation_cannot_be_attached_to_another_company(
    api_client, commercial_admin_token, db_company
):
    engagement = await _create_engagement(
        api_client, commercial_admin_token, db_company.id
    )
    response = await api_client.post(
        "/api/v1/commercial/quotations",
        headers=_auth(commercial_admin_token),
        json={
            "engagement_id": engagement["engagement_id"],
            "company_id": "00000000-0000-0000-0000-000000000001",
            "professional_fee_bdt": "10000.00",
        },
    )
    assert response.status_code == 404, response.text


@pytest.mark.asyncio
async def test_engagement_rejects_invalid_status_jump(
    api_client, commercial_admin_token, db_company
):
    engagement = await _create_engagement(
        api_client, commercial_admin_token, db_company.id
    )
    response = await api_client.patch(
        f"/api/v1/commercial/engagements/{engagement['engagement_id']}/status",
        headers=_auth(commercial_admin_token),
        json={"new_status": "COMPLETED"},
    )
    assert response.status_code == 409, response.text

@pytest.mark.asyncio
async def test_concurrent_competing_quotation_acceptance_is_serialized(
    api_client, commercial_admin_token, db_company
):
    engagement = await _create_engagement(
        api_client, commercial_admin_token, db_company.id
    )
    first_quote = await _create_quotation(
        api_client, commercial_admin_token, db_company.id, engagement["engagement_id"]
    )
    second_quote = await _create_quotation(
        api_client, commercial_admin_token, db_company.id, engagement["engagement_id"]
    )

    first_response, second_response = await asyncio.gather(
        api_client.patch(
            f"/api/v1/commercial/quotations/{first_quote['quotation_id']}/accept",
            headers=_auth(commercial_admin_token),
        ),
        api_client.patch(
            f"/api/v1/commercial/quotations/{second_quote['quotation_id']}/accept",
            headers=_auth(commercial_admin_token),
        ),
    )

    assert sorted([first_response.status_code, second_response.status_code]) == [200, 409]
    accepted = first_response if first_response.status_code == 200 else second_response
    assert accepted.json()["status"] == "ACCEPTED"


@pytest.mark.asyncio
async def test_concurrent_accept_and_reject_of_same_quotation_is_serialized(
    api_client, commercial_admin_token, db_company
):
    engagement = await _create_engagement(
        api_client, commercial_admin_token, db_company.id
    )
    quotation = await _create_quotation(
        api_client, commercial_admin_token, db_company.id, engagement["engagement_id"]
    )

    accept_response, reject_response = await asyncio.gather(
        api_client.patch(
            f"/api/v1/commercial/quotations/{quotation['quotation_id']}/accept",
            headers=_auth(commercial_admin_token),
        ),
        api_client.patch(
            f"/api/v1/commercial/quotations/{quotation['quotation_id']}/reject",
            headers=_auth(commercial_admin_token),
            json={"reason": "Concurrent rejection regression"},
        ),
    )

    assert sorted([accept_response.status_code, reject_response.status_code]) == [200, 409]
    successful = accept_response if accept_response.status_code == 200 else reject_response
    assert successful.json()["status"] in {"ACCEPTED", "REJECTED"}
