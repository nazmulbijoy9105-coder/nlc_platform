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


@pytest.mark.asyncio
async def test_client_cannot_read_update_delete_or_grant_access_to_another_tenant(
    db, db_company, db_other_company
):
    from sqlalchemy import delete, select, update

    from app.models.company import Company, CompanyUserAccess

    client = _user(UserRole.CLIENT_DIRECTOR, "tenant-a-client")
    await set_admin_context(db)
    db.add(client)
    db.add(CompanyUserAccess(
        user_id=client.id,
        company_id=db_company.id,
        can_edit=True,
        can_view_financials=True,
        is_active=True,
    ))
    await db.flush()

    await set_rls_context(db, str(client.id))
    visible = await db.execute(
        select(Company.id).where(Company.id == db_other_company.id)
    )
    assert visible.scalar_one_or_none() is None

    changed = await db.execute(
        update(Company)
        .where(Company.id == db_other_company.id)
        .values(company_name="ATTACKER MODIFIED")
    )
    assert changed.rowcount == 0

    deleted = await db.execute(
        delete(Company).where(Company.id == db_other_company.id)
    )
    assert deleted.rowcount == 0

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
                    "user_id": client.id,
                },
            )


@pytest.mark.asyncio
async def test_revoked_membership_overrides_stale_jwt_company_ids(db, db_company):
    from fastapi import HTTPException
    from sqlalchemy import delete

    from app.core.dependencies import TokenData, require_company_access
    from app.models.company import CompanyUserAccess

    client = _user(UserRole.CLIENT_DIRECTOR, "revoked-client")
    await set_admin_context(db)
    db.add(client)
    membership = CompanyUserAccess(
        user_id=client.id,
        company_id=db_company.id,
        can_edit=True,
        can_view_financials=True,
        is_active=True,
    )
    db.add(membership)
    await db.flush()

    # The JWT still contains the old company id; the database membership is revoked.
    await db.execute(
        delete(CompanyUserAccess).where(
            CompanyUserAccess.user_id == client.id,
            CompanyUserAccess.company_id == db_company.id,
        )
    )
    await db.flush()
    await set_rls_context(db, str(client.id))
    token = TokenData(
        user_id=str(client.id),
        email=client.email,
        role=UserRole.CLIENT_DIRECTOR.value,
        company_ids=[str(db_company.id)],
    )
    with pytest.raises(HTTPException) as exc:
        await require_company_access()(
            company_id=db_company.id,
            token=token,
            db=db,
        )
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_forged_user_identity_and_jwt_role_escalation_fail_closed(db):
    from fastapi import HTTPException

    from app.core.dependencies import TokenData, require_company_access, require_roles

    client = _user(UserRole.CLIENT_DIRECTOR, "real-client")
    await set_admin_context(db)
    db.add(client)
    await db.flush()

    # A forged subject has no corresponding active database identity.
    forged_id = uuid.uuid4()
    await set_rls_context(db, str(forged_id))
    forged = TokenData(
        user_id=str(forged_id),
        email="forged@nlctest.com",
        role=UserRole.CLIENT_DIRECTOR.value,
        company_ids=[],
    )
    with pytest.raises(HTTPException) as missing:
        await require_company_access()(
            company_id=uuid.uuid4(),
            token=forged,
            db=db,
        )
    assert missing.value.status_code == 401

    # A signed JWT claiming SUPER_ADMIN cannot override the database role.
    await set_rls_context(db, str(client.id))
    escalated = TokenData(
        user_id=str(client.id),
        email=client.email,
        role=UserRole.SUPER_ADMIN.value,
        company_ids=[],
    )
    with pytest.raises(HTTPException) as role_error:
        await require_roles(UserRole.SUPER_ADMIN)(token=escalated, db=db)
    assert role_error.value.status_code == 401


@pytest.mark.asyncio
async def test_score_history_is_not_mutable_by_application_role(db, db_company):
    from datetime import UTC, date, datetime

    from app.models.compliance import ComplianceScoreHistory
    from app.models.enums import RiskBand

    await set_admin_context(db)
    history = ComplianceScoreHistory(
        id=uuid.uuid4(),
        company_id=db_company.id,
        score=85,
        risk_band=RiskBand.GREEN,
        snapshot_month=date(2026, 11, 1),
        calculated_at=datetime.now(UTC),
        score_hash="a" * 64,
        engine_version="security-cert-test",
    )
    db.add(history)
    await db.flush()

    # The runtime application role must have no UPDATE or DELETE privilege.
    with pytest.raises(DBAPIError):
        async with db.begin_nested():
            await db.execute(
                text("UPDATE public.compliance_score_history SET score=1 WHERE id=:id"),
                {"id": history.id},
            )
    with pytest.raises(DBAPIError):
        async with db.begin_nested():
            await db.execute(
                text("DELETE FROM public.compliance_score_history WHERE id=:id"),
                {"id": history.id},
            )

    trigger = await db.execute(
        text("""
            SELECT EXISTS (
                SELECT 1 FROM pg_trigger
                WHERE tgrelid='public.compliance_score_history'::regclass
                  AND tgname='trg_compliance_score_history_append_only'
                  AND NOT tgisinternal
            )
        """)
    )
    assert trigger.scalar_one() is True



@pytest.mark.asyncio
async def test_every_company_scoped_table_enforces_rls_and_has_a_policy(db):
    """New tenant tables cannot silently ship without forced RLS."""
    result = await db.execute(
        text("""
            SELECT
                c.relname AS table_name,
                c.relrowsecurity AS rls_enabled,
                c.relforcerowsecurity AS force_rls,
                count(p.policyname) AS policy_count
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            JOIN pg_attribute a
              ON a.attrelid = c.oid
             AND a.attname = 'company_id'
             AND NOT a.attisdropped
            LEFT JOIN pg_policies p
              ON p.schemaname = n.nspname
             AND p.tablename = c.relname
            WHERE n.nspname = 'public'
              AND c.relkind = 'r'
            GROUP BY c.relname, c.relrowsecurity, c.relforcerowsecurity
            ORDER BY c.relname
        """)
    )
    rows = result.fetchall()
    assert rows, "Tenant table inventory must not be empty"
    violations = [
        {
            "table": row.table_name,
            "rls_enabled": row.rls_enabled,
            "force_rls": row.force_rls,
            "policy_count": row.policy_count,
        }
        for row in rows
        if not row.rls_enabled or not row.force_rls or row.policy_count < 1
    ]
    assert not violations, f"Tenant tables missing forced RLS/policies: {violations!r}"
