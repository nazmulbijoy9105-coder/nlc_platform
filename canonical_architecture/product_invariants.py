"""
Canonical Architecture — Product Invariants
"""
from enum import Enum
from typing import Dict, FrozenSet

class Invariant(str, Enum):
    R_001 = "R_001"
    R_002 = "R_002"
    R_003 = "R_003"
    R_004 = "R_004"
    R_005 = "R_005"
    R_007 = "R_007"
    R_008 = "R_008"
    R_009 = "R_009"
    R_010 = "R_010"
    R_011 = "R_011"
    R_012 = "R_012"
    R_013 = "R_013"
    R_014 = "R_014"
    R_015 = "R_015"
    R_017 = "R_017"
    R_018 = "R_018"
    R_019 = "R_019"
    R_020 = "R_020"

RESERVED_UNDEFINED: FrozenSet[str] = frozenset({"R-006", "R-016"})

INVARIANT_RULES: Dict[Invariant, str] = {
    Invariant.R_001: "Canonical Source: every rule traces to a canonical legal source.",
    Invariant.R_002: "Source Metadata: every rule carries law, provision and verification status.",
    Invariant.R_003: "Applicability First: applicability is resolved before evaluation.",
    Invariant.R_004: "Exceptions: declared exceptions are evaluated and yield NOT_APPLICABLE.",
    Invariant.R_005: "Evidence Defined: every rule declares its required evidence.",
    Invariant.R_007: "Evaluation Logic: evaluation is deterministic from canonical rule + evidence.",
    Invariant.R_008: "Unknown != Non-Compliance: missing or unverified evidence yields UNKNOWN, never NON_COMPLIANT. UNKNOWN never reduces the score.",
    Invariant.R_009: "Contradiction State: conflicting evidence yields CONTRADICTORY.",
    Invariant.R_010: "Score from Findings: score is computed only from evaluated findings (NON_COMPLIANT only).",
    Invariant.R_011: "Score != Obligation: a score never creates or removes a legal obligation.",
    Invariant.R_012: "Canonical Remediation: every statutory rule maps to a canonical rescue definition.",
    Invariant.R_013: "Unmapped != Auto Rescue: a finding with no mapped rescue is surfaced, never auto-rescued.",
    Invariant.R_014: "Rescue from Findings: rescue derives only from active findings. UNKNOWN/CONTRADICTORY open an evidence-establishing rescue, not a remedial one.",
    Invariant.R_015: "Respect Dependencies: a rescue with unmet prerequisites is BLOCKED.",
    Invariant.R_017: "Deadline -> Services: notifications derive from deadlines (wording unconfirmed in diagram).",
    Invariant.R_018: "Evidence -> Re-evaluation: new evidence re-evaluates the related rule.",
    Invariant.R_019: "Verified -> Close: a rescue closes only when verified evidence yields COMPLIANT.",
    Invariant.R_020: "Full Audit Trail: all state changes, actions and evidence are recorded, append-only.",
}

def get_invariant_rule(inv) -> str:
    return INVARIANT_RULES[Invariant(inv)]
