"""Real PostgreSQL dashboard tenant-isolation regressions."""
from __future__ import annotations

import pytest

from app.models.database import set_rls_context
from app.services.company_service import CompanyService


@pytest.mark.asyncio
async def test_risk_distribution_aggregates_only_the_authenticated_users_membership(
    db, db_company, db_other_company, db_client_user
):
    """A real client with one membership must not see the second tenant's band."""
    await set_rls_context(db, str(db_client_user.id))

    rows = await CompanyService(db).get_risk_distribution(db_client_user.id)

    assert sum(int(row["company_count"]) for row in rows) == 1
    assert len(rows) == 1
    assert str(rows[0]["risk_band"]) == "GREEN"
    assert float(rows[0]["percentage"]) == 100.0


@pytest.mark.asyncio
async def test_upcoming_deadlines_requires_authenticated_membership_scope(
    db, db_client_user
):
    """The user-scoped service must reject an omitted identity before querying."""
    await set_rls_context(db, str(db_client_user.id))

    with pytest.raises(ValueError, match="user_id is required"):
        await CompanyService(db).get_upcoming_deadlines()

@pytest.mark.asyncio
async def test_legal_staff_dashboard_includes_only_assigned_company_risk_and_deadlines(
    db, db_company, db_other_company
):
    import uuid
    from datetime import date, timedelta

    from app.models.filings import AGM
    from app.models.enums import UserRole
    from app.models.user import User

    await set_admin_context(db)
    legal_user = User(
        id=uuid.uuid4(),
        email=f"dashboard-legal-{uuid.uuid4().hex[:8]}@nlctest.com",
        full_name="Assigned Dashboard Legal Staff",
        password_hash="!test-no-login",
        role=UserRole.LEGAL_STAFF,
        is_active=True,
        totp_enabled=False,
    )
    db.add(legal_user)
    await db.flush()
    db_company.assigned_staff_id = legal_user.id
    due_date = date.today() + timedelta(days=10)
    db.add_all([
        AGM(
            company_id=db_company.id,
            financial_year=date.today().year - 1,
            agm_deadline=due_date,
            agm_held=False,
        ),
        AGM(
            company_id=db_other_company.id,
            financial_year=date.today().year - 1,
            agm_deadline=due_date,
            agm_held=False,
        ),
    ])
    await db.flush()

    await set_rls_context(db, str(legal_user.id))
    service = CompanyService(db)
    risk_rows = await service.get_risk_distribution(
        legal_user.id, include_assigned_staff=True
    )
    assert sum(int(row["company_count"]) for row in risk_rows) == 1

    deadlines = await service.get_upcoming_deadlines(
        days_ahead=30,
        user_id=legal_user.id,
        include_assigned_staff=True,
    )
    assert deadlines
    assert {row["company_id"] for row in deadlines} == {db_company.id}

