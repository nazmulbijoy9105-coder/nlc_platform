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
    assert payload["fact_value"] == "2020-01-01"
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



def test_current_status_fact_freshness_is_rule_key_specific():
    from datetime import date, timedelta

    from app.compliance.fact_provenance import fact_freshness_status

    today = date(2026, 11, 21)
    assert fact_freshness_status("member_count", today - timedelta(days=30), today) == "FRESH"
    assert fact_freshness_status("member_count", today - timedelta(days=31), today) == "STALE"
    assert fact_freshness_status("register_of_members_maintained", today - timedelta(days=90), today) == "FRESH"
    assert fact_freshness_status("register_of_members_maintained", today - timedelta(days=91), today) == "STALE"
    assert fact_freshness_status("last_agm_date", today - timedelta(days=900), today) == "STALE"
    assert fact_freshness_status("incorporation_date", today - timedelta(days=900), today) == "NOT_TIME_LIMITED"
    assert fact_freshness_status("member_count", today + timedelta(days=1), today) == "FUTURE_DATED"
    assert fact_freshness_status("unclassified_fact_key", today - timedelta(days=365), today) == "FRESH"
    assert fact_freshness_status("unclassified_fact_key", today - timedelta(days=366), today) == "STALE"


def test_only_fresh_verified_document_facts_authorize_scoring():
    from datetime import date, datetime, timedelta, timezone

    from app.compliance.fact_provenance import (
        CompanyFact,
        FactTrustLevel,
        FactVerificationStatus,
        verified_document_fact_keys,
    )

    today = date(2026, 11, 21)

    def verified_fact(key: str, observed_on: date) -> CompanyFact:
        return CompanyFact(
            fact_key=key,
            value=5,
            trust_level=FactTrustLevel.AUTHORIZED_DOCUMENT_BACKED,
            asserted_by="user-1",
            observed_on=observed_on,
            source_reference="document:123",
            document_id="doc-123",
            authorized_uploader_id="user-1",
            uploaded_at=datetime(2026, 11, 20, tzinfo=timezone.utc),
            verification_status=FactVerificationStatus.VERIFIED,
            verified_by="reviewer-1",
            verified_at=datetime(2026, 11, 21, tzinfo=timezone.utc),
        )

    facts = [
        verified_fact("member_count", today - timedelta(days=31)),
        verified_fact("last_agm_date", today - timedelta(days=900)),
        verified_fact("incorporation_date", today - timedelta(days=900)),
    ]
    assert verified_document_fact_keys(facts, as_of=today) == frozenset({"incorporation_date"})
