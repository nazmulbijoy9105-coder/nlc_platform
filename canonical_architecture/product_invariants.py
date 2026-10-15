"""
NLC Layer 1: Product Invariants (R-001 ... R-020) - HOW NLC must behave.
Source: architecture diagram, Module 7. R-006 and R-016 are absent from the
diagram; they stay reserved and undefined until confirmed.
"""
from enum import Enum
from typing import Dict, FrozenSet


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
INVARIANT_RULES = {
    Invariant.R_001: "MOA/AOA legal mapping verified.",
    Invariant.R_002: "DIR-005 Section 97 mapping review required.",
    Invariant.R_003: "DIR-006 Section 98 mapping review required.",
    Invariant.R_004: "Director interest Section 130 review required.",
    Invariant.R_005: "AGM minutes Section 89 review required.",
    Invariant.R_006: "AR-001 Section 36 review required.",
    Invariant.R_007: "Evaluation uses canonical rule definitions.",
    Invariant.R_008: "If required evidence is missing, state=UNKNOWN. Do not penalize as NON_COMPLIANT.",
    Invariant.R_009: "Labour factory Section 326 + rules review required.",
    Invariant.R_010: "Tax TIN Income Tax Act 2023 + NBR instruments review required.",
    Invariant.R_011: "Trade license local authority requirements review required.",
    Invariant.R_012: "Finding maps to remediation path.",
    Invariant.R_013: "UNKNOWN state must not negatively impact the compliance score.",
    Invariant.R_014: "Rescue plans must be dynamically generated strictly from active evaluator findings.",
    Invariant.R_015: "Rescue dependencies are respected (e.g. AGM before AR).",
    Invariant.R_016: "Services derived from evaluator findings.",
    Invariant.R_017: "Notifications derived from deadlines/events.",
    Invariant.R_018: "Submission of new documentary evidence automatically triggers re-evaluation of the related rule.",
    Invariant.R_019: "A rescue case is only closed when verified evidence establishes COMPLIANT state.",
    Invariant.R_020: "All evaluation state changes, rescue actions, and evidence submissions are permanently recorded.",
}


def get_invariant_rule(inv) -> str:
    return INVARIANT_RULES[Invariant(inv)]  # ValueError/KeyError, never a silent default
