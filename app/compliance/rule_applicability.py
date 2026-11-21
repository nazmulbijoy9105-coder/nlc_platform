"""Explicit, evidence-backed applicability assessment for live coverage reporting.

This module does not decide legal correctness, activate rules, or gate scoring.
It evaluates only declared product scope predicates. A missing policy, missing
fact, unverified fact, or non-boolean exception is UNKNOWN—not APPLICABLE.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from canonical_architecture.applicability_model import APPLICABILITY_REGISTRY

APPLICABILITY_POLICY_VERSION = "NLC-APPLICABILITY-2026-11-20.1"
_VALID_STATUSES = frozenset({"APPLICABLE", "NOT_APPLICABLE", "UNKNOWN"})
_FALSE_STRINGS = frozenset({"", "false", "no", "n", "0", "none", "null", "unknown"})
_TRUE_STRINGS = frozenset({"true", "yes", "y", "1"})


def _enum_value(value: Any) -> Any:
    return getattr(value, "value", value)


def _verified_fact(record: Any) -> tuple[Any, dict[str, Any]] | None:
    """Return a fact value/evidence only when its provenance is verified and document-backed."""
    fact = record
    if hasattr(record, "to_fact_record"):
        fact = record.to_fact_record()
    checker = getattr(fact, "is_verified_document_fact", None)
    if not callable(checker) or not checker():
        return None

    evidence = {
        "fact_id": getattr(fact, "record_id", None),
        "fact_key": getattr(fact, "fact_key", None),
        "trust_level": str(_enum_value(getattr(fact, "trust_level", None))),
        "verification_status": str(_enum_value(getattr(fact, "verification_status", None))),
        "source_reference": getattr(fact, "source_reference", None),
        "document_id": getattr(fact, "document_id", None),
        "observed_on": (
            getattr(fact, "observed_on").isoformat()
            if getattr(fact, "observed_on", None) is not None else None
        ),
        "verified_by": getattr(fact, "verified_by", None),
        "verified_at": (
            getattr(fact, "verified_at").isoformat()
            if getattr(fact, "verified_at", None) is not None else None
        ),
    }
    return getattr(fact, "value", None), evidence


def _condition_value(value: Any) -> bool | None:
    """Interpret a declared condition without treating absent/unknown as false."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value > 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in _FALSE_STRINGS:
            return False
        if normalized in _TRUE_STRINGS:
            return True
        return bool(normalized)
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return None


def _normalize_company_type(value: Any) -> str | None:
    raw = _enum_value(value)
    if not isinstance(raw, str) or not raw.strip():
        return None
    normalized = raw.strip().upper().replace("-", "_").replace(" ", "_")
    aliases = {
        "PRIVATE_LIMITED_COMPANY": "PRIVATE_LIMITED",
        "PRIVATE": "PRIVATE_LIMITED",
        "PUBLIC": "PUBLIC_LIMITED",
        "PUBLIC_LIMITED_COMPANY": "PUBLIC_LIMITED",
    }
    return aliases.get(normalized, normalized)


def evaluate_rule_applicability(
    rule_id: str,
    verified_facts: Mapping[str, Any],
    *,
    policy_registry: Mapping[str, Any] = APPLICABILITY_REGISTRY,
) -> dict[str, Any]:
    """Evaluate one rule's declared applicability predicates using verified facts only."""
    policy = policy_registry.get(rule_id)
    if policy is None:
        return {
            "status": "UNKNOWN",
            "reason": "NO_EXPLICIT_APPLICABILITY_POLICY",
            "policy_version": APPLICABILITY_POLICY_VERSION,
            "fact_evidence": [],
            "scope": [],
            "conditions": [],
            "exceptions": [],
        }

    referenced_keys = sorted(set(policy.conditions) | set(policy.exceptions) | (
        {"company_type"} if "ALL" not in policy.applies_to else set()
    ))
    values: dict[str, Any] = {}
    evidence: dict[str, dict[str, Any]] = {}
    missing: list[str] = []
    for key in referenced_keys:
        record = verified_facts.get(key)
        verified = _verified_fact(record) if record is not None else None
        if verified is None:
            missing.append(key)
            continue
        values[key], evidence[key] = verified

    result_base = {
        "policy_version": APPLICABILITY_POLICY_VERSION,
        "fact_evidence": [evidence[key] for key in sorted(evidence)],
        "scope": list(policy.applies_to),
        "conditions": list(policy.conditions),
        "exceptions": list(policy.exceptions),
    }

    if missing:
        return {
            **result_base,
            "status": "UNKNOWN",
            "reason": "MISSING_VERIFIED_FACTS:" + ",".join(missing),
        }

    if "ALL" not in policy.applies_to:
        company_type = _normalize_company_type(values.get("company_type"))
        allowed_types = {_normalize_company_type(item) for item in policy.applies_to}
        if company_type is None:
            return {**result_base, "status": "UNKNOWN", "reason": "COMPANY_TYPE_NOT_VERIFIED"}
        if company_type not in allowed_types:
            return {
                **result_base,
                "status": "NOT_APPLICABLE",
                "reason": "VERIFIED_COMPANY_TYPE_OUT_OF_SCOPE",
            }

    for key in policy.conditions:
        condition = _condition_value(values.get(key))
        if condition is None:
            return {
                **result_base,
                "status": "UNKNOWN",
                "reason": f"CONDITION_VALUE_UNINTERPRETABLE:{key}",
            }
        if not condition:
            return {
                **result_base,
                "status": "NOT_APPLICABLE",
                "reason": f"VERIFIED_SCOPE_CONDITION_FALSE:{key}",
            }

    for key in policy.exceptions:
        exception_value = values.get(key)
        if not isinstance(exception_value, bool):
            return {
                **result_base,
                "status": "UNKNOWN",
                "reason": f"EXCEPTION_FACT_NOT_BOOLEAN:{key}",
            }
        if exception_value:
            return {
                **result_base,
                "status": "NOT_APPLICABLE",
                "reason": f"VERIFIED_EXCEPTION_TRUE:{key}",
            }

    return {
        **result_base,
        "status": "APPLICABLE",
        "reason": "DECLARED_SCOPE_PREDICATES_SATISFIED_BY_VERIFIED_FACTS",
    }


def build_rule_applicability_results(
    rule_ids: Sequence[str],
    verified_facts: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    """Return an explicit APPLICABLE/NOT_APPLICABLE/UNKNOWN result for every active rule."""
    results = {
        rule_id: evaluate_rule_applicability(rule_id, verified_facts)
        for rule_id in sorted(set(rule_ids))
    }
    invalid = {
        rule_id: result.get("status")
        for rule_id, result in results.items()
        if result.get("status") not in _VALID_STATUSES
    }
    if invalid:
        raise ValueError(f"Invalid rule applicability results: {invalid!r}")
    return results
