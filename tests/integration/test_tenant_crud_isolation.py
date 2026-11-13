"""Authenticated PostgreSQL tenant-isolation regression tests.

These tests run only against the isolated local PostgreSQL integration DB.
No production rows or credentials are used.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.models.database import set_rls_context


pytestmark = [pytest.mark.integration]


@pytest.mark.asyncio
async def test_tenant_a_cannot_select_update_or_delete_tenant_b_company(
    db, db_client_user, db_other_company
):
    await set_rls_context(db, str(db_client_user.id))

    selected = await db.execute(
        text("SELECT id FROM public.companies WHERE id = :company_id"),
        {"company_id": db_other_company.id},
    )
    assert selected.scalar_one_or_none() is None

    updated = await db.execute(
        text(
            "UPDATE public.companies SET company_name = company_name "
            "WHERE id = :company_id"
        ),
        {"company_id": db_other_company.id},
    )
    assert updated.rowcount == 0

    # Runtime grants intentionally deny DELETE on companies entirely. Accept
    # either that privilege denial or an RLS-filtered zero-row result; both
    # prove Tenant A cannot delete Tenant B's record.
    try:
        async with db.begin_nested():
            deleted = await db.execute(
                text("DELETE FROM public.companies WHERE id = :company_id"),
                {"company_id": db_other_company.id},
            )
        assert deleted.rowcount == 0
    except DBAPIError as exc:
        assert "permission denied" in str(exc).lower()


@pytest.mark.asyncio
async def test_tenant_a_cannot_insert_score_history_for_tenant_b(
    db, db_client_user, db_other_company
):
    await set_rls_context(db, str(db_client_user.id))

    with pytest.raises(DBAPIError):
        async with db.begin_nested():
            await db.execute(
                text("""
                    INSERT INTO public.compliance_score_history
                        (company_id, score, risk_band, snapshot_month,
                         calculated_at, score_hash, engine_version)
                    VALUES
                        (:company_id, 90, 'GREEN', DATE '2026-11-01',
                         now(), :score_hash, 'tenant-rls-test')
                """),
                {
                    "company_id": db_other_company.id,
                    "score_hash": "a" * 64,
                },
            )


@pytest.mark.asyncio
async def test_score_history_is_append_only_in_postgresql(db, db_company):
    from datetime import date, datetime, timezone

    from app.models.compliance import ComplianceScoreHistory
    from app.models.database import set_admin_context
    from app.models.enums import RiskBand

    # Use the signed service principal only to seed an isolated test row.
    # The same nlc_app_role is used for the subsequent forbidden mutations.
    await set_admin_context(db)
    row = ComplianceScoreHistory(
        company_id=db_company.id,
        score=90,
        risk_band=RiskBand.GREEN,
        snapshot_month=date(2026, 11, 1),
        calculated_at=datetime.now(timezone.utc),
        score_hash="b" * 64,
        engine_version="tenant-rls-test",
        evaluation_status="COMPLETED",
        trigger_source="MANUAL",
    )
    db.add(row)
    await db.flush()

    with pytest.raises(DBAPIError):
        async with db.begin_nested():
            await db.execute(
                text(
                    "UPDATE public.compliance_score_history "
                    "SET score = 1 WHERE id = :row_id"
                ),
                {"row_id": row.id},
            )

    with pytest.raises(DBAPIError):
        async with db.begin_nested():
            await db.execute(
                text(
                    "DELETE FROM public.compliance_score_history "
                    "WHERE id = :row_id"
                ),
                {"row_id": row.id},
            )

    privileges = await db.execute(text("""
        SELECT
            has_table_privilege('nlc_app_role',
                'public.compliance_score_history', 'SELECT'),
            has_table_privilege('nlc_app_role',
                'public.compliance_score_history', 'INSERT'),
            has_table_privilege('nlc_app_role',
                'public.compliance_score_history', 'UPDATE'),
            has_table_privilege('nlc_app_role',
                'public.compliance_score_history', 'DELETE')
    """))
    assert privileges.one() == (True, True, False, False)

    policies = await db.execute(text("""
        SELECT cmd
          FROM pg_policies
         WHERE schemaname = 'public'
           AND tablename = 'compliance_score_history'
         ORDER BY cmd
    """))
    assert {row[0] for row in policies.fetchall()} == {"INSERT", "SELECT"}

    trigger = await db.execute(text("""
        SELECT count(*)
          FROM pg_trigger
         WHERE tgrelid = 'public.compliance_score_history'::regclass
           AND tgname = 'trg_compliance_score_history_append_only'
           AND NOT tgisinternal
    """))
    assert trigger.scalar_one() == 1
