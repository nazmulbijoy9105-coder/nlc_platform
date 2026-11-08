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
            "SELECT current_user, r.rolsuper, r.rolcreatedb, r.rolcreaterole, "
            "r.rolinherit, r.rolreplication, r.rolbypassrls "
            "FROM pg_roles r WHERE r.rolname = current_user"
        )
    )
    (
        role_name,
        is_superuser,
        can_create_db,
        can_create_role,
        inherits_roles,
        can_replicate,
        bypasses_rls,
    ) = role.one()
    assert role_name == "nlc_app_role"
    assert is_superuser is False
    assert can_create_db is False
    assert can_create_role is False
    assert inherits_roles is False
    assert can_replicate is False
    assert bypasses_rls is False

    memberships = await db.execute(
        text(
            "SELECT count(*) FROM pg_auth_members m "
            "JOIN pg_roles granted_role ON granted_role.oid = m.roleid "
            "JOIN pg_roles member_role ON member_role.oid = m.member "
            "WHERE member_role.rolname IN ('nlc_app_role', 'nlc_ci_audit_role') "
            "OR (granted_role.rolname IN ('nlc_app_role', 'nlc_ci_audit_role') "
            "AND NOT (member_role.rolsuper OR member_role.rolbypassrls))"
        )
    )
    assert memberships.scalar_one() == 0

    audit_role = await db.execute(
        text(
            "SELECT rolcanlogin, rolsuper, rolcreatedb, rolcreaterole, "
            "rolinherit, rolreplication, rolbypassrls "
            "FROM pg_roles WHERE rolname = 'nlc_ci_audit_role'"
        )
    )
    assert audit_role.one() == (True, False, False, False, False, False, False)

    for privilege in ("TRUNCATE", "TRIGGER", "REFERENCES"):
        result = await db.execute(
            text(
                "SELECT has_table_privilege('nlc_app_role', "
                "'public.companies', :privilege)"
            ),
            {"privilege": privilege},
        )
        assert result.scalar_one() is False

    dangerous_public_privileges = await db.execute(
        text(
            """
            SELECT c.relname AS relation_name, p.privilege
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            CROSS JOIN (VALUES ('TRUNCATE'), ('REFERENCES'), ('TRIGGER')) AS p(privilege)
            WHERE n.nspname = 'public'
              AND c.relkind IN ('r', 'p', 'v', 'm', 'f')
              AND has_table_privilege('nlc_app_role', c.oid, p.privilege)
            ORDER BY relation_name, p.privilege
            """
        )
    )
    assert dangerous_public_privileges.fetchall() == []
    schema_create = await db.execute(
        text("SELECT has_schema_privilege('nlc_app_role', 'public', 'CREATE')")
    )
    assert schema_create.scalar_one() is False


