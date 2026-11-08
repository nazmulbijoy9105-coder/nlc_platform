"""Regression tests for the existing commercial API/service contract."""
from __future__ import annotations

import asyncio
import uuid
from uuid import UUID, uuid4
from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.security import create_access_token
from app.models.company import Company
from app.models.commercial import Engagement, Quotation
from app.models.database import set_admin_context, set_rls_context
from app.models.enums import (
    CompanyStatus,
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


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def commercial_admin_token(db_user):
    return create_access_token({
        "sub": str(db_user.id),
        "user_id": str(db_user.id),
        "type": "access",
        "role": "ADMIN_STAFF",
        "email": db_user.email,
        "company_ids": [],
    })


async def _create_engagement(api_client, token, company_id):
    response = await api_client.post(
        "/api/v1/commercial/engagements",
        headers=_auth(token),
        json={
            "company_id": str(company_id),
            "engagement_type": "COMPLIANCE_PACKAGE",
            "revenue_tier": "COMPLIANCE_PACKAGE",
            "description": "Commercial API contract regression",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _create_quotation(api_client, token, company_id, engagement_id):
    response = await api_client.post(
        "/api/v1/commercial/quotations",
        headers=_auth(token),
        json={
            "engagement_id": engagement_id,
            "company_id": str(company_id),
            "professional_fee_bdt": "100000.00",
            "government_fee_bdt": "5000.00",
            "vat_bdt": "15000.00",
            "valid_days": 30,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio
async def test_quotation_creation_uses_decimal_totals_and_validity(
    api_client, commercial_admin_token, db_company
):
    engagement = await _create_engagement(
        api_client, commercial_admin_token, db_company.id
    )
    quotation = await _create_quotation(
        api_client,
        commercial_admin_token,
        db_company.id,
        engagement["engagement_id"],
    )

    assert Decimal(str(quotation["total_fee_bdt"])) == Decimal("120000.00")
    assert quotation["valid_until"] == (
        date.today() + timedelta(days=30)
    ).isoformat()


@pytest.mark.asyncio
async def test_quotation_accept_and_reject_routes_match_service_contract(
    api_client, commercial_admin_token, db_company
):
    engagement = await _create_engagement(
        api_client, commercial_admin_token, db_company.id
    )
    accepted = await _create_quotation(
        api_client, commercial_admin_token, db_company.id, engagement["engagement_id"]
    )
    premature_start = await api_client.patch(
        f"/api/v1/commercial/engagements/{engagement['engagement_id']}/status",
        headers=_auth(commercial_admin_token),
        json={"new_status": "IN_PROGRESS"},
    )
    assert premature_start.status_code == 409, premature_start.text

    accept_response = await api_client.patch(
        f"/api/v1/commercial/quotations/{accepted['quotation_id']}/accept",
        headers=_auth(commercial_admin_token),
    )
    assert accept_response.status_code == 200, accept_response.text
    assert accept_response.json()["status"] == "ACCEPTED"

    start_response = await api_client.patch(
        f"/api/v1/commercial/engagements/{engagement['engagement_id']}/status",
        headers=_auth(commercial_admin_token),
        json={"new_status": "IN_PROGRESS", "note": "Service delivery started"},
    )
    assert start_response.status_code == 200, start_response.text
    assert start_response.json()["status"] == "IN_PROGRESS"

    rejection_engagement = await _create_engagement(
        api_client, commercial_admin_token, db_company.id
    )
    rejected = await _create_quotation(
        api_client,
        commercial_admin_token,
        db_company.id,
        rejection_engagement["engagement_id"],
    )
    reject_response = await api_client.patch(
        f"/api/v1/commercial/quotations/{rejected['quotation_id']}/reject",
        headers=_auth(commercial_admin_token),
        json={"reason": "Client declined the proposed scope"},
    )
    assert reject_response.status_code == 200, reject_response.text
    assert reject_response.json()["status"] == "REJECTED"


@pytest.mark.asyncio
async def test_engagement_status_transition_accepts_note(
    api_client, commercial_admin_token, db_company
):
    engagement = await _create_engagement(
        api_client, commercial_admin_token, db_company.id
    )
    response = await api_client.patch(
        f"/api/v1/commercial/engagements/{engagement['engagement_id']}/status",
        headers=_auth(commercial_admin_token),
        json={"new_status": "CANCELLED", "note": "Engagement cancelled"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "CANCELLED"


@pytest.mark.asyncio
async def test_task_completion_accepts_completion_note(
    api_client, commercial_admin_token, db_company
):
    created = await api_client.post(
        "/api/v1/commercial/tasks",
        headers=_auth(commercial_admin_token),
        json={
            "company_id": str(db_company.id),
            "title": "Complete API contract test task",
            "description": "Exercise task completion endpoint",
        },
    )
    assert created.status_code == 201, created.text

    response = await api_client.patch(
        f"/api/v1/commercial/tasks/{created.json()['task_id']}/complete?company_id={db_company.id}",
        headers=_auth(commercial_admin_token),
        json={"completion_note": "Verified complete"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "COMPLETED"

    duplicate = await api_client.patch(
        f"/api/v1/commercial/tasks/{created.json()['task_id']}/complete",
        headers=_auth(commercial_admin_token),
        json={"completion_note": "Duplicate completion must not create another transition"},
    )
    assert duplicate.status_code == 422, duplicate.text
    repeated = await api_client.patch(
        f"/api/v1/commercial/tasks/{created.json()['task_id']}/complete?company_id={db_company.id}",
        headers=_auth(commercial_admin_token),
        json={"completion_note": "Should not complete twice"},
    )
    assert repeated.status_code == 409, repeated.text

@pytest.mark.asyncio
async def test_quotation_cannot_be_attached_to_another_company(
    api_client, commercial_admin_token, db_company
):
    engagement = await _create_engagement(
        api_client, commercial_admin_token, db_company.id
    )
    response = await api_client.post(
        "/api/v1/commercial/quotations",
        headers=_auth(commercial_admin_token),
        json={
            "engagement_id": engagement["engagement_id"],
            "company_id": "00000000-0000-0000-0000-000000000001",
            "professional_fee_bdt": "10000.00",
        },
    )
    assert response.status_code == 404, response.text


@pytest.mark.asyncio
async def test_engagement_rejects_invalid_status_jump(
    api_client, commercial_admin_token, db_company
):
    engagement = await _create_engagement(
        api_client, commercial_admin_token, db_company.id
    )
    response = await api_client.patch(
        f"/api/v1/commercial/engagements/{engagement['engagement_id']}/status",
        headers=_auth(commercial_admin_token),
        json={"new_status": "COMPLETED"},
    )
    assert response.status_code == 409, response.text



def test_quotation_response_supports_legacy_null_valid_until():
    from datetime import datetime, timezone
    from types import SimpleNamespace

    from app.api.commercial import _quotation_to_response

    quotation = SimpleNamespace(
        id="00000000-0000-0000-0000-000000000001",
        quotation_number="NLC-2024-0001",
        engagement_id="00000000-0000-0000-0000-000000000002",
        company_id="00000000-0000-0000-0000-000000000003",
        professional_fee_bdt=Decimal("100.00"),
        government_fee_bdt=Decimal("0.00"),
        vat_bdt=Decimal("0.00"),
        total_bdt=Decimal("100.00"),
        status="ACCEPTED",
        valid_until=None,
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    response = _quotation_to_response(quotation)
    assert response.valid_until is None
@pytest.mark.asyncio
async def test_expired_quotation_cannot_be_accepted(
    api_client, commercial_admin_token, db_company, db
):
    engagement = await _create_engagement(
        api_client, commercial_admin_token, db_company.id
    )
    quotation = await _create_quotation(
        api_client, commercial_admin_token, db_company.id, engagement["engagement_id"]
    )
    stored = await db.get(Quotation, UUID(quotation["quotation_id"]))
    assert stored is not None
    stored.valid_until = date.today() - timedelta(days=1)
    await db.flush()

    response = await api_client.patch(
        f"/api/v1/commercial/quotations/{quotation['quotation_id']}/accept",
        headers=_auth(commercial_admin_token),
    )
    assert response.status_code == 409, response.text
    assert "expired" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_accepting_quotation_with_inactive_engagement_returns_not_found(
    api_client, commercial_admin_token, db_company, db
):
    engagement = await _create_engagement(
        api_client, commercial_admin_token, db_company.id
    )
    quotation = await _create_quotation(
        api_client, commercial_admin_token, db_company.id, engagement["engagement_id"]
    )
    stored = await db.get(Engagement, UUID(engagement["engagement_id"]))
    assert stored is not None
    stored.is_active = False
    await db.flush()

    response = await api_client.patch(
        f"/api/v1/commercial/quotations/{quotation['quotation_id']}/accept",
        headers=_auth(commercial_admin_token),
    )
    assert response.status_code == 404, response.text


@pytest.mark.asyncio
async def _seed_concurrent_quotation_fixture(test_engine):
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)
    user_id = uuid.uuid4()
    company_id = uuid.uuid4()
    engagement_id = uuid.uuid4()
    first_quote_id = uuid.uuid4()
    second_quote_id = uuid.uuid4()
    today = date.today()

    async with session_factory() as session:
        await set_admin_context(session)
        session.add(
            User(
                id=user_id,
                email=f"quotation-lock-{user_id.hex}@nlctest.com",
                full_name="Quotation Lock Test Admin",
                password_hash="!seeded-no-login",
                role=UserRole.SUPER_ADMIN,
                is_active=True,
                totp_enabled=False,
            )
        )
        session.add(
            Company(
                id=company_id,
                company_name="Quotation Lock Test Ltd",
                registration_number=f"QLOCK-{company_id.hex[:12].upper()}",
                incorporation_date=today - timedelta(days=730),
                registered_address="Test address, Bangladesh",
                company_type="PRIVATE_LIMITED",
                member_count=5,
                financial_year_end=date(today.year - 1, 12, 31),
                current_compliance_score=85,
                current_risk_band=RiskBand.GREEN,
                company_status=CompanyStatus.ACTIVE,
                is_active=True,
                is_dormant=False,
                is_fdi_registered=False,
            )
        )
        session.add(
            Engagement(
                id=engagement_id,
                company_id=company_id,
                engagement_title="Concurrent quotation lock regression",
                engagement_type="COMPLIANCE_FILING",
                engagement_status=EngagementStatus.QUOTED,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                complexity=ComplexityLevel.MEDIUM,
                identified_date=today,
                quoted_date=today,
                estimated_fee_bdt=Decimal("100000.00"),
                quoted_fee_bdt=Decimal("100000.00"),
            )
        )
        session.add_all(
            [
                Quotation(
                    id=first_quote_id,
                    engagement_id=engagement_id,
                    company_id=company_id,
                    quotation_number=f"QLOCK-{first_quote_id.hex[:12].upper()}",
                    quotation_date=today,
                    valid_until=today + timedelta(days=30),
                    professional_fee_bdt=Decimal("100000.00"),
                    government_fee_bdt=Decimal("0.00"),
                    vat_bdt=Decimal("0.00"),
                    total_bdt=Decimal("100000.00"),
                    status="SENT",
                ),
                Quotation(
                    id=second_quote_id,
                    engagement_id=engagement_id,
                    company_id=company_id,
                    quotation_number=f"QLOCK-{second_quote_id.hex[:12].upper()}",
                    quotation_date=today,
                    valid_until=today + timedelta(days=30),
                    professional_fee_bdt=Decimal("120000.00"),
                    government_fee_bdt=Decimal("0.00"),
                    vat_bdt=Decimal("0.00"),
                    total_bdt=Decimal("120000.00"),
                    status="SENT",
                ),
            ]
        )
        await session.commit()

    return session_factory, user_id, company_id, engagement_id, first_quote_id, second_quote_id


async def _cleanup_concurrent_quotation_fixture(
    session_factory, user_id, company_id, engagement_id
):
    async with session_factory() as session:
        await set_admin_context(session)
        await session.execute(
            delete(Quotation).where(Quotation.engagement_id == engagement_id)
        )
        await session.execute(
            delete(Engagement).where(Engagement.id == engagement_id)
        )
        await session.execute(delete(Company).where(Company.id == company_id))
        await session.execute(delete(User).where(User.id == user_id))
        await session.commit()


async def _accept_in_independent_session(session_factory, user_id, quotation_id):
    async with session_factory() as session:
        await set_rls_context(session, str(user_id))
        try:
            quotation = await QuotationService(session).accept(quotation_id)
            if quotation is None:
                await session.rollback()
                return 404, None
            await session.commit()
            return 200, quotation.status
        except (CommercialConflictError, ValueError):
            await session.rollback()
            return 409, None


async def _reject_in_independent_session(
    session_factory, user_id, quotation_id
):
    async with session_factory() as session:
        await set_rls_context(session, str(user_id))
        try:
            quotation = await QuotationService(session).reject(
                quotation_id,
                reason="Concurrent rejection regression",
                rejected_by=user_id,
            )
            if quotation is None:
                await session.rollback()
                return 404, None
            await session.commit()
            return 200, quotation.status
        except (CommercialConflictError, ValueError):
            await session.rollback()
            return 409, None


@pytest.mark.asyncio
async def test_concurrent_competing_quotation_acceptance_is_serialized(test_engine):
    (
        session_factory,
        user_id,
        company_id,
        engagement_id,
        first_quote_id,
        second_quote_id,
    ) = await _seed_concurrent_quotation_fixture(test_engine)
    try:
        results = await asyncio.gather(
            _accept_in_independent_session(session_factory, user_id, first_quote_id),
            _accept_in_independent_session(session_factory, user_id, second_quote_id),
        )
        assert sorted(status for status, _ in results) == [200, 409]
        accepted = [value for status, value in results if status == 200]
        assert accepted == ["ACCEPTED"]
    finally:
        await _cleanup_concurrent_quotation_fixture(
            session_factory, user_id, company_id, engagement_id
        )


@pytest.mark.asyncio
async def test_concurrent_accept_and_reject_of_same_quotation_is_serialized(test_engine):
    (
        session_factory,
        user_id,
        company_id,
        engagement_id,
        first_quote_id,
        _second_quote_id,
    ) = await _seed_concurrent_quotation_fixture(test_engine)
    try:
        results = await asyncio.gather(
            _accept_in_independent_session(session_factory, user_id, first_quote_id),
            _reject_in_independent_session(session_factory, user_id, first_quote_id),
        )
        assert sorted(status for status, _ in results) == [200, 409]
        successful = [value for status, value in results if status == 200]
        assert successful[0] in {"ACCEPTED", "REJECTED"}
    finally:
        await _cleanup_concurrent_quotation_fixture(
            session_factory, user_id, company_id, engagement_id
        )


def test_quotation_accept_and_reject_lock_parent_before_locked_quotation():
    """Guard the required engagement-first lock order in both lifecycle paths."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    source = (root / "app" / "services" / "commercial_service.py").read_text(
        encoding="utf-8"
    )
    class_start = source.index("class QuotationService")
    for method_name in ("accept", "reject"):
        start = source.index(f"    async def {method_name}(", class_start)
        next_method = source.find("\n    async def ", start + 1)
        method = source[start: next_method if next_method >= 0 else len(source)]
        engagement_lock = method.index("select(Engagement)")
        quotation_lock = method.index("select(Quotation).where", method.index("with_for_update()", engagement_lock))
        assert engagement_lock < quotation_lock
        assert "with_for_update()" in method[engagement_lock:quotation_lock]
        assert "with_for_update()" in method[quotation_lock:]


@pytest.mark.asyncio
async def test_task_completion_requires_company_scope_and_runs_once(
    api_client, commercial_admin_token, db_company
):
    created = await api_client.post(
        "/api/v1/commercial/tasks",
        headers=_auth(commercial_admin_token),
        json={
            "company_id": str(db_company.id),
            "title": "Task completion tenant-scope regression",
            "priority": "MEDIUM",
        },
    )
    assert created.status_code == 201, created.text
    task_id = created.json()["task_id"]

    missing_scope = await api_client.patch(
        f"/api/v1/commercial/tasks/{task_id}/complete",
        headers=_auth(commercial_admin_token),
        json={"completion_note": "Missing company context"},
    )
    assert missing_scope.status_code == 422, missing_scope.text

    completed = await api_client.patch(
        f"/api/v1/commercial/tasks/{task_id}/complete?company_id={db_company.id}",
        headers=_auth(commercial_admin_token),
        json={"completion_note": "Completed once with authorized company context"},
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "COMPLETED"
    assert completed.json()["completed_at"] is not None

    repeated = await api_client.patch(
        f"/api/v1/commercial/tasks/{task_id}/complete?company_id={db_company.id}",
        headers=_auth(commercial_admin_token),
        json={"completion_note": "Duplicate completion must not be accepted"},
    )
    assert repeated.status_code == 409, repeated.text

    wrong_company = await api_client.patch(
        f"/api/v1/commercial/tasks/{task_id}/complete?company_id={uuid4()}",
        headers=_auth(commercial_admin_token),
        json={"completion_note": "Wrong company must not find this task"},
    )
    assert wrong_company.status_code == 404, wrong_company.text

