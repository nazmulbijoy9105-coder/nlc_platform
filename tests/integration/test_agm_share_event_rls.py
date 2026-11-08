"""PostgreSQL regression checks for the new AGM/share evidence boundary."""
from __future__ import annotations

import pytest
from sqlalchemy import text


pytestmark = [pytest.mark.integration]


@pytest.mark.asyncio
async def test_agm_and_share_event_tables_have_signed_tenant_rls(db):
    expected = {
        "agm_notice_evidence": {
            "agm_notice_evidence_tenant_select",
            "agm_notice_evidence_member_submit",
            "agm_notice_evidence_staff_verify",
        },
        "share_compliance_events": {
            "share_compliance_events_tenant_select",
            "share_compliance_events_member_submit",
            "share_compliance_events_staff_verify",
        },
    }
    for table, names in expected.items():
        result = await db.execute(
            text(
                "SELECT policyname, cmd, qual, with_check FROM pg_policies "
                "WHERE schemaname='public' AND tablename=:table"
            ),
            {"table": table},
        )
        policies = {row[0]: row for row in result.fetchall()}
        assert set(policies) == names

        select_policy = policies[f"{table}_tenant_select"]
        assert select_policy[1] == "SELECT"
        assert "nlc_can_access_company" in (select_policy[2] or "")

        insert_policy = policies[f"{table}_member_submit"]
        assert insert_policy[1] == "INSERT"
        assert "nlc_can_edit_company" in (insert_policy[3] or "")
        assert "nlc_current_user_id" in (insert_policy[3] or "")
        if table == "share_compliance_events":
            assert "event_verified" in (insert_policy[3] or "")
            assert "filing_status_verified" in (insert_policy[3] or "")
            assert "certificate_status_verified" in (insert_policy[3] or "")
        else:
            assert "entitled_member_verified" in (insert_policy[3] or "")
            assert "notice_verified" in (insert_policy[3] or "")
            assert "consent_verified" in (insert_policy[3] or "")
            assert "omission_verified" in (insert_policy[3] or "")

        update_policy = policies[f"{table}_staff_verify"]
        assert update_policy[1] == "UPDATE"
        assert "nlc_current_user_is_staff" in (update_policy[2] or "")
        assert "nlc_current_user_is_staff" in (update_policy[3] or "")
        assert "nlc_can_access_company" in (update_policy[3] or "")

        flags = await db.execute(
            text(
                "SELECT c.relrowsecurity, c.relforcerowsecurity "
                "FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
                "WHERE n.nspname='public' AND c.relname=:table"
            ),
            {"table": table},
        )
        enabled, forced = flags.one()
        assert enabled is True
        assert forced is True

        for privilege in ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE"):
            allowed = await db.execute(
                text(
                    "SELECT has_table_privilege('nlc_app_role', "
                    "CAST(:table AS text), :privilege)"
                ),
                {"table": f"public.{table}", "privilege": privilege},
            )
            assert allowed.scalar_one() is (privilege in {"SELECT", "INSERT", "UPDATE"})

    trigger_result = await db.execute(
        text(
            "SELECT tgname FROM pg_trigger WHERE NOT tgisinternal AND tgrelid IN ("
            "'public.agm_notice_evidence'::regclass, "
            "'public.share_compliance_events'::regclass)"
        )
    )
    triggers = {row[0] for row in trigger_result.fetchall()}
    assert {
        "trg_agm_notice_company_match",
        "trg_agm_notice_evidence_immutable",
        "trg_share_event_company_match",
        "trg_share_compliance_event_immutable",
    }.issubset(triggers)


@pytest.mark.asyncio
async def test_new_evidence_migration_is_the_single_current_revision(db):
    rows = await db.execute(text("SELECT version_num FROM alembic_version"))
    versions = [row[0] for row in rows.fetchall()]
    assert versions == ["0084_install_legal_rule_version_guard"]
