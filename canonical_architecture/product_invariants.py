"""
NLC Layer 1: Product Invariants. Source: architecture diagram, Module 7.
R-006 and R-016 are absent from the diagram and intentionally undefined
until confirmed (see DIAGRAM_GAPS).
"""
from enum import Enum

class Invariant(str, Enum):
    R_001 = "R-001"
    R_002 = "R-002"
    R_003 = "R-003"
    R_004 = "R-004"
    R_005 = "R-005"
    R_007 = "R-007"
    R_008 = "R-008"
    R_009 = "R-009"
    R_010 = "R-010"
    R_011 = "R-011"
    R_012 = "R-012"
    R_013 = "R-013"
    R_014 = "R-014"
    R_015 = "R-015"
    R_017 = "R-017"
    R_018 = "R-018"
    R_019 = "R-019"
    R_020 = "R-020"

DIAGRAM_GAPS = frozenset({"R-006", "R-016"})

INVARIANT_RULES = {
    Invariant.R_001: "Canonical Source: every rule traces to a canonical legal source.",
    Invariant.R_002: "Source Metadata: every source carries act, provision and verification status.",
    Invariant.R_003: "Applicability First: applicability is resolved before evaluation.",
    Invariant.R_004: "Exceptions: exceptions are evaluated and can yield NOT_APPLICABLE.",
    Invariant.R_005: "Evidence Defined: every rule declares its required evidence.",
    Invariant.R_007: "Evaluation Logic: evaluation is deterministic from canonical rule + evidence.",
    Invariant.R_008: "Unknown != Non-Compliance: missing evidence yields UNKNOWN, never NON_COMPLIANT.",
    Invariant.R_009: "Contradiction State: conflicting evidence yields CONTRADICTORY.",
    Invariant.R_010: "Score from Findings: score is computed only from evaluated findings.",
    Invariant.R_011: "Score != Obligation: a score never creates or removes a legal obligation.",
    Invariant.R_012: "Canonical Remediation: every actionable finding maps to a canonical remediation.",
    Invariant.R_013: "Unmapped != Auto Rescue: a finding without a mapped rescue does not auto-create one.",
    Invariant.R_014: "Rescue from Findings: rescue plans derive only from active findings.",
    Invariant.R_015: "Respect Dependencies: rescue steps honour prerequisites and ordering.",
    Invariant.R_017: "Deadline -> Services: notifications derive from deadlines (confirm wording).",
    Invariant.R_018: "Evidence -> Re-evaluation: new evidence re-evaluates the related rule.",
    Invariant.R_019: "Verified -> Close: rescue closes only when verified evidence yields COMPLIANT.",
    Invariant.R_020: "Full Audit Trail: all state changes, actions and evidence are recorded.",
}

def get_invariant_rule(inv: Invariant) -> str:
    return INVARIANT_RULES[inv]   # KeyError, not a silent default
