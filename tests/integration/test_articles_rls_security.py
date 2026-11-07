"""Regression coverage for historical Articles migration recovery and signed RLS."""
from __future__ import annotations

import pytest
from sqlalchemy import text

pytestmark = [pytest.mark.integration]


@pytest.mark.asyncio
async def test_articles_evidence_tables_have_signed_tenant_write_policies(db):
    expected = {
        "articles_verifications": {
            "articles_verifications_company_read",
            "articles_verifications_member_submit",
            "articles_verifications_staff_update",
        },
        "articles_verification_events": {
            "articles_verification_events_company_read",
            "articles_verification_events_actor_insert",
        },
    }

    for table, expected_names in expected.items():
        rows = await db.execute(
            text(
                "SELECT policyname, cmd, qual, with_check "
                "FROM pg_policies "
                "WHERE schemaname = 'public' AND tablename = :table"
            ),
            {"table": table},
        )
        policies = {row[0]: row for row in rows.fetchall()}
        assert set(policies) == expected_names

        read_policy = policies[f"{table}_company_read"]
        assert read_policy[1] == "SELECT"
        assert "nlc_can_access_articles_company" in (read_policy[2] or "")

        insert_name = (
            "articles_verifications_member_submit"
            if table == "articles_verifications"
            else "articles_verification_events_actor_insert"
        )
        insert_policy = policies[insert_name]
        assert insert_policy[1] == "INSERT"
        assert "nlc_current_user_id" in (insert_policy[3] or "")
        assert "nlc_can_edit_company" in (insert_policy[3] or "")
        if table == "articles_verifications":
            assert "submitted_by" in (insert_policy[3] or "")
        else:
            assert "actor_id" in (insert_policy[3] or "")

        for policy in policies.values():
            for expression in (policy[2] or "", policy[3] or ""):
                assert "current_setting" not in expression.lower()
                assert "nlc_current_user_id" not in expression.lower() or (
                    "nlc_current_user_is_staff" in expression
                    or "nlc_can_access_articles_company" in expression
                    or "nlc_can_edit_company" in expression
                )

        if table == "articles_verifications":
            update_policy = policies["articles_verifications_staff_update"]
            assert update_policy[1] == "UPDATE"
            assert "nlc_current_user_is_staff" in (update_policy[2] or "")
            assert "nlc_current_user_is_staff" in (update_policy[3] or "")

        flags = await db.execute(
            text(
                "SELECT c.relrowsecurity, c.relforcerowsecurity "
                "FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
                "WHERE n.nspname = 'public' AND c.relname = :table"
            ),
            {"table": table},
        )
        enabled, forced = flags.one()
        assert enabled is True
        assert forced is True

    helper = await db.execute(
        text(
            "SELECT pg_get_functiondef("
            "'public.nlc_can_access_articles_company(uuid)'::regprocedure)"
        )
    )
    helper_definition = helper.scalar_one()
    assert "assigned_staff_id" in helper_definition
    assert "LEGAL_STAFF" in helper_definition
    assert "company_user_access" in helper_definition

    for table, privilege in (
        ("articles_verifications", "DELETE"),
        ("articles_verifications", "TRUNCATE"),
        ("articles_verification_events", "UPDATE"),
        ("articles_verification_events", "DELETE"),
        ("articles_verification_events", "TRUNCATE"),
    ):
        result = await db.execute(
            text(
                "SELECT has_table_privilege('nlc_app_role', "
                "CAST(:table AS text), :privilege)"
            ),
            {"table": f"public.{table}", "privilege": privilege},
        )
        assert result.scalar_one() is False

    trigger_rows = await db.execute(
        text(
            "SELECT tgname FROM pg_trigger "
            "WHERE tgrelid IN ("
            "  'public.articles_verifications'::regclass, "
            "  'public.articles_verification_events'::regclass"
            ") AND NOT tgisinternal"
        )
    )
    trigger_names = {row[0] for row in trigger_rows.fetchall()}
    assert {
        "articles_verification_events_append_only",
        "articles_verification_source_immutable",
        "articles_verifications_no_delete",
    }.issubset(trigger_names)


@pytest.mark.asyncio
async def test_unsigned_admin_guc_cannot_authorize_articles_staff_write(db_for_user):
    # db_for_user starts with a valid signed tenant UUID principal.
    # Replacing only the GUC must invalidate the HMAC-bound principal.
    await db_for_user.execute(
        text("SELECT set_config('app.current_user_id', 'ADMIN', true)")
    )

    principal = await db_for_user.execute(
        text("SELECT public.nlc_current_user_principal()")
    )
    assert principal.scalar_one_or_none() is None

    staff = await db_for_user.execute(
        text("SELECT public.nlc_current_user_is_staff()")
    )
    assert staff.scalar_one() is False


@pytest.mark.asyncio
async def test_legacy_agm_evidence_reference_uses_canonical_text_type(db):
    result = await db.execute(
        text(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = 'agms' "
            "AND column_name = 'members_present_evidence_ref'"
        )
    )
    assert result.scalar_one() == "text"
