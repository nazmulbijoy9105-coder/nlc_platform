"""Immutable per-run statutory rule outcome ledger helpers.

An absent engine finding is never interpreted as compliance or non-applicability.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, Mapping

from canonical_architecture.rjsc_scope import (
    RJSC_SCOPE_VERSION,
    is_rjsc_rule_in_scope,
)


def _value(value: Any) -> str | None:
    raw = getattr(value, "value", value)
    return str(raw).strip().upper() if raw is not None else None


def _applicability(findings: list[Any]) -> tuple[str, str, str, bool]:
    """Resolve only the dedicated applicability result; never reuse scoring flags."""
    if not findings:
        return (
            "UNKNOWN",
            "NO_EXPLICIT_ENGINE_DECISION",
            "The evaluator emitted no applicability decision. No finding is not proof of non-applicability.",
            False,
        )

    decisions: set[str] = set()
    sources: set[str] = set()
    reasons: list[str] = []
    for flag in findings:
        explicit = _value(getattr(flag, "applicability_state", None))
        outcome = _value(getattr(flag, "state", None))
        detail = getattr(flag, "detail", None)
        reason = getattr(flag, "applicability_reason", None)
        if not reason and isinstance(detail, dict):
            reason = detail.get("applicability_reason")

        if explicit in {"APPLICABLE", "NOT_APPLICABLE", "UNKNOWN"}:
            decision = explicit
            source = "ENGINE_EXPLICIT_APPLICABILITY_RESULT"
        elif outcome == "NOT_APPLICABLE":
            decision = "NOT_APPLICABLE"
            source = "ENGINE_NOT_APPLICABLE_OUTCOME"
        else:
            decision = "UNKNOWN"
            source = "ENGINE_APPLICABILITY_UNRESOLVED"

        decisions.add(decision)
        sources.add(source)
        reasons.append(str(reason or {
            "APPLICABLE": "The evaluator explicitly marked the obligation applicable.",
            "NOT_APPLICABLE": "The evaluator explicitly marked the obligation not applicable.",
            "UNKNOWN": "The evaluator did not provide a conclusive applicability result.",
        }[decision]))

    if len(decisions) != 1:
        return (
            "UNKNOWN",
            "CONFLICTING_ENGINE_APPLICABILITY_RESULTS",
            "Findings for this rule contain conflicting explicit applicability results.",
            True,
        )
    state = next(iter(decisions))
    return (
        state,
        next(iter(sources)) if len(sources) == 1 else "MIXED_ENGINE_APPLICABILITY_SOURCES",
        " ".join(dict.fromkeys(reasons)),
        False,
    )


def _identity_basis(value: Any) -> str | None:
    """Normalize a statutory basis for conservative identity matching."""
    translation = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"'})
    normalized = " ".join(str(value or "").translate(translation).split()).casefold()
    return normalized or None


def build_rule_outcomes_snapshot(
    active_legal_rules: Iterable[Any],
    flags: Iterable[Any],
    applicability_results: Mapping[str, Mapping[str, Any]] | None = None,
    catalogue_identity_conflicts: Mapping[str, Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Build one immutable RJSC-only outcome row per classified catalogue rule.

    Findings for missing, inactive, conflicted, or basis-mismatched in-scope
    identities are represented only as UNKNOWN identity conflicts. Unknown rule
    IDs are fail-closed and never become unmapped RJSC findings.
    """
    from canonical_architecture.rjsc_scope import (
        RJSC_OUT_OF_SCOPE_RULE_IDS,
        RJSC_RULE_SCOPE,
    )

    rules = list(active_legal_rules)
    applicability_results = applicability_results or {}
    conflict_input = {
        str(rule_id): dict(conflict)
        for rule_id, conflict in (catalogue_identity_conflicts or {}).items()
        if is_rjsc_rule_in_scope(str(rule_id))
    }
    rules_by_id: dict[str, Any] = {}
    for rule in rules:
        rule_id = str(rule.rule_id)
        if rule_id not in RJSC_RULE_SCOPE:
            raise ValueError(
                f"Active catalogue rule is absent from the RJSC scope registry: {rule_id}"
            )
        if not is_rjsc_rule_in_scope(rule_id):
            # Out-of-scope rows are not read from the mutable catalogue. Their
            # immutable tombstones are emitted from the versioned scope registry.
            continue
        if rule_id in rules_by_id:
            raise ValueError(
                f"Duplicate active catalogue rule_id cannot be attributed: {rule_id}"
            )
        rules_by_id[rule_id] = rule
    rules = [rules_by_id[rule_id] for rule_id in sorted(rules_by_id)]

    findings_by_rule: dict[str, list[dict[str, Any]]] = {}
    raw_findings_by_rule: dict[str, list[Any]] = {}
    identity_conflicts_by_rule: dict[str, list[dict[str, Any]]] = {}
    for rule_id, conflict in conflict_input.items():
        conflict.setdefault("flag_code", None)
        conflict.setdefault("flag_statutory_basis", None)
        conflict.setdefault("resolution_status", "UNRESOLVED_STATUTORY_IDENTITY_MISMATCH")
        identity_conflicts_by_rule[rule_id] = [conflict]

    for flag in flags:
        rule_id = str(getattr(flag, "rule_id", ""))
        if not is_rjsc_rule_in_scope(rule_id):
            continue
        rule = rules_by_id.get(rule_id)
        flag_code = getattr(flag, "flag_code", None)
        flag_basis_raw = getattr(flag, "statutory_basis", None)
        flag_basis = _identity_basis(flag_basis_raw)
        catalogue_basis_raw = getattr(rule, "statutory_basis", None) if rule is not None else None
        catalogue_basis = _identity_basis(catalogue_basis_raw)

        binding_reason = None
        if rule is None:
            binding_reason = (
                identity_conflicts_by_rule.get(rule_id, [{}])[0].get("binding_reason")
                or "CATALOGUE_ENTRY_MISSING"
            )
        elif identity_conflicts_by_rule.get(rule_id):
            binding_reason = identity_conflicts_by_rule[rule_id][0].get(
                "binding_reason", "CATALOGUE_IDENTITY_CONFLICT"
            )
        elif flag_basis is None or catalogue_basis is None or flag_basis != catalogue_basis:
            binding_reason = "STATUTORY_BASIS_MISMATCH"

        if binding_reason:
            conflicts = identity_conflicts_by_rule.setdefault(rule_id, [])
            matching = next(
                (item for item in conflicts if item.get("flag_code") == flag_code),
                None,
            )
            if matching is None:
                matching = conflicts[0] if conflicts and conflicts[0].get("flag_code") is None else {}
                if not conflicts or matching is not conflicts[0]:
                    conflicts.append(matching)
            matching.setdefault("rule_id", rule_id)
            matching["flag_code"] = flag_code
            matching["flag_statutory_basis"] = flag_basis_raw
            matching.setdefault("engine_statutory_basis", flag_basis_raw)
            matching.setdefault("catalogue_statutory_basis", catalogue_basis_raw)
            matching["binding_reason"] = binding_reason
            matching["resolution_status"] = "UNRESOLVED_STATUTORY_IDENTITY_MISMATCH"
            continue

        state_value = _value(getattr(flag, "state", None)) or "UNKNOWN"
        severity_value = _value(getattr(flag, "severity", None))
        eval_state_value = _value(getattr(flag, "eval_state", None))
        findings_by_rule.setdefault(rule_id, []).append({
            "flag_code": flag_code,
            "outcome_state": state_value,
            "evaluation_state": eval_state_value,
            "severity": severity_value,
            "description": getattr(flag, "description", None),
            "statutory_basis": flag_basis_raw,
        })
        raw_findings_by_rule.setdefault(rule_id, []).append(flag)

    snapshot: list[dict[str, Any]] = []
    for rule in rules:
        rule_id = str(rule.rule_id)
        identity_conflicts = identity_conflicts_by_rule.get(rule_id, [])
        if identity_conflicts:
            findings = []
            applicability_state = "UNKNOWN"
            applicability_source = "CATALOGUE_IDENTITY_CONFLICT"
            applicability_reason = (
                "Catalogue identity is unresolved; findings and applicability "
                "cannot be attributed to this rule."
            )
            applicability_conflict = False
            applicability = {}
            state = "UNKNOWN"
            assessment_source = "IDENTITY_MISMATCH_NOT_ATTRIBUTED"
        else:
            findings = findings_by_rule.get(rule_id, [])
            raw_findings = raw_findings_by_rule.get(rule_id, [])
            (
                applicability_state,
                applicability_source,
                applicability_reason,
                applicability_conflict,
            ) = _applicability(raw_findings)
            states = {item["outcome_state"] for item in findings}
            state = (
                next(iter(states)) if len(states) == 1
                else "CONTRADICTORY" if len(states) > 1
                else "NOT_EVALUATED"
            )
            applicability = dict(applicability_results.get(rule_id, {}))
            assessment_source = (
                "ENGINE_FINDING" if findings
                else "NO_FINDING_EMITTED_NOT_PROOF_OF_COMPLIANCE"
            )

        applicability_status = str(applicability.get("status", "UNKNOWN")).upper()
        if applicability_status not in {"APPLICABLE", "NOT_APPLICABLE", "UNKNOWN"}:
            raise ValueError(
                f"Invalid applicability status for {rule_id}: {applicability_status!r}"
            )
        verified_at = getattr(rule, "verified_at", None)
        snapshot.append({
            "rule_id": rule_id,
            "scope_version": RJSC_SCOPE_VERSION,
            "scope_class": "IN_SCOPE_RJSC",
            "rule_version": rule.rule_version,
            "statutory_basis": rule.statutory_basis,
            "verification_status": rule.verification_status,
            "verified_by": rule.verified_by,
            "verified_at": verified_at.isoformat() if verified_at else None,
            "applicability_state": applicability_state,
            "applicability_source": applicability_source,
            "finding_applicability_reason": applicability_reason,
            "applicability_conflict": applicability_conflict,
            "outcome_state": state,
            "applicability_status": applicability_status,
            "applicability_reason": applicability.get(
                "reason",
                "CATALOGUE_IDENTITY_CONFLICT" if identity_conflicts
                else "NO_EXPLICIT_APPLICABILITY_RESULT",
            ),
            "applicability_policy_version": applicability.get("policy_version"),
            "applicability_fact_evidence": applicability.get("fact_evidence", []),
            "assessment_source": assessment_source,
            "findings": findings,
            "identity_conflicts": identity_conflicts,
        })

    orphan_rule_ids = set(identity_conflicts_by_rule) - set(rules_by_id)
    for orphan_rule_id in sorted(orphan_rule_ids):
        identity_conflicts = identity_conflicts_by_rule[orphan_rule_id]
        snapshot.append({
            "rule_id": orphan_rule_id,
            "scope_version": RJSC_SCOPE_VERSION,
            "scope_class": "IN_SCOPE_RJSC",
            "rule_version": None,
            "statutory_basis": None,
            "verification_status": "UNMAPPED",
            "verified_by": None,
            "verified_at": None,
            "applicability_state": "UNKNOWN",
            "applicability_source": "CATALOGUE_IDENTITY_CONFLICT",
            "finding_applicability_reason": (
                "The in-scope evaluator identity is missing or inactive in the "
                "catalogue; no finding or applicability result is attributable."
            ),
            "applicability_conflict": False,
            "outcome_state": "UNKNOWN",
            "applicability_status": "UNKNOWN",
            "applicability_reason": "CATALOGUE_IDENTITY_CONFLICT",
            "applicability_policy_version": None,
            "applicability_fact_evidence": [],
            "assessment_source": "CATALOGUE_IDENTITY_CONFLICT_NOT_ATTRIBUTED",
            "findings": [],
            "identity_conflicts": identity_conflicts,
        })
    # The 26 exclusions are immutable registry tombstones, not mutable
    # database rows. Their presence and contents cannot depend on external
    # catalogue activation, version, statutory basis, flags, or evidence.
    for rule_id in sorted(RJSC_OUT_OF_SCOPE_RULE_IDS):
        snapshot.append({
            "rule_id": rule_id,
            "scope_version": RJSC_SCOPE_VERSION,
            "scope_class": "OUT_OF_SCOPE",
            "rule_version": None,
            "statutory_basis": None,
            "verification_status": "OUT_OF_SCOPE",
            "verified_by": None,
            "verified_at": None,
            "applicability_state": "OUT_OF_SCOPE",
            "applicability_source": "RJSC_SCOPE_REGISTRY",
            "finding_applicability_reason": None,
            "applicability_conflict": False,
            "outcome_state": "OUT_OF_SCOPE",
            "applicability_status": "OUT_OF_SCOPE",
            "applicability_reason": "EXCLUDED_FROM_RJSC_ASSESSMENT",
            "applicability_policy_version": None,
            "applicability_fact_evidence": [],
            "assessment_source": "OUT_OF_SCOPE",
            "findings": [],
            "identity_conflicts": [],
        })
    return snapshot


def hash_rule_outcomes_snapshot(snapshot: list[dict[str, Any]]) -> str:
    payload = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode()).hexdigest()
