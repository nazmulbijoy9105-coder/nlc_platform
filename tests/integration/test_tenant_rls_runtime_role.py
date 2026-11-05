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

    # Membership revocation is a privileged administrative write. Perform
    # it under the signed service principal, then re-check access as the user.
    await set_admin_context(db)
    result = await db.execute(
        text(
            "UPDATE company_user_access SET is_active = FALSE "
            "WHERE user_id = :user_id AND company_id = :company_id"
        ),
        {"user_id": db_client_user.id, "company_id": db_company.id},
    )
    assert result.rowcount == 1

    await set_rls_context(db, str(db_client_user.id))
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
async def test_legal_evidence_tables_are_readable_by_members_but_writable_only_by_staff(db):
    evidence_tables = {
        "articles_verifications": {
            "articles_verifications_company_read",
            "articles_verifications_staff_insert",
            "articles_verifications_staff_update",
        },
        "articles_verification_events": {
            "articles_verification_events_company_read",
            "articles_verification_events_staff_insert",
        },
        "agm_evidence_verifications": {
            "agm_evidence_verifications_company_read",
            "agm_evidence_verifications_staff_insert",
            "agm_evidence_verifications_staff_update",
        },
        "agm_evidence_verification_events": {
            "agm_evidence_verification_events_company_read",
            "agm_evidence_verification_events_staff_insert",
        },
    }
    for table, expected_names in evidence_tables.items():
        result = await db.execute(
            text(
                "SELECT policyname, cmd, qual, with_check "
                "FROM pg_policies WHERE schemaname = 'public' AND tablename = :table"
            ),
            {"table": table},
        )
        policies = {row[0]: row for row in result.fetchall()}
        assert set(policies) == expected_names

        read_policy = policies[f"{table}_company_read"]
        assert read_policy[1] == "SELECT"
        assert "nlc_can_access_company" in (read_policy[2] or "")

        insert_policy = policies[f"{table}_staff_insert"]
        assert insert_policy[1] == "INSERT"
        assert "nlc_current_user_is_staff" in (insert_policy[3] or "")

        if not table.endswith("_events"):
            update_policy = policies[f"{table}_staff_update"]
            assert update_policy[1] == "UPDATE"
            assert "nlc_current_user_is_staff" in (update_policy[2] or "")
            assert "nlc_current_user_is_staff" in (update_policy[3] or "")


@pytest.mark.asyncio
async def test_activity_service_inserts_with_signed_actor_and_tenant(
    db, db_client_user, db_company
):
    from app.services.notification_service import ActivityService

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
async def test_signed_admin_activity_insert_does_not_cast_admin_sentinel_to_uuid(
    db, db_client_user, db_company
):
    from app.services.notification_service import ActivityService

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
