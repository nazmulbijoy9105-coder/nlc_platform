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