@pytest.mark.asyncio
async def test_runtime_pool_connects_as_nlc_app_role_and_rejects_forged_admin():
    from app.models.database import AsyncSessionLocal, verify_runtime_database_role

    await verify_runtime_database_role()
    async with AsyncSessionLocal() as session:
        identity = await session.execute(
            text("SELECT session_user, current_user, r.rolsuper, r.rolbypassrls "
                 "FROM pg_roles r WHERE r.rolname = current_user")
        )
        session_user, current_user, is_superuser, bypasses_rls = identity.one()
        assert session_user == "nlc_app_role"
        assert current_user == "nlc_app_role"
        assert is_superuser is False
        assert bypasses_rls is False

        # An ordinary runtime SQL session can set custom GUCs, but cannot
        # manufacture the HMAC signature required for the ADMIN principal.
        # Reproduce the exact production exploit: set only the unsigned ADMIN
        # GUC. The missing signature must make the principal invalid.
        await session.execute(
            text("SELECT set_config('app.current_user_id', 'ADMIN', true)")
        )
        principal = await session.execute(
            text("SELECT public.nlc_current_user_principal()")
        )
        assert principal.scalar_one_or_none() is None

        staff = await session.execute(
            text("SELECT public.nlc_current_user_is_staff()")
        )
        assert staff.scalar_one() is False

        for table in ("companies", "compliance_flags", "compliance_score_history"):
            visible = await session.execute(
                text(f"SELECT count(*) FROM public.{table}")
            )
            assert visible.scalar_one() == 0
        await session.rollback()


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
async def test_ordinary_sql_cannot_impersonate_another_tenant_user(
    db, db_client_user, db_other_company
):
    import uuid

    from app.models.company import CompanyUserAccess
    from app.models.enums import UserRole
    from app.models.user import User

    target_user = User(
        id=uuid.uuid4(),
        email=f"impersonation-target-{uuid.uuid4().hex[:8]}@nlctest.com",
        full_name="Other Tenant User",
        password_hash="!test-no-login",
        role=UserRole.CLIENT_VIEW_ONLY,
        is_active=True,
        totp_enabled=False,
    )
    db.add(target_user)
    await db.flush()
    db.add(
        CompanyUserAccess(
            user_id=target_user.id,
            company_id=db_other_company.id,
            can_edit=False,
            can_view_financials=False,
            is_active=True,
        )
    )
    await db.flush()

    # Begin as a real user, then attempt to replace both the principal and
    # signature using ordinary SQL GUC writes. The application HMAC key is
    # unavailable to this SQL session, so a forged signature must fail closed.
    await set_rls_context(db, str(db_client_user.id))
    await db.execute(
        text("SELECT set_config('app.current_user_id', :principal, true)"),
        {"principal": str(target_user.id)},
    )
    await db.execute(
        text("SELECT set_config('app.current_user_signature', '00', true)")
    )

    principal = await db.execute(
        text("SELECT public.nlc_current_user_principal()")
    )
    assert principal.scalar_one_or_none() is None

    staff = await db.execute(text("SELECT public.nlc_current_user_is_staff()"))
    assert staff.scalar_one() is False

    access = await db.execute(
        text("SELECT public.nlc_can_access_company(:company_id)"),
        {"company_id": db_other_company.id},
    )
    assert access.scalar_one() is False

    visible = await db.execute(
        text("SELECT id FROM companies WHERE id = :company_id"),
        {"company_id": db_other_company.id},
    )
    assert visible.scalar_one_or_none() is None


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


@pytest.mark.asyncio
async def test_document_policies_are_nonrecursive_and_financially_scoped(db):
    result = await db.execute(
        text(
            "SELECT policyname, cmd, qual, with_check "
            "FROM pg_policies WHERE schemaname = 'public' AND tablename = 'documents'"
        )
    )
    policies = {row[0]: row for row in result.fetchall()}
    assert set(policies) == {
        "documents_tenant_select",
        "documents_tenant_insert",
        "documents_tenant_update",
        "documents_tenant_delete",
    }

    select_policy = policies["documents_tenant_select"]
    assert "nlc_can_access_company" in (select_policy[2] or "")
    assert "nlc_can_view_financials_company" in (select_policy[2] or "")
    assert "nlc_can_access_document" not in (select_policy[2] or "")

    for name in ("documents_tenant_insert", "documents_tenant_update", "documents_tenant_delete"):
        row = policies[name]
        expressions = " ".join(str(value or "") for value in row[2:])
        assert "nlc_can_edit_company" in expressions
        assert "nlc_can_manage_financials_company" in expressions
        assert "nlc_can_access_document" not in expressions

@pytest.mark.asyncio
async def test_compliance_calendar_events_has_forced_tenant_rls(db):
    rls = await db.execute(
        text(
            "SELECT c.relrowsecurity, c.relforcerowsecurity "
            "FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
            "WHERE n.nspname='public' AND c.relname='compliance_calendar_events'"
        )
    )
    assert rls.one() == (True, True)

    policy_result = await db.execute(
        text(
            "SELECT cmd FROM pg_policies "
            "WHERE schemaname='public' AND tablename='compliance_calendar_events'"
        )
    )
    assert {row[0] for row in policy_result.fetchall()} == {
        "SELECT", "INSERT", "UPDATE", "DELETE"
    }



