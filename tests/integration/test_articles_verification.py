"""Integration coverage for the Articles of Association verification lifecycle."""
from __future__ import annotations

import uuid

import pytest

from app.models.company import CompanyUserAccess
from app.models.documents import Document
from app.models.enums import DocumentType

pytestmark = [pytest.mark.integration]


def _role_id(role: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_DNS, f"nlc-test-user-{role}")


async def _grant_staff_memberships(db, company_id):
    for role in ("ADMIN_STAFF", "LEGAL_STAFF", "SUPER_ADMIN"):
        db.add(CompanyUserAccess(
            user_id=_role_id(role),
            company_id=company_id,
            can_edit=True,
            can_view_financials=True,
            is_active=True,
        ))
    await db.flush()


async def _articles_document(db, company_id):
    document = Document(
        company_id=company_id,
        document_type=DocumentType.ARTICLES_OF_ASSOCIATION,
        title="Executed Articles of Association",
        s3_key=f"companies/{company_id}/articles/executed.pdf",
        checksum_sha256="a" * 64,
        version=1,
        ai_generated=False,
        human_approved=True,
        in_review_queue=False,
        auto_sent_blocked=True,
        is_client_visible=False,
        is_active=True,
    )
    db.add(document)
    await db.flush()
    return document


@pytest.mark.asyncio
async def test_articles_verification_submit_review_revoke_and_event_history(
    api_client, db, db_company, admin_headers, legal_headers, super_admin_headers
):
    await _grant_staff_memberships(db, db_company.id)
    document = await _articles_document(db, db_company.id)

    submitted = await api_client.post(
        f"/api/v1/companies/{db_company.id}/articles-verification",
        headers=admin_headers,
        json={"document_id": str(document.id)},
    )
    assert submitted.status_code == 201, submitted.text
    verification = submitted.json()
    assert verification["status"] == "PENDING"
    assert verification["source_checksum_sha256"] == "a" * 64
    assert verification["source_document_version"] == 1

    reviewed = await api_client.post(
        f"/api/v1/companies/{db_company.id}/articles-verification/{verification['id']}/review",
        headers=legal_headers,
        json={
            "decision": "VERIFIED",
            "effective_from": "2020-01-01",
            "quorum_variation_exists": False,
            "quorum_required": None,
            "clause_reference": "Articles clause 18",
            "reviewer_note": "Source and quorum clause checked against the executed document.",
        },
    )
    assert reviewed.status_code == 200, reviewed.text
    assert reviewed.json()["status"] == "VERIFIED"
    assert reviewed.json()["reviewed_by"] != verification["submitted_by"]

    from app.services.company_service import CompanyService
    verified_profile = await CompanyService(db).build_company_profile(db_company.id)
    assert verified_profile["articles_quorum_verified"] is True
    assert verified_profile["articles_quorum_required"] is None
    assert verified_profile["articles_quorum_verified_by"] == reviewed.json()["reviewed_by"]

    second_document = await _articles_document(db, db_company.id)
    second_document.checksum_sha256 = "b" * 64
    second_document.title = "Amended Articles of Association"
    await db.flush()
    second_submission = await api_client.post(
        f"/api/v1/companies/{db_company.id}/articles-verification",
        headers=admin_headers,
        json={"document_id": str(second_document.id)},
    )
    assert second_submission.status_code == 201, second_submission.text
    second_verification = second_submission.json()
    assert second_verification["status"] == "PENDING"

    second_review = await api_client.post(
        f"/api/v1/companies/{db_company.id}/articles-verification/{second_verification['id']}/review",
        headers=legal_headers,
        json={
            "decision": "VERIFIED",
            "effective_from": "2021-01-01",
            "quorum_variation_exists": True,
            "quorum_required": 3,
            "clause_reference": "Amended Articles clause 21",
            "quorum_clause_text": "The quorum for a general meeting shall be three members personally present.",
            "reviewer_note": "Amended quorum provision checked against the executed amended document.",
        },
    )
    assert second_review.status_code == 200, second_review.text
    assert second_review.json()["status"] == "VERIFIED"

    old_events = await api_client.get(
        f"/api/v1/companies/{db_company.id}/articles-verification/{verification['id']}/events",
        headers=admin_headers,
    )
    assert [event["action"] for event in old_events.json()] == [
        "SUBMITTED", "VERIFIED", "SUPERSEDED"
    ]
    amended_profile = await CompanyService(db).build_company_profile(db_company.id)
    assert amended_profile["articles_quorum_verified"] is True
    assert amended_profile["articles_quorum_required"] == 3
    assert second_document.id.__str__() in amended_profile["articles_quorum_evidence_ref"]

    revoked = await api_client.post(
        f"/api/v1/companies/{db_company.id}/articles-verification/{second_verification['id']}/revoke",
        headers=super_admin_headers,
        json={"reason": "The executed amended Articles were superseded by a newly registered version."},
    )
    assert revoked.status_code == 200, revoked.text
    assert revoked.json()["status"] == "REVOKED"
    assert revoked.json()["revocation_reason"]

    revoked_profile = await CompanyService(db).build_company_profile(db_company.id)
    assert revoked_profile["articles_quorum_verified"] is False
    assert revoked_profile["articles_quorum_required"] is None

    final_events = await api_client.get(
        f"/api/v1/companies/{db_company.id}/articles-verification/{second_verification['id']}/events",
        headers=admin_headers,
    )
    assert [event["action"] for event in final_events.json()] == [
        "SUBMITTED", "VERIFIED", "REVOKED"
    ]


@pytest.mark.asyncio
async def test_articles_submitter_cannot_self_review(api_client, db, db_company, legal_headers):
    await _grant_staff_memberships(db, db_company.id)
    document = await _articles_document(db, db_company.id)

    submitted = await api_client.post(
        f"/api/v1/companies/{db_company.id}/articles-verification",
        headers=legal_headers,
        json={"document_id": str(document.id)},
    )
    assert submitted.status_code == 201, submitted.text
    verification_id = submitted.json()["id"]

    reviewed = await api_client.post(
        f"/api/v1/companies/{db_company.id}/articles-verification/{verification_id}/review",
        headers=legal_headers,
        json={
            "decision": "VERIFIED",
            "effective_from": "2020-01-01",
            "quorum_variation_exists": False,
            "clause_reference": "Articles clause 18",
        },
    )
    assert reviewed.status_code == 403


@pytest.mark.asyncio
async def test_articles_submission_can_be_rejected_without_verified_only_fields(
    api_client, db, db_company, admin_headers, legal_headers
):
    await _grant_staff_memberships(db, db_company.id)
    document = await _articles_document(db, db_company.id)
    submitted = await api_client.post(
        f"/api/v1/companies/{db_company.id}/articles-verification",
        headers=admin_headers,
        json={"document_id": str(document.id)},
    )
    assert submitted.status_code == 201, submitted.text

    rejected = await api_client.post(
        f"/api/v1/companies/{db_company.id}/articles-verification/{submitted.json()['id']}/review",
        headers=legal_headers,
        json={
            "decision": "REJECTED",
            "reviewer_note": "The submitted copy is not sufficiently authenticated.",
        },
    )
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["status"] == "REJECTED"
    assert rejected.json()["effective_from"] is None
    assert rejected.json()["clause_reference"] is None
