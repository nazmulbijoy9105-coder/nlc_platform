"""Exercise dashboard KPI role scope against PostgreSQL RLS, not mocked services."""

from __future__ import annotations

import uuid

import pytest

from app.models.database import set_rls_context
from app.models.enums import UserRole
from app.models.user import User
from app.services.compliance_service import ComplianceService


pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_super_admin_kpis_include_the_authorized_portfolio(
    db, db_company, db_other_company, db_super_admin
):
    await set_rls_context(db, str(db_super_admin.id))

    result = await ComplianceService(db).get_dashboard_kpis()

    assert result["total_companies"] >= 2
    assert result["not_evaluated_count"] >= 2 or result["green_count"] + result["yellow_count"] + result["red_black_count"] >= 2


@pytest.mark.asyncio
async def test_admin_staff_kpis_include_the_authorized_portfolio(
    db, db_company, db_other_company, db_user
):
    assert db_user.role == UserRole.ADMIN_STAFF
    await set_rls_context(db, str(db_user.id))

    result = await ComplianceService(db).get_dashboard_kpis()

    assert result["total_companies"] >= 2
    assert result["not_evaluated_count"] >= 2 or result["green_count"] + result["yellow_count"] + result["red_black_count"] >= 2


@pytest.mark.asyncio
async def test_legal_staff_kpis_include_only_assigned_companies(
    db, db_company, db_other_company
):
    legal_user = User(
        id=uuid.uuid4(),
        email=f"kpi-legal-{uuid.uuid4().hex[:10]}@nlctest.com",
        full_name="KPI Legal Staff",
        password_hash="!test-no-login",
        role=UserRole.LEGAL_STAFF,
        is_active=True,
        totp_enabled=False,
    )
    db.add(legal_user)
    # Persist the referenced user before updating the company FK; without
    # this flush PostgreSQL may receive the company UPDATE first.
    await db.flush()
    db_company.assigned_staff_id = legal_user.id
    await db.flush()

    await set_rls_context(db, str(legal_user.id))
    result = await ComplianceService(db).get_dashboard_kpis(user_id=legal_user.id)

    assert result["total_companies"] == 1
