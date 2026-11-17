"""Trusted, server-controlled context for canonical finding/evidence binding.

A context is legal-operational metadata, not a customer assertion. Callers must
load it from an independently governed server-side catalogue. This module
validates shape and coverage only; it does not determine legal effective dates,
interpret statutes, approve rules, or authorise scoring.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from types import MappingProxyType
from typing import Mapping, Sequence


def _required_text(value: object, field: str, maximum: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    normalized = value.strip()
    if not normalized or len(normalized) > maximum:
        raise ValueError(f"{field} must contain 1 to {maximum} non-whitespace characters")
    return normalized


def _required_date(value: object) -> date:
    if isinstance(value, datetime) or not isinstance(value, date):
        raise ValueError("effective_date must be a date without a time component")
    return value


@dataclass(frozen=True, slots=True)
class RuleFindingContext:
    """Authoritative inputs required to bind one emitted engine rule finding.

    effective_date_basis and effective_date_source_ref record why the date
    was selected. They must point to a reviewed server-side determination;
    neither may be inferred from today's date, an engine build, or a flag date.
    """

    historical_rule_id: str
    source_namespace: str
    jurisdiction: str
    effective_date: date
    effective_date_basis: str
    effective_date_source_ref: str
    required_fact_keys: tuple[str, ...]
    evidence_roles_by_fact_key: Mapping[str, str]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "historical_rule_id",
            _required_text(self.historical_rule_id, "historical_rule_id", 100),
        )
        object.__setattr__(
            self, "source_namespace",
            _required_text(self.source_namespace, "source_namespace", 255),
        )
        object.__setattr__(
            self, "jurisdiction",
            _required_text(self.jurisdiction, "jurisdiction", 32),
        )
        object.__setattr__(self, "effective_date", _required_date(self.effective_date))
        object.__setattr__(
            self, "effective_date_basis",
            _required_text(self.effective_date_basis, "effective_date_basis", 500),
        )
        object.__setattr__(
            self, "effective_date_source_ref",
            _required_text(self.effective_date_source_ref, "effective_date_source_ref", 1000),
        )

        keys = self.required_fact_keys
        if isinstance(keys, (str, bytes)) or not isinstance(keys, Sequence):
            raise ValueError("required_fact_keys must be a sequence of fact-key strings")
        normalized_keys = tuple(
            _required_text(key, "required_fact_keys entry", 120) for key in keys
        )
        if len(normalized_keys) != len(set(normalized_keys)):
            raise ValueError("required_fact_keys must not contain duplicates")
        object.__setattr__(self, "required_fact_keys", normalized_keys)

        roles = self.evidence_roles_by_fact_key
        if not isinstance(roles, Mapping):
            raise ValueError("evidence_roles_by_fact_key must be a mapping")
        normalized_roles: dict[str, str] = {}
        for key, role in roles.items():
            normalized_key = _required_text(key, "evidence role fact key", 120)
            normalized_role = _required_text(role, "evidence role", 80)
            if normalized_key in normalized_roles:
                raise ValueError("evidence_roles_by_fact_key contains duplicate normalized keys")
            normalized_roles[normalized_key] = normalized_role
        unknown_role_keys = set(normalized_roles) - set(normalized_keys)
        if unknown_role_keys:
            raise ValueError(
                "evidence role mappings must reference declared required_fact_keys"
            )
        object.__setattr__(
            self, "evidence_roles_by_fact_key",
            MappingProxyType(normalized_roles),
        )


@dataclass(frozen=True, slots=True)
class FindingContextCatalog:
    """Complete context set for exactly one evaluation's emitted findings.

    The catalog is expected to be instantiated by trusted server-side code.
    It intentionally rejects partial coverage rather than persisting a subset.
    """

    catalog_version: str
    contexts_by_rule_id: Mapping[str, RuleFindingContext]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "catalog_version",
            _required_text(self.catalog_version, "catalog_version", 100),
        )
        contexts = self.contexts_by_rule_id
        if not isinstance(contexts, Mapping):
            raise ValueError("contexts_by_rule_id must be a mapping")
        normalized: dict[str, RuleFindingContext] = {}
        for rule_id, context in contexts.items():
            key = _required_text(rule_id, "context rule ID", 100)
            if not isinstance(context, RuleFindingContext):
                raise ValueError(f"context for {key} must be RuleFindingContext")
            if key != context.historical_rule_id:
                raise ValueError(
                    f"context key {key} does not match its historical_rule_id"
                )
            if key in normalized:
                raise ValueError("contexts_by_rule_id contains duplicate normalized rule IDs")
            normalized[key] = context
        object.__setattr__(self, "contexts_by_rule_id", MappingProxyType(normalized))

    def require_exact_coverage(self, emitted_rule_ids: Sequence[str]) -> Mapping[str, RuleFindingContext]:
        """Return immutable context map only when every emitted rule is covered.

        Duplicate emitted IDs are rejected: a caller must distinguish multiple
        findings for the same rule before creating a one-binding-per-flag row.
        Extra catalogue entries are rejected for this evaluation to expose
        stale or mismatched caller configuration.
        """
        if isinstance(emitted_rule_ids, (str, bytes)) or not isinstance(
            emitted_rule_ids, Sequence
        ):
            raise ValueError("emitted_rule_ids must be a sequence of rule IDs")
        emitted = tuple(
            _required_text(rule_id, "emitted rule ID", 100)
            for rule_id in emitted_rule_ids
        )
        if len(emitted) != len(set(emitted)):
            raise ValueError("emitted findings contain duplicate rule IDs")
        emitted_set = set(emitted)
        configured_set = set(self.contexts_by_rule_id)
        missing = sorted(emitted_set - configured_set)
        extra = sorted(configured_set - emitted_set)
        if missing or extra:
            details = []
            if missing:
                details.append(f"missing contexts: {', '.join(missing)}")
            if extra:
                details.append(f"unused contexts: {', '.join(extra)}")
            raise ValueError("Finding context coverage mismatch (" + "; ".join(details) + ")")
        return self.contexts_by_rule_id