@pytest.mark.asyncio
async def test_rescue_audit_log_has_forced_tenant_rls_and_is_append_only(db):
    relation = await db.execute(
        text(
            "SELECT c.relrowsecurity, c.relforcerowsecurity "
            "FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = 'public' AND c.relname = 'rescue_audit_log'"
        )
    )
    assert relation.one() == (True, True)

    policy_result = await db.execute(
        text(
            "SELECT policyname, cmd, qual, with_check "
            "FROM pg_policies "
            "WHERE schemaname = 'public' AND tablename = 'rescue_audit_log'"
        )
    )
    policies = {row[0]: row for row in policy_result.fetchall()}
    assert set(policies) == {
        "rescue_audit_log_tenant_select",
        "rescue_audit_log_tenant_insert",
    }
    select_policy = policies["rescue_audit_log_tenant_select"]
    assert select_policy[1] == "SELECT"
    assert "nlc_can_access_company" in (select_policy[2] or "")
    insert_policy = policies["rescue_audit_log_tenant_insert"]
    assert insert_policy[1] == "INSERT"
    assert "nlc_current_user_id" in (insert_policy[3] or "")
    assert "nlc_can_edit_company" in (insert_policy[3] or "")

    for privilege in ("UPDATE", "DELETE", "TRUNCATE"):
        result = await db.execute(
            text(
                "SELECT has_table_privilege('nlc_app_role', "
                "'public.rescue_audit_log', :privilege)"
            ),
            {"privilege": privilege},
        )
        assert result.scalar_one() is False


@pytest.mark.asyncio
async def test_human_staff_database_helpers_preserve_distinct_roles(db):
    import uuid

    from app.models.enums import UserRole
    from app.models.user import User

    await set_admin_context(db)
    users = {}
    for role in (UserRole.SUPER_ADMIN, UserRole.ADMIN_STAFF, UserRole.LEGAL_STAFF):
        user = User(
            id=uuid.uuid4(),
            email=f"rls-role-{role.value.lower()}-{uuid.uuid4().hex[:8]}@nlctest.com",
            full_name=f"RLS {role.value}",
            password_hash="!test-no-login",
            role=role,
            is_active=True,
            totp_enabled=False,
        )
        db.add(user)
        users[role] = user
    await db.flush()

    for role, user in users.items():
        await set_rls_context(db, str(user.id))
        result = await db.execute(
            text(
                "SELECT public.nlc_current_user_is_staff(), "
                "public.nlc_current_user_is_rule_admin(), "
                "public.nlc_current_user_is_super_admin()"
            )
        )
        is_staff, is_rule_admin, is_super_admin = result.one()
        assert is_staff is True
        assert is_rule_admin is (role in (UserRole.SUPER_ADMIN, UserRole.ADMIN_STAFF))
        assert is_super_admin is (role == UserRole.SUPER_ADMIN)


