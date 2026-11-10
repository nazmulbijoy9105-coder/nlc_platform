"""Orthogonal obligation state and provenance primitives for continuous compliance.

Framework-independent invariants for the AGM / annual-return / auditor slice.
Dates are Bangladesh-local legal dates supplied by the caller. effective_to
is exclusive: effective_from <= date < effective_to.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from app.compliance.fact_provenance import (
    CompanyFact as FactProvenance,
    FactTrustLevel,
    FactVerificationStatus,
    fact_provenance_payload,
)


class _StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class Applicability(_StrEnum):
    APPLIES = "APPLIES"
    DOES_NOT_APPLY = "DOES_NOT_APPLY"
    UNKNOWN = "UNKNOWN"


class EvidenceState(_StrEnum):
    VERIFIED_PRESENT = "VERIFIED_PRESENT"
    VERIFIED_ABSENT = "VERIFIED_ABSENT"
    NOT_PROVIDED = "NOT_PROVIDED"
    CONFLICTING = "CONFLICTING"


class ObligationStatus(_StrEnum):
    NOT_YET_DUE = "NOT_YET_DUE"
    DUE_SOON = "DUE_SOON"
    COMPLIANT = "COMPLIANT"
    FILED_LATE = "FILED_LATE"
    OVERDUE = "OVERDUE"
    DISPUTED = "DISPUTED"
    WAIVED = "WAIVED"
    EXEMPTED = "EXEMPTED"


@dataclass(frozen=True)
class ObligationState:
    applicability: Applicability
    evidence: EvidenceState
    status: ObligationStatus
    evidence_source: str | None = None
    evidence_checked_on: date | None = None
    statutory_deadline: date | None = None
    filed_on: date | None = None

    def __post_init__(self) -> None:
        if self.evidence is EvidenceState.VERIFIED_ABSENT:
            if not self.evidence_source or not self.evidence_source.strip():
                raise ValueError("verified absence requires a named source")
            if self.evidence_checked_on is None:
                raise ValueError("verified absence requires the verification date")
        if self.status is ObligationStatus.FILED_LATE:
            if self.filed_on is None or self.statutory_deadline is None:
                raise ValueError("FILED_LATE requires filed_on and statutory_deadline")
            if self.filed_on <= self.statutory_deadline:
                raise ValueError("FILED_LATE requires filing after the statutory deadline")
            if self.evidence is not EvidenceState.VERIFIED_PRESENT:
                raise ValueError("FILED_LATE requires verified filing evidence")
        if self.status is ObligationStatus.COMPLIANT:
            if self.applicability is not Applicability.APPLIES:
                raise ValueError("COMPLIANT requires an applicable obligation")
            if self.evidence is not EvidenceState.VERIFIED_PRESENT:
                raise ValueError("COMPLIANT requires verified-present evidence")
        if self.status is ObligationStatus.EXEMPTED:
            if self.applicability is not Applicability.DOES_NOT_APPLY:
                raise ValueError("EXEMPTED requires DOES_NOT_APPLY applicability")
        if self.status is ObligationStatus.WAIVED:
            if self.applicability is not Applicability.APPLIES:
                raise ValueError("WAIVED requires an otherwise applicable obligation")
        if self.applicability is Applicability.DOES_NOT_APPLY and self.status in (
            ObligationStatus.OVERDUE, ObligationStatus.FILED_LATE
        ):
            raise ValueError("non-applicable obligations cannot be overdue or filed late")


@dataclass(frozen=True)
class ApplicabilityResolutionTask:
    obligation_id: str
    owner_id: str
    due_on: date
    questionnaire_key: str
    document_request_key: str
    escalation_after_days: int = 14

    def __post_init__(self) -> None:
        if not all((self.obligation_id, self.owner_id, self.questionnaire_key,
                    self.document_request_key)):
            raise ValueError("resolution task requires obligation, owner, questionnaire and document request")
        if self.escalation_after_days < 1:
            raise ValueError("escalation_after_days must be positive")


@dataclass(frozen=True)
class LegalRuleSnapshot:
    rule_id: str
    rule_version: str
    catalogue_version: str
    effective_from: date
    effective_to: date | None
    statutory_citation: str
    verification_status: str
    verified_by: str | None
    verified_at: date | None

    def __post_init__(self) -> None:
        if not all((self.rule_id, self.rule_version, self.catalogue_version,
                    self.statutory_citation)):
            raise ValueError("rule identity, versions and statutory citation are required")
        if self.effective_to is not None and self.effective_to <= self.effective_from:
            raise ValueError("effective_to is exclusive and must follow effective_from")

    @property
    def may_generate_findings(self) -> bool:
        # Reuses existing LegalRule verification metadata; no parallel approval gate.
        return (
            self.verification_status.upper() == "VERIFIED"
            and bool(self.verified_by)
            and self.verified_at is not None
        )

    def is_in_force_on(self, relevant_date: date) -> bool:
        return (
            self.effective_from <= relevant_date
            and (self.effective_to is None or relevant_date < self.effective_to)
        )


@dataclass(frozen=True)
class ObligationFinding:
    obligation_id: str
    rule_id: str
    rule_version: str
    catalogue_version: str
    assessed_under_law_date: date
    facts: tuple[FactProvenance, ...]
    state: ObligationState

    def __post_init__(self) -> None:
        if not all((self.obligation_id, self.rule_id, self.rule_version,
                    self.catalogue_version)):
            raise ValueError("finding must pin obligation, rule and catalogue versions")
        if not self.facts:
            raise ValueError("finding must retain at least one fact provenance record")

    @property
    def contains_unverified_facts(self) -> bool:
        return any(
            f.trust_level is FactTrustLevel.USER_ASSERTED
            or f.verification_status is not FactVerificationStatus.VERIFIED
            for f in self.facts
        )

    @property
    def fact_provenance_snapshot(self) -> tuple[dict[str, str | None], ...]:
        """Serializable immutable provenance to persist with the finding."""
        return tuple(fact_provenance_payload(fact) for fact in self.facts)

    @property
    def fact_basis_disclosure(self) -> tuple[str, ...]:
        """Human-readable trust disclosures to render alongside every finding."""
        return tuple(
            f"{fact.fact_key}: {fact.finding_disclosure}"
            for fact in self.facts
        )
