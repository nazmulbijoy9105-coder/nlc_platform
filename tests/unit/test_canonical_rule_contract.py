"""Contract audit for the composite 85-rule canonical registry.

This gate validates the effective typed objects and the raw legacy population
independently. It also makes every typed/legacy overlap visible for review;
it deliberately does not assume that either representation is authoritative
or that textual differences are automatically defects.
"""
from __future__ import annotations

import re
from typing import Any


from canonical_architecture import statutory_rules as registry


EXPECTED_RULE_COUNT = 85
RULE_ID_RE = re.compile(r"^[A-Z]+-[0-9]{3}$")
EXPECTED_OVERLAPS = frozenset(
    {"INC-001", "AR-001", "TAX-001", "LBR-001", "TL-001", "DIR-005", "DIR-006"}
)
LEGACY_REQUIRED_KEYS = frozenset(
    {
        "rule_id", "legal_domain", "law", "requirement", "provision",
        "provision_status", "applicability", "exceptions", "evidence_required",
        "evaluation_states", "severity", "score_impact", "invariants",
    }
)
LEGACY_ALLOWED_KEYS = LEGACY_REQUIRED_KEYS | frozenset(
    {"applicability_all", "applicability_lt"}
)


def _validate_effective_rule(rule_id: str, rule: registry.StatutoryRule) -> list[str]:
    """Return contract violations without making legal-correctness claims."""
    errors: list[str] = []
    if not isinstance(rule_id, str) or not RULE_ID_RE.fullmatch(rule_id):
        errors.append("invalid_registry_key")
    if rule.rule_id != rule_id:
        errors.append("registry_key_rule_id_mismatch")

    for name in ("legal_domain", "law", "requirement", "provision", "authority"):
        value = getattr(rule, name)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{name}_must_be_non_empty_string")

    if not isinstance(rule.provision_status, registry.ProvisionStatus):
        errors.append("invalid_provision_status")
    if not isinstance(rule.severity, registry.Severity):
        errors.append("invalid_severity")
    if isinstance(rule.score_impact, bool) or not isinstance(rule.score_impact, int):
        errors.append("score_impact_must_be_integer")

    evidence = rule.evidence_required
    if not isinstance(evidence, tuple) or not evidence:
        errors.append("evidence_required_must_be_non_empty_tuple")
    elif any(not isinstance(item, str) or not item.strip() for item in evidence):
        errors.append("evidence_required_contains_blank_or_non_string")
    elif len(evidence) != len(set(evidence)):
        errors.append("evidence_required_contains_duplicates")

    exceptions = rule.exceptions
    if not isinstance(exceptions, tuple):
        errors.append("exceptions_must_be_tuple")
    elif any(not isinstance(item, str) or not item.strip() for item in exceptions):
        errors.append("exceptions_contains_blank_or_non_string")
    elif len(exceptions) != len(set(exceptions)):
        errors.append("exceptions_contains_duplicates")

    if rule.applies_if is not None and (
        not isinstance(rule.applies_if, str) or not rule.applies_if.strip()
    ):
        errors.append("applies_if_must_be_null_or_non_empty_string")
    return errors