@pytest.mark.asyncio
async def test_legal_rule_registry_is_superadmin_write_and_history_is_append_only(db):
    legal_rule_policies = await db.execute(
        text(
            "SELECT policyname, cmd, qual, with_check FROM pg_policies "
            "WHERE schemaname='public' AND tablename='legal_rules'"
        )
    )
    legal_policies = {row[0]: row[1:] for row in legal_rule_policies.fetchall()}
    assert set(legal_policies) == {
        "legal_rules_authenticated_read",
        "legal_rules_super_admin_insert",
        "legal_rules_super_admin_update",
    }
    assert "nlc_current_user_is_super_admin" in (legal_policies["legal_rules_super_admin_insert"][2] or "")
    assert "nlc_current_user_is_super_admin" in (legal_policies["legal_rules_super_admin_update"][1] or "")
    assert "nlc_current_user_is_super_admin" in (legal_policies["legal_rules_super_admin_update"][2] or "")

    for privilege in ("DELETE", "TRUNCATE"):
        allowed = await db.execute(
            text("SELECT has_table_privilege('nlc_app_role', 'public.legal_rules', :privilege)"),
            {"privilege": privilege},
        )
        assert allowed.scalar_one() is False

    history_policies = await db.execute(
        text(
            "SELECT policyname, cmd, qual, with_check FROM pg_policies "
            "WHERE schemaname='public' AND tablename='legal_rule_versions'"
        )
    )
    history = {row[0]: row[1:] for row in history_policies.fetchall()}
    assert set(history) == {
        "legal_rule_versions_rule_admin_read",
        "legal_rule_versions_super_admin_insert",
    }
    assert history["legal_rule_versions_rule_admin_read"][0] == "SELECT"
    assert "nlc_current_user_is_rule_admin" in (history["legal_rule_versions_rule_admin_read"][1] or "")
    assert history["legal_rule_versions_super_admin_insert"][0] == "INSERT"
    assert "nlc_current_user_is_super_admin" in (history["legal_rule_versions_super_admin_insert"][2] or "")

    for privilege in ("UPDATE", "DELETE", "TRUNCATE"):
        allowed = await db.execute(
            text(
                "SELECT has_table_privilege('nlc_app_role', "
                "'public.legal_rule_versions', :privilege)"
            ),
            {"privilege": privilege},
        )
        assert allowed.scalar_one() is False

    triggers = await db.execute(
        text(
            "SELECT tgname FROM pg_trigger "
            "WHERE tgrelid='public.legal_rule_versions'::regclass "
            "AND NOT tgisinternal"
        )
    )
    assert {row[0] for row in triggers.fetchall()} >= {
        "legal_rule_versions_reject_row_mutation",
        "legal_rule_versions_reject_truncate",
    }


@pytest.mark.asyncio
async def test_webhook_tables_have_signed_identity_rls(db):
    table_state = await db.execute(
        text(
            """
            SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public'
              AND c.relname IN ('webhook_endpoints', 'webhook_deliveries')
            ORDER BY c.relname
            """
        )
    )
    states = {row[0]: (row[1], row[2]) for row in table_state.fetchall()}
    assert set(states) == {"webhook_endpoints", "webhook_deliveries"}
    assert all(enabled and forced for enabled, forced in states.values())

    result = await db.execute(
        text(
            """
            SELECT tablename, policyname, cmd, qual, with_check
            FROM pg_policies
            WHERE schemaname = 'public'
              AND tablename IN ('webhook_endpoints', 'webhook_deliveries')
            ORDER BY tablename, policyname
            """
        )
    )
    policies = result.fetchall()
    expected = {
        "webhook_endpoints": {
            "webhook_endpoints_owner_select",
            "webhook_endpoints_owner_insert",
            "webhook_endpoints_owner_update",
            "webhook_endpoints_owner_delete",
        },
        "webhook_deliveries": {
            "webhook_deliveries_owner_select",
            "webhook_deliveries_owner_insert",
            "webhook_deliveries_owner_update",
            "webhook_deliveries_owner_delete",
        },
    }
    actual = {table: set() for table in expected}
    for table, policy, _cmd, qual, with_check in policies:
        actual[table].add(policy)
        expression = f"{qual or ''} {with_check or ''}".lower()
        assert "nlc_current_user_id" in expression or "nlc_current_user_is_staff" in expression
        assert "current_setting('app.current_user_id'" not in expression
    assert actual == expected


@pytest.mark.asyncio
async def test_all_public_security_definer_functions_have_safe_owners(db):
    result = await db.execute(
        text(
            """
            SELECT p.oid::regprocedure::text AS signature,
                   owner.rolname,
                   owner.rolsuper,
                   owner.rolbypassrls
            FROM pg_proc p
            JOIN pg_namespace n ON n.oid = p.pronamespace
            JOIN pg_roles owner ON owner.oid = p.proowner
            WHERE n.nspname = 'public'
              AND p.prosecdef IS TRUE
            ORDER BY signature
            """
        )
    )
    owners = result.fetchall()
    assert owners, "expected security-definer functions installed by the migrations"
    unsafe = [
        (signature, owner_name)
        for signature, owner_name, is_superuser, bypasses_rls in owners
        if not is_superuser and not bypasses_rls
    ]
    assert unsafe == [], (
        "SECURITY DEFINER functions that access FORCE-RLS data must be owned "
        f"by a BYPASSRLS or SUPERUSER migration principal: {unsafe}"
    )


