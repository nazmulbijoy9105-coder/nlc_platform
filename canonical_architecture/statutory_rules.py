"""
NLC Layer 2: Statutory Rule Registry - WHAT Bangladesh law requires.
Every provision is RECONCILE (unverified) until checked against the legal
source. Do not treat any section number here as frozen.
NLC - Legal Compliance & Rescue Platform
Layer 2: Statutory Rule Registry
Populated with canonical legal data from seed corpus.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, Tuple


class RuleState(str, Enum):
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    VERIFIED_ABSENT = "VERIFIED_ABSENT"  # confirmed absence via verified external source
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    DISPUTED = "DISPUTED"
    REQUIRES_LAWYER_JUDGMENT = "REQUIRES_LAWYER_JUDGMENT"
    CONDITIONAL = "CONDITIONAL"      # defined; no evaluator emits it yet
    CONTRADICTORY = "CONTRADICTORY"


class ProvisionStatus(str, Enum):
    RECONCILE = "RECONCILE"
    VERIFIED = "VERIFIED"


class Severity(str, Enum):
    BLACK = "BLACK"
    NOT_EVALUATED = "NOT_EVALUATED"   # legacy override band; override scoring NOT implemented here
    RED = "RED"
    YELLOW = "YELLOW"


_BASE_STATES = (RuleState.COMPLIANT, RuleState.NON_COMPLIANT,
                RuleState.UNKNOWN, RuleState.CONTRADICTORY)
_COMMON_INVARIANTS = ("R-001", "R-002", "R-003", "R-005", "R-007", "R-008",
                      "R-009", "R-010", "R-012", "R-014", "R-018", "R-019")


@dataclass(frozen=True)
class StatutoryRule:
    rule_id: str
    legal_domain: str
    law: str
    requirement: str
    provision: str
    provision_status: ProvisionStatus
    authority: str
    evidence_required: Tuple[str, ...]
    severity: Severity
    score_impact: int
    applies_if: Optional[str] = None      # company fact that must be True, else NOT_APPLICABLE
    exceptions: Tuple[str, ...] = ()      # company facts that, if True, make it NOT_APPLICABLE

    @property
    def evaluation_states(self) -> Tuple[RuleState, ...]:
        if self.applies_if or self.exceptions:
            return _BASE_STATES + (RuleState.NOT_APPLICABLE,)
        return _BASE_STATES

    @property
    def invariants(self) -> Tuple[str, ...]:
        extra = ("R-004",) if self.exceptions else ()
        return tuple(sorted(set(_COMMON_INVARIANTS + extra)))


_RULES = (
    StatutoryRule(
        "INC-001", "Corporate", "Companies Act 1994",
        "File Memorandum and Articles of Association", "Section 23",
        ProvisionStatus.RECONCILE, "RJSC", ("MOA_FILED", "AOA_FILED"),
        Severity.RED, 15),
    StatutoryRule(
        "AR-001", "Corporate", "Companies Act 1994",
        "Statutory annual filing obligation (Schedule X)", "Section 36",
        ProvisionStatus.RECONCILE, "RJSC",
        ("MEMBER_SHARE_DATA", "AGM_INFORMATION", "FILING_EVIDENCE"),
        Severity.YELLOW, 10, exceptions=("DORMANT_STRIKE_OFF",)),
    StatutoryRule(
        "TAX-001", "Tax", "Income Tax Act 2023",
        "Obtain Tax Identification Number (TIN)",
        "UNIDENTIFIED (NBR instrument to be located)",
        ProvisionStatus.RECONCILE, "NBR", ("TIN_CERTIFICATE",),
        Severity.RED, 10),
    StatutoryRule(
        "LBR-001", "Labour", "Labour Act 2006",
        "Factory license obtained", "Section 326",
        ProvisionStatus.RECONCILE, "LABOUR_DEPT", ("FACTORY_LICENSE",),
        Severity.RED, 10, applies_if="IS_MANUFACTURING",
        exceptions=("NON_FACTORY_OPERATIONS",)),
    StatutoryRule(
        "TL-001", "Local Authority", "Local authority trade licensing (instrument to be identified)",
        "Valid trade license from local authority", "UNIDENTIFIED",
        ProvisionStatus.RECONCILE, "CITY_CORPORATION", ("TRADE_LICENSE",),
        Severity.YELLOW, 5),
    StatutoryRule(
        "DIR-005", "Corporate", "Companies Act 1994",
        "Maintain statutory register mapped to DIR-005 (mapping under review)",
        "Section 130", ProvisionStatus.RECONCILE, "INTERNAL",
        ("REGISTER_DIR_005",), Severity.YELLOW, 5),
    StatutoryRule(
        "DIR-006", "Corporate", "Companies Act 1994",
        "Maintain statutory register mapped to DIR-006 (mapping under review)",
        "Section 130", ProvisionStatus.RECONCILE, "INTERNAL",
        ("REGISTER_DIR_006",), Severity.YELLOW, 5),
)

STATUTORY_RULE_REGISTRY: Dict[str, StatutoryRule] = {r.rule_id: r for r in _RULES}
if len(STATUTORY_RULE_REGISTRY) != len(_RULES):
    raise RuntimeError("duplicate rule_id in statutory rule registry")


def get_rule(rule_id: str) -> Optional[StatutoryRule]:
    """Retrieve a statutory rule by its ID."""
    return STATUTORY_RULE_REGISTRY.get(rule_id)
_LEGACY_RULE_DICTS: Dict[str, Dict[str, Any]] = {
    "INC-001": {
        "rule_id": "INC-001",
        "legal_domain": "Corporate",
        "law": "Section 23, Companies Act 1994 (Bangladesh)",
        "requirement": "Memorandum and Articles of Association not filed with RJSC. Section 23: constitutional documents must be filed.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "RED",
        "score_impact": 15,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    
    "INC-003": {
        "rule_id": "INC-003",
        "legal_domain": "Corporate",
        "law": "Sections 90(1) and 90(2), Companies Act 1994 (Bangladesh)",
        "requirement": "Minimum directors: three for a public company and a private subsidiary of a public company under Section 90(1); two for other private companies under Section 90(2). Determine company classification and verify director count before finding a breach.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "RED",
        "score_impact": 15,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "INC-004": {
        "rule_id": "INC-004",
        "legal_domain": "Corporate",
        "law": "Section 59, Companies Act 1994 (Bangladesh)",
        "requirement": "Paid-Up Capital Exceeds Authorized Capital - Paid-up capital exceeds authorized capital. Section 150: company cannot issue shares beyond authorized capital. All excess allotments void.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "BLACK",
        "score_impact": 20,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "INC-005": {
        "rule_id": "INC-005",
        "legal_domain": "Corporate",
        "law": "Section 150, Companies Act 1994; BIDA Foreign Investment Guidelines",
        "requirement": "Encashment Certificate Missing — Foreign Shareholding - Foreign shareholding detected but Encashment Certificate from AD bank not uploaded. Required under BIDA guidelines. CONDITIONAL: Only applies if has_foreign_shareholder == True.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "YELLOW",
        "score_impact": 8,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "INC-006": {
        "rule_id": "INC-006",
        "legal_domain": "Corporate",
        "law": "BIDA Foreign Investment Act 1980; BOI Guidelines",
        "requirement": "Remittance Below Work Permit Threshold - Foreign remittance below USD 50,000 threshold for work permit sponsorship. BIDA registration may be challenged. CONDITIONAL: Only applies if has_foreign_shareholder == True AND bida_registered == True.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "YELLOW",
        "score_impact": 5,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "AUD-001": {
        "rule_id": "AUD-001",
        "legal_domain": "Corporate",
        "law": "Section 210(6), Companies Act 1994 (Bangladesh)",
        "requirement": "First auditor not appointed by the Board within one calendar month of registration. Distinguish the Board's first-auditor appointment duty under Section 210(6) from the auditor's separate notice to the Registrar under Section 210(2).",
        "requirement": "First auditor not appointed by the Board within one month of registration. The engine calculates the one-month period using calendar-month semantics, not a fixed 30-day interval.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "YELLOW",
        "score_impact": 10,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "AUD-002": {
        "rule_id": "AUD-002",
        "legal_domain": "Corporate",
        "law": "Section 183, Companies Act 1994 (Bangladesh)",
        "requirement": "Accounts and audit status for AGM: Section 183 governs the balance sheet and profit-and-loss or income-and-expenditure account to be laid before the AGM. Do not infer that every resolution is void merely because audit evidence is absent.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "RED",
        "score_impact": 12,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "AUD-003": {
        "rule_id": "AUD-003",
        "legal_domain": "Corporate",
        "law": "Sections 183 and 210, Companies Act 1994 (Bangladesh)",
        "requirement": "AGM held without completed audit: this is a serious compliance finding requiring legal review of the accounts, auditor appointment and AGM consequences. It is not, by itself, a statutory BLACK classification or automatic finding of fraud; BLACK is an NLC escalation policy.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "RED",
        "score_impact": 0,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "AUD-004": {
        "rule_id": "AUD-004",
        "legal_domain": "Corporate",
        "law": "Section 210(3), Companies Act 1994 (Bangladesh)",
        "requirement": "Auditor appointment or reappointment at an AGM is assessed under Section 210(3), using verified AGM minutes and appointment records.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "YELLOW",
        "score_impact": 5,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "AGM-001": {
        "rule_id": "AGM-001",
        "legal_domain": "Corporate",
        "law": "Section 81(1), Companies Act 1994 (Bangladesh)",
        "requirement": "First AGM Default - First AGM not held within 18 months (548 days) of incorporation. Section 81 is mandatory; no waiver for private companies. Default counts from day after deadline.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "RED",
        "score_impact": 20,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "AGM-002": {
        "rule_id": "AGM-002",
        "legal_domain": "Corporate",
        "law": "Section 81(1), Companies Act 1994 (Bangladesh)",
        "requirement": "Subsequent AGM Default - Subsequent AGM not held within 15 months of preceding AGM, or 6 months of FY end — whichever earlier. Section 81 makes no exception for size or dormancy.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "RED",
        "score_impact": 20,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "AGM-003": {
        "rule_id": "AGM-003",
        "legal_domain": "Corporate",
        "law": "Section 85(1)(a), Companies Act 1994 (Bangladesh)",
        "requirement": "AGM short notice may be valid with written consent of all members entitled to attend and vote. Do not classify as defective unless absence of the required consent is verified.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "YELLOW",
        "score_impact": 5,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "AGM-004": {
        "rule_id": "AGM-004",
        "legal_domain": "Corporate",
        "law": "Section 85(1)(a), Companies Act 1994 (Bangladesh)",
        "requirement": "No notice date is recorded before the AGM. A defect is confirmed only where written short-notice consent from all members entitled to attend and vote is verified absent; otherwise legal status remains unknown.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "RED",
        "score_impact": 15,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "AGM-005": {
        "rule_id": "AGM-005",
        "legal_domain": "Corporate",
        "law": "Section 85(2)(b), Companies Act 1994 (Bangladesh)",
        "requirement": "AGM quorum is subject to the Articles: under the statutory default, a private company with no more than six members requires two members present; one with more than six requires three. Require verified attendance and a verified Articles/statutory quorum basis.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "RED",
        "score_impact": 15,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "AGM-006": {
        "rule_id": "AGM-006",
        "legal_domain": "Corporate",
        "law": "Section 89, Companies Act 1994 (Bangladesh)",
        "requirement": "AGM Minutes Not Prepared - AGM held but minutes not prepared or signed by chairman. Section 89: minutes are prima facie evidence of proceedings. Without minutes, AGM validity can be challenged.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "YELLOW",
        "score_impact": 5,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "AR-001": {
        "rule_id": "AR-001",
        "legal_domain": "Corporate",
        "law": "Section 36, Companies Act 1994 (Bangladesh) – Schedule X",
        "requirement": "Annual Return Default — Single Year - Schedule X (Annual Return) not filed within 21 days of AGM. Section 36 requires the annual summary of share capital and list of members/directors within 21 days. Every officer in default is personally liable to fine for each day of continuing default.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "YELLOW",
        "score_impact": 10,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "AR-002": {
        "rule_id": "AR-002",
        "legal_domain": "Corporate",
        "law": "Sections 36 and 304, Companies Act 1994 (Bangladesh)",
        "requirement": "Annual Return 2-Year Backlog - Annual returns unfiled for 2+ consecutive years. Multi-year default increases RJSC enforcement risk. RJSC may commence strike-off under Section 304. Directors face cumulative personal fines.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "RED",
        "score_impact": 20,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "AR-003": {
        "rule_id": "AR-003",
        "legal_domain": "Corporate",
        "law": "Sections 36 and 304, Companies Act 1994 (Bangladesh)",
        "requirement": "Annual Return 3-Year Backlog — Strike-Off Risk - Annual returns unfiled for 3+ consecutive years. RJSC has legal basis and practice of initiating strike-off under Section 304. Struck-off company loses legal personality; contracts void, accounts frozen. Corporate Rescue mandatory.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "BLACK",
        "score_impact": 20,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "AR-004": {
        "rule_id": "AR-004",
        "legal_domain": "Corporate",
        "law": "Section 36, Companies Act 1994 (Bangladesh) – Schedule X",
        "requirement": "Annual Return Filed But Incomplete - Annual Return filed but missing required attachments: audited financial statements, directors list, members list, or secretary's certificate. Incomplete filing does not satisfy Section 36; company remains in default.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "YELLOW",
        "score_impact": 8,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "DIR-001": {
        "rule_id": "DIR-001",
        "legal_domain": "Corporate",
        "law": "Section 115, Companies Act 1994 (Bangladesh)",
        "requirement": "Director appointment particulars not filed via Form XII within 14 days under Section 115. Filing default is distinct from the validity of the appointment itself.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "YELLOW",
        "score_impact": 10,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "DIR-002": {
        "rule_id": "DIR-002",
        "legal_domain": "Corporate",
        "law": "Section 115, Companies Act 1994 (Bangladesh)",
        "requirement": "Director cessation particulars not filed via Form XII within 14 days under Section 115. Filing default is distinct from the effective date and legal consequences of cessation.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "YELLOW",
        "score_impact": 10,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "DIR-003": {
        "rule_id": "DIR-003",
        "legal_domain": "Corporate",
        "law": "Section 92, Companies Act 1994 (Bangladesh)",
        "requirement": "Major Director Filing Irregularity — Over 1 Year - Director change unfiled for over 1 year. Continuing offence under Section 92. Prolonged non-filing creates compounding personal liability. Each day of default adds to statutory fine. Board resolutions may be challenged.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "RED",
        "score_impact": 15,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "DIR-004": {
        "rule_id": "DIR-004",
        "legal_domain": "Corporate",
        "law": "Section 115, Companies Act 1994 (Bangladesh)",
        "requirement": "Late or missing Form XII cessation particulars require case-specific review of the filing default, actual cessation date and third-party reliance. Non-filing alone does not automatically establish continuing director liability.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "YELLOW",
        "score_impact": 0,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "SH-001": {
        "rule_id": "SH-001",
        "legal_domain": "Corporate",
        "law": "Section 151, Companies Act 1994 (Bangladesh)",
        "requirement": "Share Allotment Not Filed — Form XV - Share allotment not filed via Form XV within 30 days. Section 50 requires return of allotment. Failure means allotment not reflected in RJSC register, creating uncertainty about issued capital.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "YELLOW",
        "score_impact": 8,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "SH-002": {
        "rule_id": "SH-002",
        "legal_domain": "Corporate",
        "law": "Section 158, Companies Act 1994 (Bangladesh)",
        "requirement": "Share Certificates Not Issued Within 60 Days - Share certificates not issued within 60 days of allotment. Section 46 requires certificates within 2 months. Non-issuance means no documentary evidence of ownership, obstructing transfers and dividends.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "YELLOW",
        "score_impact": 5,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "SH-003": {
        "rule_id": "SH-003",
        "legal_domain": "Corporate",
        "law": "Section 52, Companies Act 1994 (Bangladesh)",
        "requirement": "Capital Increase Not Filed — Form IV - Capital increase not filed via Form IV within 30 days of special resolution. Section 52 requires notice of increase. Unrecorded increases cause RJSC records to differ from actual capital.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "YELLOW",
        "score_impact": 8,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "TR-001": {
        "rule_id": "TR-001",
        "legal_domain": "Corporate",
        "law": "Section 38, Companies Act 1994 (Bangladesh)",
        "requirement": "No Share Transfer Instrument — Form 117 - Share transfer without Form 117 instrument. Section 108 requires proper instrument of transfer, duly stamped, executed by both parties. Missing instrument renders transfer void and unregistrable.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "YELLOW",
        "score_impact": 5,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "TR-002": {
        "rule_id": "TR-002",
        "legal_domain": "Corporate",
        "law": "Stamp Act 1899 (Bangladesh), Schedule I, Item 62",
        "requirement": "Stamp Duty Not Paid on Share Transfer - Stamp duty not paid on share transfer. Stamp Act 1899 requires ad valorem duty. Unstamped instrument inadmissible in court and cannot be registered. Transferee's ownership unenforceable until duty paid.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "YELLOW",
        "score_impact": 5,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "TR-003": {
        "rule_id": "TR-003",
        "legal_domain": "Corporate",
        "law": "Section 47, Companies Act 1994 (Bangladesh); Articles of Association",
        "requirement": "No Board Approval for Share Transfer - Share transfer without board approval where AoA restricts transfer. Section 47 + AoA: board approval required. Transfer in breach is void; transferee has no legal title. Register cannot be validly updated.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "YELLOW",
        "score_impact": 8,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "TR-004": {
        "rule_id": "TR-004",
        "legal_domain": "Corporate",
        "law": "Section 34, Companies Act 1994 (Bangladesh)",
        "requirement": "Register of Members Not Updated After Transfer - Register of Members not updated within 2 months of transfer lodgement. Section 34 requires register update. Until updated, transferee is not recognized member and cannot exercise rights.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "YELLOW",
        "score_impact": 5,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "TR-005": {
        "rule_id": "TR-005",
        "legal_domain": "Corporate",
        "law": "Section 47, Companies Act 1994 (Bangladesh); Articles of Association",
        "requirement": "Share Transfer Violates AoA Restriction — BLACK OVERRIDE - Transfer executed in violation of AoA restriction — pre-emption rights not offered, prohibited transferee, or board approval refused. Transfer is void ab initio. Transferee has no legal title. Rectification requires court order or unanimous ratification. BLACK OVERRIDE: forces score to BLACK band. Corporate Rescue mandatory.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "BLACK",
        "score_impact": 15,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "TR-006": {
        "rule_id": "TR-006",
        "legal_domain": "Corporate",
        "law": "Sections 34, 47, 108, Companies Act 1994 (Bangladesh)",
        "requirement": "Composite Irregular Transfer - Transfer has 2+ concurrent deficiencies from TR-001 to TR-005. Composite irregularity compounds legal risk. Each deficiency may independently void transfer. Together they indicate systemic share administration failure requiring structured remediation.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "RED",
        "score_impact": 10,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "REG-001": {
        "rule_id": "REG-001",
        "legal_domain": "Corporate",
        "law": "Sections 34, 83, 87, 90, Companies Act 1994 (Bangladesh)",
        "requirement": "Statutory Registers Incomplete - One or more of 7 mandatory statutory registers not maintained at registered office. Required: Members (Sec 34), Directors (Sec 90), Charges (Sec 87), Transfers (Sec 108), Debentures (Sec 90), AGM Minutes (Sec 83), Board Minutes (Sec 90). Failure is criminal offence; officers personally liable.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "YELLOW",
        "score_impact": 5,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "REG-002": {
        "rule_id": "REG-002",
        "legal_domain": "Corporate",
        "law": "Sections 34, 83, 87, 90, Companies Act 1994 (Bangladesh)",
        "requirement": "Core Statutory Registers Missing - Core registers missing: Members (Sec 34), Directors (Sec 90), Charges (Sec 87), or AGM Minutes (Sec 83). These are minimum required for basic corporate governance. Absence indicates fundamental governance failure.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "RED",
        "score_impact": 10,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "REG-003": {
        "rule_id": "REG-003",
        "legal_domain": "Corporate",
        "law": "Section 34(2), Companies Act 1994 (Bangladesh)",
        "requirement": "Registers Not Kept at Registered Office - Statutory registers not at registered office. Section 34(2): registers must be at registered office unless RJSC notified of alternative location. Alternative must be in Bangladesh and Board-approved. Registers open to inspection during business hours.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "YELLOW",
        "score_impact": 3,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "OFF-001": {
        "rule_id": "OFF-001",
        "legal_domain": "Corporate",
        "law": "Section 77, Companies Act 1994 (Bangladesh)",
        "requirement": "Change of Registered Office Not Filed Within 28 Days - Office change not filed via Form VI within 28 days. Section 77 requires 28-day filing (NOT 30 days). Until filed, old address remains legal registered office. Statutory notices served there are valid.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "YELLOW",
        "score_impact": 3,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "CAP-001": {
        "rule_id": "CAP-001",
        "legal_domain": "Corporate",
        "law": "Section 54, Companies Act 1994 (Bangladesh)",
        "requirement": "Capital Alteration Without Proper Resolution - Capital alteration without required board/special resolution, or forms not filed. Section 54 governs capital increase procedure. Unrecorded changes cause RJSC register to differ from actual capital, creating legal uncertainty.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "YELLOW",
        "score_impact": 5,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "CAP-002": {
        "rule_id": "CAP-002",
        "legal_domain": "Corporate",
        "law": "Section 87, Companies Act 1994 (Bangladesh)",
        "requirement": "Charge Not Registered With RJSC Within 30 Days - Charge created but not registered via Form VIII within 30 days. Section 87: unregistered charge is void against liquidator and creditors. Lender loses security interest, becomes unsecured creditor. Officers personally liable.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "YELLOW",
        "score_impact": 5,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "CAP-003": {
        "rule_id": "CAP-003",
        "legal_domain": "Corporate",
        "law": "Sections 59-60, Companies Act 1994 (Bangladesh)",
        "requirement": "Capital reduction requires compliance with Sections 59-60, including court confirmation and registration. Assess the court order, creditor protection and registration evidence; do not infer a breach from a pending workflow flag alone.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "YELLOW",
        "score_impact": 3,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "CAP-004": {
        "rule_id": "CAP-004",
        "legal_domain": "Corporate",
        "law": "Section 88(1), Companies Act 1994 (Bangladesh)",
        "requirement": "Special or extraordinary resolution copy must be filed with RJSC within 15 days under Section 88(1). The underlying transaction may have additional requirements." Unfiled resolution not binding on company or enforceable against third parties. Includes capital increase, MoA/AoA alteration, voluntary winding up.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "YELLOW",
        "score_impact": 8,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "TAX-001": {
        "rule_id": "TAX-001",
        "legal_domain": "Tax",
        "law": "Income Tax Act 2023 (Bangladesh)",
        "requirement": "Tax Identification Number (TIN) Not Obtained - No TIN from NBR. Income Tax Act 2023: TIN mandatory for all companies. Without TIN: cannot file returns, open bank accounts, obtain import licenses, participate in tenders, or claim exemptions. Directors may face liability for trading without TIN.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "RED",
        "score_impact": 10,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "TAX-002": {
        "rule_id": "TAX-002",
        "legal_domain": "Tax",
        "law": "Value Added Tax Act 2012 (Bangladesh)",
        "requirement": "VAT Registration Required But Not Obtained - Company exceeds VAT threshold but not registered. VAT Act 2012: registration required above turnover threshold (Tk 30 lakh goods, Tk 15 lakh services). Without VAT: cannot issue tax invoices, claim input credits, or legally supply taxable goods/services. CONDITIONAL: Only applies if estimated turnover exceeds threshold.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "YELLOW",
        "score_impact": 5,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "ESC-001": {
        "rule_id": "ESC-001",
        "legal_domain": "Corporate",
        "law": "Section 304, Companies Act 1994 (Bangladesh)",
        "requirement": "Strike-Off Risk Elevated - Compliance profile shows RJSC strike-off criteria under Section 304: multi-year missed filings, no recent trading, or RED flags across 3+ modules. Section 304 permits strike-off for non-filing or non-trading. Structured Regularization required immediately.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "RED",
        "score_impact": 15,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "ESC-002": {
        "rule_id": "ESC-002",
        "legal_domain": "Corporate",
        "law": "Section 304, Companies Act 1994 (Bangladesh)",
        "requirement": "Strike-Off Imminent — BLACK OVERRIDE - Immediate RJSC strike-off risk. Criteria: 3+ years non-filing, strike-off notice received, or on published strike-off list. Once struck off: company ceases to exist, contracts void, accounts frozen. Restoration requires court proceedings under Section 305. Corporate Rescue mandatory. BLACK OVERRIDE: forces score to BLACK band.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "BLACK",
        "score_impact": 25,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "ESC-003": {
        "rule_id": "ESC-003",
        "legal_domain": "Corporate",
        "law": "NLC internal risk policy (not a statutory Companies Act classification)",
        "requirement": "Internal BLACK escalation and rescue workflow. A BLACK classification, score threshold and rescue deadline are NLC policy decisions, not statutory consequences. Policy-owner approval is required.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "BLACK",
        "score_impact": 25,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "AGM-007": {
        "rule_id": "AGM-007",
        "legal_domain": "Corporate",
        "law": "Section 84, Companies Act 1994 (Bangladesh)",
        "requirement": "AGM Adjourned Without Proper Notice - AGM adjourned without proper notice. Section 84.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "YELLOW",
        "score_impact": 5,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "AUD-005": {
        "rule_id": "AUD-005",
        "legal_domain": "Corporate",
        "law": "Section 210(2), Companies Act 1994 (Bangladesh)",
        "requirement": "Subsequent Auditor Not Appointed - No auditor appointed for current FY. Section 210(2): mandatory at every AGM.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "RED",
        "score_impact": 10,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "BNK-001": {
        "rule_id": "BNK-001",
        "legal_domain": "Corporate",
        "law": "Bankruptcy Act 1997 (Bangladesh), Section 12",
        "requirement": "Winding Up Petition Filed - Winding up petition filed against company. Company under court supervision.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "BLACK",
        "score_impact": 25,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "BNK-002": {
        "rule_id": "BNK-002",
        "legal_domain": "Corporate",
        "law": "Bankruptcy Act 1997 (Bangladesh), Section 14",
        "requirement": "Liquidator Appointed - Liquidator appointed. Company under liquidation proceedings.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "BLACK",
        "score_impact": 25,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "BNK-003": {
        "rule_id": "BNK-003",
        "legal_domain": "Corporate",
        "law": "Bankruptcy Act 1997 (Bangladesh), Section 18",
        "requirement": "Court-Ordered Winding Up - Court-ordered winding up. Company being wound up by court order.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "BLACK",
        "score_impact": 35,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "BSEC-001": {
        "rule_id": "BSEC-001",
        "legal_domain": "Corporate",
        "law": "BSEC Corporate Governance Code 2023, Para 8",
        "requirement": "BSEC Quarterly Report Not Filed - BSEC quarterly report not filed (listed companies only).",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "RED",
        "score_impact": 10,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "BSEC-002": {
        "rule_id": "BSEC-002",
        "legal_domain": "Corporate",
        "law": "BSEC Corporate Governance Code 2023, Para 9",
        "requirement": "CG Certificate Not Obtained - Corporate Governance certificate not obtained (listed companies).",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "RED",
        "score_impact": 10,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "BSEC-003": {
        "rule_id": "BSEC-003",
        "legal_domain": "Corporate",
        "law": "BSEC Corporate Governance Code 2023, Para 5",
        "requirement": "Board Composition Non-Compliant - Board composition non-compliant (independent director requirement).",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "YELLOW",
        "score_impact": 8,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "BSEC-004": {
        "rule_id": "BSEC-004",
        "legal_domain": "Corporate",
        "law": "BSEC Corporate Governance Code 2018, as amended in 2023 and 2024, Condition 5",
        "requirement": "Audit Committee Not Established - Audit committee not established (listed companies).",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "YELLOW",
        "score_impact": 5,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "CHG-001": {
        "rule_id": "CHG-001",
        "legal_domain": "Corporate",
        "law": "Section 172, Companies Act 1994 (Bangladesh)",
        "requirement": "Charge satisfaction must be notified using Form XXVIII within 21 days per RJSC process guidance; confirm satisfaction date and filing receipt. Section 172 is the Act provision for registration of payment or satisfaction of mortgage/charge.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "YELLOW",
        "score_impact": 3,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "DEF-001": {
        "rule_id": "DEF-001",
        "legal_domain": "Corporate",
        "law": "Section 94, Companies Act 1994 (Bangladesh)",
        "requirement": "Director disqualification under Section 94: assess only a specified statutory or Articles ground, director identity, authoritative evidence, effective date and continuing status. The unpaid-call threshold remains disputed across Bengali/English materials (180 days versus six months) and requires lawyer review. Section 94 does not impose a universal five-year disqualification period.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN, RuleState.DISPUTED],
        "severity": "RED",
        "score_impact": 10,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "DEF-002": {
        "rule_id": "DEF-002",
        "legal_domain": "Corporate",
        "law": "Section 397, Companies Act 1994 (Bangladesh)",
        "requirement": "Unresolved Penalty Notices - Unresolved penalty notices. Section 397: fine up to Tk 10,000 per offence.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "YELLOW",
        "score_impact": 5,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "DIR-005": {
        "rule_id": "DIR-005",
        "legal_domain": "Corporate",
        "law": "Section 97, Companies Act 1994 (Bangladesh)",
        "requirement": "Register of Directors Interests Missing - Register of directors interests not maintained. Section 97.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "YELLOW",
        "score_impact": 5,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "DIR-006": {
        "rule_id": "DIR-006",
        "legal_domain": "Corporate",
        "law": "Section 98, Companies Act 1994 (Bangladesh)",
        "requirement": "Register of Contracts Missing - Register of contracts not maintained. Section 98.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "YELLOW",
        "score_impact": 5,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "ESC-004": {
        "rule_id": "ESC-004",
        "legal_domain": "Corporate",
        "law": "Section 234, Companies Act 1994 (Bangladesh)",
        "requirement": "Voluntary Winding Up - Voluntary winding up initiated. Section 196.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "BLACK",
        "score_impact": 30,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "ESC-005": {
        "rule_id": "ESC-005",
        "legal_domain": "Corporate",
        "law": "Section 199, Companies Act 1994 (Bangladesh)",
        "requirement": "Investigation Order Pending - Investigation order pending under Section 199.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "RED",
        "score_impact": 20,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "FX-001": {
        "rule_id": "FX-001",
        "legal_domain": "Corporate",
        "law": "Foreign Exchange Regulation Act 1947 (Bangladesh)",
        "requirement": "Foreign Exchange Violation - Foreign exchange violation detected under FE Regulation Act 1947.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "RED",
        "score_impact": 15,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "LBR-001": {
        "rule_id": "LBR-001",
        "legal_domain": "Labour",
        "law": "Labour Act 2006 (Bangladesh), Section 35",
        "requirement": "Factory License Missing - Factory license not obtained. Mandatory for manufacturing entities.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "RED",
        "score_impact": 10,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "LBR-002": {
        "rule_id": "LBR-002",
        "legal_domain": "Labour",
        "law": "Labour Act 2006 (Bangladesh), Section 35",
        "requirement": "Factory License Expired - Factory license expired. Renewal required.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "YELLOW",
        "score_impact": 5,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "LBR-003": {
        "rule_id": "LBR-003",
        "legal_domain": "Labour",
        "law": "Labour Act 2006 (Bangladesh), Section 209",
        "requirement": "Labour Court Order Pending - Labour court order pending against the company.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "RED",
        "score_impact": 15,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "STR-001": {
        "rule_id": "STR-001",
        "legal_domain": "Corporate",
        "law": "Section 11, Companies Act 1994 (Bangladesh)",
        "requirement": "Name Change Not Filed - Name change special resolution not filed with RJSC within the statutory period.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "YELLOW",
        "score_impact": 3,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "STR-002": {
        "rule_id": "STR-002",
        "legal_domain": "Corporate",
        "law": "Sections 12, 15-16 and 88(1), Companies Act 1994 (Bangladesh)",
        "requirement": "Object Clause Change Not Filed - MoA object clause change not filed with RJSC.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "YELLOW",
        "score_impact": 3,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "STR-003": {
        "rule_id": "STR-003",
        "legal_domain": "Corporate",
        "law": "Sections 20 and 88(1), Companies Act 1994 (Bangladesh)",
        "requirement": "AoA Alteration Not Filed - Articles of Association alteration not filed with RJSC.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "YELLOW",
        "score_impact": 3,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "TAX-003": {
        "rule_id": "TAX-003",
        "legal_domain": "Tax",
        "law": "Income Tax Act 2023, Sections 166 and 171; Tax Day under Section 2 must be taxpayer-specific",
        "requirement": "Annual Tax Return Overdue - Annual income tax return overdue. ITA 2023 Section 75.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "YELLOW",
        "score_impact": 5,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "TAX-004": {
        "rule_id": "TAX-004",
        "legal_domain": "Tax",
        "law": "Income Tax Act 2023, Sections 154-157, including Section 155 instalment dates",
        "requirement": "Advance Tax Missed - One or more advance tax quarterly instalments missed. ITA 2023 Section 74.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "YELLOW",
        "score_impact": 3,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "TL-001": {
        "rule_id": "TL-001",
        "legal_domain": "Corporate",
        "law": "City Corporation Ordinance 1983 / Pourashava Act 2009",
        "requirement": "Trade License Not Obtained - Trade License not obtained from City Corporation/Municipality.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "YELLOW",
        "score_impact": 5,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "TL-002": {
        "rule_id": "TL-002",
        "legal_domain": "Corporate",
        "law": "City Corporation Ordinance 1983 / Pourashava Act 2009",
        "requirement": "Trade License Expired - Trade License expired. Must renew by 31 March annually.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "YELLOW",
        "score_impact": 5,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "VAT-002": {
        "rule_id": "VAT-002",
        "legal_domain": "Tax",
        "law": "Value Added Tax Act 2012 (Bangladesh)",
        "requirement": "Monthly VAT Return Overdue - Monthly/Bi-monthly VAT return overdue.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "YELLOW",
        "score_impact": 8,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "VAT-003": {
        "rule_id": "VAT-003",
        "legal_domain": "Tax",
        "law": "Value Added Tax Act 2012 (Bangladesh)",
        "requirement": "VAT Annual Return Overdue - VAT Annual Return overdue for current financial year.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN],
        "severity": "YELLOW",
        "score_impact": 5,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },

    "BOD-001": {"rule_id": "BOD-001", "legal_domain": "Corporate", "law": "Section 96, Companies Act 1994 (Bangladesh)", "requirement": "Board meeting not held within 3 months. Section 96: minimum 4 board meetings per year.", "provision": "TBD", "provision_status": ProvisionStatus.RECONCILE, "applicability": "ALL_ACTIVE_COMPANIES", "exceptions": [], "evidence_required": ["DOCUMENTARY_EVIDENCE"], "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN], "severity": "YELLOW", "score_impact": 5, "invariants": ["R-007", "R-008", "R-014", "R-019"]},
    "BOD-002": {"rule_id": "BOD-002", "legal_domain": "Corporate", "law": "Section 95, Companies Act 1994 (Bangladesh)", "requirement": "Board meeting notice not given to all directors. Section 95 requires written notice.", "provision": "TBD", "provision_status": ProvisionStatus.RECONCILE, "applicability": "ALL_ACTIVE_COMPANIES", "exceptions": [], "evidence_required": ["DOCUMENTARY_EVIDENCE"], "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN], "severity": "YELLOW", "score_impact": 3, "invariants": ["R-007", "R-008", "R-014", "R-019"]},
    "BOD-003": {"rule_id": "BOD-003", "legal_domain": "Corporate", "law": "Section 89, Companies Act 1994 (Bangladesh)", "requirement": "Board meeting minutes not prepared. Section 89: minutes of all proceedings must be entered.", "provision": "TBD", "provision_status": ProvisionStatus.RECONCILE, "applicability": "ALL_ACTIVE_COMPANIES", "exceptions": [], "evidence_required": ["DOCUMENTARY_EVIDENCE"], "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN], "severity": "YELLOW", "score_impact": 5, "invariants": ["R-007", "R-008", "R-014", "R-019"]},
    "ACC-001": {"rule_id": "ACC-001", "legal_domain": "Corporate", "law": "Section 183, Companies Act 1994 (Bangladesh)", "requirement": "AGM held but balance sheet and P&L not presented. Section 183.", "provision": "TBD", "provision_status": ProvisionStatus.RECONCILE, "applicability": "ALL_ACTIVE_COMPANIES", "exceptions": [], "evidence_required": ["DOCUMENTARY_EVIDENCE"], "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN], "severity": "RED", "score_impact": 15, "invariants": ["R-007", "R-008", "R-014", "R-019"]},
    "ACC-002": {"rule_id": "ACC-002", "legal_domain": "Corporate", "law": "Section 190, Companies Act 1994 (Bangladesh)", "requirement": "Balance sheet not filed within 30 days of AGM. Section 190.", "provision": "TBD", "provision_status": ProvisionStatus.RECONCILE, "applicability": "ALL_ACTIVE_COMPANIES", "exceptions": [], "evidence_required": ["DOCUMENTARY_EVIDENCE"], "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN], "severity": "RED", "score_impact": 15, "invariants": ["R-007", "R-008", "R-014", "R-019"]},
    "ACC-003": {"rule_id": "ACC-003", "legal_domain": "Corporate", "law": "Section 181, Companies Act 1994 (Bangladesh)", "requirement": "Proper books of account not maintained. Section 181.", "provision": "TBD", "provision_status": ProvisionStatus.RECONCILE, "applicability": "ALL_ACTIVE_COMPANIES", "exceptions": [], "evidence_required": ["DOCUMENTARY_EVIDENCE"], "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN], "severity": "RED", "score_impact": 15, "invariants": ["R-007", "R-008", "R-014", "R-019"]},
    "DIR-007": {"rule_id": "DIR-007", "legal_domain": "Corporate", "law": "Section 92, Companies Act 1994 (Bangladesh)", "requirement": "Director consent to act filed using Form IX within 30 days of appointment under Section 92; distinguish this from Form XII particulars under Section 115.", "provision": "TBD", "provision_status": ProvisionStatus.RECONCILE, "applicability": "ALL_ACTIVE_COMPANIES", "exceptions": [], "evidence_required": ["DOCUMENTARY_EVIDENCE"], "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN], "severity": "YELLOW", "score_impact": 5, "invariants": ["R-007", "R-008", "R-014", "R-019"]},
    "DIR-008": {"rule_id": "DIR-008", "legal_domain": "Corporate", "law": "Section 104, Companies Act 1994 (Bangladesh)", "requirement": "Director holding office of profit without consent. Section 104.", "provision": "TBD", "provision_status": ProvisionStatus.RECONCILE, "applicability": "ALL_ACTIVE_COMPANIES", "exceptions": [], "evidence_required": ["DOCUMENTARY_EVIDENCE"], "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN], "severity": "YELLOW", "score_impact": 8, "invariants": ["R-007", "R-008", "R-014", "R-019"]},
    "DIR-010": {"rule_id": "DIR-010", "legal_domain": "Corporate", "law": "Section 110, Companies Act 1994 (Bangladesh)", "requirement": "MD term exceeds 5 years. Section 110: max 5 years at a time.", "provision": "TBD", "provision_status": ProvisionStatus.RECONCILE, "applicability": "ALL_ACTIVE_COMPANIES", "exceptions": [], "evidence_required": ["DOCUMENTARY_EVIDENCE"], "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN], "severity": "YELLOW", "score_impact": 5, "invariants": ["R-007", "R-008", "R-014", "R-019"]},
    "MEM-001": {"rule_id": "MEM-001", "legal_domain": "Corporate", "law": "Section 222, Companies Act 1994 (Bangladesh)", "requirement": "Company below minimum members. Section 222: private < 2, public < 7.", "provision": "TBD", "provision_status": ProvisionStatus.RECONCILE, "applicability": "ALL_ACTIVE_COMPANIES", "exceptions": [], "evidence_required": ["DOCUMENTARY_EVIDENCE"], "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN], "severity": "RED", "score_impact": 10, "invariants": ["R-007", "R-008", "R-014", "R-019"]},
    "INC-007": {"rule_id": "INC-007", "legal_domain": "Corporate", "law": "Section 150, Companies Act 1994 (Bangladesh)", "requirement": "Business commenced without Section 150 declaration.", "provision": "TBD", "provision_status": ProvisionStatus.RECONCILE, "applicability": "ALL_ACTIVE_COMPANIES", "exceptions": [], "evidence_required": ["DOCUMENTARY_EVIDENCE"], "evaluation_states": [RuleState.COMPLIANT, RuleState.NON_COMPLIANT, RuleState.UNKNOWN], "severity": "RED", "score_impact": 10, "invariants": ["R-007", "R-008", "R-014", "R-019"]},

}

_LEGACY_AUTHORITY = {"Corporate": "RJSC", "Tax": "NBR", "Labour": "LABOUR_DEPT"}  # UNVERIFIED default
_LEGACY_AUTHORITY_OVERRIDE: Dict[str, str] = {}   # rule_id -> authority; fill after review
_LEGACY_KEYS = frozenset({"rule_id", "legal_domain", "law", "requirement", "provision",
    "provision_status", "applicability", "exceptions", "evidence_required",
    "evaluation_states", "severity", "score_impact", "invariants"})


def _legacy_rule(key: str, d: Dict[str, Any]) -> StatutoryRule:
    extra = set(d) - _LEGACY_KEYS
    if extra:
        raise RuntimeError(f"{key}: unknown legacy keys {sorted(extra)}")
    if d["rule_id"] != key:
        raise RuntimeError(f"{key}: rule_id mismatch {d['rule_id']}")
    if d["applicability"] != "ALL_ACTIVE_COMPANIES" or d["exceptions"]:
        raise RuntimeError(f"{key}: narrowed applicability not representable")
    if list(d["evidence_required"]) != ["DOCUMENTARY_EVIDENCE"]:
        raise RuntimeError(f"{key}: unexpected legacy evidence keys")
    auth = _LEGACY_AUTHORITY_OVERRIDE.get(key) or _LEGACY_AUTHORITY[d["legal_domain"]]
    return StatutoryRule(
        key, d["legal_domain"], d["law"], d["requirement"], d["provision"],
        d["provision_status"], auth,
        (key + ":DOCUMENTARY_EVIDENCE",),   # per-rule key: shared key would couple all rules
        Severity(d["severity"]), d["score_impact"])


for _k, _d in _LEGACY_RULE_DICTS.items():
    if _k not in STATUTORY_RULE_REGISTRY:   # canonical wins on overlap
        STATUTORY_RULE_REGISTRY[_k] = _legacy_rule(_k, _d)

def as_dict(rule: StatutoryRule) -> dict:
    """Thin adapter for tests/callers that still expect dict-style access.
    Never mutates the frozen StatutoryRule.
    """
    return {
        "rule_id": rule.rule_id,
        "legal_domain": rule.legal_domain,
        "law": rule.law,
        "requirement": rule.requirement,
        "provision": rule.provision,
        "provision_status": rule.provision_status,
        "authority": rule.authority,
        "evidence_required": rule.evidence_required,
        "severity": rule.severity,
        "score_impact": rule.score_impact,
        "applies_if": rule.applies_if,
        "exceptions": rule.exceptions,
        "evaluation_states": rule.evaluation_states,
        "invariants": rule.invariants,
    }

