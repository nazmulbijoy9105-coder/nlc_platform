"""Real PostgreSQL multi-session races for commercial quotation lifecycle."""
from __future__ import annotations

import asyncio
import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.commercial import Engagement
from app.models.company import Company
from app.models.database import set_admin_context, set_rls_context
from app.models.enums import (
    CompanyStatus,
    CompanyType,
    ComplexityLevel,
    EngagementStatus,
    RevenueTier,
    RiskBand,
    UserRole,
)
from app.models.user import User
from app.services.commercial_service import (
    CommercialConflictError,
    QuotationService,
)


async def _committed_commercial_fixture(test_engine, *, quotation_count: int):
    """Create a committed tenant, staff actor, quoted engagement and quotations."""
    sessions = async_sessionmaker(test_engine, expire_on_commit=False)
    company_id = uuid.uuid4()
    user_id = uuid.uuid4()
    quotation_ids: list[uuid.UUID] = []

    async with sessions() as session:
        company = Company(
            id=company_id,
            company_name=f"Concurrent Commercial {company_id.hex[:8]} Ltd",
            registration_number=f"CC-{company_id.hex[:12].upper()}",
            company_type=CompanyType.PRIVATE_LIMITED,
            company_status=CompanyStatus.ACTIVE,
            incorporation_date=date(2023, 1, 1),
            financial_year_end=date(2025, 12, 31),
            registered_address="Test address, Dhaka, Bangladesh",
            current_compliance_score=85,
            current_risk_band=RiskBand.GREEN,
            is_active=True,
        )
        user = User(
            id=user_id,
            email=f"commercial-race-{user_id.hex}@nlctest.com",
            full_name="Commercial Concurrency Test",
            password_hash="!test-only-no-login",
            role=UserRole.ADMIN_STAFF,
            is_active=True,
            totp_enabled=False,
        )
        await set_admin_context(session)
        session.add_all([company, user])
        await session.flush()
        await set_rls_context(session, str(user_id))

        engagement = Engagement(
            company_id=company_id,
            engagement_title="Quotation concurrency regression",
            engagement_type="ADVISORY",
            engagement_status=EngagementStatus.QUOTED,
            revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
            complexity=ComplexityLevel.MEDIUM,
            identified_date=date.today(),
            quoted_date=date.today(),
            quoted_fee_bdt=Decimal("100.00"),
        )
        session.add(engagement)
        await session.flush()

        service = QuotationService(session)
        for _ in range(quotation_count):
            quotation = await service.create_quotation(
                engagement_id=engagement.id,
                company_id=company_id,
                professional_fee_bdt=Decimal("100.00"),
                valid_days=30,
            )
            quotation_ids.append(quotation.id)
        await session.commit()

    return sessions, user_id, quotation_ids


@pytest.mark.asyncio
async def test_concurrent_competing_quotation_acceptance_is_serialized(test_engine):
    """Two independent PostgreSQL sessions cannot confirm one engagement twice."""
    sessions, user_id, quotation_ids = await _committed_commercial_fixture(
        test_engine, quotation_count=2
    )
    start = asyncio.Barrier(2)

    async def accept_once(quotation_id):
        async with sessions() as session:
            await set_rls_context(session, str(user_id))
            await start.wait()
            try:
                quotation = await QuotationService(session).accept(quotation_id)
                await session.commit()
                return ("accepted", quotation.id if quotation else None)
            except CommercialConflictError:
                await session.rollback()
                return ("rejected", None)

    outcomes = await asyncio.gather(*(accept_once(qid) for qid in quotation_ids))
    assert sorted(result for result, _ in outcomes) == ["accepted", "rejected"]
    assert sum(value is not None for _, value in outcomes) == 1


@pytest.mark.asyncio
async def test_concurrent_accept_and_reject_of_same_quotation_is_serialized(test_engine):
    """Independent accept/reject transactions produce one terminal decision."""
    sessions, user_id, quotation_ids = await _committed_commercial_fixture(
        test_engine, quotation_count=1
    )
    quotation_id = quotation_ids[0]
    start = asyncio.Barrier(2)

    async def accept_once():
        async with sessions() as session:
            await set_rls_context(session, str(user_id))
            await start.wait()
            try:
                quotation = await QuotationService(session).accept(quotation_id)
                await session.commit()
                return ("accepted", quotation.status if quotation else None)
            except CommercialConflictError:
                await session.rollback()
                return ("conflict", None)

    async def reject_once():
        async with sessions() as session:
            await set_rls_context(session, str(user_id))
            await start.wait()
            try:
                quotation = await QuotationService(session).reject(
                    quotation_id, reason="Concurrent decision regression"
                )
                await session.commit()
                return ("rejected", quotation.status if quotation else None)
            except CommercialConflictError:
                await session.rollback()
                return ("conflict", None)

    outcomes = await asyncio.gather(accept_once(), reject_once())
    decisions = [result for result, _ in outcomes if result != "conflict"]
    assert len(decisions) == 1
    assert decisions[0] in {"accepted", "rejected"}
