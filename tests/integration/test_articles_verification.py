"""Integration coverage for the Articles of Association verification lifecycle."""
from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

import pytest

from app.models.company import CompanyUserAccess
from app.models.documents import ArticlesVerification, Document
from app.models.enums import DocumentType
from app.models.filings import AGM, AGMEvidenceVerification

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


@pytest.mark.asyncio
async def test_articles_pdf_upload_computes_checksum_and_stores_private_source(
    api_client, db, db_company, admin_headers, monkeypatch
):
    await _grant_staff_memberships(db, db_company.id)
    calls = {}

    class FakeS3:
        def put_object(self, **kwargs):
            calls.update(kwargs)

    import boto3
    monkeypatch.setattr(boto3, "client", lambda *args, **kwargs: FakeS3())

    payload = b"%PDF-1.7\\nNLC Articles source\\n%%EOF"
    response = await api_client.post(
        f"/api/v1/companies/{db_company.id}/articles-document",
        headers=admin_headers,
        files={"file": ("articles.pdf", payload, "application/pdf")},
    )
    assert response.status_code == 201, response.text
    result = response.json()

    import hashlib
    from app.models.documents import Document

    document = await db.get(Document, uuid.UUID(result["document_id"]))
    assert document is not None
    assert document.checksum_sha256 == hashlib.sha256(payload).hexdigest()
    assert document.document_type == DocumentType.ARTICLES_OF_ASSOCIATION
    assert document.ai_generated is False
    assert document.human_approved is False
    assert document.is_client_visible is False
    assert calls["ServerSideEncryption"] == "AES256"
    assert calls["Metadata"]["sha256"] == document.checksum_sha256


