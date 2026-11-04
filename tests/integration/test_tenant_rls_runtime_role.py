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
    await db.execute(text("SET LOCAL ROLE nlc_app_role"))

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
