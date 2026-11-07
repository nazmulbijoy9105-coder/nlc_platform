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

