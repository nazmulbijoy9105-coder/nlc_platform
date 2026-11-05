"""Database-level separation between legal staff and finance staff."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from app.models.database import set_rls_context


@pytest.mark.asyncio
async def test_legal_staff_is_not_finance_staff_under_signed_rls(api_client, db):
    legal_user_id = uuid.uuid5(uuid.NAMESPACE_DNS, "nlc-test-user-LEGAL_STAFF")
    company_id = uuid.uuid4()

    await set_rls_context(db, str(legal_user_id))
    result = await db.execute(
        text("""
            SELECT
                public.nlc_current_user_is_staff() AS is_staff,
                public.nlc_current_user_is_finance_staff() AS is_finance,
                public.nlc_can_view_billing_company(:company_id) AS can_view_billing,
                public.nlc_can_submit_payment_company(:company_id) AS can_submit_payment,
                public.nlc_can_manage_billing_company(:company_id) AS can_manage_billing
        """),
        {"company_id": company_id},
    )
    row = result.one()

    assert row.is_staff is True
    assert row.is_finance is False
    assert row.can_view_billing is False
    assert row.can_submit_payment is False
    assert row.can_manage_billing is False


@pytest.mark.asyncio
async def test_admin_staff_has_finance_access_under_signed_user_identity(api_client, db):
    admin_user_id = uuid.uuid5(uuid.NAMESPACE_DNS, "nlc-test-user-ADMIN_STAFF")
    company_id = uuid.uuid4()

    await set_rls_context(db, str(admin_user_id))
    result = await db.execute(
        text("""
            SELECT
                public.nlc_current_user_is_finance_staff() AS is_finance,
                public.nlc_can_view_billing_company(:company_id) AS can_view_billing,
                public.nlc_can_submit_payment_company(:company_id) AS can_submit_payment,
                public.nlc_can_manage_billing_company(:company_id) AS can_manage_billing
        """),
        {"company_id": company_id},
    )
    row = result.one()

    assert row.is_finance is True
    assert row.can_view_billing is True
    assert row.can_submit_payment is True
    assert row.can_manage_billing is True
