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
        "INC-001", "Corporate", "Section 23, Companies Act 1994 (Bangladesh)",
        "MoA/AoA registration is governed by section 23. Non-production in NLC records is not proof of non-registration or invalidity; verify the RJSC registration record, certified copies, incorporation date and amendments.", "UNVERIFIED CANDIDATE — Section 23, Companies Act 1994 (Bangladesh)",
        ProvisionStatus.RECONCILE, "RJSC", ("MOA_FILED", "AOA_FILED"),
        Severity.NOT_EVALUATED, 0),
    StatutoryRule(
        "AR-001", "Corporate", "Section 36 (Schedule X), Companies Act 1994 (Bangladesh)",
        "Schedule X (Annual Return) not filed within 21 days of AGM. Section 36 requires the annual summary of share capital and list of members/directors within 21 days. Every officer in default is personally liable to fine for each day of continuing default.", "UNVERIFIED CANDIDATE — Section 36 (Schedule X), Companies Act 1994 (Bangladesh)",
        ProvisionStatus.RECONCILE, "RJSC",
        ("MEMBER_SHARE_DATA", "AGM_INFORMATION", "FILING_EVIDENCE"),
        Severity.NOT_EVALUATED, 0, exceptions=("DORMANT_STRIKE_OFF",)),
    StatutoryRule(
        "TAX-001", "Tax", "Income Tax Act 2023, sections 166, 261 and 264; company-specific duty and evidence require verification",
        "Review prompt only: verify legal entity and taxpayer identity, return-filing duty under section 166, registration under section 261 and any proof-of-return requirement under section 264. A profile boolean is not authenticated evidence of a breach.",
        "UNVERIFIED CANDIDATE — Income Tax Act 2023, sections 166, 261 and 264; company-specific duty and evidence require verification",
        ProvisionStatus.RECONCILE, "NBR", ("TIN_CERTIFICATE",),
        Severity.NOT_EVALUATED, 0),
    StatutoryRule(
        "LBR-001", "Labour", "Bangladesh Labour Act 2006, Section 326, as amended by Act No. 43 of 2026",
        "Review prompt only: verify a Government direction under section 326, establishment class, effective date, exemptions and authentic licence status.", "UNVERIFIED CANDIDATE — Bangladesh Labour Act 2006, Section 326, as amended by Act No. 43 of 2026",
        ProvisionStatus.RECONCILE, "LABOUR_DEPT", ("FACTORY_LICENSE",),
        Severity.NOT_EVALUATED, 0, applies_if="IS_MANUFACTURING",
        exceptions=("NON_FACTORY_OPERATIONS",)),
    StatutoryRule(
        "TL-001", "Local Authority", "Local Government (City Corporation) Act 2009 / Local Government (Paurashava) Act 2009",
        "Trade License not obtained from City Corporation/Municipality.", "UNVERIFIED CANDIDATE — Local Government (City Corporation) Act 2009 / Local Government (Paurashava) Act 2009",
        ProvisionStatus.RECONCILE, "CITY_CORPORATION", ("TRADE_LICENSE",),
        Severity.NOT_EVALUATED, 0),
    StatutoryRule(
        "DIR-005", "Corporate", "Companies Act 1994, Section 130 (director-interest disclosure); generic register duty/title requires legal reconciliation",
        "Review prompt only: Section 130 concerns disclosure of a director's interest in a company contract or arrangement; it does not by itself establish this generic register obligation. Verify the actual duty, Articles and documentary evidence.",
        "UNVERIFIED CANDIDATE — Companies Act 1994, Section 130 (director-interest disclosure); generic register duty/title requires legal reconciliation", ProvisionStatus.RECONCILE, "INTERNAL",
        ("REGISTER_DIR_005",), Severity.NOT_EVALUATED, 0),
    StatutoryRule(
        "DIR-006", "Corporate", "Companies Act 1994 and applicable Articles; exact register obligation requires counsel verification",
        "Review prompt only: no universal register-of-contracts duty has been established for this generic rule. Verify the exact statutory provision, company Articles, contract category and evidence.",
        "UNVERIFIED CANDIDATE — Companies Act 1994 and applicable Articles; exact register obligation requires counsel verification", ProvisionStatus.RECONCILE, "INTERNAL",
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
        "requirement": "MoA/AoA registration is governed by section 23. Non-production in NLC records is not proof of non-registration or invalidity; verify the RJSC registration record, certified copies, incorporation date and amendments.",
        "provision": "UNVERIFIED CANDIDATE — Section 23, Companies Act 1994 (Bangladesh)",
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
        "requirement": "Minimum directors: three for a public company and a private subsidiary of a public company under Section 90(1); two for other private companies under Section 90(2). Require verified director count and verified company classification.",
        "provision": "UNVERIFIED CANDIDATE — Sections 90(1) and 90(2), Companies Act 1994 (Bangladesh)",
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
        "law": "Section 56, Companies Act 1994 (Bangladesh) — applicability and consequences require lawyer review",
        "requirement": "Paid-up capital exceeds recorded authorised capital. This is a data/legal review trigger; verify capital resolutions, Form IV and RJSC register. Do not automatically conclude excess allotments are void.",
        "provision": "UNVERIFIED CANDIDATE — Section 56, Companies Act 1994 (Bangladesh) — applicability and consequences require lawyer review",
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
        "law": "GFET-2018 Vol.1, Chapter 9, paragraph 2(A); FE Circular No.10 (21 June 2023); FEID Circular No.01 (27 January 2025) and subsequent applicable circulars",
        "requirement": "No AD-bank encashment-certificate record is present. This is an internal evidence-review signal only; it does not prove a breach. Verify the applicable GFET paragraph, current Bangladesh Bank circulars, foreign-currency-account retention rules and zone-specific exceptions. CONDITIONAL: foreign-shareholder cases only.",
        "provision": "UNVERIFIED CANDIDATE — GFET-2018 Vol.1, Chapter 9, paragraph 2(A); FE Circular No.10 (21 June 2023); FEID Circular No.01 (27 January 2025) and subsequent applicable circulars",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "has_foreign_shareholder == True",
        "exceptions": [],
        "evidence_required": [
            "INC-005:SUBSCRIPTION_OR_ALLOTMENT_RECORD",
            "INC-005:AD_BANK_ENCASHMENT_CERTIFICATE_OR_PERMITTED_FC_ACCOUNT_EVIDENCE",
            "INC-005:REMITTANCE_IDENTITY_AND_BANK_PROVENANCE",
            "INC-005:CURRENT_BANGLADESH_BANK_CIRCULAR_VERSION",
        ],
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "INC-006": {
        "rule_id": "INC-006",
        "legal_domain": "Corporate",
        "law": "BIDA Guidelines for permission to establish foreign commercial offices and issue work permits in Bangladesh (2023); exact operative clause/version and current amendments require verification",
        "requirement": "Reported initial-establishment remittance below the USD 50,000 reference amount is an internal screening prompt only. Verify the current BIDA guideline, applicant category, date, exceptions and supporting bank evidence. No statutory breach or work-permit refusal is inferred. CONDITIONAL: foreign-shareholder and BIDA-registered cases only.",
        "provision": "UNVERIFIED CANDIDATE — BIDA Guidelines for permission to establish foreign commercial offices and issue work permits in Bangladesh (2023); exact operative clause/version and current amendments require verification",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "AUD-001": {
        "rule_id": "AUD-001",
        "legal_domain": "Corporate",
        "law": "Section 210(6), Companies Act 1994 (Bangladesh)",
        "requirement": "First auditor not appointed by the Board within one calendar month of incorporation. Section 210(6): the Board shall appoint the first auditor within one month of the date of registration. 'One month' means a calendar month (not a fixed 30 days). Company cannot produce compliant accounts for the first AGM until an auditor is appointed.",
        "provision": "UNVERIFIED CANDIDATE — Section 210(6), Companies Act 1994 (Bangladesh)",
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
        "requirement": "Audit/accounts not ready for presentation at the AGM. Section 183 governs the balance sheet and profit-and-loss or income-and-expenditure account to be laid before the AGM. Do not describe this fact alone as automatically invalidating every resolution.",
        "provision": "UNVERIFIED CANDIDATE — Section 183, Companies Act 1994 (Bangladesh)",
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
        "requirement": "AGM recorded without completed audit. This requires review of the actual accounts, auditor appointment and applicable exceptions. It is not automatically a statutory BLACK classification or a finding of fraud.",
        "provision": "UNVERIFIED CANDIDATE — Sections 183 and 210, Companies Act 1994 (Bangladesh)",
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
        "requirement": "Auditor reappointment or appointment at the AGM must be assessed under Section 210(3), using verified AGM minutes and appointment records.",
        "provision": "UNVERIFIED CANDIDATE — Section 210(3), Companies Act 1994 (Bangladesh)",
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
        "requirement": "First AGM must be held within 18 calendar months of incorporation. Calculate with calendar-month arithmetic; do not use a fixed-day approximation.",
        "provision": "UNVERIFIED CANDIDATE — Section 81(1), Companies Act 1994 (Bangladesh)",
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
        "requirement": "A subsequent AGM must be held in each Gregorian calendar year and no more than 15 months after the preceding AGM, subject to the first-AGM proviso where the first AGM is held in the incorporation year and a verified Registrar extension within the statutory limit.",
        "provision": "UNVERIFIED CANDIDATE — Section 81(1), Companies Act 1994 (Bangladesh)",
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
        "requirement": "AGM notice was shorter than the statutory notice period. Shorter notice may be valid with written consent of all members entitled to attend and vote. Do not classify as defective unless absence of the required consent is verified.",
        "provision": "UNVERIFIED CANDIDATE — Section 85(1)(a), Companies Act 1994 (Bangladesh)",
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
        "provision": "UNVERIFIED CANDIDATE — Section 85(1)(a), Companies Act 1994 (Bangladesh)",
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
        "law": "Section 85(2)(b), Companies Act 1994 (Bangladesh), read with the Articles",
        "requirement": "AGM held but the applicable quorum was not met. Under the default in Section 85(2)(b), a private company with not more than six members requires two members present; a private company with more than six members requires three; other companies require five members personally present. The Articles may provide otherwise and must be checked before a final determination.",
        "provision": "UNVERIFIED CANDIDATE — Section 85(2)(b), Companies Act 1994 (Bangladesh), read with the Articles",
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
        "requirement": "Review prompt only: the record indicates minutes may be absent, but the minute book and contemporaneous records have not been independently verified.",
        "provision": "UNVERIFIED CANDIDATE — Section 89, Companies Act 1994 (Bangladesh)",
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
        "law": "Section 36 (Schedule X), Companies Act 1994 (Bangladesh)",
        "requirement": "Schedule X (Annual Return) not filed within 21 days of AGM. Section 36 requires the annual summary of share capital and list of members/directors within 21 days. Every officer in default is personally liable to fine for each day of continuing default.",
        "provision": "UNVERIFIED CANDIDATE — Section 36 (Schedule X), Companies Act 1994 (Bangladesh)",
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
        "law": "Section 36 and Schedule X (annual-return duty); Section 346 governs a separate Registrar strike-off procedure.",
        "requirement": "Two or more reported outstanding annual returns are an internal review signal only. Backlog alone does not establish Registrar strike-off, dissolution, director liability or mandatory rescue.",
        "provision": "UNVERIFIED CANDIDATE — Section 36 and Schedule X (annual-return duty); Section 346 governs a separate Registrar strike-off procedure.",
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
        "law": "Section 36 and Schedule X (annual-return duty); Section 346 requires separate Registrar grounds and statutory notice steps.",
        "requirement": "Three or more reported outstanding annual returns remain an internal review signal only. A backlog does not prove that RJSC has commenced Section 346 proceedings, that the company is dissolved, or that directors have incurred a separate penalty.",
        "provision": "UNVERIFIED CANDIDATE — Section 36 and Schedule X (annual-return duty); Section 346 requires separate Registrar grounds and statutory notice steps.",
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
        "law": "Section 36, Schedule X, Companies Act 1994 (Bangladesh)",
        "requirement": "Annual Return filed but missing required attachments: audited financial statements, directors list, members list, or secretary's certificate. Incomplete filing does not satisfy Section 36; company remains in default.",
        "provision": "UNVERIFIED CANDIDATE — Section 36, Schedule X, Companies Act 1994 (Bangladesh)",
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
        "law": "Section 115(2), Companies Act 1994 (Bangladesh)",
        "requirement": "Director appointment particulars not filed via Form XII within 14 days under Section 115. Filing default must be distinguished from whether the appointment itself is valid.",
        "provision": "UNVERIFIED CANDIDATE — Section 115(2), Companies Act 1994 (Bangladesh)",
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
        "law": "Section 115(2), Companies Act 1994 (Bangladesh)",
        "requirement": "Director cessation particulars not filed via Form XII within 14 days under Section 115. Filing default must be distinguished from the effective date and legal consequences of resignation, removal or death.",
        "provision": "UNVERIFIED CANDIDATE — Section 115(2), Companies Act 1994 (Bangladesh)",
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
        "law": "Section 115(2), Companies Act 1994 (Bangladesh); 365-day threshold is NLC policy only",
        "requirement": "A delay exceeding 365 days is an NLC internal escalation threshold only. The underlying Form XII particulars filing duty is under section 115(2) (14 days); do not infer a separate continuing offence, daily penalty, personal liability or invalid board resolutions without a distinct provision and case-specific evidence.",
        "provision": "UNVERIFIED CANDIDATE — Section 115(2), Companies Act 1994 (Bangladesh); 365-day threshold is NLC policy only",
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
        "requirement": "Late or missing Form XII cessation particulars require case-specific review of statutory filing default, actual cessation date and third-party reliance. Non-filing alone does not automatically establish continuing director liability.",
        "provision": "UNVERIFIED CANDIDATE — Section 115, Companies Act 1994 (Bangladesh)",
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
        "requirement": "Section 151 requires a company having share capital to file the return of allotment and prescribed supporting documents within 60 days after allotment, subject to any Registrar extension granted under the section.",
        "provision": "UNVERIFIED CANDIDATE — Section 151, Companies Act 1994 (Bangladesh)",
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
        "requirement": "Section 158 requires share certificates within 90 days after allotment or registration of transfer. This rule currently models allotment date only; transfer-registration events must be added before complete coverage can be claimed.",
        "provision": "UNVERIFIED CANDIDATE — Section 158, Companies Act 1994 (Bangladesh)",
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
        "requirement": "RJSC guidance identifies Form IV notice of increase of share capital under Section 56 as due within 15 days; confirm the exact statutory trigger, company scope and current form before assessing a default.",
        "provision": "UNVERIFIED CANDIDATE — Section 56, Companies Act 1994 (Bangladesh)",
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
        "provision": "UNVERIFIED CANDIDATE — Section 38(3), Companies Act 1994 (Bangladesh)",
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
        "law": "Stamp Act 1899, current Schedule I and applicable amendments",
        "requirement": "Verify the instrument category, execution facts, current Stamp Act 1899 Schedule I rate, amendments, exemption/adjudication and authenticated payment evidence. Do not infer inadmissibility, invalidity or unenforceable title from a missing receipt.",
        "provision": "UNVERIFIED CANDIDATE — Stamp Act 1899, current Schedule I and applicable amendments",
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
        "law": "Section 38(7), Companies Act 1994 (Bangladesh), and the company’s Articles",
        "requirement": "Section 38(7) preserves the company's power under its Articles to refuse registration. Board approval is not a universal statutory requirement; verify the operative Articles, transfer class, notices, refusal and remedies. Do not declare the transfer void or title absent automatically.",
        "provision": "UNVERIFIED CANDIDATE — Section 38(7), Companies Act 1994 (Bangladesh), and the company’s Articles",
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
        "requirement": "Section 38(4) concerns notice of refusal: where the company refuses registration, it must notify both transferor and transferee within 30 days after the instrument is lodged. This rule does not create a universal two-month register-update deadline; verify the actual refusal and dispatch evidence.",
        "provision": "UNVERIFIED CANDIDATE — Section 38(4), Companies Act 1994 (Bangladesh)",
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
        "law": "Section 38(7), Companies Act 1994 (Bangladesh), and the company’s Articles",
        "requirement": "Reported registration despite an Articles restriction requires case-specific review under section 38(7), the Articles, notices, registration record and remedies. The section preserves a power to refuse registration; it does not automatically make every restricted transfer void ab initio.",
        "provision": "UNVERIFIED CANDIDATE — Section 38(7), Companies Act 1994 (Bangladesh), and the company’s Articles",
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
        "provision": "UNVERIFIED CANDIDATE — Sections 34 and 38, Companies Act 1994 (Bangladesh), and applicable Articles",
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
        "law": "Section 34, Companies Act 1994 (Bangladesh)",
        "requirement": "One or more of 7 mandatory statutory registers not maintained at registered office. Required: Members (Sec 34), Directors (Sec 90), Charges (Sec 87), Transfers (Sec 108), Debentures (Sec 90), AGM Minutes (Sec 83), Board Minutes (Sec 90). Failure is criminal offence; officers personally liable.",
        "provision": "UNVERIFIED CANDIDATE — Section 34, Companies Act 1994 (Bangladesh)",
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
        "law": "Sections 34, 89, 115, 174, Companies Act 1994 (Bangladesh)",
        "requirement": "Core statutory records missing. Distinguishes (1) internal register-keeping obligations — Members (Sec 34), Meeting minutes (Sec 89), Charges register (Sec 174) — from (2) RJSC filing obligations such as director particulars (Sec 115). Each missing item is an independent legal obligation. Absence of internal registers is a governance failure; missing RJSC filings are separate filing defaults.",
        "provision": "UNVERIFIED CANDIDATE — Sections 34, 89, 115, 174, Companies Act 1994 (Bangladesh)",
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
        "requirement": "Statutory registers not at registered office. Section 34(2): registers must be at registered office unless RJSC notified of alternative location. Alternative must be in Bangladesh and Board-approved. Registers open to inspection during business hours.",
        "provision": "UNVERIFIED CANDIDATE — Section 34(2), Companies Act 1994 (Bangladesh)",
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
        "requirement": "Office change not filed via Form VI within 28 days. Section 77 requires 28-day filing (NOT 30 days). Until filed, old address remains legal registered office. Statutory notices served there are valid.",
        "provision": "UNVERIFIED CANDIDATE — Section 77, Companies Act 1994 (Bangladesh)",
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
        "requirement": "Verify the specific alteration type and Articles authority under section 53. Section 54 addresses specified consolidation/conversion/subdivision notices; increase of registered share capital is separately governed by section 56. Do not assume a special resolution without checking the Act and Articles.",
        "provision": "UNVERIFIED CANDIDATE — Sections 53, 54 and 56, Companies Act 1994 (Bangladesh)",
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
        "law": "Section 159(1), Companies Act 1994 (Bangladesh)",
        "requirement": "Review-only until the executed charge instrument, verified creation date, Section 159 registrability and RJSC Form XVIII filing status/date are evidenced. Missing evidence is UNKNOWN; a late filing requires legal review of any Registrar extension and its effect.",
        "provision": "UNVERIFIED CANDIDATE — Section 159(1), Companies Act 1994 (Bangladesh)",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["EXECUTED_CHARGE_INSTRUMENT", "CREATION_DATE", "SECTION_159_REGISTRABILITY", "RJSC_FORM_XVIII_FILING_STATUS", "FORM_XVIII_FILED_DATE", "REGISTRAR_EXTENSION_IF_ANY"],
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "CAP-003": {
        "rule_id": "CAP-003",
        "legal_domain": "Corporate",
        "law": "Sections 59-60, Companies Act 1994 (Bangladesh)",
        "requirement": "A pending capital-reduction workflow without verified court-confirmation evidence requires lawyer review. A pending workflow alone does not prove an unlawful completed reduction.",
        "provision": "UNVERIFIED CANDIDATE — Sections 59-60, Companies Act 1994 (Bangladesh)",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "CAP-004": {
        "rule_id": "CAP-004",
        "legal_domain": "Corporate",
        "law": "Section 88(1), Companies Act 1994 (Bangladesh) — 15 days",
        "requirement": "Copy of a special or extraordinary resolution must be filed with RJSC within 15 days under Section 88(1). This filing duty does not by itself determine whether every underlying transaction is valid or complete.",
        "provision": "UNVERIFIED CANDIDATE — Section 88(1), Companies Act 1994 (Bangladesh) — 15 days",
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
        "law": "Income Tax Act 2023, sections 166, 261 and 264; company-specific duty and evidence require verification",
        "requirement": "Review prompt only: verify legal entity and taxpayer identity, return-filing duty under section 166, registration under section 261 and any proof-of-return requirement under section 264. A profile boolean is not authenticated evidence of a breach.",
        "provision": "UNVERIFIED CANDIDATE — Income Tax Act 2023, sections 166, 261 and 264; company-specific duty and evidence require verification",
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
        "law": "Value Added Tax and Supplementary Duty Act 2012, sections 2(48), 2(57), 4 and 10, as amended by Act No. 77 of 2026 and Finance Act No. 96 of 2026; exact current section and taxpayer-specific instruments require counsel verification",
        "requirement": "Review prompt only. Verify rolling 12-month taxable turnover, mandatory-registration categories and taxpayer activity. Above BDT 30 lakh up to BDT 50 lakh may require turnover-tax enlistment; above BDT 50 lakh may require VAT registration. Verify the 30-day application period and effective date before any breach finding.",
        "provision": "UNVERIFIED CANDIDATE — Value Added Tax and Supplementary Duty Act 2012, sections 2(48), 2(57), 4 and 10, as amended by Act No. 77 of 2026 and Finance Act No. 96 of 2026; exact current section and taxpayer-specific instruments require counsel verification",
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
        "requirement": "Review prompt only: multi-year backlog is an internal escalation indicator, not proof that RJSC commenced strike-off. Verify statutory grounds, Registrar notice, service, procedural stage, appeal, restoration and current company status.",
        "provision": "UNVERIFIED CANDIDATE — Section 346, Companies Act 1994 (Bangladesh); Registrar process and case-specific evidence required",
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
        "law": "Section 346, Companies Act 1994 (Bangladesh); Registrar process and case-specific evidence required",
        "requirement": "Review prompt only: verify the statutory grounds, Registrar notice, service, procedural stage, appeal, restoration and current register status. A filing backlog or unverified list indicator is not proof that strike-off is imminent or has occurred.",
        "provision": "UNVERIFIED CANDIDATE — Section 346, Companies Act 1994 (Bangladesh); Registrar process and case-specific evidence required",
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
        "law": "NLC internal risk policy; not a statutory risk band under the Companies Act 1994.",
        "requirement": "Internal BLACK escalation and rescue workflow. A BLACK classification, score threshold and rescue deadline are NLC policy decisions, not statutory consequences. Policy-owner approval is required.",
        "provision": "UNVERIFIED CANDIDATE — NLC internal risk policy; not a statutory risk band under the Companies Act 1994.",
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
        "requirement": "Review prompt only: verify the applicable Articles, meeting resolution, adjournment terms, notice method and exact statutory consequence before classifying a breach.",
        "provision": "UNVERIFIED CANDIDATE — Companies Act 1994, Section 85 and the company Articles; exact adjournment provision requires counsel verification",
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
        "law": "Section 210(3), Companies Act 1994 (Bangladesh)",
        "requirement": "No verified record establishes whether the retiring auditor was reappointed or a statutory exception applied. Evidence-status only; no 120-day deadline.",
        "provision": "UNVERIFIED CANDIDATE — Section 210(3), Companies Act 1994 (Bangladesh)",
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
        "law": "Companies Act 1994 (Bangladesh), Part V, including sections 241–244; exact petition provision requires case review",
        "requirement": "Reported company winding-up petition. Verify the Companies Act petition, grounds, court, case number, service, current status, withdrawal/dismissal/stay and authenticated court record. Do not conflate corporate winding-up with personal bankruptcy.",
        "provision": "UNVERIFIED CANDIDATE — Companies Act 1994 (Bangladesh), Part V, including sections 241–244; exact petition provision requires case review",
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
        "law": "Companies Act 1994 (Bangladesh), Part V; section 255 applies to court-appointed Official Liquidators; route-specific provision requires review",
        "requirement": "Reported liquidator appointment. Verify whether the appointment arises from a court winding-up order, voluntary winding-up or another statutory route; obtain the appointment instrument and confirm the appointee’s authority and current status.",
        "provision": "UNVERIFIED CANDIDATE — Companies Act 1994 (Bangladesh), Part V; section 255 applies to court-appointed Official Liquidators; route-specific provision requires review",
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
        "law": "Companies Act 1994 (Bangladesh), Part V, including sections 241–246; exact order provision requires case review",
        "requirement": "Reported court winding-up order. Verify the authenticated order, operative date, court jurisdiction, appeal/stay, correction, suspension or discharge, and current liquidation status.",
        "provision": "UNVERIFIED CANDIDATE — Companies Act 1994 (Bangladesh), Part V, including sections 241–246; exact order provision requires case review",
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
        "law": "Applicable BSEC financial-reporting instrument; exact notification, issuer class, reporting period and due date require verification",
        "requirement": "Review prompt only: verify the exact BSEC financial-reporting instrument, listed issuer class, reporting period and due date; this is not Corporate Governance Code Condition 8.",
        "provision": "UNVERIFIED CANDIDATE — Applicable BSEC financial-reporting instrument; exact notification, issuer class, reporting period and due date require verification",
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
        "law": "BSEC Corporate Governance Code 2018, as amended by applicable 2023 and 2024 notifications; exact condition-specific applicability and evidence require verification",
        "requirement": "Review prompt only: Condition 9 requires annual corporate-governance compliance certification by a practicing professional accountant or secretary other than the statutory auditor, with disclosure in the annual report. Verify listed-issuer scope, certifier eligibility, AGM appointment and evidence.",
        "provision": "UNVERIFIED CANDIDATE — BSEC Corporate Governance Code 2018, as amended by applicable 2023 and 2024 notifications; exact condition-specific applicability and evidence require verification",
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
        "law": "BSEC Corporate Governance Code 2018, as amended by applicable 2023 and 2024 notifications; exact condition-specific applicability and evidence require verification",
        "requirement": "Review prompt only: verify Condition 1 board size, independent-director ratio, eligibility and appointment process. The 2024 amendment adds at least one female independent director; BSEC's 26 July 2026 register lists a further extension, reported to 31 December 2026. Verify the original notice and any later direction before applying a deadline.",
        "provision": "UNVERIFIED CANDIDATE — BSEC Corporate Governance Code 2018, as amended by applicable 2023 and 2024 notifications; exact condition-specific applicability and evidence require verification",
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
        "law": "BSEC Corporate Governance Code 2018, as amended by applicable 2023 and 2024 notifications; exact condition-specific applicability and evidence require verification",
        "requirement": "Review prompt only: verify Condition 5 audit committee composition, independent director, financial literacy, quorum, meetings, duties and listed-issuer scope. Do not infer non-compliance from a single profile boolean.",
        "provision": "UNVERIFIED CANDIDATE — BSEC Corporate Governance Code 2018, as amended by applicable 2023 and 2024 notifications; exact condition-specific applicability and evidence require verification",
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
        "requirement": "Review-only. Confirm that the charge is registrable under s.159, authenticate satisfaction and its date, and verify RJSC filing status/date before assessing the 21-day s.172(1) duty. Missing evidence is UNKNOWN; a late Form XXVIII filing requires review of any Registrar extension and its legal effect.",
        "provision": "UNVERIFIED CANDIDATE — Section 172(1), read with Section 159, Companies Act 1994 (Bangladesh)",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "CONDITIONAL — only charges whose registration is required by section 159",
        "exceptions": ["Charges not registrable under section 159"],
        "evidence_required": ["CHARGE_SATISFACTION_EVENT", "SATISFACTION_DATE", "SECTION_159_REGISTRABILITY", "RJSC_SATISFACTION_FILING_STATUS", "FORM_XXVIII_FILED_DATE", "REGISTRAR_EXTENSION_IF_ANY"],
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },
    "DEF-001": {
        "rule_id": "DEF-001",
        "legal_domain": "Corporate",
        "law": "Section 94(1)(d), Companies Act 1994 (Bangladesh)",
        "requirement": "Director disqualification requires a specified Section 94 or Articles ground, director identity, authoritative evidence, effective date and continuing status. Unpaid-call ground remains DISPUTED: official Bengali text says 180 days, while English/case materials say six months. Do not automatically classify until a Bangladesh company-law reviewer resolves the discrepancy. Section 94 does not prescribe a universal five-year ban. This finding is not an automatic BLACK override and remains outside production scoring pending independent legal approval.",
        "provision": "UNVERIFIED CANDIDATE — Section 94(1)(d), Companies Act 1994 (Bangladesh)",
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
        "law": "Case-specific enabling provision required; not a universal section",
        "requirement": "Review prompt only: each penalty/prosecution notice must be matched to its enabling provision, issuing authority, service, response deadline, appeal/stay and current disposition. No universal Companies Act penalty provision is assumed.",
        "provision": "UNVERIFIED CANDIDATE — Case-specific enabling provision required; not a universal section",
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
        "requirement": "Review prompt only: Section 130 concerns disclosure of a director's interest in a company contract or arrangement; it does not by itself establish this generic register obligation. Verify the actual duty, Articles and documentary evidence.",
        "provision": "UNVERIFIED CANDIDATE — Companies Act 1994, Section 130 (director-interest disclosure); generic register duty/title requires legal reconciliation",
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
        "law": "Companies Act 1994 and applicable Articles; exact register obligation requires counsel verification",
        "requirement": "Review prompt only: no universal register-of-contracts duty has been established for this generic rule. Verify the exact statutory provision, company Articles, contract category and evidence.",
        "provision": "UNVERIFIED CANDIDATE — Companies Act 1994 and applicable Articles; exact register obligation requires counsel verification",
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
        "law": "Section 286 and following provisions, Companies Act 1994 (Bangladesh)",
        "requirement": "Reported voluntary winding-up resolution. Verify the statutory ground, resolution, applicable solvency declaration, liquidator appointment, creditor process and current status under Part V; no automatic BLACK classification.",
        "provision": "UNVERIFIED CANDIDATE — Section 286 and following provisions, Companies Act 1994 (Bangladesh)",
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
        "requirement": "Reported company investigation. Verify the Government inspector appointment under section 195 or 197, the scope of any section 199 related-entity investigation, authenticated order, parties and current status. An inquiry is not itself a finding of liability.",
        "provision": "UNVERIFIED CANDIDATE — Sections 195 and 197; section 199 where related entities are included, Companies Act 1994 (Bangladesh)",
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
        "requirement": "Foreign exchange violation detected under FE Regulation Act 1947.",
        "provision": "UNVERIFIED CANDIDATE — Foreign Exchange Regulation Act 1947 (Bangladesh)",
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
        "law": "Bangladesh Labour Act 2006, Section 326, as amended by Act No. 43 of 2026",
        "requirement": "Review prompt only: verify a Government direction under section 326, establishment class, effective date, exemptions and authentic licence status.",
        "provision": "UNVERIFIED CANDIDATE — Bangladesh Labour Act 2006, Section 326, as amended by Act No. 43 of 2026",
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
        "law": "Bangladesh Labour Act 2006, Section 326, as amended by Act No. 43 of 2026",
        "requirement": "Review prompt only: verify the section 326 Government direction, licence class, five-year/contractor one-year term, renewal application and any extension.",
        "provision": "UNVERIFIED CANDIDATE — Bangladesh Labour Act 2006, Section 326, as amended by Act No. 43 of 2026",
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
        "law": "Bangladesh Labour Act 2006 and the specific Labour Court order; enabling provision and operative status require case-specific verification",
        "requirement": "Review prompt only: verify certified order, parties, company identity, service, operative directions, appeal/revision and stay before finding non-compliance.",
        "provision": "UNVERIFIED CANDIDATE — Bangladesh Labour Act 2006 and the specific Labour Court order; enabling provision and operative status require case-specific verification",
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
        "law": "Sections 11 and 88(1), Companies Act 1994 (Bangladesh)",
        "requirement": "Name change under Section 11; copy of special resolution to RJSC within 15 days under Section 88(1). Further name-change certificate/registration steps must be separately verified.",
        "provision": "UNVERIFIED CANDIDATE — Sections 11 and 88(1), Companies Act 1994 (Bangladesh)",
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
        "requirement": "MoA object-clause alteration: Sections 12 and 15-16 may require court confirmation/registration; copy of special resolution is filed under Section 88(1) within 15 days. Do not treat the 15-day copy filing as completion of court confirmation.",
        "provision": "UNVERIFIED CANDIDATE — Sections 12, 15-16 and 88(1), Companies Act 1994 (Bangladesh)",
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
        "requirement": "AoA alteration under Section 20; special-resolution copy filed within 15 days under Section 88(1). Verify any further registration step.",
        "provision": "UNVERIFIED CANDIDATE — Sections 20 and 88(1), Companies Act 1994 (Bangladesh)",
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
        "law": "Income Tax Act 2023, Sections 170(2) and 171, as amended by Finance Act 2026 (Act No. 96 of 2026); taxpayer-specific and holiday verification required",
        "requirement": "For non-individual taxpayers, verify the s.170(2) deadline: 15th day of ninth month after income-year end, but not earlier than the following 15 September; check holiday roll-forward, extensions and taxpayer classification.",
        "provision": "UNVERIFIED CANDIDATE — Income Tax Act 2023, Sections 170(2) and 171, as amended by Finance Act 2026 (Act No. 96 of 2026); taxpayer-specific and holiday verification required",
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
        "law": "Income Tax Act 2023, sections 154-157, as amended by Finance Act 2026 (Act 96/2026), sections 87-88; NOT_EVALUATED pending taxpayer-specific verification",
        "requirement": "Review prompt only: s.154(1) threshold is BDT 10 lakh after Finance Act 2026 s.87; s.156 retains a separate BDT 6 lakh new-assessee threshold in the current Act text. Verify s.155 A-B computation, source deductions, four instalments, s.155(5) estimates, exclusions, holiday adjustment and payment evidence.",
        "provision": "UNVERIFIED CANDIDATE — Income Tax Act 2023, sections 154-157, as amended by Finance Act 2026 (Act 96/2026), sections 87-88; NOT_EVALUATED pending taxpayer-specific verification",
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
        "law": "Local Government (City Corporation) Act 2009 / Local Government (Paurashava) Act 2009",
        "requirement": "Trade License not obtained from City Corporation/Municipality.",
        "provision": "UNVERIFIED CANDIDATE — Local Government (City Corporation) Act 2009 / Local Government (Paurashava) Act 2009",
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
        "law": "Local Government (City Corporation) Act 2009 / Local Government (Paurashava) Act 2009",
        "requirement": "Trade License expired. Must renew by 31 March annually.",
        "provision": "UNVERIFIED CANDIDATE — Local Government (City Corporation) Act 2009 / Local Government (Paurashava) Act 2009",
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
        "law": "Value Added Tax and Supplementary Duty Act 2012, section 64 as amended by Finance Act 2026 and VAT Amendment Ordinance 2026, with applicable VAT Rules/SROs",
        "requirement": "Review prompt only: verify the applicable section 64 version, tax period, taxpayer class, due date, holiday rule, extension and filing evidence.",
        "provision": "UNVERIFIED CANDIDATE — Value Added Tax and Supplementary Duty Act 2012, section 64 as amended by Finance Act 2026 and VAT Amendment Ordinance 2026, with applicable VAT Rules/SROs",
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
        "law": "Value Added Tax Act 2012 (Bangladesh); specific annual-return obligation and due date require current-law verification",
        "requirement": "Review prompt only: no universal annual return obligation is assumed; identify the taxpayer-specific operative Act/Rule/SRO before assessing a filing default.",
        "provision": "UNVERIFIED CANDIDATE — Value Added Tax Act 2012 (Bangladesh); specific annual-return obligation and due date require current-law verification",
        "provision_status": ProvisionStatus.RECONCILE,
        "applicability": "ALL_ACTIVE_COMPANIES",
        "exceptions": [],
        "evidence_required": ["DOCUMENTARY_EVIDENCE"],
        "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT],
        "severity": "NOT_EVALUATED",
        "score_impact": 0,
        "invariants": ["R-007", "R-008", "R-014", "R-019"]
    },

    "BOD-001": {"rule_id": "BOD-001", "legal_domain": "Corporate", "law": "Section 96, Companies Act 1994 (Bangladesh)", "requirement": "Section 96 requires at least one Board meeting every three months and at least four meetings per year. Review prompt only until the complete, verified meeting history and relevant annual period are available.", "provision": "UNVERIFIED CANDIDATE — Section 96, Companies Act 1994 (Bangladesh)", "provision_status": ProvisionStatus.RECONCILE, "applicability": "ALL_ACTIVE_COMPANIES", "exceptions": [], "evidence_required": ["DOCUMENTARY_EVIDENCE"], "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT], "severity": "NOT_EVALUATED", "score_impact": 0, "invariants": ["R-007", "R-008", "R-014", "R-019"]},
    "BOD-002": {"rule_id": "BOD-002", "legal_domain": "Corporate", "law": "Section 95, Companies Act 1994 (Bangladesh)", "requirement": "Review prompt only: verify notice to each director then in Bangladesh, service, address, dispatch/receipt evidence and any applicable Articles before a breach finding.", "provision": "UNVERIFIED CANDIDATE — Section 95, Companies Act 1994 (Bangladesh)", "provision_status": ProvisionStatus.RECONCILE, "applicability": "ALL_ACTIVE_COMPANIES", "exceptions": [], "evidence_required": ["DOCUMENTARY_EVIDENCE"], "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT], "severity": "NOT_EVALUATED", "score_impact": 0, "invariants": ["R-007", "R-008", "R-014", "R-019"]},
    "BOD-003": {"rule_id": "BOD-003", "legal_domain": "Corporate", "law": "Section 89, Companies Act 1994 (Bangladesh)", "requirement": "Review prompt only: verify minute book, subsequent approval/signature, custody and inspection records; missing upload alone does not establish non-creation.", "provision": "UNVERIFIED CANDIDATE — Section 89, Companies Act 1994 (Bangladesh)", "provision_status": ProvisionStatus.RECONCILE, "applicability": "ALL_ACTIVE_COMPANIES", "exceptions": [], "evidence_required": ["DOCUMENTARY_EVIDENCE"], "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT], "severity": "NOT_EVALUATED", "score_impact": 0, "invariants": ["R-007", "R-008", "R-014", "R-019"]},
    "ACC-001": {"rule_id": "ACC-001", "legal_domain": "Corporate", "law": "Section 183, Companies Act 1994 (Bangladesh)", "requirement": "AGM held but balance sheet and P&L not presented. Section 183.", "provision": "UNVERIFIED CANDIDATE — Section 183, Companies Act 1994 (Bangladesh)", "provision_status": ProvisionStatus.RECONCILE, "applicability": "ALL_ACTIVE_COMPANIES", "exceptions": [], "evidence_required": ["DOCUMENTARY_EVIDENCE"], "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT], "severity": "NOT_EVALUATED", "score_impact": 0, "invariants": ["R-007", "R-008", "R-014", "R-019"]},
    "ACC-002": {"rule_id": "ACC-002", "legal_domain": "Corporate", "law": "Section 190, Companies Act 1994 (Bangladesh)", "requirement": "Balance sheet not filed within 30 days of AGM. Section 190.", "provision": "UNVERIFIED CANDIDATE — Section 190, Companies Act 1994 (Bangladesh)", "provision_status": ProvisionStatus.RECONCILE, "applicability": "ALL_ACTIVE_COMPANIES", "exceptions": [], "evidence_required": ["DOCUMENTARY_EVIDENCE"], "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT], "severity": "NOT_EVALUATED", "score_impact": 0, "invariants": ["R-007", "R-008", "R-014", "R-019"]},
    "ACC-003": {"rule_id": "ACC-003", "legal_domain": "Corporate", "law": "Section 181, Companies Act 1994 (Bangladesh)", "requirement": "Proper books of account not maintained. Section 181.", "provision": "UNVERIFIED CANDIDATE — Section 181, Companies Act 1994 (Bangladesh)", "provision_status": ProvisionStatus.RECONCILE, "applicability": "ALL_ACTIVE_COMPANIES", "exceptions": [], "evidence_required": ["DOCUMENTARY_EVIDENCE"], "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT], "severity": "NOT_EVALUATED", "score_impact": 0, "invariants": ["R-007", "R-008", "R-014", "R-019"]},
    "DIR-007": {"rule_id": "DIR-007", "legal_domain": "Corporate", "law": "Section 93(2), Companies Act 1994 (Bangladesh); section 92/Form IX mapping requires review", "requirement": "Written consent to act as director must be filed with the Registrar within 30 days after appointment under section 93(2). Distinguish pre-appointment consent under section 92 and reconcile the current RJSC Form IX instructions before assessment.", "provision": "UNVERIFIED CANDIDATE — Section 93(2), Companies Act 1994 (Bangladesh); section 92/Form IX mapping requires review", "provision_status": ProvisionStatus.RECONCILE, "applicability": "ALL_ACTIVE_COMPANIES", "exceptions": [], "evidence_required": ["DOCUMENTARY_EVIDENCE"], "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT], "severity": "NOT_EVALUATED", "score_impact": 0, "invariants": ["R-007", "R-008", "R-014", "R-019"]},
    "DIR-008": {"rule_id": "DIR-008", "legal_domain": "Corporate", "law": "Section 104, Companies Act 1994 (Bangladesh)", "requirement": "Review prompt only: verify the exact office held, statutory exclusions, company relationship and whether general-meeting consent was obtained. A profile boolean alone cannot establish breach.", "provision": "UNVERIFIED CANDIDATE — Section 104, Companies Act 1994 (Bangladesh)", "provision_status": ProvisionStatus.RECONCILE, "applicability": "ALL_ACTIVE_COMPANIES", "exceptions": [], "evidence_required": ["DOCUMENTARY_EVIDENCE"], "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT], "severity": "NOT_EVALUATED", "score_impact": 0, "invariants": ["R-007", "R-008", "R-014", "R-019"]},
    "DIR-010": {"rule_id": "DIR-010", "legal_domain": "Corporate", "law": "Section 110, Companies Act 1994 (Bangladesh)", "requirement": "Review prompt only: verify current appointment instrument, term, reappointment, approval and continuity before assessing the five-year-at-a-time limit.", "provision": "UNVERIFIED CANDIDATE — Section 110, Companies Act 1994 (Bangladesh)", "provision_status": ProvisionStatus.RECONCILE, "applicability": "ALL_ACTIVE_COMPANIES", "exceptions": [], "evidence_required": ["DOCUMENTARY_EVIDENCE"], "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT], "severity": "NOT_EVALUATED", "score_impact": 0, "invariants": ["R-007", "R-008", "R-014", "R-019"]},
    "MEM-001": {"rule_id": "MEM-001", "legal_domain": "Corporate", "law": "Section 222, Companies Act 1994 (Bangladesh)", "requirement": "Company below minimum members. Section 222: private < 2, public < 7.", "provision": "UNVERIFIED CANDIDATE — Section 222, Companies Act 1994 (Bangladesh)", "provision_status": ProvisionStatus.RECONCILE, "applicability": "ALL_ACTIVE_COMPANIES", "exceptions": [], "evidence_required": ["DOCUMENTARY_EVIDENCE"], "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT], "severity": "NOT_EVALUATED", "score_impact": 0, "invariants": ["R-007", "R-008", "R-014", "R-019"]},
    "INC-007": {"rule_id": "INC-007", "legal_domain": "Corporate", "law": "Section 150(1) and (6), Companies Act 1994 (Bangladesh)", "requirement": "Section 150 commencement declaration is not universal: subsection (6) excludes private companies and companies that do not issue a prospectus inviting public subscription. Review only where public-company status, prospectus issue and every section 150 condition are independently verified.", "provision": "UNVERIFIED CANDIDATE — Section 150(1) and (6), Companies Act 1994 (Bangladesh)", "provision_status": ProvisionStatus.RECONCILE, "applicability": "ALL_ACTIVE_COMPANIES", "exceptions": [], "evidence_required": ["DOCUMENTARY_EVIDENCE"], "evaluation_states": [RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT], "severity": "NOT_EVALUATED", "score_impact": 0, "invariants": ["R-007", "R-008", "R-014", "R-019"]},

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
    applicability = d["applicability"]
    if not isinstance(applicability, str) or not applicability.strip():
        raise RuntimeError(f"{key}: applicability must be a non-empty string")
    exceptions = d["exceptions"]
    if not isinstance(exceptions, (list, tuple)) or any(
        not isinstance(item, str) or not item.strip() for item in exceptions
    ):
        raise RuntimeError(f"{key}: exceptions must be non-empty strings")
    evidence_required = d["evidence_required"]
    if not isinstance(evidence_required, (list, tuple)) or not evidence_required or any(
        not isinstance(item, str) or not item.strip() for item in evidence_required
    ):
        raise RuntimeError(
            f"{key}: evidence_required must contain unique, non-empty strings"
        )
    # Admit both placeholder DOCUMENTARY_EVIDENCE stubs and fully specified
    # multi-item evidence lists (INC-005, INC-006, CAP-003). The previous
    # DOCUMENTARY_EVIDENCE-only gate silently dropped those three rules and
    # left STATUTORY_RULE_REGISTRY at 82 while the engine exposes 85.
    auth = _LEGACY_AUTHORITY_OVERRIDE.get(key) or _LEGACY_AUTHORITY[d["legal_domain"]]
    applies_if = None if applicability == "ALL_ACTIVE_COMPANIES" else applicability
    return StatutoryRule(
        key, d["legal_domain"], d["law"], d["requirement"], d["provision"],
        d["provision_status"], auth, tuple(evidence_required),
        Severity(d["severity"]), d["score_impact"],
        applies_if=applies_if,
        exceptions=tuple(exceptions),
    )


for _k, _d in _LEGACY_RULE_DICTS.items():
    if _k not in STATUTORY_RULE_REGISTRY:   # explicit typed rule wins on overlap
        STATUTORY_RULE_REGISTRY[_k] = _legacy_rule(_k, _d)

# Exact runtime parity is an import-time invariant; permissive >=80 tests are unsafe.
_EXPECTED_RULE_IDS = frozenset(_LEGACY_RULE_DICTS) | frozenset(rule.rule_id for rule in _RULES)
if len(_EXPECTED_RULE_IDS) != 85 or set(STATUTORY_RULE_REGISTRY) != _EXPECTED_RULE_IDS:
    missing = sorted(_EXPECTED_RULE_IDS - set(STATUTORY_RULE_REGISTRY))
    unexpected = sorted(set(STATUTORY_RULE_REGISTRY) - _EXPECTED_RULE_IDS)
    raise RuntimeError(
        f"canonical statutory registry parity failure: expected=85 actual={len(STATUTORY_RULE_REGISTRY)} "
        f"missing={missing} unexpected={unexpected}"
    )

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

