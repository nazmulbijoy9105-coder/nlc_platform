"""Trust provenance for company facts and uploaded compliance documents."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any


class _StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class FactTrustLevel(_StrEnum):
    USER_ASSERTED = "USER_ASSERTED"
    AUTHORIZED_DOCUMENT_BACKED = "AUTHORIZED_DOCUMENT_BACKED"


class FactVerificationStatus(_StrEnum):
    UNVERIFIED = "UNVERIFIED"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"


@dataclass(frozen=True)
class CompanyFact:
    """A fact value plus the provenance needed to explain downstream findings."""

    fact_key: str
    value: Any
    trust_level: FactTrustLevel
    asserted_by: str
    observed_on: date
    source_reference: str | None = None
    document_id: str | None = None
    authorized_uploader_id: str | None = None
    uploaded_at: datetime | None = None
    verification_status: FactVerificationStatus = FactVerificationStatus.UNVERIFIED
    verified_by: str | None = None
    verified_at: datetime | None = None
    verification_note: str | None = None

    def __post_init__(self) -> None:
        if not self.fact_key.strip() or not self.asserted_by.strip():
            raise ValueError("fact_key and asserted_by are required")
        if self.trust_level is FactTrustLevel.USER_ASSERTED:
            if any((self.document_id, self.authorized_uploader_id, self.uploaded_at)):
                raise ValueError("user-asserted facts cannot claim document provenance")
            if self.verification_status is FactVerificationStatus.VERIFIED:
                raise ValueError("user-asserted facts cannot be marked document-verified")
        if self.trust_level is FactTrustLevel.AUTHORIZED_DOCUMENT_BACKED:
            if not all((self.document_id, self.authorized_uploader_id,
                        self.uploaded_at, self.source_reference)):
                raise ValueError(
                    "authorized document-backed facts require document, authorized uploader, "
                    "upload timestamp and source reference"
                )
        if self.verification_status is FactVerificationStatus.VERIFIED:
            if not self.verified_by or self.verified_at is None:
                raise ValueError("verified facts require verifier identity and timestamp")
        elif self.verified_by or self.verified_at:
            raise ValueError("verification metadata is only valid for VERIFIED facts")

    @property
    def is_verified_document_fact(self) -> bool:
        return (
            self.trust_level is FactTrustLevel.AUTHORIZED_DOCUMENT_BACKED
            and self.verification_status is FactVerificationStatus.VERIFIED
        )

    @property
    def finding_disclosure(self) -> str:
        if self.trust_level is FactTrustLevel.USER_ASSERTED:
            return "Based on user-asserted information; not independently verified."
        if self.verification_status is FactVerificationStatus.VERIFIED:
            return "Based on an authorized document checked by the recorded verifier."
        if self.verification_status is FactVerificationStatus.REJECTED:
            return "Supporting document was reviewed and rejected; this fact is unverified."
        if self.verification_status is FactVerificationStatus.SUPERSEDED:
            return "Supporting document was superseded; use the current fact record."
        return "Based on an authorized upload that has not yet been verified."


def fact_provenance_payload(fact: CompanyFact) -> dict[str, Any]:
    """JSON-safe provenance copied into immutable finding/evaluation snapshots."""
    return {
        "fact_key": fact.fact_key,
        "trust_level": fact.trust_level.value,
        "asserted_by": fact.asserted_by,
        "observed_on": fact.observed_on.isoformat(),
        "source_reference": fact.source_reference,
        "document_id": fact.document_id,
        "authorized_uploader_id": fact.authorized_uploader_id,
        "uploaded_at": fact.uploaded_at.isoformat() if fact.uploaded_at else None,
        "verification_status": fact.verification_status.value,
        "verified_by": fact.verified_by,
        "verified_at": fact.verified_at.isoformat() if fact.verified_at else None,
        "verification_note": fact.verification_note,
        "finding_disclosure": fact.finding_disclosure,
    }
