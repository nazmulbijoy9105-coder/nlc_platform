"""
Real-database tenant isolation tests.

Each request uses a persisted CLIENT_DIRECTOR user and CompanyUserAccess rows.
The JWT deliberately advertises both tenant IDs; authorization must follow the
active database membership, not the caller-controlled/stale company_ids claim.
"""
import pytest
from app.core.security import create_access_token

pytestmark = [pytest.mark.integration]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_client_can_access_member_company_but_not_foreign_company(
    api_client, db_client_user, db_company, db_other_company
):
    token = create_access_token({
        "sub": str(db_client_user.id),
        "user_id": str(db_client_user.id),
        "type": "access",
        "role": "CLIENT_DIRECTOR",
        "email": db_client_user.email,
        # Intentionally include a foreign company to prove this claim is not
        # sufficient to grant access without an active DB membership.
        "company_ids": [str(db_company.id), str(db_other_company.id)],
    })

    own_response = await api_client.get(
        f"/api/v1/companies/{db_company.id}",
        headers=_auth(token),
    )
    assert own_response.status_code == 200, own_response.text

    foreign_response = await api_client.get(
        f"/api/v1/companies/{db_other_company.id}",
        headers=_auth(token),
    )
    assert foreign_response.status_code == 403, foreign_response.text


@pytest.mark.asyncio
async def test_client_membership_revocation_denies_company_access(
    api_client, db, db_client_user, db_company
):
    from sqlalchemy import update
    from app.models.company import CompanyUserAccess

    token = create_access_token({
        "sub": str(db_client_user.id),
        "user_id": str(db_client_user.id),
        "type": "access",
        "role": "CLIENT_DIRECTOR",
        "email": db_client_user.email,
        "company_ids": [str(db_company.id)],
    })

    await db.execute(
        update(CompanyUserAccess)
        .where(
            CompanyUserAccess.user_id == db_client_user.id,
            CompanyUserAccess.company_id == db_company.id,
        )
        .values(is_active=False)
    )
    await db.flush()

    response = await api_client.get(
        f"/api/v1/companies/{db_company.id}",
        headers=_auth(token),
    )
    assert response.status_code == 403, response.text

    # Revoked membership must also disappear from collection and filing
    # queries; stale CompanyUserAccess rows are not current authorization.
    companies_response = await api_client.get(
        "/api/v1/companies",
        headers=_auth(token),
    )
    assert companies_response.status_code == 200, companies_response.text
    assert str(db_company.id) not in str(companies_response.json())

    filings_response = await api_client.get(
        f"/api/v1/filings?company_id={db_company.id}",
        headers=_auth(token),
    )
    assert filings_response.status_code == 200, filings_response.text
    filings = filings_response.json()
    assert filings == {"agms": [], "audits": [], "annual_returns": []}

    documents_response = await api_client.get(
        f"/api/v1/documents/{db_company.id}",
        headers=_auth(token),
    )
    assert documents_response.status_code == 403, documents_response.text


@pytest.mark.asyncio
async def test_dashboard_risk_and_deadlines_are_scoped_and_revoke_immediately(
    api_client, db, db_user, db_company, db_other_company
):
    from datetime import date, timedelta
    from sqlalchemy import update
    from app.models.company import CompanyUserAccess
    from app.services.filing_service import AGMService

    # This staff user is intentionally assigned to only one of two companies.
    db.add(CompanyUserAccess(
        company_id=db_company.id,
        user_id=db_user.id,
        is_active=True,
    ))
    deadline = date.today() + timedelta(days=10)
    filing_service = AGMService(db)
    await filing_service.create_agm(
        company_id=db_company.id,
        financial_year=2025,
        agm_deadline=deadline,
    )
    await filing_service.create_agm(
        company_id=db_other_company.id,
        financial_year=2025,
        agm_deadline=deadline,
    )
    await db.flush()

    token = create_access_token({
        "sub": str(db_user.id),
        "user_id": str(db_user.id),
        "type": "access",
        "role": "ADMIN_STAFF",
        "email": db_user.email,
        # A stale/overbroad token claim must not reveal the foreign company.
        "company_ids": [str(db_company.id), str(db_other_company.id)],
    })
    headers = _auth(token)

    risk = await api_client.get("/api/v1/companies/dashboard/risk", headers=headers)
    assert risk.status_code == 200, risk.text
    assert sum(item["company_count"] for item in risk.json()) == 1

    deadlines = await api_client.get(
        "/api/v1/companies/dashboard/deadlines?days_ahead=30",
        headers=headers,
    )
    assert deadlines.status_code == 200, deadlines.text
    visible_ids = {str(item["company_id"]) for item in deadlines.json()}
    assert str(db_company.id) in visible_ids
    assert str(db_other_company.id) not in visible_ids

    await db.execute(
        update(CompanyUserAccess)
        .where(
            CompanyUserAccess.user_id == db_user.id,
            CompanyUserAccess.company_id == db_company.id,
        )
        .values(is_active=False)
    )
    await db.flush()

    risk_after_revoke = await api_client.get(
        "/api/v1/companies/dashboard/risk", headers=headers
    )
    assert risk_after_revoke.status_code == 200, risk_after_revoke.text
    assert risk_after_revoke.json() == []

    deadlines_after_revoke = await api_client.get(
        "/api/v1/companies/dashboard/deadlines?days_ahead=30",
        headers=headers,
    )
    assert deadlines_after_revoke.status_code == 200, deadlines_after_revoke.text
    assert str(db_company.id) not in {
        str(item["company_id"]) for item in deadlines_after_revoke.json()
    }
