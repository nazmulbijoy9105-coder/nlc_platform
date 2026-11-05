"""Exercise tenant policies as the non-bypass application database role."""
from __future__ import annotations

import pytest
from sqlalchemy import text

from app.models.database import set_rls_context

pytestmark = [pytest.mark.integration]


@pytest.mark.asyncio
async def test_non_bypass_app_role_sees_only_active_member_companies(
    db,
    db_client_user,
    db_company,
    db_other_company,
):
    await set_rls_context(db, str(db_client_user.id))
    active_role = await db.execute(text("SELECT current_user"))
    assert active_role.scalar_one() == "nlc_app_role"

    visible = await db.execute(
        text("SELECT id FROM companies ORDER BY id")
    )
    visible_ids = {str(row[0]) for row in visible.fetchall()}

    assert str(db_company.id) in visible_ids
    assert str(db_other_company.id) not in visible_ids

    other_memberships = await db.execute(
        text(
            "SELECT count(*) FROM company_user_access "
            "WHERE company_id = :company_id"
        ),
        {"company_id": db_other_company.id},
    )
    assert other_memberships.scalar_one() == 0


@pytest.mark.asyncio
async def test_app_role_has_no_schema_creation_or_truncate_privilege(db):
    role = await db.execute(
        text(
            "SELECT rolsuper, rolbypassrls FROM pg_roles "
            "WHERE rolname = 'nlc_app_role'"
        )
    )
    is_superuser, bypasses_rls = role.one()
    assert is_superuser is False
    assert bypasses_rls is False

    can_create = await db.execute(
        text("SELECT has_schema_privilege('nlc_app_role', 'public', 'CREATE')")
    )
    can_truncate = await db.execute(
        text(
            "SELECT has_table_privilege("
            "'nlc_app_role', 'public.companies', 'TRUNCATE')"
        )
    )
    assert can_create.scalar_one() is False
    assert can_truncate.scalar_one() is False

    secret_schema = await db.execute(
        text("SELECT has_schema_privilege('nlc_app_role', 'nlc_private', 'USAGE')")
    )
    secret_table = await db.execute(
        text("SELECT has_table_privilege('nlc_app_role', 'nlc_private.rls_signing_key', 'SELECT')")
    )
    assert secret_schema.scalar_one() is False
    assert secret_table.scalar_one() is False


@pytest.mark.asyncio
async def test_valid_signed_admin_principal_is_recognized_as_staff(db):
    from app.models.database import set_admin_context

    await set_admin_context(db)
    active_role = await db.execute(text("SELECT current_user"))
    assert active_role.scalar_one() == "nlc_app_role"
    result = await db.execute(
        text("SELECT public.nlc_current_user_is_staff()")
    )
    assert result.scalar_one() is True


@pytest.mark.asyncio
async def test_forged_admin_principal_without_matching_signature_is_rejected(
    db, db_client_user
):
    await set_rls_context(db, str(db_client_user.id))
    await db.execute(
        text("SELECT set_config('app.current_user_id', 'ADMIN', true)")
    )
    result = await db.execute(
        text("SELECT public.nlc_current_user_is_staff()")
    )
    assert result.scalar_one() is False


@pytest.mark.asyncio
async def test_admin_sentinel_cannot_grant_staff_access(db, db_client_user):
    """A caller-controlled GUC value must never grant privileged staff access."""
    await set_rls_context(db, str(db_client_user.id))
    await db.execute(text("SET LOCAL ROLE nlc_app_role"))
    await db.execute(
        text("SELECT set_config('app.current_user_id', 'ADMIN', true)")
    )
    result = await db.execute(
        text("SELECT public.nlc_current_user_is_staff()")
    )
    assert result.scalar_one() is False


@pytest.mark.asyncio
async def test_identity_guc_cannot_be_replayed_for_another_user(db, db_client_user, db_other_company):
    """A signature for one principal must not authorize another UUID."""
    import uuid

    await set_rls_context(db, str(db_client_user.id))
    await db.execute(text("SET LOCAL ROLE nlc_app_role"))
    forged_user_id = str(uuid.uuid4())
    await db.execute(
        text("SELECT set_config('app.current_user_id', :uid, true)"),
        {"uid": forged_user_id},
    )
    result = await db.execute(text("SELECT public.nlc_current_user_id()"))
    assert result.scalar_one() is None
    access = await db.execute(
        text("SELECT public.nlc_can_access_company(:company_id)"),
        {"company_id": db_other_company.id},
    )
    assert access.scalar_one() is False


