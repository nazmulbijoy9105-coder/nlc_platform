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
    Invariant.R_008: "If required evidence is missing, state=UNKNOWN. Do not penalize as NON_COMPLIANT.",
    Invariant.R_013: "UNKNOWN state must not negatively impact the compliance score.",
    Invariant.R_014: "Rescue plans must be dynamically generated strictly from active evaluator findings.",
    Invariant.R_018: "Submission of new documentary evidence automatically triggers re-evaluation of the related rule.",
    Invariant.R_019: "A rescue case is only closed when verified evidence establishes COMPLIANT state.",
    Invariant.R_020: "All evaluation state changes, rescue actions, and evidence submissions are permanently recorded.",
}

def get_invariant_rule(inv: Invariant) -> str:
    return INVARIANT_RULES.get(inv, "Invariant not defined.")
