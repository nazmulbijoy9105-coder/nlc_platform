"""
NLC Evidence Type Mapping

Maps each verified rule to specific evidence types required to prove
compliance or non-compliance. Replaces generic DOCUMENTARY_EVIDENCE
with specific, auditable evidence categories.

Evidence types are derived from the Companies Act 1994 (Bangladesh)
section text — specifically the evidentiary provisions (S31, S45, S89,
S150, S165, S208, S337) that specify what records are conclusive or
prima facie evidence.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple

@dataclass(frozen=True)
class EvidenceMapping:
    """Maps a rule to the specific evidence required to evaluate it."""
    rule_id: str
    primary_evidence: Tuple[str, ...]      # documents that prove compliance
    non_compliance_evidence: Tuple[str, ...]  # documents that prove breach
    evidentiary_standard: str               # "conclusive", "prima_facie", "documentary"
    source_section: str                     # Act section that defines the evidence

# ═════════════════════════════════════════════════════════════════════
# EVIDENCE TYPES
# ═════════════════════════════════════════════════════════════════════

RJSC_FILING_ACK = "RJSC_FILING_ACKNOWLEDGEMENT"
BOARD_RESOLUTION = "BOARD_RESOLUTION"
AGM_MINUTES = "AGM_MINUTES_SIGNED_BY_CHAIRMAN"
AUDITED_ACCOUNTS = "AUDITED_FINANCIAL_STATEMENTS"
COURT_ORDER = "COURT_ORDER"
REGISTER_ENTRY = "STATUTORY_REGISTER_ENTRY"
SHARE_CERTIFICATE = "SHARE_CERTIFICATE_UNDER_SEAL"
FORM_XII = "FORM_XII_DIRECTOR_CHANGE"
FORM_VI = "FORM_VI_OFFICE_CHANGE"
FORM_VIII = "FORM_VIII_CHARGE_REGISTRATION"
FORM_XV = "FORM_XV_ALLOTMENT_RETURN"
FORM_XVII = "FORM_XVII_TRANSFER_INSTRUMENT"
RJSC_CERTIFICATE = "RJSC_CERTIFICATE_OF_INCORPORATION"
DIRECTOR_CONSENT = "DIRECTOR_CONSENT_IN_WRITING"
INSOLVENCY_ORDER = "INSOLVENCY_COURT_ORDER"
PENALTY_NOTICE = "PENALTY_NOTICE_FROM_REGISTRAR"

# ═════════════════════════════════════════════════════════════════════
# EVIDENCE MAPPINGS — 35 verified rules
# ═════════════════════════════════════════════════════════════════════

EVIDENCE_REGISTRY: dict[str, EvidenceMapping] = {
    "AGM-001": EvidenceMapping("AGM-001",
        (AGM_MINUTES, RJSC_FILING_ACK),
        (RJSC_FILING_ACK,),  # absence of AGM filing
        "prima_facie", "S89"),
    "AGM-002": EvidenceMapping("AGM-002",
        (AGM_MINUTES, RJSC_FILING_ACK),
        (RJSC_FILING_ACK,),
        "prima_facie", "S89"),
    "AGM-003": EvidenceMapping("AGM-003",
        (AGM_MINUTES, "NOTICE_SENT_PROOF"),
        ("NOTICE_DEFECTIVE",),
        "documentary", "S85"),
    "AGM-004": EvidenceMapping("AGM-004",
        ("NOTICE_SENT_PROOF", AGM_MINUTES),
        ("NO_NOTICE_SENT",),
        "documentary", "S85"),
    "AGM-005": EvidenceMapping("AGM-005",
        (AGM_MINUTES, "ATTENDANCE_REGISTER"),
        ("INSUFFICIENT_QUORUM",),
        "documentary", "S85(2)(b)"),
    "AGM-006": EvidenceMapping("AGM-006",
        (AGM_MINUTES,),
        ("MINUTES_MISSING",),
        "prima_facie", "S89"),
    "AGM-007": EvidenceMapping("AGM-007",
        (AGM_MINUTES, "ADJOURNMENT_NOTICE"),
        ("ADJOURNMENT_WITHOUT_NOTICE",),
        "documentary", "S84"),

    "REG-001": EvidenceMapping("REG-001",
        (REGISTER_ENTRY,),
        ("REGISTER_MISSING",),
        "prima_facie", "S45"),
    "REG-002": EvidenceMapping("REG-002",
        (REGISTER_ENTRY,),
        ("CORE_REGISTERS_MISSING",),
        "prima_facie", "S45"),
    "REG-003": EvidenceMapping("REG-003",
        (REGISTER_ENTRY, "BOARD_RESOLUTION_ON_LOCATION"),
        ("REGISTER_NOT_AT_REGISTERED_OFFICE",),
        "documentary", "S34(2)"),

    "OFF-001": EvidenceMapping("OFF-001",
        (FORM_VI, RJSC_FILING_ACK),
        ("OFFICE_CHANGE_NOT_FILED",),
        "documentary", "S77"),

    "DIR-001": EvidenceMapping("DIR-001",
        (FORM_XII, RJSC_FILING_ACK),
        ("APPOINTMENT_NOT_FILED",),
        "documentary", "S92"),
    "DIR-002": EvidenceMapping("DIR-002",
        (FORM_XII, RJSC_FILING_ACK),
        ("DEPARTURE_NOT_FILED",),
        "documentary", "S92"),
    "DIR-003": EvidenceMapping("DIR-003",
        (FORM_XII, RJSC_FILING_ACK),
        ("FILING_OVERDUE_1_YEAR",),
        "documentary", "S92"),
    "DIR-004": EvidenceMapping("DIR-004",
        (FORM_XII, REGISTER_ENTRY),
        ("DEPARTED_DIRECTOR_STILL_ACTIVE",),
        "prima_facie", "S115"),
    "DIR-007": EvidenceMapping("DIR-007",
        (DIRECTOR_CONSENT, RJSC_FILING_ACK),
        ("CONSENT_NOT_FILED",),
        "documentary", "S93(2)"),
    "DIR-008": EvidenceMapping("DIR-008",
        (BOARD_RESOLUTION,),
        ("OFFICE_OF_PROFIT_WITHOUT_CONSENT",),
        "documentary", "S104"),
    "DIR-010": EvidenceMapping("DIR-010",
        (BOARD_RESOLUTION, "MD_APPOINTMENT_LETTER"),
        ("MD_TERM_EXCEEDS_5_YEARS",),
        "documentary", "S110"),

    "CAP-001": EvidenceMapping("CAP-001",
        (BOARD_RESOLUTION, RJSC_FILING_ACK),
        ("CAPITAL_CHANGE_WITHOUT_RESOLUTION",),
        "documentary", "S53"),
    "CAP-002": EvidenceMapping("CAP-002",
        (FORM_VIII, RJSC_FILING_ACK),
        ("CHARGE_NOT_REGISTERED",),
        "conclusive", "S159"),
    "CAP-003": EvidenceMapping("CAP-003",
        (COURT_ORDER, BOARD_RESOLUTION),
        ("CAPITAL_REDUCTION_WITHOUT_COURT",),
        "conclusive", "S59"),
    "CHG-001": EvidenceMapping("CHG-001",
        (FORM_VIII, RJSC_FILING_ACK),
        ("CHARGE_NOT_REGISTERED",),
        "conclusive", "S159"),

    "STR-001": EvidenceMapping("STR-001",
        (BOARD_RESOLUTION, RJSC_FILING_ACK, RJSC_CERTIFICATE),
        ("NAME_CHANGE_NOT_FILED",),
        "conclusive", "S11"),
    "STR-002": EvidenceMapping("STR-002",
        (BOARD_RESOLUTION, COURT_ORDER, RJSC_FILING_ACK),
        ("OBJECT_CHANGE_NOT_FILED",),
        "documentary", "S17"),
    "STR-003": EvidenceMapping("STR-003",
        (BOARD_RESOLUTION, RJSC_FILING_ACK),
        ("AOA_ALTERATION_NOT_FILED",),
        "documentary", "S18"),

    "ACC-001": EvidenceMapping("ACC-001",
        (AUDITED_ACCOUNTS, AGM_MINUTES),
        ("FINANCIAL_STATEMENTS_NOT_PRESENTED",),
        "documentary", "S183"),
    "ACC-002": EvidenceMapping("ACC-002",
        (AUDITED_ACCOUNTS, RJSC_FILING_ACK),
        ("BALANCE_SHEET_NOT_FILED",),
        "documentary", "S190"),
    "ACC-003": EvidenceMapping("ACC-003",
        ("BOOKS_OF_ACCOUNT",),
        ("BOOKS_NOT_MAINTAINED",),
        "documentary", "S181"),

    "BOD-001": EvidenceMapping("BOD-001",
        (BOARD_RESOLUTION, "BOARD_MEETING_MINUTES"),
        ("BOARD_MEETING_NOT_HELD",),
        "documentary", "S96"),
    "BOD-002": EvidenceMapping("BOD-002",
        ("BOARD_MEETING_NOTICE",),
        ("NOTICE_NOT_GIVEN",),
        "documentary", "S95"),
    "BOD-003": EvidenceMapping("BOD-003",
        ("BOARD_MEETING_MINUTES",),
        ("MINUTES_NOT_PREPARED",),
        "prima_facie", "S89"),

    "INC-001": EvidenceMapping("INC-001",
        (RJSC_CERTIFICATE, RJSC_FILING_ACK),
        ("MOA_AOA_NOT_FILED",),
        "conclusive", "S23"),
    "INC-003": EvidenceMapping("INC-003",
        (REGISTER_ENTRY, FORM_XII),
        ("MINIMUM_DIRECTORS_NOT_MET",),
        "documentary", "S90(2)"),
    "INC-004": EvidenceMapping("INC-004",
        (REGISTER_ENTRY, FORM_XV),
        ("PAID_UP_EXCEEDS_AUTHORIZED",),
        "conclusive", "S53"),
    "INC-007": EvidenceMapping("INC-007",
        (RJSC_FILING_ACK, "COMMENCEMENT_DECLARATION"),
        ("BUSINESS_STARTED_WITHOUT_DECLARATION",),
        "conclusive", "S150"),

    "MEM-001": EvidenceMapping("MEM-001",
        (REGISTER_ENTRY,),
        ("MEMBERSHIP_BELOW_MINIMUM",),
        "prima_facie", "S222"),

    "TR-001": EvidenceMapping("TR-001",
        (FORM_XVII, "STAMP_DUTY_CERTIFICATE"),
        ("NO_TRANSFER_INSTRUMENT",),
        "documentary", "S38"),

    "ESC-001": EvidenceMapping("ESC-001",
        (RJSC_FILING_ACK, "FILING_HISTORY"),
        ("STRIKE_OFF_RISK_ELEVATED",),
        "documentary", "S346"),
    "ESC-002": EvidenceMapping("ESC-002",
        ("STRIKE_OFF_NOTICE", "FILING_HISTORY"),
        ("STRIKE_OFF_IMMINENT",),
        "documentary", "S346"),

    "DEF-001": EvidenceMapping("DEF-001",
        (INSOLVENCY_ORDER, "COURT_FINDING_OF_UNSOUND_MIND"),
        ("DIRECTOR_DISQUALIFIED",),
        "conclusive", "S94"),
    "DEF-002": EvidenceMapping("DEF-002",
        (PENALTY_NOTICE,),
        ("PENALTY_NOTICES_UNRESOLVED",),
        "documentary", "S397"),
}