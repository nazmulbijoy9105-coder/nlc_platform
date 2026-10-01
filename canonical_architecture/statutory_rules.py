"""
NLC - Legal Compliance & Rescue Platform
Layer 2: Statutory Rule Registry
Defines the canonical legal rules extracted from Bangladesh Corporate Law.
"""
from typing import Any, Dict, List
from enum import Enum

class RuleState(str, Enum):
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    CONDITIONAL = "CONDITIONAL"
    CONTRADICTORY = "CONTRADICTORY"

class ProvisionStatus(str, Enum):
    RECONCILE = "RECONCILE"  # Do not freeze section until legal source verified
    VERIFIED = "VERIFIED"

STATUTORY_RULE_REGISTRY: Dict[str, Dict[str, Any]] = {
    "AR-001": {
        "rule_id": "AR-001",
        "legal_domain": "Corporate",
        "law": "Companies Act 1994",
        "requirement": "Statutory annual filing obligation (Schedule X)",
        "provision": "Section 36",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": ["DORMANT_STRIKE_OFF"],
        "evidence_required": ["MEMBER_SHARE_DATA", "AGM_INFORMATION", "FILING_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN, RuleState.CONTRADICTORY],
        "severity": "YELLOW",
        "score_impact": 10,
        "invariants": ["R-006", "R-007", "R-008", "R-014", "R-018"]
    },
    "INC-001": {
        "rule_id": "INC-001",
        "legal_domain": "Corporate",
        "law": "Companies Act 1994",
        "requirement": "File Memorandum and Articles of Association",
        "provision": "Section 11",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_COMPANIES",
        "exceptions": [],
        "evidence_required": ["MOA_FILED", "AOA_FILED"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT],
        "severity": "RED",
        "score_impact": 15,
        "invariants": ["R-001", "R-007", "R-014", "R-019"]
    },
    "TAX-001": {
        "rule_id": "TAX-001",
        "legal_domain": "Tax",
        "law": "Income Tax Act 2023",
        "requirement": "Obtain Tax Identification Number (TIN)",
        "provision": "NBR Instruments",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_COMPANIES",
        "exceptions": [],
        "evidence_required": ["TIN_CERTIFICATE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT],
        "severity": "RED",
        "score_impact": 10,
        "invariants": ["R-010", "R-014", "R-019"]
    },
    "LBR-001": {
        "rule_id": "LBR-001",
        "legal_domain": "Labour",
        "law": "Labour Act 2006",
        "requirement": "Factory license obtained",
        "provision": "Section 326",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "MANUFACTURING_ENTITIES",
        "exceptions": ["NON_FACTORY_OPERATIONS"],
        "evidence_required": ["FACTORY_LICENSE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN, RuleState.NOT_APPLICABLE],
        "severity": "RED",
        "score_impact": 10,
        "invariants": ["R-009", "R-014", "R-019"]
    }
    # ... 75+ more canonical rules
}

def get_rule(rule_id: str) -> Dict[str, Any] | None:
    return STATUTORY_RULE_REGISTRY.get(rule_id)
