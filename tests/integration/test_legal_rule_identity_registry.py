"""Database-level invariants for the canonical legal-rule identity registry."""
from __future__ import annotations

import asyncio
import uuid
from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

pytestmark = [pytest.mark.integration]


@pytest.mark.asyncio
async def test_alias_registry_is_forced_rls_and_has_overlap_guard(db):
    relation = await db.execute(
        text(
            "SELECT c.relrowsecurity, c.relforcerowsecurity "
            "FROM pg_class c "
            "JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = 'public' AND c.relname = 'legal_rule_aliases'"
        )
    )
    assert relation.one() == (True, True)

    trigger = await db.execute(
        text(
            "SELECT t.tgname, pg_get_triggerdef(t.oid), p.prosrc "
            "FROM pg_trigger t "
            "JOIN pg_class c ON c.oid = t.tgrelid "
            "JOIN pg_namespace n ON n.oid = c.relnamespace "
            "JOIN pg_proc p ON p.oid = t.tgfoid "
            "WHERE n.nspname = 'public' "
            "AND c.relname = 'legal_rule_aliases' "
            "AND t.tgname = 'trg_legal_rule_alias_no_overlap' "
            "AND NOT t.tgisinternal"
        )
    )
    trigger_row = trigger.one()
    assert "BEFORE INSERT" in trigger_row[1]
    assert "NEW.resolution_status <> 'RESOLVED'" in trigger_row[2]
    assert "existing.resolution_status = 'RESOLVED'" in trigger_row[2]
    assert "source_namespace" in trigger_row[2]
    assert "historical_rule_id" in trigger_row[2]
    assert "daterange(" in trigger_row[2]
    assert "pg_advisory_xact_lock(" in trigger_row[2]

    # 0117 intentionally grants the application role SELECT only; signed
    # RLS context controls which registry rows it can read. The audit role
    # must have no table access, and the application role must never write.
    for role in ("nlc_app_role", "nlc_ci_audit_role"):
        privileges = await db.execute(
            text(
                "SELECT "
                "has_table_privilege(:role, "
                "'public.legal_rule_aliases', 'SELECT'), "
                "has_table_privilege(:role, "
                "'public.legal_rule_aliases', 'INSERT'), "
                "has_table_privilege(:role, "
                "'public.legal_rule_aliases', 'UPDATE'), "
                "has_table_privilege(:role, "
                "'public.legal_rule_aliases', 'DELETE')"
            ),
            {"role": role},
        )
        can_select, can_insert, can_update, can_delete = privileges.one()
        if role == "nlc_app_role":
            assert can_select is True
            assert (can_insert, can_update, can_delete) == (False, False, False)
        else:
            assert (can_select, can_insert, can_update, can_delete) == (
                False, False, False, False
            )



async def _insert_alias_identity(db) -> str:
    result = await db.execute(
        text(
            "INSERT INTO public.legal_rule_identities "
            "(jurisdiction, creation_basis) "
            "VALUES ('BD', 'integration-test fixture') RETURNING id"
        )
    )
    return str(result.scalar_one())


async def _insert_alias(
    db, *, canonical_id: str, historical_id: str,
    status: str, valid_from: date, valid_to: date | None,
) -> None:
    await db.execute(
        text(
            "INSERT INTO public.legal_rule_aliases "
            "(canonical_rule_id, source_namespace, historical_rule_id, "
            "resolution_status, valid_from, valid_to) "
            "VALUES (CAST(:canonical_id AS uuid), 'integration-test', "
            ":historical_id, :status, CAST(:valid_from AS date), "
            "CAST(:valid_to AS date))"
        ),
        {
            "canonical_id": canonical_id,
            "historical_id": historical_id,
            "status": status,
            "valid_from": valid_from,
            "valid_to": valid_to,
        },
    )


@pytest.mark.asyncio
async def test_alias_overlap_guard_rejects_overlapping_resolved_intervals(db):
    canonical_id = await _insert_alias_identity(db)
    historical_id = f"overlap-{uuid.uuid4()}"
    await _insert_alias(
        db, canonical_id=canonical_id, historical_id=historical_id,
        status="RESOLVED", valid_from=date(2020, 1, 1), valid_to=date(2022, 1, 1),
    )

    with pytest.raises(DBAPIError) as exc_info:
        async with db.begin_nested():
            await _insert_alias(
                db, canonical_id=canonical_id, historical_id=historical_id,
                status="RESOLVED", valid_from=date(2021, 1, 1), valid_to=date(2023, 1, 1),
            )

    assert getattr(exc_info.value.orig, "sqlstate", None) == "23P01"


