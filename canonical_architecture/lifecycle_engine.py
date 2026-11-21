"""
NLC - Legal Compliance & Rescue Platform
Canonical Lifecycle Orchestrator
Enforces the strict flow: Legal Source -> Rule -> Evaluation -> Rescue -> Action -> Audit
Governed by Product Invariants R-001...R-020.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence, Union

from canonical_architecture.statutory_rules import (
    STATUTORY_RULE_REGISTRY, RuleState, StatutoryRule, evaluate_applicability,
)
from canonical_architecture.evaluator import EvidenceStatus, evaluate_rule
from canonical_architecture.statutory_rescue import STATUTORY_RESCUE_REGISTRY
from canonical_architecture.legal_reconciliation import LEGAL_RECONCILIATION

EvidenceInput = Union[Mapping[str, Any], Sequence[Any]]


class CanonicalLifecycleEngine:
    """Orchestrates the canonical compliance and rescue lifecycle."""

    def __init__(self) -> None:
        self.rule_registry = STATUTORY_RULE_REGISTRY
        self.rescue_registry = STATUTORY_RESCUE_REGISTRY
        self.reconciliation_registry = LEGAL_RECONCILIATION
        self.audit_trail: List[Dict[str, Any]] = []  # R-020: Immutable Trace

    def _audit(self, action: str, details: Dict[str, Any]) -> None:
        """R-020: Record immutable trace of decisions/actions."""
        self.audit_trail.append({"action": action, "details": details})

    def _applicability_state(
        self, rule: StatutoryRule, facts: Mapping[str, Any]
    ) -> RuleState | None:
        """Use the same three-state applicability contract as the canonical evaluator."""
        return evaluate_applicability(rule, facts)

    def _evidence_satisfies(self, rule: StatutoryRule, evidence: EvidenceInput) -> bool:
        if isinstance(evidence, Mapping):
            if not evidence:
                return False
            for key in rule.evidence_required:
                short = key.split(":")[-1] if ":" in key else key
                val = evidence.get(key) or evidence.get(short) or evidence.get(short.lower())
                if not val:
                    return False
            return True
        if not evidence:
            return False
        for ev in evidence:
            if not ev:
                continue
            if hasattr(ev, "is_valid") and not getattr(ev, "is_valid"):
                continue
            if hasattr(ev, "status") and str(getattr(ev, "status", "")).upper() in (
                "REJECTED", "INVALID",
            ):
                continue
            return True
        return False

    def evaluate_finding(
        self,
        rule_id: str,
        evidence: EvidenceInput,
        facts: Mapping[str, Any] | None = None,
    ) -> RuleState:
        """Evaluate scope facts separately from evidence.

        Facts are the authoritative applicability input when supplied.
        For backward compatibility, callers that omit facts retain the
        historical behaviour where a mapping may contain both facts and
        evidence keys.
        """
        rule = self.rule_registry.get(rule_id)
        if rule is None:
            return RuleState.UNKNOWN
        legacy_combined_map: Mapping[str, Any] = (
            evidence if isinstance(evidence, Mapping) else {}
        )
        applicability_facts = legacy_combined_map if facts is None else facts
        applicability = self._applicability_state(rule, applicability_facts)
        if applicability is not None:
            return applicability
        if isinstance(evidence, Mapping):
            evidence_statuses: Dict[str, EvidenceStatus] = {}
            for key in rule.evidence_required:
                short = key.split(":")[-1] if ":" in key else key
                value = evidence.get(key)
                if value is None:
                    value = evidence.get(short)
                if value is None:
                    value = evidence.get(short.lower())
                value = getattr(value, "value", value)
                if value is True or value == EvidenceStatus.VERIFIED_PRESENT.value:
                    evidence_statuses[key] = EvidenceStatus.VERIFIED_PRESENT
                elif value == EvidenceStatus.VERIFIED_ABSENT.value:
                    evidence_statuses[key] = EvidenceStatus.VERIFIED_ABSENT
                elif value == EvidenceStatus.CONFLICTING.value:
                    evidence_statuses[key] = EvidenceStatus.CONFLICTING
                else:
                    evidence_statuses[key] = EvidenceStatus.UNVERIFIED
            return evaluate_rule(rule, applicability_facts, evidence_statuses).state

        if not evidence:
            return RuleState.UNKNOWN
        verified = self._evidence_satisfies(rule, evidence)
        return RuleState.COMPLIANT if verified else RuleState.UNKNOWN

    def generate_rescue_plan(self, active_findings: List[str]) -> List[Dict[str, Any]]:
        steps: List[Dict[str, Any]] = []
        for rule_id in active_findings:
            rescue_def = self.rescue_registry.get(rule_id)
            if rescue_def is None:
                continue
            if hasattr(rescue_def, "rescue_id"):
                steps.append({
                    "rescue_id": rescue_def.rescue_id,
                    "related_rules": [rule_id],
                    "actions": list(getattr(rescue_def, "statutory_actions", ())),
                    "service": getattr(rescue_def, "service_workflow", ""),
                    "deadline": getattr(rescue_def, "deadline_basis", ""),
                })
            elif isinstance(rescue_def, dict):
                steps.append({
                    "rescue_id": rescue_def.get("rescue_id"),
                    "related_rules": [rule_id],
                    "actions": rescue_def.get("statutory_actions", []),
                    "service": rescue_def.get("service_workflow", ""),
                    "deadline": rescue_def.get("deadline_basis", ""),
                })
        self._audit("RESCUE_GENERATED", {"steps": len(steps)})
        return steps

    def submit_new_evidence(
        self,
        rule_id: str,
        evidence: EvidenceInput,
        verification_recorded: bool = False,
        facts: Mapping[str, Any] | None = None,
    ) -> RuleState:
        self._audit("EVIDENCE_SUBMITTED", {"rule_id": rule_id})
        new_state = self.evaluate_finding(rule_id, evidence, facts=facts)
        if new_state is RuleState.COMPLIANT and verification_recorded:
            self._audit("RESCUE_CLOSED", {"rule_id": rule_id, "reason": "Verified compliant"})
        return new_state


lifecycle_engine = CanonicalLifecycleEngine()
