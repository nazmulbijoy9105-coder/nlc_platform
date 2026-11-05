"""Runtime regression tests for signed PostgreSQL identity and tenant RLS."""
from __future__ import annotations

import pytest
from sqlalchemy import text

from app.models.database import set_admin_context, set_rls_context
from app.services.notification_service import ActivityService

pytestmark = [pytest.mark.integration]


@pytest.mark.asyncio
async def test_runtime_role_is_non_bypass_and_has_no_dangerous_privileges(db):
    await set_rls_context(db, "00000000-0000-0000-0000-000000000001")
    role = await db.execute(
        text(
            "SELECT current_user, r.rolsuper, r.rolbypassrls "
            "FROM pg_roles r WHERE r.rolname = current_user"
        )
    )
    role_name, is_superuser, bypasses_rls = role.one()
    assert role_name == "nlc_app_role"
    assert is_superuser is False
    assert bypasses_rls is False

    for privilege in ("TRUNCATE", "TRIGGER", "REFERENCES"):
        result = await db.execute(
            text(
                "SELECT has_table_privilege('nlc_app_role', "
                "'public.companies', :privilege)"
            ),
            {"privilege": privilege},
        )
        assert result.scalar_one() is False


@pytest.mark.asyncio
async def test_activity_log_has_exactly_one_strict_actor_tenant_policy(db):
    result = await db.execute(
        text(
            "SELECT policyname, cmd, qual, with_check "
            "FROM pg_policies "
            "WHERE schemaname = 'public' AND tablename = 'user_activity_logs'"
        )
    )
    policies = result.fetchall()
    assert len(policies) == 1
    policy_name, command, using_expression, check_expression = policies[0]
    assert policy_name == "user_activity_logs_actor_tenant"
    assert command == "ALL"
    assert using_expression
    assert check_expression
    for expression in (using_expression, check_expression):
        assert "nlc_current_user_is_staff" in expression
        assert "nlc_current_user_id" in expression
        assert "nlc_can_access_company" in expression


@pytest.mark.asyncio
async def test_activity_service_inserts_with_signed_actor_and_tenant(
    db, db_client_user, db_company
):
    action = "SIGNED_RLS_ACTIVITY_INSERT"
    await set_rls_context(db, str(db_client_user.id))
    await ActivityService(db).log(
        user_id=db_client_user.id,
        company_id=db_company.id,
        action=action,
        resource_type="IntegrationTest",
        description="ActivityService signed actor and tenant regression",
    )

    result = await db.execute(
        text(
            "SELECT count(*) FROM user_activity_logs "
            "WHERE user_id = :user_id AND company_id = :company_id AND action = :action"
        ),
        {
            "user_id": db_client_user.id,
            "company_id": db_company.id,
            "action": action,
        },
    )
    assert result.scalar_one() == 1


@pytest.mark.asyncio
async def test_signed_admin_can_insert_activity_without_uuid_cast_failure(
    db, db_client_user, db_company
):
    action = "SIGNED_ADMIN_ACTIVITY_INSERT"
    await set_admin_context(db)
    staff = await db.execute(text("SELECT public.nlc_current_user_is_staff()"))
    assert staff.scalar_one() is True

    await ActivityService(db).log(
        user_id=db_client_user.id,
        company_id=db_company.id,
        action=action,
        resource_type="IntegrationTest",
        description="Signed ADMIN principal must not be cast to UUID",
    )
    result = await db.execute(
        text(
            "SELECT count(*) FROM user_activity_logs "
            "WHERE user_id = :user_id AND company_id = :company_id AND action = :action"
        ),
        {
            "user_id": db_client_user.id,
            "company_id": db_company.id,
            "action": action,
        },
    )
    assert result.scalar_one() == 1


@pytest.mark.asyncio
async def test_forged_admin_guc_does_not_escalate_signed_user(db, db_client_user, db_other_company):
    await set_rls_context(db, str(db_client_user.id))
    await db.execute(
        text("SELECT set_config('app.current_user_id', 'ADMIN', true)")
    )

    staff = await db.execute(text("SELECT public.nlc_current_user_is_staff()"))
    assert staff.scalar_one() is False

    access = await db.execute(
        text("SELECT public.nlc_can_access_company(:company_id)"),
        {"company_id": db_other_company.id},
    )
    assert access.scalar_one() is False


@pytest.mark.asyncio
async def test_user_sees_only_companies_with_active_membership(
    db, db_client_user, db_company, db_other_company
):
    await set_rls_context(db, str(db_client_user.id))
    visible = await db.execute(text("SELECT id FROM companies"))
    visible_ids = {str(row[0]) for row in visible.fetchall()}
    assert str(db_company.id) in visible_ids
    assert str(db_other_company.id) not in visible_ids


@pytest.mark.asyncio
async def test_revoked_membership_and_deactivated_user_fail_closed(
    db, db_client_user, db_company
):
    await set_admin_context(db)
    await db.execute(
        text(
            "UPDATE company_user_access SET is_active = FALSE "
            "WHERE user_id = :user_id AND company_id = :company_id"
        ),
        {"user_id": db_client_user.id, "company_id": db_company.id},
    )
    await db.execute(
        text("UPDATE users SET is_active = FALSE WHERE id = :user_id"),
        {"user_id": db_client_user.id},
    )

    await set_rls_context(db, str(db_client_user.id))
    access = await db.execute(
        text("SELECT public.nlc_can_access_company(:company_id)"),
        {"company_id": db_company.id},
    )
    assert access.scalar_one() is False


@pytest.mark.asyncio
async def test_view_only_member_can_read_but_cannot_mutate_tenant_company(db, db_company):
    import uuid

    from app.models.company import CompanyUserAccess
    from app.models.enums import UserRole
    from app.models.user import User

    view_user = User(
        id=uuid.uuid4(),
        email=f"view-only-{uuid.uuid4().hex[:8]}@nlctest.com",
        full_name="View Only Tenant User",
        password_hash="!test-no-login",
        role=UserRole.CLIENT_VIEW_ONLY,
        is_active=True,
        totp_enabled=False,
    )
    db.add(view_user)
    await db.flush()
    db.add(
        CompanyUserAccess(
            user_id=view_user.id,
            company_id=db_company.id,
            can_edit=False,
            can_view_financials=False,
            is_active=True,
        )
    )
    await db.flush()

    await set_rls_context(db, str(view_user.id))
    visible = await db.execute(
        text("SELECT company_name FROM companies WHERE id = :company_id"),
        {"company_id": db_company.id},
    )
    assert visible.scalar_one() == db_company.company_name

    update_result = await db.execute(
        text(
            "UPDATE companies SET company_name = :new_name WHERE id = :company_id"
        ),
        {"new_name": "Unauthorized Mutation Ltd", "company_id": db_company.id},
    )
    assert update_result.rowcount == 0

    unchanged = await db.execute(
        text("SELECT company_name FROM companies WHERE id = :company_id"),
        {"company_id": db_company.id},
    )
    assert unchanged.scalar_one() == db_company.company_name
