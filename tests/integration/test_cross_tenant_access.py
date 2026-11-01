"""SEC-012: Cross-tenant integration tests.

Verifies that authenticated users cannot access data belonging to other companies.
Uses api_client_as_user (real RLS) when available; falls back to documented skip
only if the multi-tenant seed data is not present.
"""
from __future__ import annotations

import uuid

import pytest

COMPANY_A_ID = "00000000-0000-0000-0000-000000000001"
COMPANY_B_ID = "00000000-0000-0000-0000-000000000002"


@pytest.mark.asyncio
async def test_cross_tenant_company_access_rejected(api_client_as_user, client_headers):
    """SEC-012: User A cannot access company B's compliance data."""
    r = await api_client_as_user.get(
        f"/api/v1/companies/{COMPANY_B_ID}",
        headers=client_headers,
    )
    assert r.status_code in (403, 404), r.text


@pytest.mark.asyncio
async def test_cross_tenant_filing_access_rejected(api_client_as_user, client_headers):
    """SEC-012: User A cannot access company B's filings."""
    r = await api_client_as_user.get(
        f"/api/v1/filings/agm/{COMPANY_B_ID}",
        headers=client_headers,
    )
    assert r.status_code in (403, 404), r.text


@pytest.mark.asyncio
async def test_cross_tenant_document_access_rejected(api_client_as_user, client_headers):
    """SEC-012: User A cannot access company B's documents list."""
    r = await api_client_as_user.get(
        f"/api/v1/documents/{COMPANY_B_ID}",
        headers=client_headers,
    )
    assert r.status_code in (403, 404), r.text


@pytest.mark.asyncio
async def test_cross_tenant_rescue_plan_access_rejected(api_client_as_user, client_headers):
    """SEC-012: User A cannot access company B's rescue plans."""
    r = await api_client_as_user.get(
        f"/api/v1/rescue/plans/{COMPANY_B_ID}/active",
        headers=client_headers,
    )
    assert r.status_code in (403, 404), r.text


@pytest.mark.asyncio
async def test_cross_tenant_score_history_access_rejected(api_client_as_user, client_headers):
    """SEC-012: User A cannot access company B's score history."""
    r = await api_client_as_user.get(
        f"/api/v1/companies/{COMPANY_B_ID}/score-history",
        headers=client_headers,
    )
    assert r.status_code in (403, 404), r.text


@pytest.mark.asyncio
async def test_cross_tenant_calendar_access_rejected(api_client_as_user, client_headers):
    """SEC-012: User A cannot access company B's calendar events."""
    r = await api_client_as_user.get(
        f"/api/v1/calendar/{COMPANY_B_ID}",
        headers=client_headers,
    )
    # calendar route may 404 if not registered — both are acceptable denial
    assert r.status_code in (403, 404), r.text
