from datetime import date, datetime, timezone

import pytest

from app.compliance.fact_provenance import (
    CompanyFact, FactTrustLevel, FactVerificationStatus, fact_provenance_payload,
)


def test_user_asserted_fact_is_explicitly_unverified():
    fact = CompanyFact(
        fact_key="incorporation_date",
        value="2020-01-01",
        trust_level=FactTrustLevel.USER_ASSERTED,
        asserted_by="company-user-1",
        observed_on=date(2026, 11, 11),
    )
    assert fact.finding_disclosure.startswith("Based on user-asserted")
    assert fact.verification_status is FactVerificationStatus.UNVERIFIED


def test_user_asserted_fact_cannot_claim_document_verification():
    with pytest.raises(ValueError, match="cannot be marked document-verified"):
        CompanyFact(
            fact_key="incorporation_date",
            value="2020-01-01",
            trust_level=FactTrustLevel.USER_ASSERTED,
            asserted_by="company-user-1",
            observed_on=date(2026, 11, 11),
            verification_status=FactVerificationStatus.VERIFIED,
            verified_by="reviewer-1",
            verified_at=datetime.now(timezone.utc),
        )


def test_authorized_document_backed_fact_requires_full_upload_provenance():
    with pytest.raises(ValueError, match="require document"):
        CompanyFact(
            fact_key="incorporation_date",
            value="2020-01-01",
            trust_level=FactTrustLevel.AUTHORIZED_DOCUMENT_BACKED,
            asserted_by="company-user-1",
            observed_on=date(2026, 11, 11),
        )


def test_uploaded_document_is_not_automatically_verified():
    fact = CompanyFact(
        fact_key="incorporation_date",
        value="2020-01-01",
        trust_level=FactTrustLevel.AUTHORIZED_DOCUMENT_BACKED,
        asserted_by="company-user-1",
        observed_on=date(2026, 11, 11),
        source_reference="upload:certificate-1",
        document_id="document-1",
        authorized_uploader_id="company-admin-1",
        uploaded_at=datetime(2026, 11, 11, 10, tzinfo=timezone.utc),
    )
    assert not fact.is_verified_document_fact
    assert "not yet been verified" in fact.finding_disclosure


def test_verified_document_fact_requires_verifier_and_timestamp():
    with pytest.raises(ValueError, match="require verifier identity"):
        CompanyFact(
            fact_key="incorporation_date",
            value="2020-01-01",
            trust_level=FactTrustLevel.AUTHORIZED_DOCUMENT_BACKED,
            asserted_by="company-user-1",
            observed_on=date(2026, 11, 11),
            source_reference="upload:certificate-1",
            document_id="document-1",
            authorized_uploader_id="company-admin-1",
            uploaded_at=datetime(2026, 11, 11, 10, tzinfo=timezone.utc),
            verification_status=FactVerificationStatus.VERIFIED,
        )


def test_verified_document_fact_carries_verifier_and_finding_disclosure():
    fact = CompanyFact(
        fact_key="incorporation_date",
        value="2020-01-01",
        trust_level=FactTrustLevel.AUTHORIZED_DOCUMENT_BACKED,
        asserted_by="company-user-1",
        observed_on=date(2026, 11, 11),
        source_reference="upload:certificate-1",
        document_id="document-1",
        authorized_uploader_id="company-admin-1",
        uploaded_at=datetime(2026, 11, 11, 10, tzinfo=timezone.utc),
        verification_status=FactVerificationStatus.VERIFIED,
        verified_by="reviewer-1",
        verified_at=datetime(2026, 11, 12, 9, tzinfo=timezone.utc),
        verification_note="Certificate number and company name matched.",
    )
    assert fact.is_verified_document_fact
    payload = fact_provenance_payload(fact)
    assert payload["trust_level"] == "AUTHORIZED_DOCUMENT_BACKED"
    assert payload["verified_by"] == "reviewer-1"
    assert "checked by the recorded verifier" in payload["finding_disclosure"]


def test_verification_metadata_cannot_be_attached_to_unverified_document():
    with pytest.raises(ValueError, match="only valid for VERIFIED"):
        CompanyFact(
            fact_key="incorporation_date",
            value="2020-01-01",
            trust_level=FactTrustLevel.AUTHORIZED_DOCUMENT_BACKED,
            asserted_by="company-user-1",
            observed_on=date(2026, 11, 11),
            source_reference="upload:certificate-1",
            document_id="document-1",
            authorized_uploader_id="company-admin-1",
            uploaded_at=datetime(2026, 11, 11, 10, tzinfo=timezone.utc),
            verified_by="reviewer-1",
            verified_at=datetime(2026, 11, 12, 9, tzinfo=timezone.utc),
        )
