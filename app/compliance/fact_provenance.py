"""Trust provenance for company facts and uploaded compliance documents."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any
from uuid import UUID


class _StrEnum(str, Enum):
    def __str__(self) -> str:
        return str(self.value)


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
    record_id: str | None = None

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


# NLC internal evidence freshness policy (calendar days from observed_on).
# These are conservative product controls, not statutory filing deadlines.
FACT_MAX_AGE_DAYS: dict[str, int] = {
    "current_director_count": 30,
    "is_private_subsidiary_of_public_company": 90,
    "member_count": 30,
    "company_operating": 30,
    "name_change_pending": 30,
    "object_clause_change_pending": 30,
    "aoa_alteration_pending": 30,
    "register_of_members_maintained": 90,
    "register_of_directors_maintained": 90,
    "register_of_charges_maintained": 90,
    "minutes_book_agm_maintained": 90,
    "minutes_book_board_maintained": 90,
    "register_location": 90,
    "trade_license_obtained": 90,
    "trade_license_expiry": 365,
    "annual_return_filed": 365,
    "annual_return_content_complete": 365,
}


INTERNAL_PROFILE_FACT_KEYS = frozenset({
    "verified_fact_keys",
    "catalogue_binding_required",
    "catalogue_rule_versions",
    "catalogue_rule_active",
})


def is_internal_profile_fact_key(fact_key: str) -> bool:
    """Identify reviewer/system trust metadata that is never a user company fact."""
    key = fact_key.strip()
    return (
        key in INTERNAL_PROFILE_FACT_KEYS
        or key.startswith("catalogue_")
        or key.endswith((
            "_verified",
            "_verified_at",
            "_verified_by",
            "_evidence_ref",
            "_evidence_reference",
        ))
    )


FACT_NO_EXPIRY_KEYS = frozenset({
    # Immutable identifiers / dates. Other historical events require a recent
    # evidence observation (default 365 days) so newer events cannot be missed.
    "incorporation_date",
    "company_registration_number",
    "tin_obtained",
})


def fact_freshness_max_age_days(fact_key: str) -> int | None:
    """Return NLC's maximum age; unknown facts default to 365 days, not infinity."""
    if fact_key in FACT_NO_EXPIRY_KEYS:
        return None
    return FACT_MAX_AGE_DAYS.get(fact_key, 365)


def fact_freshness_status(fact_key: str, observed_on: date, as_of: date) -> str:
    """Classify whether a verified document fact is current enough for scoring."""
    if not isinstance(observed_on, date) or observed_on > as_of:
        return "FUTURE_DATED"
    max_age = fact_freshness_max_age_days(fact_key)
    if max_age is None:
        return "NOT_TIME_LIMITED"
    return "FRESH" if (as_of - observed_on).days <= max_age else "STALE"


def verified_document_fact_keys(facts: Any, *, as_of: date) -> frozenset[str]:
    """Only fresh authorized-document-backed VERIFIED facts may authorize scoring."""
    keys: set[str] = set()
    for fact in facts:
        trust_level = getattr(fact.trust_level, "value", fact.trust_level)
        verification_status = getattr(
            fact.verification_status, "value", fact.verification_status
        )
        if (
            not is_internal_profile_fact_key(fact.fact_key)
            and trust_level == FactTrustLevel.AUTHORIZED_DOCUMENT_BACKED.value
            and verification_status == FactVerificationStatus.VERIFIED.value
            and fact_freshness_status(fact.fact_key, fact.observed_on, as_of)
            in {"FRESH", "NOT_TIME_LIMITED"}
        ):
            keys.add(fact.fact_key)
    return frozenset(keys)


def _json_safe_fact_value(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _json_safe_fact_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe_fact_value(item) for item in value]
    return value


def fact_provenance_payload(fact: CompanyFact) -> dict[str, Any]:
    """JSON-safe provenance copied into immutable finding/evaluation snapshots."""
    return {
        "fact_id": fact.record_id,
        "fact_key": fact.fact_key,
        "fact_value": _json_safe_fact_value(fact.value),
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
        "disclosure": fact.finding_disclosure,
    }


def coerce_company_profile_fact_value(fact_key: str, value: Any) -> Any:
    """Validate JSON fact values against the declared scalar CompanyProfile field type."""
    from typing import get_args, get_type_hints

    from app.rule_engine import CompanyProfile

    annotation = get_type_hints(CompanyProfile).get(fact_key)
    if annotation is None:
        raise ValueError(f"Unsupported CompanyProfile fact key: {fact_key}")
    candidates = get_args(annotation) or (annotation,)
    if value is None:
        if type(None) in candidates:
            return None
        raise ValueError(f"Company fact {fact_key} cannot be null.")
    if datetime in candidates and isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"Company fact {fact_key} must be an ISO datetime.") from exc
    if date in candidates and isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"Company fact {fact_key} must be an ISO date.") from exc
    if bool in candidates and not isinstance(value, bool):
        if isinstance(value, str) and value.strip().lower() in {"true", "false"}:
            return value.strip().lower() == "true"
        raise ValueError(f"Company fact {fact_key} must be a boolean.")
    if int in candidates and (isinstance(value, bool) or not isinstance(value, int)):
        if isinstance(value, float) and not value.is_integer():
            raise ValueError(f"Company fact {fact_key} must be an integer.")
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Company fact {fact_key} must be an integer.") from exc
    if float in candidates and not isinstance(value, (int, float)):
        try:
            return float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Company fact {fact_key} must be numeric.") from exc
    if str in candidates and not isinstance(value, str):
        raise ValueError(f"Company fact {fact_key} must be a string.")
    return value
