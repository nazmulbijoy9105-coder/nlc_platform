"""Governance gate for server-side finding-context catalogue entries.

This module records the provenance and independent legal-review state of a
RuleFindingContext. It does not decide legal meaning, validate statutory
interpretation, or activate statutory scoring.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from types import MappingProxyType
from typing import Mapping, Sequence
from uuid import UUID

from app.rule_engine.canonical_identity import canonical_definition_hash
from app.rule_engine.finding_context import RuleFindingContext


_REVIEW_STATES = {"REVIEW_REQUIRED", "APPROVED", "REJECTED"}


def _required_text(value: object, field: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    normalized = value.strip()
    if not normalized or len(normalized) > maximum:
        raise ValueError(f"{field} must contain 1 to {maximum} non-whitespace characters")
    return normalized


def _actor_id(value: object, field: str) -> str:
    try:
        return str(UUID(str(value)))
    except (TypeError, ValueError, AttributeError) as exc:
        raise ValueError(f"{field} must be a UUID") from exc


def _aware_datetime(value: object, field: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be a timezone-aware datetime")
    return value


def context_payload(context: RuleFindingContext) -> dict:
    """Return the complete, stable legal-operational context payload."""
    return {
        "historical_rule_id": context.historical_rule_id,
        "source_namespace": context.source_namespace,
        "jurisdiction": context.jurisdiction,
        "effective_date": context.effective_date.isoformat(),
        "effective_date_basis": context.effective_date_basis,
        "effective_date_source_ref": context.effective_date_source_ref,
        "required_fact_keys": list(context.required_fact_keys),
        "evidence_roles_by_fact_key": dict(context.evidence_roles_by_fact_key),
    }


def finding_context_digest(context: RuleFindingContext) -> str:
    """Digest all context fields; any post-review change invalidates approval."""
    return canonical_definition_hash({"finding_context": context_payload(context)})


@dataclass(frozen=True, slots=True)
class GovernedRuleFindingContext:
    """A context plus source provenance and independent legal-review evidence."""

    context: RuleFindingContext
    source_instrument: str
    source_provision: str
    authored_by: str
    authored_at: datetime
    review_status: str = "REVIEW_REQUIRED"
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    review_basis: str | None = None
    reviewed_context_sha256: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.context, RuleFindingContext):
            raise ValueError("context must be RuleFindingContext")
        object.__setattr__(
            self, "source_instrument",
            _required_text(self.source_instrument, "source_instrument", 500),
        )
        object.__setattr__(
            self, "source_provision",
            _required_text(self.source_provision, "source_provision", 255),
        )
        object.__setattr__(self, "authored_by", _actor_id(self.authored_by, "authored_by"))
        object.__setattr__(self, "authored_at", _aware_datetime(self.authored_at, "authored_at"))
        state = _required_text(self.review_status, "review_status", 32).upper()
        if state not in _REVIEW_STATES:
            raise ValueError("review_status must be REVIEW_REQUIRED, APPROVED or REJECTED")
        object.__setattr__(self, "review_status", state)

        if state == "REVIEW_REQUIRED":
            if any(value is not None for value in (
                self.reviewed_by, self.reviewed_at, self.review_basis,
                self.reviewed_context_sha256,
            )):
                raise ValueError("Unreviewed context cannot carry legal-review fields")
            return

        if state == "REJECTED":
            if self.reviewed_by is None or self.reviewed_at is None or not self.review_basis:
                raise ValueError("Rejected context requires reviewer, timestamp and review basis")
            object.__setattr__(self, "reviewed_by", _actor_id(self.reviewed_by, "reviewed_by"))
            object.__setattr__(self, "reviewed_at", _aware_datetime(self.reviewed_at, "reviewed_at"))
            object.__setattr__(self, "review_basis", _required_text(self.review_basis, "review_basis", 2000))
            if self.reviewed_context_sha256 is not None:
                raise ValueError("Rejected context must not carry an approval digest")
            return

        if self.reviewed_by is None or self.reviewed_at is None or not self.review_basis:
            raise ValueError("Approved context requires reviewer, timestamp and review basis")
        reviewer = _actor_id(self.reviewed_by, "reviewed_by")
        if reviewer == self.authored_by:
            raise ValueError("Legal reviewer must be independent of the context author")
        reviewed_at = _aware_datetime(self.reviewed_at, "reviewed_at")
        if reviewed_at < self.authored_at:
            raise ValueError("reviewed_at cannot precede authored_at")
        digest = _required_text(self.reviewed_context_sha256, "reviewed_context_sha256", 64).lower()
        if digest != finding_context_digest(self.context):
            raise ValueError("Review digest does not match the exact current context")
        object.__setattr__(self, "reviewed_by", reviewer)
        object.__setattr__(self, "reviewed_at", reviewed_at)
        object.__setattr__(self, "review_basis", _required_text(self.review_basis, "review_basis", 2000))
        object.__setattr__(self, "reviewed_context_sha256", digest)

    @property
    def is_usable_for_binding(self) -> bool:
        """Only independently reviewed, exact-digest contexts pass this gate."""
        return (
            self.review_status == "APPROVED"
            and self.reviewed_by != self.authored_by
            and self.reviewed_context_sha256 == finding_context_digest(self.context)
        )


@dataclass(frozen=True, slots=True)
class GovernedFindingContextCatalog:
    """Immutable catalogue snapshot; approval is checked per emitted rule."""

    catalog_version: str
    entries_by_rule_id: Mapping[str, GovernedRuleFindingContext]

    def __post_init__(self) -> None:
        version = _required_text(self.catalog_version, "catalog_version", 100)
        if not isinstance(self.entries_by_rule_id, Mapping):
            raise ValueError("entries_by_rule_id must be a mapping")
        entries: dict[str, GovernedRuleFindingContext] = {}
        for rule_id, entry in self.entries_by_rule_id.items():
            key = _required_text(rule_id, "catalogue rule ID", 100)
            if not isinstance(entry, GovernedRuleFindingContext):
                raise ValueError(f"catalogue entry for {key} must be GovernedRuleFindingContext")
            if key != entry.context.historical_rule_id:
                raise ValueError(f"catalogue key {key} does not match its context rule ID")
            if key in entries:
                raise ValueError("catalogue contains duplicate normalized rule IDs")
            entries[key] = entry
        object.__setattr__(self, "catalog_version", version)
        object.__setattr__(self, "entries_by_rule_id", MappingProxyType(entries))

    def require_approved_coverage(
        self, emitted_rule_ids: Sequence[str]
    ) -> Mapping[str, RuleFindingContext]:
        """Return contexts only for exact coverage and independently approved entries."""
        if isinstance(emitted_rule_ids, (str, bytes)) or not isinstance(emitted_rule_ids, Sequence):
            raise ValueError("emitted_rule_ids must be a sequence of rule IDs")
        emitted = tuple(_required_text(item, "emitted rule ID", 100) for item in emitted_rule_ids)
        if len(emitted) != len(set(emitted)):
            raise ValueError("emitted findings contain duplicate rule IDs")
        emitted_set = set(emitted)
        configured_set = set(self.entries_by_rule_id)
        missing = sorted(emitted_set - configured_set)
        extra = sorted(configured_set - emitted_set)
        if missing or extra:
            details = []
            if missing:
                details.append(f"missing contexts: {', '.join(missing)}")
            if extra:
                details.append(f"unused contexts: {', '.join(extra)}")
            raise ValueError("Finding context coverage mismatch (" + "; ".join(details) + ")")
        blocked = sorted(
            rule_id for rule_id in emitted
            if not self.entries_by_rule_id[rule_id].is_usable_for_binding
        )
        if blocked:
            raise ValueError(
                "Finding contexts are not independently legally approved: "
                + ", ".join(blocked)
            )
        return MappingProxyType({
            rule_id: self.entries_by_rule_id[rule_id].context
            for rule_id in emitted
        })