def _legacy_contract_errors(rule_id: str, definition: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = LEGACY_REQUIRED_KEYS - set(definition)
    extra = set(definition) - LEGACY_ALLOWED_KEYS
    if missing:
        errors.append(f"missing_keys:{','.join(sorted(missing))}")
    if extra:
        errors.append(f"unknown_keys:{','.join(sorted(extra))}")
    if definition.get("rule_id") != rule_id:
        errors.append("dictionary_key_rule_id_mismatch")

    for name in ("legal_domain", "law", "requirement", "provision", "applicability"):
        value = definition.get(name)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{name}_must_be_non_empty_string")

    evidence = definition.get("evidence_required")
    if not isinstance(evidence, (list, tuple)) or not evidence:
        errors.append("evidence_required_must_be_non_empty_sequence")
    elif any(not isinstance(item, str) or not item.strip() for item in evidence):
        errors.append("evidence_required_contains_blank_or_non_string")
    elif len(evidence) != len(set(evidence)):
        errors.append("evidence_required_contains_duplicates")

    exceptions = definition.get("exceptions")
    if not isinstance(exceptions, (list, tuple)):
        errors.append("exceptions_must_be_sequence")
    elif any(not isinstance(item, str) or not item.strip() for item in exceptions):
        errors.append("exceptions_contains_blank_or_non_string")
    elif len(exceptions) != len(set(exceptions)):
        errors.append("exceptions_contains_duplicates")

    score = definition.get("score_impact")
    if isinstance(score, bool) or not isinstance(score, int):
        errors.append("score_impact_must_be_integer")
    if not isinstance(definition.get("provision_status"), registry.ProvisionStatus):
        errors.append("invalid_provision_status")
    try:
        registry.Severity(definition.get("severity"))
    except (TypeError, ValueError):
        errors.append("invalid_severity")
    return errors


def _overlap_differences() -> dict[str, dict[str, tuple[Any, Any]]]:
    """Compare typed and legacy source fields after documented field mapping.

    The output is an audit inventory, not a declaration that one side is right.
    Authority is derived by the legacy converter and applicability is normalized
    separately because legacy uses a string sentinel for universal applicability.
    """
    differences: dict[str, dict[str, tuple[Any, Any]]] = {}
    overlap = {rule.rule_id for rule in registry._RULES} & set(registry._LEGACY_RULE_DICTS)
    for rule_id in sorted(overlap):
        typed = registry.STATUTORY_RULE_REGISTRY[rule_id]
        legacy = registry._LEGACY_RULE_DICTS[rule_id]
        mapped = {
            "legal_domain": legacy.get("legal_domain"),
            "law": legacy.get("law"),
            "requirement": legacy.get("requirement"),
            "provision": legacy.get("provision"),
            "provision_status": legacy.get("provision_status"),
            "evidence_required": tuple(legacy.get("evidence_required", ())),
            "severity": registry.Severity(legacy.get("severity")),
            "score_impact": legacy.get("score_impact"),
            "exceptions": tuple(legacy.get("exceptions", ())),
            "authority": registry._LEGACY_AUTHORITY_OVERRIDE.get(rule_id) or registry._LEGACY_AUTHORITY[legacy.get("legal_domain")],
            "evaluation_states": tuple(legacy.get("evaluation_states", ())),
            "invariants": tuple(legacy.get("invariants", ())),
        }
        current = {
            "legal_domain": typed.legal_domain,
            "law": typed.law,
            "requirement": typed.requirement,
            "provision": typed.provision,
            "provision_status": typed.provision_status,
            "evidence_required": typed.evidence_required,
            "severity": typed.severity,
            "score_impact": typed.score_impact,
            "exceptions": typed.exceptions,
            "authority": typed.authority,
            "evaluation_states": typed.evaluation_states,
            "invariants": typed.invariants,
        }
        delta = {
            field: (mapped[field], current[field])
            for field in mapped
            if mapped[field] != current[field]
        }
        legacy_applicability = legacy.get("applicability")
        typed_applicability = typed.applies_if or "ALL_ACTIVE_COMPANIES"
        if legacy_applicability != typed_applicability:
            delta["applicability"] = (legacy_applicability, typed_applicability)
        differences[rule_id] = delta
    return differences


def test_effective_registry_has_exactly_85_unique_canonical_identities():
    ids = list(registry.STATUTORY_RULE_REGISTRY)
    assert len(ids) == EXPECTED_RULE_COUNT
    assert len(ids) == len(set(ids))
    assert set(ids) == set(registry._EXPECTED_RULE_IDS)


def test_every_effective_rule_passes_the_shared_structural_contract():
    failures = {
        rule_id: _validate_effective_rule(rule_id, rule)
        for rule_id, rule in registry.STATUTORY_RULE_REGISTRY.items()
    }
    failures = {rule_id: errors for rule_id, errors in failures.items() if errors}
    assert not failures, failures


def test_every_raw_legacy_definition_passes_the_legacy_source_contract():
    failures = {
        rule_id: _legacy_contract_errors(rule_id, definition)
        for rule_id, definition in registry._LEGACY_RULE_DICTS.items()
    }
    failures = {rule_id: errors for rule_id, errors in failures.items() if errors}
    assert not failures, failures


def test_typed_legacy_overlap_population_is_explicit_and_complete():
    typed_ids = {rule.rule_id for rule in registry._RULES}
    legacy_ids = set(registry._LEGACY_RULE_DICTS)
    overlap = typed_ids & legacy_ids
    assert overlap == EXPECTED_OVERLAPS
    assert overlap <= set(registry.STATUTORY_RULE_REGISTRY)


def test_every_shadowed_definition_is_included_in_overlap_difference_audit():
    """Prevent the seven shadowed legacy definitions from disappearing silently."""
    differences = _overlap_differences()
    assert set(differences) == EXPECTED_OVERLAPS
    assert all(isinstance(delta, dict) for delta in differences.values())


def test_legacy_converter_accepts_every_legacy_source_definition():
    """Exercise conversion for all 85 legacy definitions, including shadowed ones."""
    failures = {}
    for rule_id, definition in registry._LEGACY_RULE_DICTS.items():
        try:
            converted = registry._legacy_rule(rule_id, definition)
            errors = _validate_effective_rule(rule_id, converted)
            if errors:
                failures[rule_id] = errors
        except Exception as exc:  # expose the rule ID and converter failure
            failures[rule_id] = [f"{type(exc).__name__}:{exc}"]
    assert not failures, failures
