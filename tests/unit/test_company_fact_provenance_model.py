from datetime import date, datetime, timezone
import uuid

from app.models.company_fact import CompanyFact


def _document_fact(**overrides) -> CompanyFact:
    values = {
        "id": uuid.uuid4(),
        "company_id": uuid.uuid4(),
        "fact_key": "incorporation_date",
        "fact_value": "2020-01-15",
        "trust_level": "AUTHORIZED_DOCUMENT_BACKED",
        "asserted_by": uuid.uuid4(),
        "observed_on": date(2026, 11, 11),
        "source_reference": "document:incorporation-certificate",
        "document_id": uuid.uuid4(),
        "authorized_uploader_id": uuid.uuid4(),
        "uploaded_at": datetime(2026, 11, 10, tzinfo=timezone.utc),
        "verification_status": "UNVERIFIED",
    }
    values.update(overrides)
    return CompanyFact(**values)


def test_uploaded_document_fact_is_not_automatically_verified() -> None:
    payload = _document_fact().provenance_payload()

    assert payload["trust_level"] == "AUTHORIZED_DOCUMENT_BACKED"
    assert payload["verification_status"] == "UNVERIFIED"
    assert "not yet been verified" in payload["disclosure"]
    assert payload["document_id"]


def test_verified_document_fact_retains_reviewer_and_timestamp() -> None:
    reviewer_id = uuid.uuid4()
    verified_at = datetime(2026, 11, 11, 10, 0, tzinfo=timezone.utc)
    payload = _document_fact(
        verification_status="VERIFIED",
        verified_by=reviewer_id,
        verified_at=verified_at,
    ).provenance_payload()

    assert payload["verified_by"] == str(reviewer_id)
    assert payload["verified_at"] == verified_at.isoformat()
    assert "checked by the recorded verifier" in payload["disclosure"]


def test_user_asserted_fact_discloses_unverified_origin() -> None:
    payload = CompanyFact(
        id=uuid.uuid4(),
        company_id=uuid.uuid4(),
        fact_key="registered_office_address",
        fact_value={"address": "Dhaka"},
        trust_level="USER_ASSERTED",
        asserted_by=uuid.uuid4(),
        observed_on=date(2026, 11, 11),
        source_reference="company-profile",
        verification_status="UNVERIFIED",
    ).provenance_payload()

    assert payload["trust_level"] == "USER_ASSERTED"
    assert payload["document_id"] is None
    assert "not independently verified" in payload["disclosure"]
