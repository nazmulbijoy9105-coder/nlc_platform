"""
Deterministic evaluation (R-003, R-004, R-007, R-008, R-009, R-010, R-018).
Order: applicability -> exceptions -> evidence. No I/O, no clock, no randomness.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Mapping, Optional

from .statutory_rules import RuleState, StatutoryRule, STATUTORY_RULE_REGISTRY


class EvidenceStatus(str, Enum):
    VERIFIED_PRESENT = "VERIFIED_PRESENT"
    VERIFIED_ABSENT = "VERIFIED_ABSENT"   # confirmed not to exist: the only path to NON_COMPLIANT
    UNVERIFIED = "UNVERIFIED"             # uploaded but not verified; same as missing
    CONFLICTING = "CONFLICTING"


@dataclass(frozen=True)
class Finding:
    rule_id: str
    state: RuleState
    reason: str = ""


# R-010: only established breaches reduce the score.
SCORING_STATES = frozenset({RuleState.NON_COMPLIANT})


def evaluate_rule(rule: StatutoryRule,
                  facts: Mapping[str, bool],
                  evidence: Mapping[str, EvidenceStatus]) -> Finding:
    rid = rule.rule_id
    if rule.applies_if is not None:                                   # R-003
        if rule.applies_if not in facts:
            return Finding(rid, RuleState.UNKNOWN, f"applicability fact {rule.applies_if} not provided")
        if not facts[rule.applies_if]:
            return Finding(rid, RuleState.NOT_APPLICABLE, f"{rule.applies_if} is false")
    for ex in rule.exceptions:                                        # R-004
        if facts.get(ex) is True:
            return Finding(rid, RuleState.NOT_APPLICABLE, f"exception {ex}")

    statuses = {e: evidence.get(e, EvidenceStatus.UNVERIFIED) for e in rule.evidence_required}
    absent = [e for e, s in statuses.items() if s is EvidenceStatus.VERIFIED_ABSENT]
    if absent:
        return Finding(rid, RuleState.NON_COMPLIANT, "verified absent: " + ", ".join(absent))
    conflicting = [e for e, s in statuses.items() if s is EvidenceStatus.CONFLICTING]
    if conflicting:                                                   # R-009
        return Finding(rid, RuleState.CONTRADICTORY, "conflicting: " + ", ".join(conflicting))
    if all(s is EvidenceStatus.VERIFIED_PRESENT for s in statuses.values()):
        return Finding(rid, RuleState.COMPLIANT, "all required evidence verified")
    missing = [e for e, s in statuses.items() if s is not EvidenceStatus.VERIFIED_PRESENT]
    return Finding(rid, RuleState.UNKNOWN, "unverified or missing: " + ", ".join(missing))  # R-008


def evaluate_all(facts: Mapping[str, bool],
                 evidence: Mapping[str, EvidenceStatus],
                 registry: Optional[Dict[str, StatutoryRule]] = None) -> List[Finding]:
    reg = STATUTORY_RULE_REGISTRY if registry is None else registry
    out = []
    for rid in sorted(reg):
        f = evaluate_rule(reg[rid], facts, evidence)
        if f.state not in reg[rid].evaluation_states:
            raise ValueError(f"{rid} produced undeclared state {f.state}")
        out.append(f)
    return out


def reevaluate(rule_id: str, facts: Mapping[str, bool],
               evidence: Mapping[str, EvidenceStatus]) -> Finding:
    """R-018: call when new evidence arrives. Unknown rule_id raises KeyError."""
    return evaluate_rule(STATUTORY_RULE_REGISTRY[rule_id], facts, evidence)


def compute_score(findings: List[Finding]) -> int:
    total = 100
    for f in findings:
        if f.state in SCORING_STATES:
            total -= STATUTORY_RULE_REGISTRY[f.rule_id].score_impact
    return max(0, total)