@pytest.mark.asyncio
async def test_articles_upload_rejects_non_pdf_payload(api_client, db, db_company, admin_headers):
    await _grant_staff_memberships(db, db_company.id)
    response = await api_client.post(
        f"/api/v1/companies/{db_company.id}/articles-document",
        headers=admin_headers,
        files={"file": ("articles.pdf", b"not a pdf", "application/pdf")},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_agm_quorum_uses_only_reviewed_version_pinned_register_evidence(
    api_client, db, db_company, admin_headers, legal_headers
):
    await _grant_staff_memberships(db, db_company.id)
    meeting_date = date(2025, 7, 1)
    agm = AGM(
        company_id=db_company.id,
        financial_year=2024,
        agm_deadline=date(2025, 6, 30),
    )
    db.add(agm)
    await db.flush()

    articles_document = await _articles_document(db, db_company.id)
    now = datetime.now(UTC)
    db.add(ArticlesVerification(
        company_id=db_company.id,
        document_id=articles_document.id,
        source_checksum_sha256=articles_document.checksum_sha256,
        source_document_version=articles_document.version,
        status="VERIFIED",
        submitted_by=_role_id("ADMIN_STAFF"),
        submitted_at=now,
        reviewed_by=_role_id("LEGAL_STAFF"),
        reviewed_at=now,
        effective_from=date(2020, 1, 1),
        quorum_variation_exists=False,
        quorum_required=None,
        clause_reference="Articles clause 18",
    ))
    member_doc = Document(
        company_id=db_company.id,
        document_type=DocumentType.OTHER,
        title="AGM_EVIDENCE:MEMBERS_REGISTER",
        s3_key=f"companies/{db_company.id}/members-register.pdf",
        checksum_sha256="c" * 64,
        version=1,
        ai_generated=False,
        is_active=True,
    )
    attendance_doc = Document(
        company_id=db_company.id,
        document_type=DocumentType.OTHER,
        title="AGM_EVIDENCE:ATTENDANCE_REGISTER",
        s3_key=f"companies/{db_company.id}/attendance-register.pdf",
        checksum_sha256="d" * 64,
        version=1,
        ai_generated=False,
        is_active=True,
    )
    db.add_all([member_doc, attendance_doc])
    await db.flush()

    member_submission = await api_client.post(
        f"/api/v1/companies/{db_company.id}/agm-evidence",
        headers=admin_headers,
        json={
            "agm_id": str(agm.id),
            "document_id": str(member_doc.id),
            "meeting_date": meeting_date.isoformat(),
            "evidence_kind": "MEMBERS_REGISTER",
        },
    )
    assert member_submission.status_code == 201, member_submission.text
    attendance_submission = await api_client.post(
        f"/api/v1/companies/{db_company.id}/agm-evidence",
        headers=admin_headers,
        json={
            "agm_id": str(agm.id),
            "document_id": str(attendance_doc.id),
            "meeting_date": meeting_date.isoformat(),
            "evidence_kind": "ATTENDANCE_REGISTER",
        },
    )
    assert attendance_submission.status_code == 201, attendance_submission.text

    member_review = await api_client.post(
        f"/api/v1/companies/{db_company.id}/agm-evidence/{member_submission.json()['id']}/review",
        headers=legal_headers,
        json={"decision": "VERIFIED", "verified_count": 7, "reviewer_note": "Seven members identified in the register."},
    )
    assert member_review.status_code == 200, member_review.text
    attendance_review = await api_client.post(
        f"/api/v1/companies/{db_company.id}/agm-evidence/{attendance_submission.json()['id']}/review",
        headers=legal_headers,
        json={"decision": "VERIFIED", "verified_count": 2, "reviewer_note": "Two qualifying members personally present."},
    )
    assert attendance_review.status_code == 200, attendance_review.text

    from app.services.filing_service import AGMService
    recorded = await AGMService(db).mark_held(
        agm_id=agm.id,
        agm_date=meeting_date,
        members_present=99,  # deliberately false caller input must be ignored
        auditor_reappointed=True,
        members_total_at_agm=99,
        members_total_evidence_ref="untrusted://caller-value",
        members_present_evidence_ref="untrusted://caller-value",
    )
    assert recorded is not None
    assert recorded.members_present == 2
    assert recorded.members_total_at_agm == 7
    assert recorded.quorum_required == 3
    assert recorded.quorum_met is False
    assert recorded.quorum_basis == "SECTION_85_2_B_DEFAULT_ARTICLES_VERIFIED_NO_VARIATION"
    assert recorded.members_total_evidence_ref == f"document:{member_doc.id}:sha256:{'c' * 64}"
    assert recorded.members_present_evidence_ref == f"document:{attendance_doc.id}:sha256:{'d' * 64}"


@pytest.mark.asyncio
async def test_agm_evidence_submitter_cannot_review_and_invalid_counts_are_rejected(
    api_client, db, db_company, admin_headers, legal_headers
):
    await _grant_staff_memberships(db, db_company.id)
    agm = AGM(company_id=db_company.id, financial_year=2025)
    db.add(agm)
    document = Document(
        company_id=db_company.id,
        document_type=DocumentType.OTHER,
        title="AGM_EVIDENCE:MEMBERS_REGISTER",
        s3_key=f"companies/{db_company.id}/members-register-self-review.pdf",
        checksum_sha256="e" * 64,
        version=1,
        ai_generated=False,
        is_active=True,
    )
    db.add(document)
    await db.flush()
    submitted = await api_client.post(
        f"/api/v1/companies/{db_company.id}/agm-evidence",
        headers=legal_headers,
        json={
            "agm_id": str(agm.id),
            "document_id": str(document.id),
            "meeting_date": "2025-07-01",
            "evidence_kind": "MEMBERS_REGISTER",
        },
    )
    assert submitted.status_code == 201, submitted.text
    self_review = await api_client.post(
        f"/api/v1/companies/{db_company.id}/agm-evidence/{submitted.json()['id']}/review",
        headers=legal_headers,
        json={"decision": "VERIFIED", "verified_count": 5, "reviewer_note": "Self-review must be prohibited."},
    )
    assert self_review.status_code == 403
