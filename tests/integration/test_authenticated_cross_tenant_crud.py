"""Authenticated tenant-A versus tenant-B CRUD isolation regressions."""

from __future__ import annotations

import uuid
from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.models.database import set_admin_context, set_rls_context

pytestmark = [pytest.mark.integration]


@pytest.mark.asyncio
async def test_signed_app_role_blocks_cross_tenant_select_insert_update_delete(
    db, db_client_user, db_company, db_other_company
):
    """Exercise all four CRUD paths under the real non-BYPASSRLS app role."""
    from app.models.enums import UserRole
    from app.models.user import User

    other_user = User(
        id=uuid.uuid4(),
        email=f"tenant-b-{uuid.uuid4().hex[:10]}@nlctest.com",
        full_name="Tenant B Owner",
        password_hash="!test-no-login",
        role=UserRole.CLIENT_DIRECTOR,
        is_active=True,
        totp_enabled=False,
    )
    await set_admin_context(db)
    db.add(other_user)
    await db.flush()

    endpoint_id = uuid.uuid4()
    await db.execute(
        text(
            """
            INSERT INTO webhook_endpoints
                (id, user_id, url, secret, events, is_active, created_at, updated_at)
            VALUES
                (:id, :user_id, 'https://tenant-b.invalid/webhook', 'test-secret',
                 ARRAY['company.updated']::varchar[], TRUE, NOW(), NOW())
            """
        ),
        {"id": endpoint_id, "user_id": other_user.id},
    )

    await set_rls_context(db, str(db_client_user.id))
    identity = await db.execute(text("SELECT current_user, session_user"))
    current_user, _session_user = identity.one()
    assert current_user == "nlc_app_role"

    # SELECT: Tenant A cannot see Tenant B's company or webhook endpoint.
    foreign_company = await db.execute(
        text("SELECT id FROM companies WHERE id = :company_id"),
        {"company_id": db_other_company.id},
    )
    assert foreign_company.scalar_one_or_none() is None
    foreign_endpoint = await db.execute(
        text("SELECT id FROM webhook_endpoints WHERE id = :endpoint_id"),
        {"endpoint_id": endpoint_id},
    )
    assert foreign_endpoint.scalar_one_or_none() is None

    # INSERT: a Tenant A actor cannot write an activity row against Tenant B.
    with pytest.raises(DBAPIError):
        async with db.begin_nested():
            await db.execute(
                text(
                    """
                    INSERT INTO user_activity_logs
                        (id, user_id, company_id, action, logged_at)
                    VALUES (:id, :user_id, :company_id, 'CROSS_TENANT_INSERT', NOW())
                    """
                ),
                {
                    "id": uuid.uuid4(),
                    "user_id": db_client_user.id,
                    "company_id": db_other_company.id,
                },
            )

    # UPDATE: RLS filters the foreign row; no row is changed.
    update_result = await db.execute(
        text(
            "UPDATE companies SET company_name = 'TENANT_A_FORGED_WRITE' "
            "WHERE id = :company_id"
        ),
        {"company_id": db_other_company.id},
    )
    assert update_result.rowcount == 0

    # DELETE: webhook_endpoints grants DELETE to the app role, so this tests
    # row-level tenant filtering rather than a table-level privilege denial.
    delete_result = await db.execute(
        text("DELETE FROM webhook_endpoints WHERE id = :endpoint_id"),
        {"endpoint_id": endpoint_id},
    )
    assert delete_result.rowcount == 0

    # Verify both target records remain unchanged under the signed admin
    # principal; the test transaction is rolled back by the db fixture.
    await set_admin_context(db)
    company_name = await db.execute(
        text("SELECT company_name FROM companies WHERE id = :company_id"),
        {"company_id": db_other_company.id},
    )
    assert company_name.scalar_one() == db_other_company.company_name
    endpoint_exists = await db.execute(
        text("SELECT count(*) FROM webhook_endpoints WHERE id = :endpoint_id"),
        {"endpoint_id": endpoint_id},
    )
    assert endpoint_exists.scalar_one() == 1


@pytest.mark.asyncio
async def test_authenticated_api_uses_database_membership_not_jwt_company_claims(
    api_client_as_user, db_for_user
):
    """A signed-in client may read Tenant A but not Tenant B, even if JWT claims B."""
    from app.core.security import create_access_token
    from app.models.company import Company, CompanyUserAccess
    from app.models.database import set_admin_context, set_rls_context
    from app.models.user import User

    user_id = uuid.uuid5(uuid.NAMESPACE_DNS, "nlc-test-user-CLIENT_DIRECTOR")
    user = await db_for_user.get(User, user_id)
    assert user is not None

    company_a = Company(
        id=uuid.uuid4(),
        company_name="Authenticated Tenant A Ltd",
        registration_number=f"AUTH-A-{uuid.uuid4().hex[:8].upper()}",
        company_type="PRIVATE_LIMITED",
        incorporation_date=date(2024, 1, 1),
        financial_year_end=date(2024, 12, 31),
        registered_address="Tenant A, Dhaka",
        member_count=2,
        is_active=True,
        is_dormant=False,
        is_fdi_registered=False,
    )
    company_b = Company(
        id=uuid.uuid4(),
        company_name="Authenticated Tenant B Ltd",
        registration_number=f"AUTH-B-{uuid.uuid4().hex[:8].upper()}",
        company_type="PRIVATE_LIMITED",
        incorporation_date=date(2024, 1, 1),
        financial_year_end=date(2024, 12, 31),
        registered_address="Tenant B, Dhaka",
        member_count=2,
        is_active=True,
        is_dormant=False,
        is_fdi_registered=False,
    )

    await set_admin_context(db_for_user)
    db_for_user.add_all([company_a, company_b])
    await db_for_user.flush()
    db_for_user.add(
        CompanyUserAccess(
            user_id=user_id,
            company_id=company_a.id,
            can_edit=True,
            can_view_financials=True,
            is_active=True,
        )
    )
    await db_for_user.flush()
    await set_rls_context(db_for_user, str(user_id))

    # Deliberately claim access to both tenants. The API must consult the
    # persisted active CompanyUserAccess row, not trust company_ids in the JWT.
    token = create_access_token(
        {
            "sub": str(user_id),
            "user_id": str(user_id),
            "email": user.email,
            "role": "CLIENT_DIRECTOR",
            "company_ids": [str(company_a.id), str(company_b.id)],
        }
    )
    headers = {"Authorization": f"Bearer {token}"}

    own_response = await api_client_as_user.get(
        f"/api/v1/companies/{company_a.id}", headers=headers
    )
    assert own_response.status_code == 200, own_response.text

    foreign_response = await api_client_as_user.get(
        f"/api/v1/companies/{company_b.id}", headers=headers
    )
    assert foreign_response.status_code in (403, 404), foreign_response.text

    forged_identity = create_access_token(
        {
            "sub": str(uuid.uuid4()),
            "user_id": str(uuid.uuid4()),
            "email": "forged-admin@nlctest.invalid",
            "role": "SUPER_ADMIN",
            "company_ids": [str(company_a.id), str(company_b.id)],
        }
    )
    forged_response = await api_client_as_user.get(
        f"/api/v1/companies/{company_b.id}",
        headers={"Authorization": f"Bearer {forged_identity}"},
    )
    assert forged_response.status_code == 401, forged_response.text
