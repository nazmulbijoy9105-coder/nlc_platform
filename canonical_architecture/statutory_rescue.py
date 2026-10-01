"""
NLC - Legal Compliance & Rescue Platform
Layer 3: Statutory Rescue Registry
Defines the legally required remediation paths, services, and deadlines.
"""
from typing import Any, Dict, List
from canonical_architecture.statutory_rules import RuleState

STATUTORY_RESCUE_REGISTRY: Dict[str, Dict[str, Any]] = {
    "AR-001": {
        "rescue_id": "AR-RESCUE-001",
        "triggered_by": "AR-001",
        "objective": "Regularize statutory annual filing deficiency",
        "prerequisites": ["AGM_HELD"],  # R-015: Must hold AGM before filing Return
        "statutory_actions": [
            "reconstruct missing information",
            "prepare statutory filing",
            "obtain required approval/signature",
            "submit to authority",
            "capture acknowledgement"
        ],
        "authority": "RJSC",
        "service_workflow": "RJSC_FILING",
        "deadline_basis": "21_DAYS_FROM_AGM",
        "notification_required": True,
        "verification": "FILING_ACKNOWLEDGEMENT",
        "closure_condition": "AR-001 == RuleState.COMPLIANT"
    },
    "INC-001": {
        "rescue_id": "INC-RESCUE-001",
        "triggered_by": "INC-001",
        "objective": "File missing MOA/AOA",
        "prerequisites": [],
        "statutory_actions": [
            "draft MOA/AOA",
            "obtain subscriber signatures",
            "submit to RJSC"
        ],
        "authority": "RJSC",
        "service_workflow": "RJSC_FILING",
        "deadline_basis": "IMMEDIATE",
        "notification_required": True,
        "verification": "RJSC_CERTIFICATE",
        "closure_condition": "INC-001 == RuleState.COMPLIANT"
    },
    "TAX-001": {
        "rescue_id": "TAX-RESCUE-001",
        "triggered_by": "TAX-001",
        "objective": "Obtain TIN from NBR",
        "prerequisites": [],
        "statutory_actions": [
            "apply for TIN via NBR portal",
            "verify entity details"
        ],
        "authority": "NBR",
        "service_workflow": "NBR_TAX",
        "deadline_basis": "IMMEDIATE",
        "notification_required": True,
        "verification": "TIN_CERTIFICATE",
        "closure_condition": "TAX-001 == RuleState.COMPLIANT"
    }
}

def get_rescue_plan(active_findings: List[str]) -> List[Dict[str, Any]]:
    """
    R-014: RESCUE <- evaluator findings.
    Generates a legally canonical rescue sequence strictly from active findings.
    """
    steps = []
    for rule_id in active_findings:
        rescue_def = STATUTORY_RESCUE_REGISTRY.get(rule_id)
        if rescue_def:
            steps.append({
                "rescue_id": rescue_def["rescue_id"],
                "triggered_by": rule_id,
                "actions": rescue_def["statutory_actions"],
                "service": rescue_def["service_workflow"],
                "deadline": rescue_def["deadline_basis"],
                "closure_condition": rescue_def["closure_condition"]
            })
    return steps