@pytest.mark.asyncio
async def test_runtime_startup_rejects_mismatched_rls_signing_secret(monkeypatch):
    import app.models.database as database

    monkeypatch.setattr(database, "_rls_signature", lambda principal: "invalid-signature")
    with pytest.raises(RuntimeError, match="does not match the database signing key"):
        await database.verify_runtime_database_role()


@pytest.mark.asyncio
async def test_public_aggregate_views_execute_as_invoker_and_obey_tenant_rls(
    db, db_client_user, db_company, db_other_company
):
    """View ownership must not bypass forced tenant RLS on base tables."""
    result = await db.execute(
        text(
            """
            SELECT c.relname, c.reloptions
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public'
              AND c.relkind = 'v'
              AND c.relname IN (
                  'vw_admin_dashboard_kpis',
                  'vw_company_flag_summary',
                  'vw_risk_distribution',
                  'vw_upcoming_deadlines',
                  'vw_revenue_pipeline'
              )
            """
        )
    )
    options = {name: (reloptions or []) for name, reloptions in result.fetchall()}
    expected = {
        "vw_admin_dashboard_kpis",
        "vw_company_flag_summary",
        "vw_risk_distribution",
        "vw_upcoming_deadlines",
        "vw_revenue_pipeline",
    }
    assert set(options) == expected
    for name, reloptions in options.items():
        assert "security_invoker=true" in reloptions, name

    await set_rls_context(db, str(db_client_user.id))
    visible = await db.execute(
        text("SELECT company_id FROM public.vw_company_flag_summary")
    )
    visible_company_ids = {str(row[0]) for row in visible.fetchall()}
    assert str(db_company.id) in visible_company_ids
    assert str(db_other_company.id) not in visible_company_ids