@pytest.mark.asyncio
async def test_alias_overlap_guard_allows_adjacent_and_unresolved_intervals(db):
    first_canonical_id = await _insert_alias_identity(db)
    second_canonical_id = await _insert_alias_identity(db)
    ambiguous_canonical_id = await _insert_alias_identity(db)
    unresolved_canonical_id = await _insert_alias_identity(db)
    historical_id = f"adjacent-{uuid.uuid4()}"
    await _insert_alias(
        db, canonical_id=first_canonical_id, historical_id=historical_id,
        status="RESOLVED", valid_from=date(2020, 1, 1), valid_to=date(2021, 1, 1),
    )
    # Half-open intervals [2020, 2021) and [2021, 2022) do not overlap.
    await _insert_alias(
        db, canonical_id=second_canonical_id, historical_id=historical_id,
        status="RESOLVED", valid_from=date(2021, 1, 1), valid_to=date(2022, 1, 1),
    )
    # Non-resolved candidates remain representable even when their dates
    # overlap a resolved mapping; they are not active resolution claims.
    await _insert_alias(
        db, canonical_id=ambiguous_canonical_id, historical_id=historical_id,
        status="AMBIGUOUS", valid_from=date(2020, 6, 1), valid_to=date(2020, 7, 1),
    )
    await _insert_alias(
        db, canonical_id=unresolved_canonical_id, historical_id=historical_id,
        status="UNRESOLVED", valid_from=date(2020, 6, 1), valid_to=date(2020, 7, 1),
    )



@pytest.mark.asyncio
async def test_alias_overlap_guard_serializes_concurrent_resolved_inserts(test_engine):
    historical_id = f"concurrent-{uuid.uuid4()}"
    async with test_engine.begin() as setup:
        ids = await setup.execute(
            text(
                "INSERT INTO public.legal_rule_identities "
                "(jurisdiction, creation_basis) VALUES "
                "('BD', 'concurrency-test fixture'), "
                "('BD', 'concurrency-test fixture') RETURNING id"
            )
        )
        canonical_ids = [str(value) for value in ids.scalars().all()]
    assert len(canonical_ids) == 2

    first = await test_engine.connect()
    second = await test_engine.connect()
    first_tx = await first.begin()
    second_tx = await second.begin()
    second_started = asyncio.Event()

    try:
        await _insert_alias(
            first, canonical_id=canonical_ids[0], historical_id=historical_id,
            status="RESOLVED", valid_from=date(2020, 1, 1), valid_to=date(2022, 1, 1),
        )
        second_pid = (await second.execute(text("SELECT pg_backend_pid()"))).scalar_one()

        async def competing_insert():
            second_started.set()
            await _insert_alias(
                second, canonical_id=canonical_ids[1], historical_id=historical_id,
                status="RESOLVED", valid_from=date(2021, 1, 1), valid_to=date(2023, 1, 1),
            )

        competing = asyncio.create_task(competing_insert())
        await second_started.wait()
        # Prove the second backend is actually blocked on the advisory lock
        # before releasing the first transaction; otherwise this is merely
        # a sequential duplicate-insert test.
        async with test_engine.connect() as observer:
            waiting_on_lock = False
            for _ in range(500):
                wait_event = await observer.execute(
                    text(
                        "SELECT wait_event_type FROM pg_stat_activity "
                        "WHERE pid = :pid"
                    ),
                    {"pid": second_pid},
                )
                if wait_event.scalar_one_or_none() == "Lock":
                    waiting_on_lock = True
                    break
                await asyncio.sleep(0.01)
        assert waiting_on_lock, "second insert never waited for the advisory lock"
        await first_tx.commit()

        with pytest.raises(DBAPIError) as exc_info:
            await competing
        sqlstate = (
            getattr(exc_info.value.orig, "sqlstate", None)
            or getattr(exc_info.value.orig, "pgcode", None)
        )
        assert sqlstate == "23P01"
        await second_tx.rollback()
    finally:
        if first_tx.is_active:
            await first_tx.rollback()
        if second_tx.is_active:
            await second_tx.rollback()
        await first.close()
        await second.close()
