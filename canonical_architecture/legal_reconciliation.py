"""
NLC - Legal Reconciliation Module
Controls the verification status of statutory provisions.
"""
from typing import Any, Dict
from canonical_architecture.statutory_rules import STATUTORY_RULE_REGISTRY, ProvisionStatus

# Canonical Legal Reconciliation Registry
# Tracks the legal source verification status for every rule.
LEGAL_RECONCILIATION: Dict[str, Dict[str, Any]] = {
    "AGM-001": {
        "rule_id": "AGM-001",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "AGM-002": {
        "rule_id": "AGM-002",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "AGM-003": {
        "rule_id": "AGM-003",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "AGM-004": {
        "rule_id": "AGM-004",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "AGM-005": {
        "rule_id": "AGM-005",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "AGM-006": {
        "rule_id": "AGM-006",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "AGM-007": {
        "rule_id": "AGM-007",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "AR-001": {
        "rule_id": "AR-001",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "AR-002": {
        "rule_id": "AR-002",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "AR-003": {
        "rule_id": "AR-003",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "AR-004": {
        "rule_id": "AR-004",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "AUD-001": {
        "rule_id": "AUD-001",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "AUD-002": {
        "rule_id": "AUD-002",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "AUD-003": {
        "rule_id": "AUD-003",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "AUD-004": {
        "rule_id": "AUD-004",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "AUD-005": {
        "rule_id": "AUD-005",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "BNK-001": {
        "rule_id": "BNK-001",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "BNK-002": {
        "rule_id": "BNK-002",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "BNK-003": {
        "rule_id": "BNK-003",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "BSEC-001": {
        "rule_id": "BSEC-001",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "BSEC-002": {
        "rule_id": "BSEC-002",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "BSEC-003": {
        "rule_id": "BSEC-003",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "BSEC-004": {
        "rule_id": "BSEC-004",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "CAP-001": {
        "rule_id": "CAP-001",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "CAP-002": {
        "rule_id": "CAP-002",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "CAP-003": {
        "rule_id": "CAP-003",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "CAP-004": {
        "rule_id": "CAP-004",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "CHG-001": {
        "rule_id": "CHG-001",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "DEF-001": {
        "rule_id": "DEF-001",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "DEF-002": {
        "rule_id": "DEF-002",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "DIR-001": {
        "rule_id": "DIR-001",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "DIR-002": {
        "rule_id": "DIR-002",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "DIR-003": {
        "rule_id": "DIR-003",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "DIR-004": {
        "rule_id": "DIR-004",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "DIR-005": {
        "rule_id": "DIR-005",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "DIR-006": {
        "rule_id": "DIR-006",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "ESC-001": {
        "rule_id": "ESC-001",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "ESC-002": {
        "rule_id": "ESC-002",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "ESC-003": {
        "rule_id": "ESC-003",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "ESC-004": {
        "rule_id": "ESC-004",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "ESC-005": {
        "rule_id": "ESC-005",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "FX-001": {
        "rule_id": "FX-001",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "INC-001": {
        "rule_id": "INC-001",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "INC-002": {
        "rule_id": "INC-002",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "INC-003": {
        "rule_id": "INC-003",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "INC-004": {
        "rule_id": "INC-004",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "INC-005": {
        "rule_id": "INC-005",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "INC-006": {
        "rule_id": "INC-006",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "LBR-001": {
        "rule_id": "LBR-001",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "LBR-002": {
        "rule_id": "LBR-002",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "LBR-003": {
        "rule_id": "LBR-003",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "OFF-001": {
        "rule_id": "OFF-001",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "REG-001": {
        "rule_id": "REG-001",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "REG-002": {
        "rule_id": "REG-002",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "REG-003": {
        "rule_id": "REG-003",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "SH-001": {
        "rule_id": "SH-001",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "SH-002": {
        "rule_id": "SH-002",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "SH-003": {
        "rule_id": "SH-003",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "STR-001": {
        "rule_id": "STR-001",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "STR-002": {
        "rule_id": "STR-002",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "STR-003": {
        "rule_id": "STR-003",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "TAX-001": {
        "rule_id": "TAX-001",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "TAX-002": {
        "rule_id": "TAX-002",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "TAX-003": {
        "rule_id": "TAX-003",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "TAX-004": {
        "rule_id": "TAX-004",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "TL-001": {
        "rule_id": "TL-001",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "TL-002": {
        "rule_id": "TL-002",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "TR-001": {
        "rule_id": "TR-001",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "TR-002": {
        "rule_id": "TR-002",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "TR-003": {
        "rule_id": "TR-003",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "TR-004": {
        "rule_id": "TR-004",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "TR-005": {
        "rule_id": "TR-005",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "TR-006": {
        "rule_id": "TR-006",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "VAT-002": {
        "rule_id": "VAT-002",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
    "VAT-003": {
        "rule_id": "VAT-003",
        "verified": False,
        "verified_by": None,
        "verified_at": None,
        "source": None,
        "notes": "Awaiting legal source reconciliation."
    },
}

def get_reconciliation_status(rule_id: str) -> str:
    """Returns the provision status based on reconciliation."""
    recon = LEGAL_RECONCILIATION.get(rule_id)
    if recon and recon.get("verified"):
        return ProvisionStatus.VERIFIED.value
    return ProvisionStatus.RECONCILE.value

def verify_provision(rule_id: str, verified_by: str, source: str) -> bool:
    """Marks a rule's provision as legally verified."""
    if rule_id in LEGAL_RECONCILIATION:
        LEGAL_RECONCILIATION[rule_id].update({
            "verified": True,
            "verified_by": verified_by,
            "source": source,
            "notes": "Verified against legal source."
        })
        
        # Also update the STATUTORY_RULE_REGISTRY
        if rule_id in STATUTORY_RULE_REGISTRY:
            STATUTORY_RULE_REGISTRY[rule_id]["provision_status"] = ProvisionStatus.VERIFIED
            if "provision" not in STATUTORY_RULE_REGISTRY[rule_id] or STATUTORY_RULE_REGISTRY[rule_id]["provision"] == "TBD":
                STATUTORY_RULE_REGISTRY[rule_id]["provision"] = source
        return True
    return False
