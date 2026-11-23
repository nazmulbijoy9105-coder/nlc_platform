"""Immutable per-run statutory rule outcome ledger helpers.

An absent engine finding is never interpreted as compliance or non-applicability.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable, Mapping


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
    normalized = " ".join(str(value or "").split()).casefold()
    return normalized or None


def build_rule_outcomes_snapshot(
    active_legal_rules: Iterable[Any],
    flags: Iterable[Any],
    applicability_results: Mapping[str, Mapping[str, Any]] | None = None,
    catalogue_identity_conflicts: Mapping[str, Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    rules = list(active_legal_rules)
    applicability_results = applicability_results or {}
    catalogue_identity_conflicts = catalogue_identity_conflicts or {}
    rules_by_id: dict[str, Any] = {}
    for rule in rules:
        if rule.rule_id in rules_by_id:
            raise ValueError(
                f"Duplicate active catalogue rule_id cannot be attributed: {rule.rule_id}"
            )
        rules_by_id[rule.rule_id] = rule

    findings_by_rule: dict[str, list[dict[str, Any]]] = {}
    raw_findings_by_rule: dict[str, list[Any]] = {}
    identity_conflicts_by_rule: dict[str, list[dict[str, Any]]] = {
        str(rule_id): [dict(conflict)]
        for rule_id, conflict in catalogue_identity_conflicts.items()
    }
    unmapped_findings: dict[str, list[dict[str, Any]]] = {}
    unmapped_raw_findings: dict[str, list[Any]] = {}

    for flag in flags:
        rule = rules_by_id.get(flag.rule_id)
        flag_basis = _identity_basis(getattr(flag, "statutory_basis", None))
        catalogue_basis = (
            _identity_basis(getattr(rule, "statutory_basis", None))
            if rule is not None else None
        )
        if rule is not None and (
            flag_basis is None or catalogue_basis is None or flag_basis != catalogue_basis
        ):
            identity_conflicts_by_rule.setdefault(flag.rule_id, []).append({
                "flag_code": getattr(flag, "flag_code", None),
                "flag_statutory_basis": getattr(flag, "statutory_basis", None),
                "engine_statutory_basis": getattr(flag, "statutory_basis", None),
                "catalogue_statutory_basis": getattr(rule, "statutory_basis", None),
                "binding_reason": "STATUTORY_BASIS_MISMATCH",
                "resolution_status": "UNRESOLVED_STATUTORY_IDENTITY_MISMATCH",
            })
            continue

        state_value = _value(getattr(flag, "state", None)) or "UNKNOWN"
        severity_value = _value(getattr(flag, "severity", None))
        eval_state_value = _value(getattr(flag, "eval_state", None))
        finding = {
            "flag_code": getattr(flag, "flag_code", None),
            "outcome_state": state_value,
            "evaluation_state": eval_state_value,
            "severity": severity_value,
            "description": getattr(flag, "description", None),
            "statutory_basis": getattr(flag, "statutory_basis", None),
        }
        if rule is None:
            unmapped_findings.setdefault(flag.rule_id, []).append(finding)
            unmapped_raw_findings.setdefault(flag.rule_id, []).append(flag)
        else:
            findings_by_rule.setdefault(flag.rule_id, []).append(finding)
            raw_findings_by_rule.setdefault(flag.rule_id, []).append(flag)

    snapshot: list[dict[str, Any]] = []
    for rule in rules:
        rule_id = rule.rule_id
        findings = findings_by_rule.get(rule_id, [])
        identity_conflicts = identity_conflicts_by_rule.get(rule_id, [])
        raw_findings = raw_findings_by_rule.get(rule_id, [])
        applicability_state, applicability_source, applicability_reason, applicability_conflict = _applicability(
            raw_findings
        )
        states = {item["outcome_state"] for item in findings}
        state = (
            next(iter(states)) if len(states) == 1
            else "CONTRADICTORY" if len(states) > 1
            else "UNKNOWN" if identity_conflicts
            else "NOT_EVALUATED"
        )
        verified_at = getattr(rule, "verified_at", None)
        applicability = dict(applicability_results.get(rule_id, {}))
        applicability_status = str(applicability.get("status", "UNKNOWN")).upper()
        if applicability_status not in {"APPLICABLE", "NOT_APPLICABLE", "UNKNOWN"}:
            raise ValueError(
                f"Invalid applicability status for {rule_id}: {applicability_status!r}"
            )
        if identity_conflicts and not findings:
            assessment_source = "IDENTITY_MISMATCH_NOT_ATTRIBUTED"
        elif identity_conflicts:
            assessment_source = "ENGINE_FINDING_WITH_IDENTITY_CONFLICT"
        else:
            assessment_source = (
                "ENGINE_FINDING" if findings
                else "NO_FINDING_EMITTED_NOT_PROOF_OF_COMPLIANCE"
            )
        snapshot.append({
            "rule_id": rule_id,
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
                "reason", "NO_EXPLICIT_APPLICABILITY_RESULT"
            ),
            "applicability_policy_version": applicability.get("policy_version"),
            "applicability_fact_evidence": applicability.get("fact_evidence", []),
            "assessment_source": assessment_source,
            "findings": findings,
            "identity_conflicts": identity_conflicts,
        })

    orphan_rule_ids = (set(unmapped_findings) | set(catalogue_identity_conflicts)) - set(rules_by_id)
    for orphan_rule_id in sorted(orphan_rule_ids):
        findings = unmapped_findings.get(orphan_rule_id, [])
        identity_conflicts = identity_conflicts_by_rule.get(orphan_rule_id, [])
        if not identity_conflicts:
            identity_conflicts = [{
                "flag_code": None,
                "flag_statutory_basis": None,
                "engine_statutory_basis": None,
                "catalogue_statutory_basis": None,
                "binding_reason": "CATALOGUE_ENTRY_MISSING",
                "resolution_status": "UNRESOLVED_STATUTORY_IDENTITY_MISMATCH",
            }]
        applicability_state, applicability_source, applicability_reason, applicability_conflict = _applicability(
            unmapped_raw_findings.get(orphan_rule_id, [])
        )
        states = {item["outcome_state"] for item in findings}
        state = (
            next(iter(states)) if len(states) == 1
            else "CONTRADICTORY" if len(states) > 1
            else "UNKNOWN"
        )
        snapshot.append({
            "rule_id": orphan_rule_id,
            "rule_version": None,
            "statutory_basis": None,
            "verification_status": "UNMAPPED",
            "verified_by": None,
            "verified_at": None,
            "applicability_state": applicability_state,
            "applicability_source": applicability_source,
            "finding_applicability_reason": applicability_reason,
            "applicability_conflict": applicability_conflict,
            "outcome_state": state,
            "applicability_status": "UNKNOWN",
            "applicability_reason": "RULE_NOT_IN_ACTIVE_CATALOGUE",
            "applicability_policy_version": None,
            "applicability_fact_evidence": [],
            "assessment_source": "ENGINE_FINDING_WITHOUT_ACTIVE_CATALOGUE_RULE",
            "findings": findings,
            "identity_conflicts": identity_conflicts,
        })
    return snapshot

def hash_rule_outcomes_snapshot(snapshot: list[dict[str, Any]]) -> str:
    payload = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode()).hexdigest()
