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
