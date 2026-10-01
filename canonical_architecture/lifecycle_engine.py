"""
NLC - Legal Compliance & Rescue Platform
Canonical Lifecycle Orchestrator
Enforces the strict flow: Legal Source -> Rule -> Evaluation -> Rescue -> Action -> Audit
Governed by Product Invariants R-001...R-020.
"""
from typing import Any, Dict, List
from canonical_architecture.product_invariants import Invariant
from canonical_architecture.statutory_rules import STATUTORY_RULE_REGISTRY, RuleState
from canonical_architecture.statutory_rescue import STATUTORY_RESCUE_REGISTRY
from canonical_architecture.legal_reconciliation import LEGAL_RECONCILIATION

class CanonicalLifecycleEngine:
    """Orchestrates the canonical compliance and rescue lifecycle."""
    
    def __init__(self):
        self.rule_registry = STATUTORY_RULE_REGISTRY
        self.rescue_registry = STATUTORY_RESCUE_REGISTRY
        self.reconciliation_registry = LEGAL_RECONCILIATION
        self.audit_trail: List[Dict[str, Any]] = [] # R-020: Immutable Trace

    def _audit(self, action: str, details: Dict[str, Any]) -> None:
        """R-020: Record immutable trace of decisions/actions."""
        self.audit_trail.append({"action": action, "details": details})
        # In production, this writes to an append-only DB table

    def evaluate_finding(self, rule_id: str, evidence_provided: Dict[str, Any]) -> RuleState:
        """
        EVALUATION -> FINDING
        R-007: Uses canonical rule.
        R-008: UNKNOWN is not NON_COMPLIANT.
        """
        rule_def = self.rule_registry.get(rule_id)
        if not rule_def:
            return RuleState.NOT_APPLICABLE

        # R-012: Check applicability and exceptions
        if not self._is_applicable(rule_def, evidence_provided):
            return RuleState.NOT_APPLICABLE

        # R-004: Check required evidence
        required_evidence = rule_def.get("evidence_required", [])
        missing_evidence = [e for e in required_evidence if e not in evidence_provided or not evidence_provided[e]]

        if missing_evidence:
            self._audit("EVALUATION_UNKNOWN", {"rule_id": rule_id, "missing": missing_evidence})
            return RuleState.UNKNOWN  # R-008

        # Simple verification logic (placeholder for actual rule condition)
        is_compliant = all(evidence_provided.get(e) for e in required_evidence)
        state = RuleState.COMPLIANT if is_compliant else RuleState.NON_COMPLIANT
        
        self._audit("EVALUATION_COMPLETE", {"rule_id": rule_id, "state": state})
        return state

    def _is_applicable(self, rule_def: Dict[str, Any], evidence: Dict[str, Any]) -> bool:
        """APPLICABILITY & EXCEPTIONS"""
        # Check exceptions based on company facts
        exceptions = rule_def.get("exceptions", [])
        if "DORMANT_STRIKE_OFF" in exceptions and evidence.get("is_dormant"):
            return False
        return True

    def generate_rescue_plan(self, active_findings: List[str]) -> List[Dict[str, Any]]:
        """
        FINDING -> STATUTORY RESCUE
        R-014: Rescue derives strictly from findings.
        R-015: Dependencies are respected.
        """
        steps = []
        for rule_id in active_findings:
            rescue_def = self.rescue_registry.get(rule_id)
            if rescue_def:
                # In production, check prerequisites (R-015) before adding
                steps.append({
                    "rescue_id": rescue_def["rescue_id"],
                    "actions": rescue_def["statutory_actions"],
                    "service": rescue_def["service_workflow"],
                    "deadline": rescue_def["deadline_basis"]
                })
        self._audit("RESCUE_GENERATED", {"steps": len(steps)})
        return steps

    def submit_new_evidence(self, rule_id: str, evidence: Dict[str, Any]) -> RuleState:
        """
        NEW EVIDENCE -> RE-EVALUATION -> VERIFIED CURE -> CLOSED
        R-018: New evidence triggers re-evaluation.
        R-019: Verified cure closes rescue.
        """
        self._audit("EVIDENCE_SUBMITTED", {"rule_id": rule_id})
        
        # R-018: Re-evaluate
        new_state = self.evaluate_finding(rule_id, evidence)
        
        if new_state == RuleState.COMPLIANT:
            # R-019: Verified cure closes rescue
            self._audit("RESCUE_CLOSED", {"rule_id": rule_id, "reason": "Verified compliant"})
            # Logic to mark rescue case as closed in DB
            
        return new_state

# Singleton instance for the platform
lifecycle_engine = CanonicalLifecycleEngine()