@pytest.mark.asyncio
async def test_legal_staff_cannot_read_engagements_quotations_or_revenue_pipeline(
    db, db_company, db_client_user
):
    """Legal staff permissions must not inherit commercial revenue visibility."""
    import uuid
    from datetime import date
    from decimal import Decimal

    from app.models.commercial import Engagement, Quotation
    from app.models.company import CompanyUserAccess
    from app.models.enums import RevenueTier, UserRole
    from app.models.user import User

    admin_user = User(
        id=uuid.uuid4(),
        email=f"revenue-admin-{uuid.uuid4().hex[:8]}@nlctest.com",
        full_name="Revenue Admin",
        password_hash="!test-no-login",
        role=UserRole.ADMIN_STAFF,
        is_active=True,
        totp_enabled=False,
    )
    legal_user = User(
        id=uuid.uuid4(),
        email=f"revenue-legal-{uuid.uuid4().hex[:8]}@nlctest.com",
        full_name="Legal Staff",
        password_hash="!test-no-login",
        role=UserRole.LEGAL_STAFF,
        is_active=True,
        totp_enabled=False,
    )
    view_only_user = User(
        id=uuid.uuid4(),
        email=f"revenue-viewer-{uuid.uuid4().hex[:8]}@nlctest.com",
        full_name="Client View Only",
        password_hash="!test-no-login",
        role=UserRole.CLIENT_VIEW_ONLY,
        is_active=True,
        totp_enabled=False,
    )
    await set_admin_context(db)
    db.add_all([admin_user, legal_user, view_only_user])
    await db.flush()
    system_gate = await db.execute(
        text("SELECT public.nlc_current_user_is_revenue_staff()")
    )
    assert system_gate.scalar_one() is True
    db.add_all([
        CompanyUserAccess(
            user_id=legal_user.id,
            company_id=db_company.id,
            can_edit=True,
            can_view_financials=True,
            is_active=True,
        ),
        CompanyUserAccess(
            user_id=view_only_user.id,
            company_id=db_company.id,
            can_edit=False,
            can_view_financials=False,
            is_active=True,
        ),
    ])
    await db.flush()
    await set_rls_context(db, str(admin_user.id))
    engagement = Engagement(
        company_id=db_company.id,
        engagement_title="Restricted commercial revenue test",
        engagement_type="COMPLIANCE_PACKAGE",
        revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
        identified_date=date.today(),
        estimated_fee_bdt=Decimal("50000.00"),
    )
    db.add(engagement)
    await db.flush()
    quotation = Quotation(
        engagement_id=engagement.id,
        company_id=db_company.id,
        quotation_number=f"Q-REVENUE-{uuid.uuid4().hex[:12].upper()}",
        quotation_date=date.today(),
        valid_until=date.today(),
        professional_fee_bdt=Decimal("50000.00"),
        government_fee_bdt=Decimal("0.00"),
        vat_bdt=Decimal("0.00"),
        total_bdt=Decimal("50000.00"),
        status="DRAFT",
    )
    db.add(quotation)
    await db.flush()

    await set_rls_context(db, str(admin_user.id))
    admin_gate = await db.execute(
        text("SELECT public.nlc_current_user_is_revenue_staff()")
    )
    assert admin_gate.scalar_one() is True
    admin_rows = await db.execute(
        text("SELECT count(*) FROM public.engagements WHERE id = :id"),
        {"id": engagement.id},
    )
    assert admin_rows.scalar_one() == 1
    admin_quotes = await db.execute(
        text("SELECT count(*) FROM public.quotations WHERE id = :id"),
        {"id": quotation.id},
    )
    assert admin_quotes.scalar_one() == 1

    await set_rls_context(db, str(db_client_user.id))
    customer_quotes = await db.execute(
        text("SELECT count(*) FROM public.quotations WHERE id = :id"),
        {"id": quotation.id},
    )
    assert customer_quotes.scalar_one() == 1

    await set_rls_context(db, str(view_only_user.id))
    view_only_quotes = await db.execute(
        text("SELECT count(*) FROM public.quotations WHERE id = :id"),
        {"id": quotation.id},
    )
    assert view_only_quotes.scalar_one() == 0

    await set_rls_context(db, str(legal_user.id))
    legal_gate = await db.execute(
        text("SELECT public.nlc_current_user_is_revenue_staff()")
    )
    assert legal_gate.scalar_one() is False
    legal_rows = await db.execute(
        text("SELECT count(*) FROM public.engagements WHERE id = :id"),
        {"id": engagement.id},
    )
    assert legal_rows.scalar_one() == 0
    legal_quotes = await db.execute(
        text("SELECT count(*) FROM public.quotations WHERE id = :id"),
        {"id": quotation.id},
    )
    assert legal_quotes.scalar_one() == 0
    revenue_rows = await db.execute(
        text("SELECT count(*) FROM public.vw_revenue_pipeline")
    )
    assert revenue_rows.scalar_one() == 0


@pytest.mark.asyncio
async def test_client_cannot_change_own_role_or_active_status(db, db_client_user):
    """RLS self-row updates must not permit privilege/activation changes."""
    from sqlalchemy.exc import DBAPIError
    from app.models.enums import UserRole

    await set_rls_context(db, str(db_client_user.id))

    # The users_self_update policy is intentionally row-scoped. The database
    # trigger must independently reject changes to authorization attributes.
    with pytest.raises(DBAPIError, match="Only a verified SUPER_ADMIN"):
        async with db.begin_nested():
            await db.execute(
                text("UPDATE public.users SET role = :role WHERE id = :user_id"),
                {"role": UserRole.SUPER_ADMIN.value, "user_id": db_client_user.id},
            )

    with pytest.raises(DBAPIError, match="Only a verified SUPER_ADMIN"):
        async with db.begin_nested():
            await db.execute(
                text("UPDATE public.users SET is_active = FALSE WHERE id = :user_id"),
                {"user_id": db_client_user.id},
            )

    await db.rollback()