@pytest.mark.asyncio
async def test_unsigned_identity_and_forged_admin_are_rejected(db, db_client_user):
    await set_rls_context(db, str(db_client_user.id))
    await db.execute(text("SET LOCAL ROLE nlc_app_role"))
    await db.execute(text("SELECT set_config('app.current_user_signature', '', true)"))
    valid = await db.execute(text("SELECT public.nlc_current_user_context_valid()"))
    assert valid.scalar_one() is False
    await db.execute(text("SELECT set_config('app.current_user_id', 'ADMIN', true)"))
    await db.execute(text("SELECT set_config('app.current_user_signature', repeat('0', 64), true)"))
    staff = await db.execute(text("SELECT public.nlc_current_user_is_staff()"))
    assert staff.scalar_one() is False


@pytest.mark.asyncio
async def test_valid_signed_identity_resolves_to_authenticated_user(db, db_client_user):
    await set_rls_context(db, str(db_client_user.id))
    await db.execute(text("SET LOCAL ROLE nlc_app_role"))
    valid = await db.execute(text("SELECT public.nlc_current_user_context_valid()"))
    resolved = await db.execute(text("SELECT public.nlc_current_user_id()"))
    assert valid.scalar_one() is True
    assert str(resolved.scalar_one()) == str(db_client_user.id)


@pytest.mark.asyncio
async def test_revoked_membership_stops_company_access_immediately(db, db_client_user, db_company):
    from sqlalchemy import text

    await set_rls_context(db, str(db_client_user.id))
    await db.execute(
        text(
            "UPDATE company_user_access SET is_active = FALSE "
            "WHERE user_id = :user_id AND company_id = :company_id"
        ),
        {"user_id": db_client_user.id, "company_id": db_company.id},
    )
    await db.execute(text("SET LOCAL ROLE nlc_app_role"))
    result = await db.execute(
        text("SELECT public.nlc_can_access_company(:company_id)"),
        {"company_id": db_company.id},
    )
    assert result.scalar_one() is False


@pytest.mark.asyncio
async def test_deactivated_user_loses_database_tenant_access(db, db_client_user, db_company):
    from app.models.database import set_admin_context

    # Only a trusted staff/service context may change activation state.
    await set_admin_context(db)
    await db.execute(
        text("UPDATE users SET is_active = FALSE WHERE id = :user_id"),
        {"user_id": db_client_user.id},
    )
    await set_rls_context(db, str(db_client_user.id))
    await db.execute(text("SET LOCAL ROLE nlc_app_role"))
    result = await db.execute(
        text("SELECT public.nlc_can_access_company(:company_id)"),
        {"company_id": db_company.id},
    )
    assert result.scalar_one() is False


@pytest.mark.asyncio
async def test_activity_log_has_exactly_one_actor_and_tenant_policy(db):
    result = await db.execute(text(
        "SELECT count(*), bool_or(policyname = 'user_activity_logs_actor_tenant') "
        "FROM pg_policies "
        "WHERE schemaname = 'public' AND tablename = 'user_activity_logs'"
    ))
    policy_count, has_strict_policy = result.one()
    assert policy_count == 1
    assert has_strict_policy is True


@pytest.mark.asyncio
async def test_activity_service_inserts_with_signed_actor_and_keeps_transaction_usable(
    db, db_client_user, db_company
):
    """The real service path must insert under signed user+tenant RLS context."""
    from app.models.infrastructure import UserActivityLog
    from app.services.notification_service import ActivityService

    action = "INTEGRATION_ACTIVITY_INSERT_REGRESSION"
    await set_rls_context(db, str(db_client_user.id))
    await ActivityService(db).log(
        user_id=db_client_user.id,
        company_id=db_company.id,
        action=action,
        resource_type="IntegrationTest",
        description="Signed actor and tenant insert regression",
    )

    # A successful query after flush proves the session transaction was not
    # left aborted by a swallowed PostgreSQL/RLS error.
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
