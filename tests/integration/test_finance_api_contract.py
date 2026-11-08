"""End-to-end invoice and offline payment ledger contract."""
from __future__ import annotations

from decimal import Decimal

import pytest


@pytest.mark.asyncio
async def test_invoice_payment_approval_reconciles_once(
    api_client, admin_headers, db_company
):
    created = await api_client.post(
        "/api/v1/finance/invoices",
        headers=admin_headers,
        json={
            "company_id": str(db_company.id),
            "lines": [
                {
                    "description": "RJSC annual compliance service",
                    "quantity": "1.00",
                    "unit_price_bdt": "10000.00",
                }
            ],
            "tax_bdt": "0.00",
        },
    )
    assert created.status_code == 201, created.text
    invoice = created.json()
    assert Decimal(str(invoice["total_bdt"])) == Decimal("10000.00")
    assert invoice["status"] == "DRAFT"

    issued = await api_client.post(
        f"/api/v1/finance/invoices/{invoice['invoice_id']}/issue",
        headers=admin_headers,
    )
    assert issued.status_code == 200, issued.text
    assert issued.json()["status"] == "ISSUED"

    submitted = await api_client.post(
        f"/api/v1/finance/companies/{db_company.id}/payments/offline",
        headers=admin_headers,
        json={
            "invoice_id": invoice["invoice_id"],
            "method": "CASH",
            "amount_bdt": "2500.00",
        },
    )
    assert submitted.status_code == 201, submitted.text
    submission = submitted.json()
    assert submission["status"] == "PENDING_REVIEW"

    approved = await api_client.post(
        f"/api/v1/finance/payment-submissions/{submission['submission_id']}/approve",
        headers=admin_headers,
        json={},
    )
    assert approved.status_code == 200, approved.text
    payment_id = approved.json()["payment_id"]

    repeated = await api_client.post(
        f"/api/v1/finance/payment-submissions/{submission['submission_id']}/approve",
        headers=admin_headers,
        json={},
    )
    assert repeated.status_code == 200, repeated.text
    assert repeated.json()["payment_id"] == payment_id

    current = await api_client.get(
        f"/api/v1/finance/invoices/{invoice['invoice_id']}",
        headers=admin_headers,
    )
    assert current.status_code == 200, current.text
    assert Decimal(str(current.json()["paid_bdt"])) == Decimal("2500.00")
    assert Decimal(str(current.json()["balance_bdt"])) == Decimal("7500.00")
    assert current.json()["status"] == "PARTIALLY_PAID"

    overpayment = await api_client.post(
        f"/api/v1/finance/companies/{db_company.id}/payments/offline",
        headers=admin_headers,
        json={
            "invoice_id": invoice["invoice_id"],
            "method": "CASH",
            "amount_bdt": "7500.01",
        },
    )
    assert overpayment.status_code == 409, overpayment.text


@pytest.mark.asyncio
async def test_offline_payment_rejects_naive_datetime(
    api_client, admin_headers, db_company
):
    created = await api_client.post(
        "/api/v1/finance/invoices",
        headers=admin_headers,
        json={
            "company_id": str(db_company.id),
            "lines": [
                {"description": "Service", "quantity": "1", "unit_price_bdt": "500.00"}
            ],
        },
    )
    assert created.status_code == 201, created.text
    invoice = created.json()
    issued = await api_client.post(
        f"/api/v1/finance/invoices/{invoice['invoice_id']}/issue",
        headers=admin_headers,
    )
    assert issued.status_code == 200, issued.text

    response = await api_client.post(
        f"/api/v1/finance/companies/{db_company.id}/payments/offline",
        headers=admin_headers,
        json={
            "invoice_id": invoice["invoice_id"],
            "method": "CASH",
            "amount_bdt": "100.00",
            "paid_at": "2026-11-07T10:00:00",
        },
    )
    assert response.status_code == 409, response.text
