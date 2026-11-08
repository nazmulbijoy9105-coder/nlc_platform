"""Verify the application pool connects as the restricted PostgreSQL role."""
from __future__ import annotations

import os

import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_runtime_database_pool_uses_nlc_app_role_and_rejects_unsigned_admin():
    if os.getenv("REQUIRE_RLS_APP_ROLE", "").lower() != "true":
        pytest.skip("runtime-role connection check is enabled in the production-like CI job")

    from app.models.database import AsyncSessionLocal, verify_runtime_database_role

    # Exercise the same fail-fast check invoked by the FastAPI lifespan.
    await verify_runtime_database_role()

    async with AsyncSessionLocal() as session:
        role_result = await session.execute(text("""
            SELECT current_user AS role_name,
                   r.rolsuper AS is_superuser,
                   r.rolbypassrls AS bypasses_rls,
                   r.rolcreatedb AS can_create_databases,
                   r.rolcreaterole AS can_create_roles,
                   r.rolinherit AS inherits_privileges,
                   r.rolreplication AS can_replicate
              FROM pg_roles r
             WHERE r.rolname = current_user
        """))
        role = role_result.one()
        assert role.role_name == "nlc_app_role"
        assert role.is_superuser is False
        assert role.bypasses_rls is False
        assert role.can_create_databases is False
        assert role.can_create_roles is False
        assert role.inherits_privileges is False
        assert role.can_replicate is False

        # No identity means no tenant rows. A caller-controlled ADMIN GUC
        # without the database HMAC signature must remain unauthenticated.
        await session.execute(text("""
            SELECT set_config('app.current_user_id', '', true),
                   set_config('app.current_user_signature', '', true)
        """))
        anonymous = await session.execute(text("""
            SELECT public.nlc_current_user_principal() AS principal,
                   public.nlc_current_user_id() AS user_id,
                   (SELECT count(*) FROM public.companies) AS visible_companies
        """))
        anonymous_row = anonymous.one()
        assert anonymous_row.principal is None
        assert anonymous_row.user_id is None
        assert anonymous_row.visible_companies == 0

        await session.execute(text("""
            SELECT set_config('app.current_user_id', 'ADMIN', true),
                   set_config('app.current_user_signature', '', true)
        """))
        forged = await session.execute(text("""
            SELECT public.nlc_current_user_principal() AS principal,
                   public.nlc_current_user_is_staff() AS is_staff,
                   (SELECT count(*) FROM public.companies) AS visible_companies
        """))
        forged_row = forged.one()
        assert forged_row.principal is None
        assert forged_row.is_staff is False
        assert forged_row.visible_companies == 0
