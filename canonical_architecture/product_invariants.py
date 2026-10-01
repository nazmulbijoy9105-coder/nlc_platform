"""
NLC - Legal Compliance & Rescue Platform
Layer 1: Product Invariants (R-001 ... R-020)
Governs how the engine is allowed to evaluate, remediate, and audit.
"""
from enum import Enum

class Invariant(str, Enum):
    # Evaluation & Applicability
    R_001 = "MOA_AOA_LEGAL_MAPPING_VERIFIED"
    R_002 = "DIR_005_SECTION_97_MAPPING_REVIEW"
    R_003 = "DIR_006_SECTION_98_MAPPING_REVIEW"
    R_004 = "DIR_INTEREST_SECTION_130_REVIEW"
    R_005 = "AGM_MINUTES_SECTION_89_REVIEW"
    R_006 = "AR_001_SECTION_36_REVIEW"
    R_007 = "EVALUATION_USES_CANONICAL_RULE"
    R_008 = "UNKNOWN_IS_NOT_NON_COMPLIANT"
    R_009 = "LABOUR_FACTORY_SECTION_326_REVIEW"
    R_010 = "TAX_TIN_INCOME_TAX_ACT_2023_REVIEW"
    R_011 = "TRADE_LICENSE_LOCAL_AUTHORITY_REVIEW"
    R_012 = "FINDING_MAPS_TO_REMEDIATION"
    R_013 = "UNKNOWN_DOES_NOT_TRIGGER_NON_COMPLIANCE"
    
    # Rescue & Services
    R_014 = "RESCUE_DERIVES_FROM_FINDING"
    R_015 = "RESCUE_DEPENDENCIES_ARE_RESPECTED"
    R_016 = "SERVICES_DERIVED_FROM_EVALUATOR_FINDINGS"
    R_017 = "NOTIFICATIONS_DERIVED_FROM_DEADLINES"
    
    # Re-evaluation & Audit
    R_018 = "NEW_EVIDENCE_TRIGGERS_RE_EVALUATION"
    R_019 = "VERIFIED_CURE_CLOSES_RESCUE"
    R_020 = "IMMUTABLE_AUDIT_TRAIL_REQUIRED"

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

def get_invariant_rule(inv: Invariant) -> str:
    return INVARIANT_RULES.get(inv, "Invariant not defined.")
