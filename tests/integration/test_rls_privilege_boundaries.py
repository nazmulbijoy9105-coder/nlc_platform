"""Regression tests for staff write scope and company membership RLS."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.models.database import set_admin_context, set_rls_context
from app.models.enums import UserRole
from app.models.user import User

pytestmark = [pytest.mark.integration]


def _user(role: UserRole, label: str) -> User:
    suffix = uuid.uuid4().hex[:10]
    return User(
        id=uuid.uuid4(),
        email=f"{label}-{suffix}@nlctest.com",
        full_name=f"RLS {label}",
        password_hash="!test-no-login",
        role=role,
        is_active=True,
        totp_enabled=False,
    )


@pytest.mark.asyncio
async def test_legal_staff_cannot_grant_unassigned_company_membership_or_edit_other_user(
    db, db_other_company
):
    legal_staff = _user(UserRole.LEGAL_STAFF, "legal-staff")
    target_user = _user(UserRole.CLIENT_VIEW_ONLY, "target-user")

    await set_admin_context(db)
    db.add_all([legal_staff, target_user])
    await db.flush()

    # The legal-staff user has no assignment or existing membership for this
    # company. Staff status alone must not create a tenant access path.
    await set_rls_context(db, str(legal_staff.id))

    with pytest.raises(DBAPIError):
        async with db.begin_nested():
            await db.execute(
                text("""
                    INSERT INTO public.company_user_access
                        (id, company_id, user_id, can_edit,
                         can_view_financials, is_active)
                    VALUES
                        (:id, :company_id, :user_id, true, true, true)
                """),
                {
                    "id": uuid.uuid4(),
                    "company_id": db_other_company.id,
                    "user_id": legal_staff.id,
                },
            )

    visible_memberships = await db.execute(
        text("""
            SELECT count(*)
            FROM public.company_user_access
            WHERE company_id = :company_id
        """),
        {"company_id": db_other_company.id},
    )
    assert visible_memberships.scalar_one() == 0

    visible_user = await db.execute(
        text("SELECT id FROM public.users WHERE id = :target_user_id"),
        {"target_user_id": target_user.id},
    )
    assert visible_user.scalar_one_or_none() is None

    updated = await db.execute(
        text("""
            UPDATE public.users
               SET password_hash = :password_hash
             WHERE id = :target_user_id
        """),
        {
            "password_hash": "attacker-controlled-hash",
            "target_user_id": target_user.id,
        },
    )
    assert updated.rowcount == 0


@pytest.mark.asyncio
async def test_signed_admin_service_principal_can_still_grant_company_membership(
    db, db_company
):
    legal_staff = _user(UserRole.LEGAL_STAFF, "assigned-legal-staff")
    client_user = _user(UserRole.CLIENT_VIEW_ONLY, "client-user")

    await set_admin_context(db)
    db.add_all([legal_staff, client_user])
    await db.flush()

    result = await db.execute(
        text("""
            INSERT INTO public.company_user_access
                (id, company_id, user_id, can_edit,
                 can_view_financials, is_active)
            VALUES
                (:id, :company_id, :user_id, false, false, true)
        """),
        {
            "id": uuid.uuid4(),
            "company_id": db_company.id,
            "user_id": client_user.id,
        },
    )
    assert result.rowcount == 1


@pytest.mark.asyncio
async def test_staff_membership_policies_are_scoped_and_admin_write_is_explicit(db):
    result = await db.execute(
        text("""
            SELECT tablename, policyname, cmd, qual, with_check
            FROM pg_policies
            WHERE schemaname = 'public'
              AND tablename IN ('users', 'company_user_access')
            ORDER BY tablename, policyname
        """)
    )
    policies = result.fetchall()
    by_name = {row.policyname: row for row in policies}

    assert "users_staff_write" not in by_name
    assert "users_self_or_staff_select" not in by_name
    assert "company_user_access_staff_write" not in by_name
    assert by_name["users_self_or_admin_select"].cmd == "SELECT"
    assert "nlc_current_user_id" in by_name["users_self_or_admin_select"].qual
    assert "nlc_current_user_is_rule_admin" in by_name["users_self_or_admin_select"].qual
    assert by_name["users_admin_write"].cmd == "ALL"
    assert "nlc_current_user_is_rule_admin" in by_name["users_admin_write"].qual
    assert by_name["company_user_access_admin_write"].cmd == "ALL"
    assert (
        "nlc_current_user_is_rule_admin"
        in by_name["company_user_access_admin_write"].qual
    )
    assert "company_user_access_scoped_read" in by_name
    assert "nlc_can_access_company" in by_name["company_user_access_scoped_read"].qual
