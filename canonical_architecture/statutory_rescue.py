"""
NLC - Legal Compliance & Rescue Platform
Layer 3: Statutory Rescue Registry
"""
from typing import Any, Dict, List
from canonical_architecture.statutory_rules import RuleState

STATUTORY_RESCUE_REGISTRY: Dict[str, Dict[str, Any]] = {
    "INC-001": {
        "rescue_id": "INC-RESCUE-001",
        "triggered_by": "INC-001",
        "objective": "Remediate: Certificate of Incorporation Not Obtained",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "INC-001 == RuleState.COMPLIANT"
    },
    "INC-002": {
        "rescue_id": "INC-RESCUE-002",
        "triggered_by": "INC-002",
        "objective": "Remediate: Memorandum and Articles Not Filed",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "INC-002 == RuleState.COMPLIANT"
    },
    "INC-003": {
        "rescue_id": "INC-RESCUE-003",
        "triggered_by": "INC-003",
        "objective": "Remediate: Minimum Directors Not Appointed",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "INC-003 == RuleState.COMPLIANT"
    },
    "INC-004": {
        "rescue_id": "INC-RESCUE-004",
        "triggered_by": "INC-004",
        "objective": "Remediate: Paid-Up Capital Exceeds Authorized Capital",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "INC-004 == RuleState.COMPLIANT"
    },
    "INC-005": {
        "rescue_id": "INC-RESCUE-005",
        "triggered_by": "INC-005",
        "objective": "Remediate: Encashment Certificate Missing — Foreign Shareholding",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "INC-005 == RuleState.COMPLIANT"
    },
    "INC-006": {
        "rescue_id": "INC-RESCUE-006",
        "triggered_by": "INC-006",
        "objective": "Remediate: Remittance Below Work Permit Threshold",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "INC-006 == RuleState.COMPLIANT"
    },
    "AUD-001": {
        "rescue_id": "AUD-RESCUE-001",
        "triggered_by": "AUD-001",
        "objective": "Remediate: First Auditor Not Appointed Within 30 Days",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "AUD-001 == RuleState.COMPLIANT"
    },
    "AUD-002": {
        "rescue_id": "AUD-RESCUE-002",
        "triggered_by": "AUD-002",
        "objective": "Remediate: Audit Not Completed Before AGM",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "AUD-002 == RuleState.COMPLIANT"
    },
    "AUD-003": {
        "rescue_id": "AUD-RESCUE-003",
        "triggered_by": "AUD-003",
        "objective": "Remediate: AGM Held Without Completed Audit — BLACK OVERRIDE",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "AUD-003 == RuleState.COMPLIANT"
    },
    "AUD-004": {
        "rescue_id": "AUD-RESCUE-004",
        "triggered_by": "AUD-004",
        "objective": "Remediate: Auditor Not Reappointed at AGM",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "AUD-004 == RuleState.COMPLIANT"
    },
    "AGM-001": {
        "rescue_id": "AGM-RESCUE-001",
        "triggered_by": "AGM-001",
        "objective": "Remediate: First AGM Default",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "AGM-001 == RuleState.COMPLIANT"
    },
    "AGM-002": {
        "rescue_id": "AGM-RESCUE-002",
        "triggered_by": "AGM-002",
        "objective": "Remediate: Subsequent AGM Default",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "AGM-002 == RuleState.COMPLIANT"
    },
    "AGM-003": {
        "rescue_id": "AGM-RESCUE-003",
        "triggered_by": "AGM-003",
        "objective": "Remediate: AGM Notice Defective — Insufficient Days",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "AGM-003 == RuleState.COMPLIANT"
    },
    "AGM-004": {
        "rescue_id": "AGM-RESCUE-004",
        "triggered_by": "AGM-004",
        "objective": "Remediate: AGM Notice Missing",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "AGM-004 == RuleState.COMPLIANT"
    },
    "AGM-005": {
        "rescue_id": "AGM-RESCUE-005",
        "triggered_by": "AGM-005",
        "objective": "Remediate: AGM Quorum Not Met",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "AGM-005 == RuleState.COMPLIANT"
    },
    "AGM-006": {
        "rescue_id": "AGM-RESCUE-006",
        "triggered_by": "AGM-006",
        "objective": "Remediate: AGM Minutes Not Prepared",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "AGM-006 == RuleState.COMPLIANT"
    },
    "AR-001": {
        "rescue_id": "AR-RESCUE-001",
        "triggered_by": "AR-001",
        "objective": "Remediate: Annual Return Default — Single Year",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "AR-001 == RuleState.COMPLIANT"
    },
    "AR-002": {
        "rescue_id": "AR-RESCUE-002",
        "triggered_by": "AR-002",
        "objective": "Remediate: Annual Return 2-Year Backlog",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "AR-002 == RuleState.COMPLIANT"
    },
    "AR-003": {
        "rescue_id": "AR-RESCUE-003",
        "triggered_by": "AR-003",
        "objective": "Remediate: Annual Return 3-Year Backlog — Strike-Off Risk",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "AR-003 == RuleState.COMPLIANT"
    },
    "AR-004": {
        "rescue_id": "AR-RESCUE-004",
        "triggered_by": "AR-004",
        "objective": "Remediate: Annual Return Filed But Incomplete",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "AR-004 == RuleState.COMPLIANT"
    },
    "DIR-001": {
        "rescue_id": "DIR-RESCUE-001",
        "triggered_by": "DIR-001",
        "objective": "Remediate: Director Appointment Not Filed Within 14 Days",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "DIR-001 == RuleState.COMPLIANT"
    },
    "DIR-002": {
        "rescue_id": "DIR-RESCUE-002",
        "triggered_by": "DIR-002",
        "objective": "Remediate: Director Departure Not Filed Within 14 Days",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "DIR-002 == RuleState.COMPLIANT"
    },
    "DIR-003": {
        "rescue_id": "DIR-RESCUE-003",
        "triggered_by": "DIR-003",
        "objective": "Remediate: Major Director Filing Irregularity — Over 1 Year",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "DIR-003 == RuleState.COMPLIANT"
    },
    "DIR-004": {
        "rescue_id": "DIR-RESCUE-004",
        "triggered_by": "DIR-004",
        "objective": "Remediate: Departed Director Still Active on RJSC Register",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "DIR-004 == RuleState.COMPLIANT"
    },
    "SH-001": {
        "rescue_id": "SH-RESCUE-001",
        "triggered_by": "SH-001",
        "objective": "Remediate: Share Allotment Not Filed — Form XV",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "SH-001 == RuleState.COMPLIANT"
    },
    "SH-002": {
        "rescue_id": "SH-RESCUE-002",
        "triggered_by": "SH-002",
        "objective": "Remediate: Share Certificates Not Issued Within 60 Days",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "SH-002 == RuleState.COMPLIANT"
    },
    "SH-003": {
        "rescue_id": "SH-RESCUE-003",
        "triggered_by": "SH-003",
        "objective": "Remediate: Capital Increase Not Filed — Form IV",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "SH-003 == RuleState.COMPLIANT"
    },
    "TR-001": {
        "rescue_id": "TR-RESCUE-001",
        "triggered_by": "TR-001",
        "objective": "Remediate: No Share Transfer Instrument — Form 117",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "TR-001 == RuleState.COMPLIANT"
    },
    "TR-002": {
        "rescue_id": "TR-RESCUE-002",
        "triggered_by": "TR-002",
        "objective": "Remediate: Stamp Duty Not Paid on Share Transfer",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "TR-002 == RuleState.COMPLIANT"
    },
    "TR-003": {
        "rescue_id": "TR-RESCUE-003",
        "triggered_by": "TR-003",
        "objective": "Remediate: No Board Approval for Share Transfer",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "TR-003 == RuleState.COMPLIANT"
    },
    "TR-004": {
        "rescue_id": "TR-RESCUE-004",
        "triggered_by": "TR-004",
        "objective": "Remediate: Register of Members Not Updated After Transfer",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "TR-004 == RuleState.COMPLIANT"
    },
    "TR-005": {
        "rescue_id": "TR-RESCUE-005",
        "triggered_by": "TR-005",
        "objective": "Remediate: Share Transfer Violates AoA Restriction — BLACK OVERRIDE",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "TR-005 == RuleState.COMPLIANT"
    },
    "TR-006": {
        "rescue_id": "TR-RESCUE-006",
        "triggered_by": "TR-006",
        "objective": "Remediate: Composite Irregular Transfer",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "TR-006 == RuleState.COMPLIANT"
    },
    "REG-001": {
        "rescue_id": "REG-RESCUE-001",
        "triggered_by": "REG-001",
        "objective": "Remediate: Statutory Registers Incomplete",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "REG-001 == RuleState.COMPLIANT"
    },
    "REG-002": {
        "rescue_id": "REG-RESCUE-002",
        "triggered_by": "REG-002",
        "objective": "Remediate: Core Statutory Registers Missing",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "REG-002 == RuleState.COMPLIANT"
    },
    "REG-003": {
        "rescue_id": "REG-RESCUE-003",
        "triggered_by": "REG-003",
        "objective": "Remediate: Registers Not Kept at Registered Office",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "REG-003 == RuleState.COMPLIANT"
    },
    "OFF-001": {
        "rescue_id": "OFF-RESCUE-001",
        "triggered_by": "OFF-001",
        "objective": "Remediate: Change of Registered Office Not Filed Within 28 Days",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "OFF-001 == RuleState.COMPLIANT"
    },
    "CAP-001": {
        "rescue_id": "CAP-RESCUE-001",
        "triggered_by": "CAP-001",
        "objective": "Remediate: Capital Alteration Without Proper Resolution",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "CAP-001 == RuleState.COMPLIANT"
    },
    "CAP-002": {
        "rescue_id": "CAP-RESCUE-002",
        "triggered_by": "CAP-002",
        "objective": "Remediate: Charge Not Registered With RJSC Within 30 Days",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "CAP-002 == RuleState.COMPLIANT"
    },
    "CAP-003": {
        "rescue_id": "CAP-RESCUE-003",
        "triggered_by": "CAP-003",
        "objective": "Remediate: Charge Satisfaction Not Filed",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "CAP-003 == RuleState.COMPLIANT"
    },
    "CAP-004": {
        "rescue_id": "CAP-RESCUE-004",
        "triggered_by": "CAP-004",
        "objective": "Remediate: Special Resolution Not Filed With RJSC",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "CAP-004 == RuleState.COMPLIANT"
    },
    "TAX-001": {
        "rescue_id": "TAX-RESCUE-001",
        "triggered_by": "TAX-001",
        "objective": "Remediate: Tax Identification Number (TIN) Not Obtained",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "TAX-001 == RuleState.COMPLIANT"
    },
    "TAX-002": {
        "rescue_id": "TAX-RESCUE-002",
        "triggered_by": "TAX-002",
        "objective": "Remediate: VAT Registration Required But Not Obtained",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "TAX-002 == RuleState.COMPLIANT"
    },
    "ESC-001": {
        "rescue_id": "ESC-RESCUE-001",
        "triggered_by": "ESC-001",
        "objective": "Remediate: Strike-Off Risk Elevated",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "ESC-001 == RuleState.COMPLIANT"
    },
    "ESC-002": {
        "rescue_id": "ESC-RESCUE-002",
        "triggered_by": "ESC-002",
        "objective": "Remediate: Strike-Off Imminent — BLACK OVERRIDE",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "ESC-002 == RuleState.COMPLIANT"
    },
    "ESC-003": {
        "rescue_id": "ESC-RESCUE-003",
        "triggered_by": "ESC-003",
        "objective": "Remediate: Corporate Rescue Mandatory — Systemic Failure",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "ESC-003 == RuleState.COMPLIANT"
    },
    "AGM-007": {
        "rescue_id": "AGM-RESCUE-007",
        "triggered_by": "AGM-007",
        "objective": "Remediate: AGM Adjourned Without Proper Notice",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "AGM-007 == RuleState.COMPLIANT"
    },
    "AUD-005": {
        "rescue_id": "AUD-RESCUE-005",
        "triggered_by": "AUD-005",
        "objective": "Remediate: Subsequent Auditor Not Appointed",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "AUD-005 == RuleState.COMPLIANT"
    },
    "BNK-001": {
        "rescue_id": "BNK-RESCUE-001",
        "triggered_by": "BNK-001",
        "objective": "Remediate: Winding Up Petition Filed",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "BNK-001 == RuleState.COMPLIANT"
    },
    "BNK-002": {
        "rescue_id": "BNK-RESCUE-002",
        "triggered_by": "BNK-002",
        "objective": "Remediate: Liquidator Appointed",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "BNK-002 == RuleState.COMPLIANT"
    },
    "BNK-003": {
        "rescue_id": "BNK-RESCUE-003",
        "triggered_by": "BNK-003",
        "objective": "Remediate: Court-Ordered Winding Up",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "BNK-003 == RuleState.COMPLIANT"
    },
    "BSEC-001": {
        "rescue_id": "BSEC-RESCUE-001",
        "triggered_by": "BSEC-001",
        "objective": "Remediate: BSEC Quarterly Report Not Filed",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "BSEC-001 == RuleState.COMPLIANT"
    },
    "BSEC-002": {
        "rescue_id": "BSEC-RESCUE-002",
        "triggered_by": "BSEC-002",
        "objective": "Remediate: CG Certificate Not Obtained",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "BSEC-002 == RuleState.COMPLIANT"
    },
    "BSEC-003": {
        "rescue_id": "BSEC-RESCUE-003",
        "triggered_by": "BSEC-003",
        "objective": "Remediate: Board Composition Non-Compliant",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "BSEC-003 == RuleState.COMPLIANT"
    },
    "BSEC-004": {
        "rescue_id": "BSEC-RESCUE-004",
        "triggered_by": "BSEC-004",
        "objective": "Remediate: Audit Committee Not Established",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "BSEC-004 == RuleState.COMPLIANT"
    },
    "CHG-001": {
        "rescue_id": "CHG-RESCUE-001",
        "triggered_by": "CHG-001",
        "objective": "Remediate: Charge Satisfaction Not Filed",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "CHG-001 == RuleState.COMPLIANT"
    },
    "DEF-001": {
        "rescue_id": "DEF-RESCUE-001",
        "triggered_by": "DEF-001",
        "objective": "Remediate: Director Disqualified",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "DEF-001 == RuleState.COMPLIANT"
    },
    "DEF-002": {
        "rescue_id": "DEF-RESCUE-002",
        "triggered_by": "DEF-002",
        "objective": "Remediate: Unresolved Penalty Notices",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "DEF-002 == RuleState.COMPLIANT"
    },
    "DIR-005": {
        "rescue_id": "DIR-RESCUE-005",
        "triggered_by": "DIR-005",
        "objective": "Remediate: Register of Directors Interests Missing",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "DIR-005 == RuleState.COMPLIANT"
    },
    "DIR-006": {
        "rescue_id": "DIR-RESCUE-006",
        "triggered_by": "DIR-006",
        "objective": "Remediate: Register of Contracts Missing",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "DIR-006 == RuleState.COMPLIANT"
    },
    "ESC-004": {
        "rescue_id": "ESC-RESCUE-004",
        "triggered_by": "ESC-004",
        "objective": "Remediate: Voluntary Winding Up",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "ESC-004 == RuleState.COMPLIANT"
    },
    "ESC-005": {
        "rescue_id": "ESC-RESCUE-005",
        "triggered_by": "ESC-005",
        "objective": "Remediate: Investigation Order Pending",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "ESC-005 == RuleState.COMPLIANT"
    },
    "FX-001": {
        "rescue_id": "FX-RESCUE-001",
        "triggered_by": "FX-001",
        "objective": "Remediate: Foreign Exchange Violation",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "FX-001 == RuleState.COMPLIANT"
    },
    "LBR-001": {
        "rescue_id": "LBR-RESCUE-001",
        "triggered_by": "LBR-001",
        "objective": "Remediate: Factory License Missing",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "LBR-001 == RuleState.COMPLIANT"
    },
    "LBR-002": {
        "rescue_id": "LBR-RESCUE-002",
        "triggered_by": "LBR-002",
        "objective": "Remediate: Factory License Expired",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "LBR-002 == RuleState.COMPLIANT"
    },
    "LBR-003": {
        "rescue_id": "LBR-RESCUE-003",
        "triggered_by": "LBR-003",
        "objective": "Remediate: Labour Court Order Pending",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "LBR-003 == RuleState.COMPLIANT"
    },
    "STR-001": {
        "rescue_id": "STR-RESCUE-001",
        "triggered_by": "STR-001",
        "objective": "Remediate: Name Change Not Filed",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "STR-001 == RuleState.COMPLIANT"
    },
    "STR-002": {
        "rescue_id": "STR-RESCUE-002",
        "triggered_by": "STR-002",
        "objective": "Remediate: Object Clause Change Not Filed",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "STR-002 == RuleState.COMPLIANT"
    },
    "STR-003": {
        "rescue_id": "STR-RESCUE-003",
        "triggered_by": "STR-003",
        "objective": "Remediate: AoA Alteration Not Filed",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "STR-003 == RuleState.COMPLIANT"
    },
    "TAX-003": {
        "rescue_id": "TAX-RESCUE-003",
        "triggered_by": "TAX-003",
        "objective": "Remediate: Annual Tax Return Overdue",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "TAX-003 == RuleState.COMPLIANT"
    },
    "TAX-004": {
        "rescue_id": "TAX-RESCUE-004",
        "triggered_by": "TAX-004",
        "objective": "Remediate: Advance Tax Missed",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "TAX-004 == RuleState.COMPLIANT"
    },
    "TL-001": {
        "rescue_id": "TL-RESCUE-001",
        "triggered_by": "TL-001",
        "objective": "Remediate: Trade License Not Obtained",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "TL-001 == RuleState.COMPLIANT"
    },
    "TL-002": {
        "rescue_id": "TL-RESCUE-002",
        "triggered_by": "TL-002",
        "objective": "Remediate: Trade License Expired",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "TL-002 == RuleState.COMPLIANT"
    },
    "VAT-002": {
        "rescue_id": "VAT-RESCUE-002",
        "triggered_by": "VAT-002",
        "objective": "Remediate: Monthly VAT Return Overdue",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "VAT-002 == RuleState.COMPLIANT"
    },
    "VAT-003": {
        "rescue_id": "VAT-RESCUE-003",
        "triggered_by": "VAT-003",
        "objective": "Remediate: VAT Annual Return Overdue",
        "prerequisites": [],
        "statutory_actions": [
            "review legal requirement",
            "prepare required documentation",
            "submit to relevant authority"
        ],
        "authority": "RJSC",
        "service_workflow": "GENERAL_LEGAL_SERVICE",
        "deadline_basis": "STATUTORY",
        "notification_required": True,
        "verification": "DOCUMENTARY_EVIDENCE",
        "closure_condition": "VAT-003 == RuleState.COMPLIANT"
    },

    "BOD-001": {"rescue_id": "BOD-RESCUE-001", "triggered_by": "BOD-001", "objective": "Remediate: Board Meeting Not Held", "prerequisites": [], "statutory_actions": ["convene board meeting", "prepare agenda", "notify all directors"], "authority": "RJSC", "service_workflow": "GENERAL_LEGAL_SERVICE", "deadline_basis": "STATUTORY", "notification_required": True, "verification": "DOCUMENTARY_EVIDENCE", "closure_condition": "BOD-001 == RuleState.COMPLIANT"},
    "BOD-002": {"rescue_id": "BOD-RESCUE-002", "triggered_by": "BOD-002", "objective": "Remediate: Board Meeting Notice Not Given", "prerequisites": [], "statutory_actions": ["issue written notice", "circulate to all directors"], "authority": "RJSC", "service_workflow": "GENERAL_LEGAL_SERVICE", "deadline_basis": "STATUTORY", "notification_required": True, "verification": "DOCUMENTARY_EVIDENCE", "closure_condition": "BOD-002 == RuleState.COMPLIANT"},
    "BOD-003": {"rescue_id": "BOD-RESCUE-003", "triggered_by": "BOD-003", "objective": "Remediate: Board Minutes Not Prepared", "prerequisites": [], "statutory_actions": ["prepare minutes", "have chairman sign"], "authority": "RJSC", "service_workflow": "GENERAL_LEGAL_SERVICE", "deadline_basis": "STATUTORY", "notification_required": True, "verification": "DOCUMENTARY_EVIDENCE", "closure_condition": "BOD-003 == RuleState.COMPLIANT"},
    "ACC-001": {"rescue_id": "ACC-RESCUE-001", "triggered_by": "ACC-001", "objective": "Remediate: Financial Statements Not Presented", "prerequisites": [], "statutory_actions": ["prepare balance sheet", "prepare P&L account", "present at next AGM"], "authority": "RJSC", "service_workflow": "GENERAL_LEGAL_SERVICE", "deadline_basis": "STATUTORY", "notification_required": True, "verification": "DOCUMENTARY_EVIDENCE", "closure_condition": "ACC-001 == RuleState.COMPLIANT"},
    "ACC-002": {"rescue_id": "ACC-RESCUE-002", "triggered_by": "ACC-002", "objective": "Remediate: Financial Statements Not Filed", "prerequisites": [], "statutory_actions": ["file balance sheet with Registrar", "pay late fee if applicable"], "authority": "RJSC", "service_workflow": "GENERAL_LEGAL_SERVICE", "deadline_basis": "STATUTORY", "notification_required": True, "verification": "DOCUMENTARY_EVIDENCE", "closure_condition": "ACC-002 == RuleState.COMPLIANT"},
    "ACC-003": {"rescue_id": "ACC-RESCUE-003", "triggered_by": "ACC-003", "objective": "Remediate: Books Not Kept", "prerequisites": [], "statutory_actions": ["maintain proper books", "engage accountant"], "authority": "RJSC", "service_workflow": "GENERAL_LEGAL_SERVICE", "deadline_basis": "STATUTORY", "notification_required": True, "verification": "DOCUMENTARY_EVIDENCE", "closure_condition": "ACC-003 == RuleState.COMPLIANT"},
    "DIR-007": {"rescue_id": "DIR-RESCUE-007", "triggered_by": "DIR-007", "objective": "Remediate: Director Consent Not Filed", "prerequisites": [], "statutory_actions": ["obtain director consent", "file with Registrar"], "authority": "RJSC", "service_workflow": "GENERAL_LEGAL_SERVICE", "deadline_basis": "STATUTORY", "notification_required": True, "verification": "DOCUMENTARY_EVIDENCE", "closure_condition": "DIR-007 == RuleState.COMPLIANT"},
    "DIR-008": {"rescue_id": "DIR-RESCUE-008", "triggered_by": "DIR-008", "objective": "Remediate: Director Office of Profit", "prerequisites": [], "statutory_actions": ["obtain company consent", "disclose in general meeting"], "authority": "RJSC", "service_workflow": "GENERAL_LEGAL_SERVICE", "deadline_basis": "STATUTORY", "notification_required": True, "verification": "DOCUMENTARY_EVIDENCE", "closure_condition": "DIR-008 == RuleState.COMPLIANT"},
    "DIR-010": {"rescue_id": "DIR-RESCUE-010", "triggered_by": "DIR-010", "objective": "Remediate: MD Term Exceeds 5 Years", "prerequisites": [], "statutory_actions": ["review MD appointment", "re-appoint if needed"], "authority": "RJSC", "service_workflow": "GENERAL_LEGAL_SERVICE", "deadline_basis": "STATUTORY", "notification_required": True, "verification": "DOCUMENTARY_EVIDENCE", "closure_condition": "DIR-010 == RuleState.COMPLIANT"},
    "MEM-001": {"rescue_id": "MEM-RESCUE-001", "triggered_by": "MEM-001", "objective": "Remediate: Below Minimum Members", "prerequisites": [], "statutory_actions": ["recruit new members", "restore minimum"], "authority": "RJSC", "service_workflow": "GENERAL_LEGAL_SERVICE", "deadline_basis": "STATUTORY", "notification_required": True, "verification": "DOCUMENTARY_EVIDENCE", "closure_condition": "MEM-001 == RuleState.COMPLIANT"},
    "INC-007": {"rescue_id": "INC-RESCUE-007", "triggered_by": "INC-007", "objective": "Remediate: Business Commenced Without Declaration", "prerequisites": [], "statutory_actions": ["file Section 150 declaration", "verify minimum subscription"], "authority": "RJSC", "service_workflow": "GENERAL_LEGAL_SERVICE", "deadline_basis": "STATUTORY", "notification_required": True, "verification": "DOCUMENTARY_EVIDENCE", "closure_condition": "INC-007 == RuleState.COMPLIANT"},

}

def get_rescue_plan(active_findings: List[str]) -> List[Dict[str, Any]]:
    steps = []
    for rule_id in active_findings:
        rescue_def = STATUTORY_RESCUE_REGISTRY.get(rule_id)
        if rescue_def:
            steps.append({
                "rescue_id": rescue_def["rescue_id"],
                "triggered_by": rule_id,
                "actions": rescue_def["statutory_actions"],
                "service": rescue_def["service_workflow"],
                "closure_condition": rescue_def["closure_condition"]
            })
    return steps
