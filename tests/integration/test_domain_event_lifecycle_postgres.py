"""PostgreSQL end-to-end invariants for lifecycle domain events."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.company import Company, CompanyUserAccess
from app.models.domain_event import DomainEventConsumption, DomainEventOutbox
from app.models.enums import CompanyStatus, CompanyType, DirectorStatus, RiskBand
from app.models.people import Director
from app.services.domain_events import DomainEventType, publish_domain_event
from app.services.people_service import (
    DirectorService,
    ShareholderService,
    ShareTransferService,
)


pytestmark = [pytest.mark.integration]


@pytest.mark.asyncio
async def test_company_change_and_outbox_event_rollback_together(db, db_company):
    director_id = uuid.uuid4()
    event_id = uuid.uuid4()

    with pytest.raises(RuntimeError, match="force transaction rollback"):
        async with db.begin_nested():
            director = Director(
                id=director_id,
                company_id=db_company.id,
                full_name="Rollback Test Director",
                director_status=DirectorStatus.ACTIVE,
            )
            db.add(director)
            await db.flush()
            event = await publish_domain_event(
                db,
                company_id=db_company.id,
                event_type=DomainEventType.DIRECTOR_CHANGED,
                aggregate_type="director",
                aggregate_id=director.id,
                payload={"change": "appointed"},
            )
            event_id = event.id
            raise RuntimeError("force transaction rollback")

    assert await db.get(Director, director_id) is None
    assert await db.get(DomainEventOutbox, event_id) is None


@pytest.mark.asyncio
async def test_people_services_emit_compact_company_lifecycle_events(db, db_company):
    director = await DirectorService(db).appoint_director(
        db_company.id,
        full_name="Private Person",
        appointment_date=date(2026, 1, 5),
        nid_number="DO-NOT-COPY-INTO-EVENT",
    )
    shareholder = await ShareholderService(db).add_shareholder(
        db_company.id,
        shareholder_name="Private Shareholder",
        shares_held=100,
        effective_date=date(2026, 1, 5),
        nid_or_reg_number="DO-NOT-COPY-INTO-EVENT",
    )
    transfer = await ShareTransferService(db).record_transfer(
        db_company.id,
        transferor_name="Private Transferor",
        transferee_name="Private Transferee",
        shares_transferred=25,
        transfer_date=date(2026, 2, 1),
    )

    result = await db.execute(
        select(DomainEventOutbox).where(
            DomainEventOutbox.aggregate_id.in_(
                [director.id, shareholder.id, transfer.id]
            )
        )
    )
    events = {event.aggregate_id: event for event in result.scalars().all()}

    assert events[director.id].event_type == DomainEventType.DIRECTOR_CHANGED
    assert events[shareholder.id].event_type == DomainEventType.SHAREHOLDER_CHANGED
    assert events[transfer.id].event_type == DomainEventType.SHARE_TRANSFER_CHANGED
    serialized_payloads = str([event.payload for event in events.values()])
    assert "DO-NOT-COPY-INTO-EVENT" not in serialized_payloads
    assert "Private Person" not in serialized_payloads
    assert "Private Shareholder" not in serialized_payloads
    assert "Private Transferor" not in serialized_payloads
    assert "Private Transferee" not in serialized_payloads


@pytest.mark.asyncio
async def test_event_consumer_receipt_is_idempotent_in_postgres(db, db_company):
    event = await publish_domain_event(
        db,
        company_id=db_company.id,
        event_type=DomainEventType.FILING_RECEIPT_RECORDED,
        aggregate_type="annual_return",
        aggregate_id=uuid.uuid4(),
        payload={"filing_type": "ANNUAL_RETURN", "receipt_reference_present": True},
    )

    first = await db.execute(
        pg_insert(DomainEventConsumption)
        .values(
            id=uuid.uuid4(),
            event_id=event.id,
            company_id=db_company.id,
            consumer_name="filing_receipt_v1",
            outcome={"compliance_reevaluation": "completed"},
        )
        .on_conflict_do_nothing(index_elements=["event_id", "consumer_name"])
        .returning(DomainEventConsumption.id)
    )
    second = await db.execute(
        pg_insert(DomainEventConsumption)
        .values(
            id=uuid.uuid4(),
            event_id=event.id,
            company_id=db_company.id,
            consumer_name="filing_receipt_v1",
            outcome={"compliance_reevaluation": "completed"},
        )
        .on_conflict_do_nothing(index_elements=["event_id", "consumer_name"])
        .returning(DomainEventConsumption.id)
    )

    assert first.scalar_one() is not None
    assert second.scalar_one_or_none() is None
    rows = await db.execute(
        select(DomainEventConsumption).where(
            DomainEventConsumption.event_id == event.id,
            DomainEventConsumption.consumer_name == "filing_receipt_v1",
        )
    )
    assert len(rows.scalars().all()) == 1


@pytest.mark.asyncio
async def test_outbox_rls_returns_only_companies_in_signed_user_scope(db_for_user):
    from app.models.database import set_admin_context, set_rls_context

    actor_id = (
        await db_for_user.execute(text("SELECT public.nlc_current_user_id()"))
    ).scalar_one()
    await set_admin_context(db_for_user)

    def company(name: str, registration: str) -> Company:
        return Company(
            id=uuid.uuid4(),
            company_name=name,
            registration_number=registration,
            incorporation_date=date(2020, 1, 1),
            registered_address="Dhaka, Bangladesh",
            company_type=CompanyType.PRIVATE_LIMITED,
            financial_year_end=date(2025, 12, 31),
            company_status=CompanyStatus.ACTIVE,
            current_risk_band=RiskBand.GREEN,
            current_compliance_score=90,
            is_active=True,
        )

    visible_company = company("Visible Tenant Ltd", f"VISIBLE-{uuid.uuid4().hex[:8]}")
    hidden_company = company("Hidden Tenant Ltd", f"HIDDEN-{uuid.uuid4().hex[:8]}")
    db_for_user.add_all([visible_company, hidden_company])
    await db_for_user.flush()
    db_for_user.add(
        CompanyUserAccess(
            user_id=actor_id,
            company_id=visible_company.id,
            can_edit=True,
            can_view_financials=True,
            is_active=True,
        )
    )
    for company_row in (visible_company, hidden_company):
        db_for_user.add(
            DomainEventOutbox(
                id=uuid.uuid4(),
                company_id=company_row.id,
                event_type=DomainEventType.DIRECTOR_CHANGED,
                aggregate_type="director",
                aggregate_id=uuid.uuid4(),
                payload={"change": "appointed"},
                occurred_at=datetime.now(timezone.utc),
                available_at=datetime.now(timezone.utc),
            )
        )
    await db_for_user.flush()

    await set_rls_context(db_for_user, str(actor_id))
    visible = await db_for_user.execute(
        select(DomainEventOutbox.company_id)
    )
    assert set(visible.scalars().all()) == {visible_company.id}


@pytest.mark.asyncio
async def test_consumer_receipts_are_forced_admin_worker_only(db):
    policies = await db.execute(
        text(
            "SELECT policyname, qual, with_check FROM pg_policies "
            "WHERE schemaname='public' AND tablename='domain_event_consumptions'"
        )
    )
    rows = policies.fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "domain_event_consumptions_admin_only"
    assert "nlc_current_user_principal" in (rows[0][1] or "")
    assert "'ADMIN'" in (rows[0][1] or "")
    assert "'ADMIN'" in (rows[0][2] or "")

    flags = await db.execute(
        text(
            "SELECT c.relrowsecurity, c.relforcerowsecurity "
            "FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
            "WHERE n.nspname='public' AND c.relname='domain_event_consumptions'"
        )
    )
    enabled, forced = flags.one()
    assert enabled is True
    assert forced is True


def test_domain_event_processing_migration_is_linear_and_at_head():
    alembic_ini = Path(__file__).resolve().parents[2] / "alembic.ini"
    script = ScriptDirectory.from_config(Config(str(alembic_ini)))
    heads = script.get_heads()
    assert len(heads) == 1, f"multiple Alembic heads: {heads}"
    ancestors = {
        revision.revision
        for revision in script.walk_revisions(base="base", head=heads[0])
    }
    assert "0105_domain_event_outbox" in ancestors
    assert "0106_domain_event_processing_controls" in ancestors
