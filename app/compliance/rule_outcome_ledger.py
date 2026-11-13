"""Immutable per-run statutory rule outcome ledger helpers.

An absent engine finding is never interpreted as compliance.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable


def build_rule_outcomes_snapshot(
    active_legal_rules: Iterable[Any],
    flags: Iterable[Any],
) -> list[dict[str, Any]]:
    findings_by_rule: dict[str, list[dict[str, Any]]] = {}
    for flag in flags:
        state = getattr(flag, "state", None)
        state_value = getattr(state, "value", state) or "UNKNOWN"
        severity = getattr(flag, "severity", None)
        severity_value = getattr(severity, "value", severity)
        eval_state = getattr(flag, "eval_state", None)
        eval_state_value = getattr(eval_state, "value", eval_state)
        findings_by_rule.setdefault(flag.rule_id, []).append({
            "flag_code": getattr(flag, "flag_code", None),
            "outcome_state": str(state_value),
            "evaluation_state": str(eval_state_value) if eval_state_value is not None else None,
            "severity": str(severity_value) if severity_value is not None else None,
            "description": getattr(flag, "description", None),
            "statutory_basis": getattr(flag, "statutory_basis", None),
        })

    snapshot: list[dict[str, Any]] = []
    for rule in active_legal_rules:
        findings = findings_by_rule.get(rule.rule_id, [])
        states = {item["outcome_state"] for item in findings}
        state = (
            next(iter(states)) if len(states) == 1
            else "CONTRADICTORY" if len(states) > 1
            else "NOT_EVALUATED"
        )
        verified_at = getattr(rule, "verified_at", None)
        snapshot.append({
            "rule_id": rule.rule_id,
            "rule_version": rule.rule_version,
            "statutory_basis": rule.statutory_basis,
            "verification_status": rule.verification_status,
            "verified_by": rule.verified_by,
            "verified_at": verified_at.isoformat() if verified_at else None,
            "outcome_state": state,
            "assessment_source": (
                "ENGINE_FINDING" if findings
                else "NO_FINDING_EMITTED_NOT_PROOF_OF_COMPLIANCE"
            ),
            "findings": findings,
        })
    catalogue_ids = {rule.rule_id for rule in active_legal_rules}
    for orphan_rule_id in sorted(set(findings_by_rule) - catalogue_ids):
        findings = findings_by_rule[orphan_rule_id]
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
            "outcome_state": state,
            "assessment_source": "ENGINE_FINDING_WITHOUT_ACTIVE_CATALOGUE_RULE",
            "findings": findings,
        })
    return snapshot


def hash_rule_outcomes_snapshot(snapshot: list[dict[str, Any]]) -> str:
    payload = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode()).hexdigest()
