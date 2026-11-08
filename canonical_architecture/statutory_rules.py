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


_BASE_STATES = (RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT)
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
        "MoA/AoA Registration Status Requires Verification", "Section 23",
        ProvisionStatus.RECONCILE, "RJSC", ("MOA_FILED", "AOA_FILED"),
        Severity.NOT_EVALUATED, 0),
    StatutoryRule(
        "AR-001", "Corporate", "Companies Act 1994",
        "Statutory annual filing obligation (Schedule X)", "Section 36",
        ProvisionStatus.RECONCILE, "RJSC",
        ("MEMBER_SHARE_DATA", "AGM_INFORMATION", "FILING_EVIDENCE"),
        Severity.NOT_EVALUATED, 0, exceptions=("DORMANT_STRIKE_OFF",)),
    StatutoryRule(
        "TAX-001", "Tax", "Income Tax Act 2023",
        "Obtain Tax Identification Number (TIN)",
        "UNIDENTIFIED (NBR instrument to be located)",
        ProvisionStatus.RECONCILE, "NBR", ("TIN_CERTIFICATE",),
        Severity.NOT_EVALUATED, 0),
    StatutoryRule(
        "LBR-001", "Labour", "Labour Act 2006",
        "Factory license obtained", "Section 326",
        ProvisionStatus.RECONCILE, "LABOUR_DEPT", ("FACTORY_LICENSE",),
        Severity.NOT_EVALUATED, 0, applies_if="IS_MANUFACTURING",
        exceptions=("NON_FACTORY_OPERATIONS",)),
    StatutoryRule(
        "TL-001", "Local Authority", "Local authority trade licensing (instrument to be identified)",
        "Valid trade license from local authority", "UNIDENTIFIED",
        ProvisionStatus.RECONCILE, "CITY_CORPORATION", ("TRADE_LICENSE",),
        Severity.NOT_EVALUATED, 0),
    StatutoryRule(
        "DIR-005", "Corporate", "Companies Act 1994",
        "Maintain statutory register mapped to DIR-005 (mapping under review)",
        "Section 130", ProvisionStatus.RECONCILE, "INTERNAL",
        ("REGISTER_DIR_005",), Severity.NOT_EVALUATED, 0),
    StatutoryRule(
        "DIR-006", "Corporate", "Companies Act 1994",
        "Maintain statutory register mapped to DIR-006 (mapping under review)",
        "Section 130", ProvisionStatus.RECONCILE, "INTERNAL",
        ("REGISTER_DIR_006",), Severity.NOT_EVALUATED, 0),
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
        "requirement": "Section 23 governs registration of the memorandum and articles. NLC non-production is a data gap, not proof of non-registration or invalidity; require authenticated RJSC registry search, certified filed copies and amendment history.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
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
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "INC-004": {
        "rule_id": "INC-004",
        "legal_domain": "Corporate",
        "law": "Section 56, Companies Act 1994 (Bangladesh) — review required",
        "requirement": "Paid-up capital exceeds recorded authorised capital. Treat as a legal/data discrepancy requiring verification of resolutions, Form IV, the register and RJSC record; do not automatically conclude excess allotments are void.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "INC-005": {
        "rule_id": "INC-005",
        "legal_domain": "Corporate",
        "law": "GFET-2018 Vol.1, Chapter 9, paragraph 2(A); FE Circular No.10 (21 June 2023); FEID Circular No.01 (27 January 2025) and subsequent circulars",
        "requirement": "An AD-bank encashment-certificate record is not present for a foreign-shareholder case. This is an evidence-review prompt only; verify the applicable GFET instructions, current circulars, foreign-currency-account retention and zone exceptions. Absence of an upload is not proof of breach.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "FOREIGN_SHAREHOLDER_AND_RELEVANT_SHARE_ISSUANCE_OR_INWARD_REMITTANCE_CASES_ONLY",
        "exceptions": ["SPECIAL_ZONE_OR_EXPORT_PROCESSING_ZONE_REGIME_REQUIRES_CHECK", "FOREIGN_CURRENCY_ACCOUNT_RETENTION_OR_PERMITTED_NON_ENCASHMENT_ROUTE_REQUIRES_CHECK", "NO_CURRENT_SHARE_ISSUE_OR_NO_INWARD_REMITTANCE_REQUIRES_CHECK"],
        "evidence_required": ["SUBSCRIPTION_OR_ALLOTMENT_RECORD", "AD_BANK_ENCASHMENT_CERTIFICATE_OR_PERMITTED_FC_ACCOUNT_EVIDENCE", "REMITTANCE_IDENTITY_AND_BANK_PROVENANCE", "CURRENT_BANGLADESH_BANK_CIRCULAR_VERSION"],
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "INC-006": {
        "rule_id": "INC-006",
        "legal_domain": "Corporate",
        "law": "BIDA Guidelines for permission to establish foreign commercial offices and issue work permits in Bangladesh (2023); exact operative clause/version and current amendments require verification",
        "requirement": "A reported initial-establishment remittance below the USD 50,000 reference amount is a screening prompt only. Verify the operative BIDA guideline, applicant category, effective version, exceptions and bank evidence. Do not infer a statutory breach or automatic work-permit refusal.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "BIDA_REGISTERED_FOREIGN_INVESTMENT_ENTITY_APPLYING_FOR_WORK_PERMIT_ONLY",
        "exceptions": ["APPLICANT_CATEGORY_OUTSIDE_2023_GUIDELINE", "INITIAL_APPLICATION_VS_RENEWAL_SCOPE_REQUIRES_CHECK", "GUIDELINE_VERSION_OR_AMENDMENT_REQUIRES_CHECK", "OTHER_LAWFUL_PERMIT_OR_INVESTMENT_ROUTE_REQUIRES_CHECK"],
        "evidence_required": ["BIDA_APPLICATION_AND_APPLICANT_CATEGORY", "CURRENT_WORK_PERMIT_GUIDELINE", "AD_BANK_REMITTANCE_AND_FX_CERTIFICATE", "DATE_AND_SOURCE_OF_INITIAL_ESTABLISHMENT_COST"],
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "AUD-001": {
        "rule_id": "AUD-001",
        "legal_domain": "Corporate",
        "law": "Section 210(6), Companies Act 1994 (Bangladesh)",
        "requirement": "First auditor not appointed by the Board within one calendar month of registration. Distinguish the Board's first-auditor appointment duty under Section 210(6) from the auditor's separate notice to the Registrar under Section 210(2).",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
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
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
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
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
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
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
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
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
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
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
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
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
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
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
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
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
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
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
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
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "AR-002": {
        "rule_id": "AR-002",
        "legal_domain": "Corporate",
        "law": "Section 36 and Schedule X, Companies Act 1994 (Bangladesh); Section 346 governs a separate Registrar strike-off process",
        "requirement": "Two or more reported outstanding annual returns are an internal review signal only. Backlog alone does not establish Registrar strike-off, dissolution, director liability or a mandatory rescue outcome.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "AR-003": {
        "rule_id": "AR-003",
        "legal_domain": "Corporate",
        "law": "Section 36 and Schedule X, Companies Act 1994 (Bangladesh); Section 346 governs a separate Registrar strike-off process",
        "requirement": "Three or more reported outstanding annual returns remain an internal review signal only. A backlog does not prove that RJSC has commenced Section 346 proceedings, that the company is dissolved, or that directors have incurred a separate penalty.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
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
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
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
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
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
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "DIR-003": {
        "rule_id": "DIR-003",
        "legal_domain": "Corporate",
        "law": "Section 115, Companies Act 1994 (Bangladesh)",
        "requirement": "Form XII particulars are due within 14 days under section 115(2). Any 365-day escalation is NLC internal policy only, not a separate continuing offence or daily penalty; distinguish filing default from appointment/cessation validity.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
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
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "SH-001": {
        "rule_id": "SH-001",
        "legal_domain": "Corporate",
        "law": "Section 151, Companies Act 1994 (Bangladesh)",
        "requirement": "Share Allotment Not Filed — Form XV - Share allotment return and prescribed supporting documents not filed within 60 days after allotment under Section 151, subject to a Registrar extension under the section.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "SH-002": {
        "rule_id": "SH-002",
        "legal_domain": "Corporate",
        "law": "Section 158, Companies Act 1994 (Bangladesh)",
        "requirement": "Share certificates not made ready for delivery within 90 days after allotment or, for a transfer, within 90 days after registration of the transfer, under Section 158. Check the applicable issue terms and trigger event.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "SH-003": {
        "rule_id": "SH-003",
        "legal_domain": "Corporate",
        "law": "Section 56, Companies Act 1994 (Bangladesh)",
        "requirement": "Capital Increase Not Filed — Form IV - Form IV notice of increase of share capital not filed within 15 days under Section 56, subject to verification of the exact triggering event, company scope and any applicable extension.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "TR-001": {
        "rule_id": "TR-001",
        "legal_domain": "Corporate",
        "law": "Section 38(3), Companies Act 1994 (Bangladesh)",
        "requirement": "Section 38(3) requires a proper transfer instrument duly stamped and executed by transferor and transferee, together with the relevant share/debenture certificate, subject to the statutory lost-instrument/indemnity exception. A missing upload is not proof of absence or automatic invalidity.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "TR-002": {
        "rule_id": "TR-002",
        "legal_domain": "Corporate",
        "law": "Stamp Act 1899 (Bangladesh), Schedule I, Item 62",
        "requirement": "Verify the instrument category, execution facts, current Stamp Act 1899 Schedule I rate, amendments, exemption/adjudication and authenticated payment evidence. Do not infer inadmissibility, invalidity or unenforceable title from a missing receipt.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "TR-003": {
        "rule_id": "TR-003",
        "legal_domain": "Corporate",
        "law": "Section 38(7), Companies Act 1994 (Bangladesh); Articles of Association",
        "requirement": "Board approval is not a universal statutory requirement. Section 38(7) preserves the company's power under its Articles to refuse registration; verify the operative restriction, notice, refusal and remedy. Do not declare a transfer void or title absent automatically.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "TR-004": {
        "rule_id": "TR-004",
        "legal_domain": "Corporate",
        "law": "Section 38(4), Companies Act 1994 (Bangladesh)",
        "requirement": "Where the company refuses registration of a share/debenture transfer, it must send notice of refusal to both transferor and transferee within 30 days after the instrument is lodged. This is not a universal two-month register-update deadline; verify the actual refusal and dispatch evidence.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "TR-005": {
        "rule_id": "TR-005",
        "legal_domain": "Corporate",
        "law": "Section 38(7), Companies Act 1994 (Bangladesh); Articles of Association",
        "requirement": "Reported registration despite an Articles restriction requires case-specific review under section 38(7), the Articles, notices, registration record and remedies. The section preserves a power to refuse registration; it does not automatically make every restricted transfer void ab initio.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "TR-006": {
        "rule_id": "TR-006",
        "legal_domain": "Corporate",
        "law": "Sections 34 and 38, Companies Act 1994 (Bangladesh), and applicable Articles",
        "requirement": "Two or more transfer-record review signals require document and Articles reconciliation. The composite is an internal review prompt, not a statutory breach, invalidity or title finding.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
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
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
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
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
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
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
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
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "CAP-001": {
        "rule_id": "CAP-001",
        "legal_domain": "Corporate",
        "law": "Sections 53, 54 and 56, Companies Act 1994 (Bangladesh)",
        "requirement": "Verify the specific capital alteration type and Articles authority under section 53. Section 54 addresses specified consolidation/conversion/subdivision notices; increase of registered share capital is separately governed by section 56. Do not assume a special resolution without checking the Act and Articles.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "CAP-002": {
        "rule_id": "CAP-002",
        "legal_domain": "Corporate",
        "law": "Section 159, Companies Act 1994 (Bangladesh)",
        "requirement": "Charge creation must be registered within 21 days using Form XVIII under Section 159. Verify that the instrument is registrable, the creation date and RJSC registration evidence before concluding default.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "CAP-003": {
        "rule_id": "CAP-003",
        "legal_domain": "Corporate",
        "law": "Sections 59-60, Companies Act 1994 (Bangladesh)",
        "requirement": "Capital reduction requires compliance with Sections 59-60, including court confirmation and registration. Assess the court order, creditor protection and registration evidence; do not infer a breach from a pending workflow flag alone.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "CAPITAL_REDUCTION_PROCEDURE_TRIGGERED_ONLY",
        "exceptions": ["NO_PROPOSED_OR_COMPLETED_CAPITAL_REDUCTION", "COMPANY_TYPE_AND_ARTICLES_AUTHORITY_REQUIRE_COUNSEL_REVIEW"],
        "evidence_required": ["SPECIAL_RESOLUTION", "COURT_APPLICATION_AND_ORDER", "CREDITOR_NOTICE_AND_OBJECTION_RECORD", "REGISTRAR_REGISTRATION_EVIDENCE"],
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "CAP-004": {
        "rule_id": "CAP-004",
        "legal_domain": "Corporate",
        "law": "Section 88(1), Companies Act 1994 (Bangladesh)",
        "requirement": "A copy of every special and extraordinary resolution must be filed with the Registrar within 15 days under Section 88(1). This filing requirement does not itself establish that the underlying transaction is complete or valid; assess any additional statutory steps.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
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
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "TAX-002": {
        "rule_id": "TAX-002",
        "legal_domain": "Tax",
        "law": "Value Added Tax and Supplementary Duty Act 2012, sections 2(48), 2(57), 4 and 10, as amended by Act No. 77 of 2026 and Finance Act No. 96 of 2026",
        "requirement": "Review prompt only. The current statutory thresholds are BDT 30 lakh for turnover-tax enlistment and BDT 50 lakh for VAT registration, measured against the statutory 12-month turnover rules and exclusions. Section 4(2) mandatory-registration categories may apply irrespective of threshold. Section 10, as substituted by Finance Act No. 96 of 2026, provides the current enlistment application process and 30-day period. Reported annual turnover alone does not establish taxable turnover, a statutory trigger, failure to enlist/register, or a breach. Do not score or classify a breach without current taxpayer-specific legal and documentary review.",
        "provision": "Sections 2(48), 2(57), 4 and 10",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "CONDITIONAL — taxpayer activity, statutory exclusions and mandatory-registration categories",
        "exceptions": ["Exempt supplies", "Sale of capital assets", "Other statutory exclusions", "Mandatory registration categories under section 4(2) require separate analysis"],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "ESC-001": {
        "rule_id": "ESC-001",
        "legal_domain": "Corporate",
        "law": "Section 346, Companies Act 1994 (Bangladesh); Registrar process and case-specific evidence required",
        "requirement": "Multi-year filing backlog is an internal escalation indicator, not proof that RJSC commenced strike-off. Verify statutory grounds, notice, service, stage, appeal, restoration and current status.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "ESC-002": {
        "rule_id": "ESC-002",
        "legal_domain": "Corporate",
        "law": "Section 346, Companies Act 1994 (Bangladesh)",
        "requirement": "Review-only status. Section 346 requires Registrar grounds and a statutory notice sequence, including the first inquiry, registered follow-up, Gazette notice and the 90-day show-cause period. A filing backlog or unverified list indicator is not proof of strike-off, dissolution or automatic restoration consequences.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
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
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "AGM-007": {
        "rule_id": "AGM-007",
        "legal_domain": "Corporate",
        "law": "Companies Act 1994, Section 85 and the company Articles; exact adjournment provision requires counsel verification",
        "requirement": "Adjourned-AGM notice issue requires review of Articles, resolution, adjournment terms, notice method and statutory consequence.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
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
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "BNK-001": {
        "rule_id": "BNK-001",
        "legal_domain": "Corporate",
        "law": "Companies Act 1994 (Bangladesh), Part V, sections 241–244",
        "requirement": "Reported company winding-up petition; verify Companies Act grounds, petition provision, court, case number, service, current status and authenticated court record. Do not conflate corporate winding-up with personal bankruptcy.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "BNK-002": {
        "rule_id": "BNK-002",
        "legal_domain": "Corporate",
        "law": "Companies Act 1994 (Bangladesh), Part V; section 255 for court-appointed Official Liquidators; route-specific provision requires review",
        "requirement": "Reported liquidator appointment; distinguish court winding-up, voluntary winding-up and other statutory routes; verify the appointment instrument, appointee authority and current status.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "BNK-003": {
        "rule_id": "BNK-003",
        "legal_domain": "Corporate",
        "law": "Companies Act 1994 (Bangladesh), Part V, sections 241–246",
        "requirement": "Reported court winding-up order; verify authenticated order, operative date, jurisdiction, appeal/stay, suspension/discharge and current liquidation status.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
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
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
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
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
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
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
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
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "CHG-001": {
        "rule_id": "CHG-001",
        "legal_domain": "Corporate",
        "law": "Section 172(1), read with Section 159, Companies Act 1994 (Bangladesh)",
        "requirement": "Review-only unless the charge is proved to be registrable under s.159, satisfaction and its date are authenticated, and the RJSC filing status is independently evidenced. Section 172(1) requires notice of payment/satisfaction of a registrable charge within 21 days. A missing satisfaction date or unverified registry search is UNKNOWN, not proof of non-filing.",
        "provision": "Sections 159 and 172(1)",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "CONDITIONAL — only charges whose registration is required by section 159",
        "exceptions": ["Charges not registrable under section 159"],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
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
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
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
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "DIR-005": {
        "rule_id": "DIR-005",
        "legal_domain": "Corporate",
        "law": "Companies Act 1994, Section 130 (director-interest disclosure); generic register duty/title requires legal reconciliation",
        "requirement": "The profile reports no director-interest register. Section 130 concerns disclosure of interests in company contracts/arrangements; it does not by itself establish this generic register duty.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "DIR-006": {
        "rule_id": "DIR-006",
        "legal_domain": "Corporate",
        "law": "Companies Act 1994 and applicable Articles; exact register-of-contracts provision not established",
        "requirement": "The profile reports no register of contracts. Exact statutory/Articles obligation, contract category and evidence require counsel verification.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "ESC-004": {
        "rule_id": "ESC-004",
        "legal_domain": "Corporate",
        "law": "Section 286, Companies Act 1994 (Bangladesh)",
        "requirement": "Reported voluntary winding-up resolution; verify statutory ground, resolution, solvency declaration where applicable, liquidator appointment, creditor process and current status under Part V.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "ESC-005": {
        "rule_id": "ESC-005",
        "legal_domain": "Corporate",
        "law": "Sections 195 and 197; section 199 where related entities are included, Companies Act 1994 (Bangladesh)",
        "requirement": "Reported company investigation; verify Government inspector appointment under section 195 or 197, the scope of any section 199 related-entity investigation, authenticated order, parties and current status. An inquiry is not itself a finding of liability.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
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
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
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
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
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
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
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
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
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
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
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
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
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
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "TAX-003": {
        "rule_id": "TAX-003",
        "legal_domain": "Tax",
        "law": "Income Tax Act 2023, Sections 166 and 171; Tax Day under Section 2 must be taxpayer-specific",
        "requirement": "Company return deadline must be derived from current Section 171 and the taxpayer-specific Tax Day definition in Section 2, including applicable amendments, exclusions and extensions.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "TAX-004": {
        "rule_id": "TAX-004",
        "legal_domain": "Tax",
        "law": "Income Tax Act 2023, Sections 154-157, including Section 155 instalment dates",
        "requirement": "Advance tax liability and instalments must be evaluated under Sections 154-157, including Section 155 dates, public-holiday adjustment, new-assessee treatment and taxpayer-specific eligibility.",
        "provision": "TBD",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
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
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
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
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
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
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
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
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },

    "BOD-001": {"rule_id": "BOD-001", "legal_domain": "Corporate", "law": "Section 96, Companies Act 1994 (Bangladesh)", "requirement": "Section 96 requires at least one Board meeting every three months and at least four meetings per year; full verified meeting history is required before evaluation.", "provision": "TBD", "provision_status": ProvisionStatus.RECONCILE, "applicability": "ALL_ACTIVE_COMPANIES", "exceptions": [], "evidence_required": ["DOCUMENTARY_EVIDENCE"], "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT], "severity": "NOT_EVALUATED", "score_impact": 0, "invariants": ["R-007", "R-008", "R-014", "R-019"]},
    "BOD-002": {"rule_id": "BOD-002", "legal_domain": "Corporate", "law": "Section 95, Companies Act 1994 (Bangladesh)", "requirement": "Written notice to each director then in Bangladesh; verify service, address, dispatch/receipt and applicable Articles before any breach finding.", "provision": "TBD", "provision_status": ProvisionStatus.RECONCILE, "applicability": "ALL_ACTIVE_COMPANIES", "exceptions": [], "evidence_required": ["DOCUMENTARY_EVIDENCE"], "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT], "severity": "NOT_EVALUATED", "score_impact": 0, "invariants": ["R-007", "R-008", "R-014", "R-019"]},
    "BOD-003": {"rule_id": "BOD-003", "legal_domain": "Corporate", "law": "Section 89, Companies Act 1994 (Bangladesh)", "requirement": "Minutes must be entered in the minute book; verify records, subsequent signature, custody and inspection. Missing upload alone is not proof of non-creation.", "provision": "TBD", "provision_status": ProvisionStatus.RECONCILE, "applicability": "ALL_ACTIVE_COMPANIES", "exceptions": [], "evidence_required": ["DOCUMENTARY_EVIDENCE"], "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT], "severity": "NOT_EVALUATED", "score_impact": 0, "invariants": ["R-007", "R-008", "R-014", "R-019"]},
    "ACC-001": {"rule_id": "ACC-001", "legal_domain": "Corporate", "law": "Section 183, Companies Act 1994 (Bangladesh)", "requirement": "AGM held but balance sheet and P&L not presented. Section 183.", "provision": "TBD", "provision_status": ProvisionStatus.RECONCILE, "applicability": "ALL_ACTIVE_COMPANIES", "exceptions": [], "evidence_required": ["DOCUMENTARY_EVIDENCE"], "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT], "severity": "NOT_EVALUATED", "score_impact": 0, "invariants": ["R-007", "R-008", "R-014", "R-019"]},
    "ACC-002": {"rule_id": "ACC-002", "legal_domain": "Corporate", "law": "Section 190, Companies Act 1994 (Bangladesh)", "requirement": "Balance sheet not filed within 30 days of AGM. Section 190.", "provision": "TBD", "provision_status": ProvisionStatus.RECONCILE, "applicability": "ALL_ACTIVE_COMPANIES", "exceptions": [], "evidence_required": ["DOCUMENTARY_EVIDENCE"], "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT], "severity": "NOT_EVALUATED", "score_impact": 0, "invariants": ["R-007", "R-008", "R-014", "R-019"]},
    "ACC-003": {"rule_id": "ACC-003", "legal_domain": "Corporate", "law": "Section 181, Companies Act 1994 (Bangladesh)", "requirement": "Proper books of account not maintained. Section 181.", "provision": "TBD", "provision_status": ProvisionStatus.RECONCILE, "applicability": "ALL_ACTIVE_COMPANIES", "exceptions": [], "evidence_required": ["DOCUMENTARY_EVIDENCE"], "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT], "severity": "NOT_EVALUATED", "score_impact": 0, "invariants": ["R-007", "R-008", "R-014", "R-019"]},
    "DIR-007": {"rule_id": "DIR-007", "legal_domain": "Corporate", "law": "Section 93(2), Companies Act 1994 (Bangladesh)", "requirement": "Written consent to act as director filed with the Registrar within 30 days of appointment under Section 93(2). Distinguish the separate pre-appointment consent/eligibility requirements in Section 92 and reconcile the Form IX mapping with the current RJSC form instructions before activation.", "provision": "TBD", "provision_status": ProvisionStatus.RECONCILE, "applicability": "ALL_ACTIVE_COMPANIES", "exceptions": [], "evidence_required": ["DOCUMENTARY_EVIDENCE"], "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT], "severity": "NOT_EVALUATED", "score_impact": 0, "invariants": ["R-007", "R-008", "R-014", "R-019"]},
    "DIR-008": {"rule_id": "DIR-008", "legal_domain": "Corporate", "law": "Section 104, Companies Act 1994 (Bangladesh)", "requirement": "Verify office category, statutory exclusions, company relationship and general-meeting consent before assessing an office-of-profit issue.", "provision": "TBD", "provision_status": ProvisionStatus.RECONCILE, "applicability": "ALL_ACTIVE_COMPANIES", "exceptions": [], "evidence_required": ["DOCUMENTARY_EVIDENCE"], "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT], "severity": "NOT_EVALUATED", "score_impact": 0, "invariants": ["R-007", "R-008", "R-014", "R-019"]},
    "DIR-010": {"rule_id": "DIR-010", "legal_domain": "Corporate", "law": "Section 110, Companies Act 1994 (Bangladesh)", "requirement": "Verify current managing-director appointment instrument, term, reappointment, approval and continuity before assessing the five-year-at-a-time limit.", "provision": "TBD", "provision_status": ProvisionStatus.RECONCILE, "applicability": "ALL_ACTIVE_COMPANIES", "exceptions": [], "evidence_required": ["DOCUMENTARY_EVIDENCE"], "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT], "severity": "NOT_EVALUATED", "score_impact": 0, "invariants": ["R-007", "R-008", "R-014", "R-019"]},
    "MEM-001": {"rule_id": "MEM-001", "legal_domain": "Corporate", "law": "Section 222, Companies Act 1994 (Bangladesh)", "requirement": "Company below minimum members. Section 222: private < 2, public < 7.", "provision": "TBD", "provision_status": ProvisionStatus.RECONCILE, "applicability": "ALL_ACTIVE_COMPANIES", "exceptions": [], "evidence_required": ["DOCUMENTARY_EVIDENCE"], "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT], "severity": "NOT_EVALUATED", "score_impact": 0, "invariants": ["R-007", "R-008", "R-014", "R-019"]},
    "INC-007": {"rule_id": "INC-007", "legal_domain": "Corporate", "law": "Section 150(1) and (6), Companies Act 1994 (Bangladesh)", "requirement": "Review only if the company is a public company that issued a prospectus inviting public subscription and all section 150(1) conditions are applicable and evidenced. Section 150(6) excludes private companies and companies not issuing such a prospectus.", "provision": "Section 150(1), (6)", "provision_status": ProvisionStatus.RECONCILE, "applicability": "PUBLIC_COMPANY_WITH_PROSPECTUS_ONLY; verify every statutory condition", "exceptions": ["Private company", "Public company not issuing a prospectus inviting public subscription", "Other statutory exclusions or valid Registrar evidence"], "evidence_required": ["DOCUMENTARY_EVIDENCE"], "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT], "severity": "NOT_EVALUATED", "score_impact": 0, "invariants": ["R-007", "R-008", "R-014", "R-019"]},

}

_LEGACY_AUTHORITY = {"Corporate": "RJSC", "Tax": "NBR", "Labour": "LABOUR_DEPT"}  # UNVERIFIED default
_LEGACY_AUTHORITY_OVERRIDE: Dict[str, str] = {}   # rule_id -> authority; fill after review
_LEGACY_KEYS = frozenset({"rule_id", "legal_domain", "law", "requirement", "provision",
    "provision_status", "applicability", "exceptions", "evidence_required",
    "evaluation_states", "severity", "score_impact", "invariants"})


def _legacy_rule(key: str, d: Dict[str, Any]) -> Optional[StatutoryRule]:
    extra = set(d) - _LEGACY_KEYS
    if extra:
        raise RuntimeError(f"{key}: unknown legacy keys {sorted(extra)}")
    if d["rule_id"] != key:
        raise RuntimeError(f"{key}: rule_id mismatch {d['rule_id']}")
    applicability = d["applicability"]
    if not isinstance(applicability, str) or not applicability.strip():
        raise RuntimeError(f"{key}: applicability must be a non-empty string")
    exceptions = d["exceptions"]
    if not isinstance(exceptions, (list, tuple)) or any(
        not isinstance(item, str) or not item.strip() for item in exceptions
    ):
        raise RuntimeError(f"{key}: exceptions must be non-empty strings")
    evidence_required = d["evidence_required"]
    if (
        not isinstance(evidence_required, (list, tuple))
        or not evidence_required
        or any(not isinstance(item, str) or not item.strip() for item in evidence_required)
        or len(set(evidence_required)) != len(evidence_required)
    ):
        raise RuntimeError(
            f"{key}: evidence_required must contain unique, non-empty strings"
        )
    if list(d["evidence_required"]) != ["DOCUMENTARY_EVIDENCE"]:
        return None
    auth = _LEGACY_AUTHORITY_OVERRIDE.get(key) or _LEGACY_AUTHORITY[d["legal_domain"]]
    applies_if = None if applicability == "ALL_ACTIVE_COMPANIES" else applicability
    return StatutoryRule(
        key, d["legal_domain"], d["law"], d["requirement"], d["provision"],
        d["provision_status"], auth,
        tuple(f"{key}:{item}" for item in evidence_required),
        Severity(d["severity"]), d["score_impact"],
        applies_if=applies_if,
        exceptions=tuple(exceptions),
    )


for _k, _d in _LEGACY_RULE_DICTS.items():
    if _k not in STATUTORY_RULE_REGISTRY:   # canonical wins on overlap
        _r = _legacy_rule(_k, _d)
        if _r is not None:
            STATUTORY_RULE_REGISTRY[_k] = _r

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

