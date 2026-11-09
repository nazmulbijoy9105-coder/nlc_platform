# ═══════════════════════════════════════════════════════════════════════
# NEUM LEX COUNSEL — RJSC COMPLIANCE INTELLIGENCE PLATFORM
# LAYER C: LEGAL RULE ENGINE — BANGLADESH CA 1994 COMPLIANT v2.1
# All ILRMF v2.1 Rules | Deterministic | AI-Non-Editable
# Version: 2.1 | Classification: PROPRIETARY IP — NEUM LEX COUNSEL
# Governed by: Internal AI Constitution v2.0
# ═══════════════════════════════════════════════════════════════════════

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

# F3 UNKNOWN policy constants (legal fix 2026-10-30)
UNKNOWN_COVERAGE_CAP = 5   # max total points withheld for unknown facts
UNKNOWN_COVERAGE_PER = 1   # points withheld per UNKNOWN flag


logger = logging.getLogger("nlc.rule_engine")

# ───────────────────────────────────────────────────────────────────────
# RULE ENGINE VERSION — Immutable in production
# ───────────────────────────────────────────────────────────────────────
RULE_ENGINE_VERSION = "2.2"
ILRMF_VERSION = "2.2"

# ═══════════════════════════════════════════════════════════════════════
# ENUMERATIONS
# ═══════════════════════════════════════════════════════════════════════

class Severity(str, Enum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"
    BLACK = "BLACK"
    NOT_EVALUATED = "NOT_EVALUATED"

class RevenueTier(str, Enum):
    COMPLIANCE_PACKAGE = "COMPLIANCE_PACKAGE"
    STRUCTURED_REGULARIZATION = "STRUCTURED_REGULARIZATION"
    CORPORATE_RESCUE = "CORPORATE_RESCUE"

class ExposureBand(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    SEVERE = "SEVERE"

class RuleType(str, Enum):
    DEADLINE = "DEADLINE"
    DEPENDENCY = "DEPENDENCY"
    THRESHOLD = "THRESHOLD"
    CASCADE = "CASCADE"
    ESCALATION = "ESCALATION"
    CONDITIONAL = "CONDITIONAL"

class LifecycleStage(str, Enum):
    INCORPORATION = "INCORPORATION"
    PRE_FIRST_AGM = "PRE_FIRST_AGM"
    POST_FIRST_AGM = "POST_FIRST_AGM"
    ANNUAL_COMPLIANCE_CYCLE = "ANNUAL_COMPLIANCE_CYCLE"
    STRUCTURAL_CHANGE = "STRUCTURAL_CHANGE"
    IRREGULAR_STATUS = "IRREGULAR_STATUS"
    STATUTORY_DEFAULT = "STATUTORY_DEFAULT"
    DORMANT_STRIKE_OFF = "DORMANT_STRIKE_OFF"

# ═══════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════

class RuleState(str, Enum):
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    VERIFIED_ABSENT = "VERIFIED_ABSENT"  # confirmed absence via verified external source
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    CONDITIONAL = "CONDITIONAL"
    CONTRADICTORY = "CONTRADICTORY"
    DISPUTED = "DISPUTED"
    REQUIRES_LAWYER_JUDGMENT = "REQUIRES_LAWYER_JUDGMENT"

class ApplicabilityState(str, Enum):
    APPLICABLE = "APPLICABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ApplicabilityDecision:
    state: ApplicabilityState
    reason: str

@dataclass
class ComplianceFlag:
    rule_id: str
    flag_code: str
    severity: Severity
    score_impact: int
    revenue_tier: RevenueTier
    description: str
    statutory_basis: str
    rule_version: str = RULE_ENGINE_VERSION
    triggered_date: date = field(default_factory=date.today)
    detail: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    is_black_override: bool = False
    escalation_pending: bool = False
    state: RuleState = RuleState.NON_COMPLIANT
    conditional_applies: bool = True
    eval_state: str = "VIOLATION"   # F3: UNKNOWN -> impact forced to 0

    def __post_init__(self):
        # F3 UNKNOWN policy: unknown facts are indeterminate, not violations
        if self.state not in (RuleState.NON_COMPLIANT, RuleState.VERIFIED_ABSENT) or self.eval_state != "VIOLATION":
            self.score_impact = 0

@dataclass
class DirectorChange:
    director_id: str
    event_type: str
    event_date: date
    # Form XII status and section 93(2) director-consent status are separate facts.
    # None means not verified; absence of an upload is not proof of non-filing.
    form_filed: bool | None = None
    form_filed_date: Optional[date] = None
    form_type: str = "XII"
    form_filed_verified: bool = False
    form_filed_evidence_ref: str | None = None
    consent_filed: bool | None = None
    consent_filed_date: Optional[date] = None
    consent_verified: bool = False
    consent_evidence_ref: str | None = None

@dataclass
class ShareTransfer:
    transfer_id: str
    transfer_date: date
    # None means the evidence/status has not been verified; do not infer absence.
    instrument_recorded: bool | None = None
    stamp_duty_paid: bool | None = None
    stamp_duty_applicability_verified: bool = False
    stamp_duty_amount: Optional[float] = None
    board_approval: bool | None = None
    share_register_updated: bool | None = None
    aoa_restriction_apply: bool | None = None
    board_approval_obtained: bool | None = None
    form_117_filed: bool | None = None
    transfer_registered: bool | None = None
    registration_refused: bool | None = None
    refusal_notice_sent: bool | None = None
    instrument_lodged_date: Optional[date] = None
    articles_clause_evidence_ref: str | None = None
    refusal_decision_evidence_ref: str | None = None
    transfer_registration_evidence_ref: str | None = None

@dataclass
class ShareComplianceEventEvidence:
    event_reference: str
    event_type: str
    event_date: date
    event_verified: bool = False
    event_evidence_ref: str | None = None
    filing_form: str | None = None
    filing_status: bool | None = None
    filing_status_verified: bool = False
    filing_date: date | None = None
    filing_evidence_ref: str | None = None
    certificate_issued: bool | None = None
    certificate_status_verified: bool = False
    certificate_issue_date: date | None = None
    certificate_evidence_ref: str | None = None


@dataclass
class ChargeEvent:
    charge_id: str
    creation_date: date
    charge_type: str
    amount_bdt: float
    charge_holder: str
    form_xviii_filed: bool | None = None
    form_xviii_filed_date: Optional[date] = None
    creation_date_verified: bool = False
    creation_date_evidence_ref: str | None = None
    form_xviii_filing_status_verified: bool = False
    form_xviii_filing_evidence_ref: str | None = None
    form_xix_filed: bool = False
    form_xxviii_filed: bool = False
    satisfied: bool | None = None
    satisfaction_date: Optional[date] = None
    satisfaction_filed: bool | None = None
    satisfaction_filed_date: Optional[date] = None
    # Section 172 applies only to charges whose registration is required by s.159.
    registrable_under_s159: bool | None = None
    registrability_verified: bool = False
    registrability_evidence_ref: str | None = None
    satisfaction_verified: bool = False
    satisfaction_evidence_ref: str | None = None
    satisfaction_filing_status_verified: bool = False
    satisfaction_filing_evidence_ref: str | None = None

@dataclass
class CompanyProfile:
    company_id: str
    company_name: str
    company_type: str = "PRIVATE_LIMITED"
    incorporation_date: date | None = None
    financial_year_end: Optional[date] = field(default=None)
    agm_count: int | None = None
    agm_history_verified: bool = False
    agm_history_evidence_ref: str | None = None
    agm_history_verified_at: date | None = None
    agm_history_verified_by: str | None = None
    last_agm_date: Optional[date] = None
    agm_extension_granted_until: date | None = None
    agm_extension_application_date: date | None = None
    agm_extension_verified: bool = False
    agm_extension_evidence_ref: str | None = None
    agm_extension_verified_at: date | None = None
    agm_extension_verified_by: str | None = None
    agm_held_this_cycle: bool | None = None
    agm_held_without_audit: bool | None = None
    agm_scheduled_date: Optional[date] = None
    notice_sent_date: Optional[date] = None
    short_notice_consent_obtained: bool | None = None
    short_notice_consent_verified: bool = False
    short_notice_consent_evidence_ref: str | None = None
    members_present_at_agm: int | None = None
    # Section 85(2)(b) is only the default where the Articles do not provide otherwise.
    agm_quorum_required: int | None = None
    agm_quorum_basis_verified: bool = False
    agm_attendance_verified: bool = False
    agm_attendance_evidence_ref: str | None = None
    agm_quorum_evidence_ref: str | None = None
    auditor_reappointed_at_agm: bool | None = None
    auditor_reappointment_verified: bool = False
    auditor_reappointment_evidence_ref: str | None = None
    accounts_adopted_at_agm: bool | None = None
    agm_minutes_prepared: bool | None = None
    first_auditor_appointed: bool | None = None
    first_auditor_appointment_date: Optional[date] = None
    first_auditor_appointment_verified: bool = False
    first_auditor_appointment_evidence_ref: str | None = None
    first_auditor_appointment_verified_at: date | None = None
    first_auditor_appointment_verified_by: str | None = None
    audit_complete: bool | None = None
    audit_completion_verified: bool = False
    audit_completion_evidence_ref: str | None = None
    audit_completion_verified_at: date | None = None
    audit_completion_verified_by: str | None = None
    last_audit_signed_date: Optional[date] = None
    audit_in_progress: bool = False
    auditor_name: Optional[str] = None
    auditor_firm_reg_no: Optional[str] = None
    last_return_filed_year: Optional[int] = None
    unfiled_returns_count: int | None = None
    annual_return_filed: bool = False
    annual_return_content_complete: bool = False
    annual_return_filed_date: Optional[date] = None
    schedule_x_attached: bool = False
    balance_sheet_attached: bool = False
    profit_loss_attached: bool = False
    directors_list_attached: bool = False
    shareholders_list_attached: bool = False
    director_changes: List[DirectorChange] = field(default_factory=list)
    current_director_count: int | None = None
    directors_verified: bool = False
    directors_verification_evidence_ref: str | None = None
    directors_verified_at: date | None = None
    directors_verified_by: str | None = None
    is_private_subsidiary_of_public_company: bool | None = None
    subsidiary_status_verified: bool = False
    subsidiary_status_evidence_ref: str | None = None
    subsidiary_status_verified_at: date | None = None
    subsidiary_status_verified_by: str | None = None
    minimum_directors_met: bool | None = None
    shareholder_change_date: Optional[date] = None
    form_xv_filed: bool | None = None
    form_xv_filed_date: Optional[date] = None
    last_allotment_date: Optional[date] = None
    share_certificates_issued: bool | None = None
    share_certificates_issued_date: Optional[date] = None
    authorized_capital_bdt: float = 0.0
    paid_up_capital_bdt: float = 0.0
    paid_up_ge_authorized: bool | None = None
    share_transfers: List[ShareTransfer] = field(default_factory=list)
    share_compliance_events: List[ShareComplianceEventEvidence] = field(default_factory=list)
    registered_office_address: str = ""
    registered_office_change_date: Optional[date] = None
    form_vi_filed: bool = False
    form_vi_filed_date: Optional[date] = None
    aoa_transfer_restriction: bool = False
    has_foreign_shareholder: bool = False
    foreign_shareholding_pct: float = 0.0
    is_dormant: bool = False
    is_fdi_registered: bool = False
    fdi_registration_date: Optional[date] = None
    bida_registered: bool = False
    maintained_registers: List[str] = field(default_factory=lambda: ["members", "directors", "charges", "transfers", "debentures", "minutes_agm", "minutes_board"])
    register_of_members_maintained: bool = False
    register_of_directors_maintained: bool = False
    register_of_charges_maintained: bool = False
    minutes_book_agm_maintained: bool = False
    minutes_book_board_maintained: bool = False
    register_location: str = "registered_office"
    capital_increase_date: Optional[date] = None
    capital_increase_resolution: bool | None = None
    capital_increase_special_resolution: bool = False
    form_iv_filed: bool | None = None
    form_iv_filed_date: Optional[date] = None
    form_iii_filed: bool | None = None
    form_iii_filed_date: Optional[date] = None
    # ── Board meeting (Section 95, 96, 89) ──
    last_board_meeting_date: Optional[date] = None
    board_meeting_notice_given: bool | None = None
    board_minutes_prepared: bool | None = None
    # ── Accounts (Section 181, 183, 190) ──
    financial_statements_presented: bool | None = None
    financial_statements_filed: bool | None = None
    books_of_account_kept: bool | None = None
    # ── Director extended (Section 93, 104, 110) ──
    director_consent_filed: bool | None = None
    director_office_of_profit: bool = False
    managing_director_appointment_date: Optional[date] = None
    # ── Members (Section 222) ──
    member_count: int | None = None
    # ── Business commencement (Section 150) ──
    business_commencement_declaration_filed: bool | None = None
    section150_prospectus_issued: bool | None = None
    section150_applicability_verified: bool = False
    section150_applicability_evidence_ref: str | None = None
    business_commencement_declaration_verified: bool = False
    business_commencement_declaration_evidence_ref: str | None = None
    charges: List[ChargeEvent] = field(default_factory=list)
    special_resolution_date: Optional[date] = None
    special_resolution_filed: bool = False
    special_resolution_filed_date: Optional[date] = None
    encashment_certificate_uploaded: bool = False
    encashment_certificate_date: Optional[date] = None
    remittance_amount_usd: float = 0.0
    rjsc_status: str = "ACTIVE"
    rjsc_strike_off_notice_date: Optional[date] = None
    on_rjsc_strike_off_list: bool = False
    last_rjsc_compliance_date: Optional[date] = None
    tin_obtained: bool | None = None
    tin_number: Optional[str] = None
    vat_registered: bool | None = None
    vat_number: Optional[str] = None
    last_tax_return_filed: Optional[date] = None
    trade_license_obtained: bool | None = None
    trade_license_expiry: Optional[date] = None
    last_tax_return_filed_year: Optional[int] = None
    tax_return_filed_for_current_fy: bool | None = None
    advance_tax_q1_paid: bool | None = None
    advance_tax_q2_paid: bool | None = None
    advance_tax_q3_paid: bool | None = None
    advance_tax_q4_paid: bool | None = None
    tds_deposited_up_to_date: bool = True
    last_tds_deposit_date: Optional[date] = None
    last_vat_return_filed: Optional[date] = None
    vat_annual_return_filed_for_fy: bool | None = None
    minimum_tax_paid: bool = True
    tax_clearance_obtained: bool = False
    tax_return_deadline_extended: bool = False
    any_director_disqualified: bool = False
    disqualification_details: List[str] = field(default_factory=list)
    # P0 LEGAL FIX: Structured disqualification grounds per Section 94.
    # Each entry must specify: ground_type, director_name, evidence_ref,
    # authority, effective_date. Without verified evidence, DEF-001
    # must NOT auto-trigger BLACK — it falls back to NOT_EVALUATED.
    # Ground types: UNSOUND_MIND, UNDISCHARGED_INSOLVENT,
    # PENDING_INSOLVENCY, UNPAID_CALL, MINOR, AOA_PRESCRIBED
    disqualification_grounds: List[dict] = field(default_factory=list)
    penalty_notices_received: int | None = 0
    penalty_notices_resolved: int | None = 0
    moa_aoa_filed: bool | None = None
    # Stored legacy booleans are not proof of registry verification.
    moa_aoa_verified: bool = False
    moa_aoa_evidence_ref: str | None = None
    moa_aoa_verified_at: date | None = None
    moa_aoa_verified_by: str | None = None
    annual_turnover_bdt: float = 0.0
    name_change_pending: bool = False
    name_change_date: Optional[date] = None
    name_change_sr_passed: bool = False
    object_clause_change_pending: bool = False
    object_clause_change_date: Optional[date] = None
    aoa_alteration_pending: bool = False
    aoa_alteration_date: Optional[date] = None
    capital_reduction_pending: bool = False
    capital_reduction_date: Optional[date] = None
    capital_reduction_court_order_obtained: bool = False
    # ── Insolvency (Bankruptcy Act 1997) ──
    winding_up_petition_filed: bool = False
    winding_up_petition_date: Optional[date] = None
    liquidator_appointed: bool = False
    court_ordered_winding_up: bool = False
    # ── Labour (Labour Act 2006) ──
    # Tri-state applicability (R-003/R-008): None = unknown, False = not a factory, True = manufacturing.
    is_manufacturing: bool | None = None
    factory_license_required_by_direction: bool | None = None
    factory_license_obtained: bool | None = None
    factory_license_expiry: Optional[date] = None
    worker_compensation_filed: bool | None = None
    labour_court_order_pending: bool = False
    # -- Additional Companies Act 1994 --
    agm_adjourned_without_notice: bool = False
    register_of_directors_interests: bool | None = None
    register_of_contracts: bool | None = None
    voluntary_winding_up: bool = False
    investigation_order: bool = False
    # -- BSEC Corporate Governance Code 2023 --
    bsec_listed: bool = False
    bsec_quarterly_report_filed: bool | None = None
    cg_certificate_obtained: bool | None = None
    board_independent_director: bool | None = None
    audit_committee_established: bool | None = None
    # -- Bangladesh Bank / Foreign Exchange --
    foreign_exchange_violation: bool = False

@dataclass
class ScoreBreakdown:
    agm_score: int
    audit_score: int
    return_score: int
    director_score: int
    shareholding_score: int
    capital_score: int
    office_score: int
    register_score: int
    tax_score: int
    raw_total: int
    final_score: int
    override_applied: bool
    override_reason: Optional[str]
    risk_band: Severity
    exposure_band: ExposureBand
    revenue_tier: RevenueTier
    active_flag_count: int
    coverage: float
    black_flag_count: int
    red_flag_count: int
    yellow_flag_count: int
    green_flag_count: int
    # Additional sub-scores for reconciliation
    bankruptcy_score: int | None = 0
    labour_score: int | None = 0
    bsec_score: int | None = 0
    fx_score: int | None = 0
    escalation_score: int | None = 0
    score_hash: str = ""
    category_deductions: Dict[str, int] = field(default_factory=dict)
    coverage_basis: str = "WEIGHTED_PROFILE_INPUT_COMPLETENESS"

@dataclass
class EngineOutput:
    company_id: str
    evaluation_date: date
    engine_version: str
    ilrmf_version: str
    flags: List[ComplianceFlag]
    score_breakdown: ScoreBreakdown
    lifecycle_stage: LifecycleStage
    rescue_sequence: List[Dict[str, Any]]
    fdi_module_active: bool
    tax_module_active: bool

# ═══════════════════════════════════════════════════════════════════════
# BANGLADESH COMPANIES ACT 1994 CONSTANTS
# ═══════════════════════════════════════════════════════════════════════

FY_END_AGM_DEADLINE_DAYS = 182
AGM_NOTICE_MINIMUM_DAYS = 21
PRIVATE_COMPANY_QUORUM_SMALL = 2   # Section 85(2)(b): private company with ≤6 members
PRIVATE_COMPANY_QUORUM_LARGE = 3   # Section 85(2)(b): private company with >6 members
PRIVATE_COMPANY_QUORUM = PRIVATE_COMPANY_QUORUM_SMALL  # backward compat alias
ANNUAL_RETURN_DEADLINE_DAYS = 21   # Companies Act 1994, Section 36 (Schedule X)
DIRECTOR_FILING_DEADLINE_DAYS = 14
SHARE_CERTIFICATE_DEADLINE_DAYS = 90
REGISTERED_OFFICE_DEADLINE_DAYS = 28
# P0 LEGAL FIX: Section 210(6) says "within one month" — this is a
# CALENDAR MONTH, not 30 days. A calendar month from Jan 15 = Feb 15;
# from Jan 31 = Feb 28/29 (last day of month). Using 30 days would be
# legally incorrect for months with 28/29/31 days. We now compute the
# deadline by adding one calendar month to the incorporation date.
FIRST_AUDITOR_DEADLINE_DAYS = 30  # DEPRECATED: kept for backward compat, use _add_one_month()
CHARGE_REGISTRATION_DEADLINE_DAYS = 21  # Section 159(1): charge registration within 21 days of creation
ALLOTMENT_FILING_DEADLINE_DAYS = 60  # Section 151: return of allotment
CAPITAL_INCREASE_NOTICE_DEADLINE_DAYS = 15  # Section 56: notice of increase
SPECIAL_RESOLUTION_DEADLINE_DAYS = 15  # Companies Act 1994, Section 88 (15 days)

REQUIRED_REGISTERS = [
    "members", "directors", "charges", "transfers", "debentures",
    "minutes_agm", "minutes_board",
]
CORE_REGISTERS = ["members", "directors", "charges", "minutes_agm"]

# Explicit counsel-authorized BLACK override allowlist. A rule being
# marked BLACK in engine code is not sufficient authority to force a BLACK
# score. Keep this empty until each rule has independent approval recorded
# in the signed legal approval register and the release process authorizes it.
AUTHORIZED_BLACK_OVERRIDE_RULE_IDS: frozenset[str] = frozenset()

# Backward-compatible alias; never use this set to grant authorization.
BLACK_OVERRIDE_RULES: set[str] = set()

# 100-point scoring model v2 - per-category deduction caps.
# key -> (max_deduction, rule_id_prefixes). UNKNOWN states never reach the
# deduction phase (violations are NON_COMPLIANT only).
CATEGORY_CAPS: dict[str, tuple[int, tuple[str, ...]]] = {
    "TAX":  (15, ("TAX-", "VAT-")),
    "AGM":  (30, ("AGM-",)),
    "AUD":  (25, ("AUD-",)),
    "RET":  (20, ("AR-",)),
    "DIR":  (25, ("DIR-", "INC-", "DEF-", "TL-", "BOD-", "MEM-")),
    "SHR":  (20, ("SH-", "TR-")),
    "CAP":  (15, ("CAP-", "STR-", "CHG-", "ACC-")),
    "OFF":  (10, ("OFF-",)),
    "REG":  (10, ("REG-",)),
    "BNK":  (20, ("BNK-",)),
    "LBR":  (10, ("LBR-",)),
    "BSEC": (15, ("BSEC-",)),
    "FX":   (10, ("FX-",)),
    "ESC":  (15, ("ESC-",)),
}

# ═══════════════════════════════════════════════════════════════════════
# P0 PRODUCTION GATE: Verified Rule IDs
# ═══════════════════════════════════════════════════════════════════════
# Only rules in this set contribute to the authoritative compliance score.
# Unverified rules still generate flags (for visibility) but their
# score_impact is excluded from _calculate_score() and _calculate_raw_score().
#
# Rationale: statutory citations for these 38 rules have undergone an
# internal source check against the Companies Act 1994 (Bangladesh) text.
# This is not independent legal approval or a complete amendment review.
# Rules not yet internally verified
# (AUD-*, SH-*, TR-002~006, ESC-003~005, TAX-*, LBR-*, BNK-*, FX-*,
# BSEC-*) require lawyer review before they can influence the score.
#
# No BLACK override is exempt from independent legal approval. A critical
# severity label cannot bypass the global release gate or the exact rule-ID
# allowlist.
# Candidate scoring allowlist copied from the main-branch internal source-check register.
# These 38 IDs have an internal statutory-source check only. This is NOT
# independent legal approval and must never be represented as such.
# The set allows deterministic scoring mechanics to be exercised in tests and
# diagnostic calculations, but no score, risk band, BLACK override, or rescue
# classification is released to users while LEGAL_SCORE_RELEASED is False.
# Exclusions (including AGM-005, AUD-*, TAX-*, LBR-*, BNK-*, FX-*, BSEC-*,
# disputed DEF-001 and unreviewed share-transfer/filing rules) remain provisional.
# The production allowlist is intentionally empty until each applicable rule
# has named, independent current-law approval in the signed approval register.
# Internal source triage or engine/seed parity is not legal approval.
VERIFIED_RULE_IDS: frozenset[str] = frozenset()

# Release remains disabled until the complete applicable rule corpus has named,
# independent current-law approval recorded in the signed, versioned register.
# Internal source checking is not independent counsel approval.
# Release remains disabled until the applicable corpus has named, independent
# current-law approval recorded in the signed, versioned legal approval register.
LEGAL_SCORE_RELEASED: bool = False
# Fail-closed release gate: internal source checking is not legal approval.
# Only after counsel approves current law, applicability, exceptions, evidence
# standards and effective dates may this flag be changed to True.

def legal_score_is_released() -> bool:
    """The global switch and a non-empty counsel-approved rule set are both required."""
    return LEGAL_SCORE_RELEASED is True and bool(VERIFIED_RULE_IDS)



REVENUE_TIER_MAP = {
    Severity.GREEN: RevenueTier.COMPLIANCE_PACKAGE,
    Severity.YELLOW: RevenueTier.COMPLIANCE_PACKAGE,
    Severity.RED: RevenueTier.STRUCTURED_REGULARIZATION,
    Severity.BLACK: RevenueTier.CORPORATE_RESCUE,

    Severity.NOT_EVALUATED: RevenueTier.COMPLIANCE_PACKAGE,
}

FOREIGN_WORK_PERMIT_THRESHOLD_USD = 50000
BIDA_ADVANTAGE_THRESHOLD_USD = 100000
# VAT registration and turnover-tax enlistment are separate regimes.
# Operative VAT Act as amended by VAT Amendment Act 2026 (Act 77/2026):
# registration threshold BDT 50 lakh; turnover-tax enlistment threshold BDT 30 lakh.
# Annual turnover alone does not establish rolling 12-month turnover, mandatory
# registration category, tax period or breach. Findings remain NOT_EVALUATED.
_VAT_REGISTRATION_THRESHOLD_BDT = 5000000
_VAT_TURNOVER_TAX_ENLISTMENT_THRESHOLD_BDT = 3000000


_COVERAGE_FIELDS: dict[str, float] = {
    "last_agm_date":            2.0,
    "last_audit_signed_date":   2.0,
    "last_return_filed_year":   2.0,
    "first_auditor_appointed":  1.0,
    "tin_obtained":             1.0,
    "current_director_count":   0.5,
    "member_count":             0.5,
}


def _input_coverage(company) -> float:
    """Weighted completeness of selected company-profile input fields.

    This is NOT the fraction of statutory rules evaluated or verified. It is
    an input-data completeness indicator only. Tri-state booleans (None=
    unknown, True/False=known) count as known when False; director count is
    counted only when independently RJSC-verified.
    """
    total_weight = sum(_COVERAGE_FIELDS.values())
    known_weight = 0.0
    for field_name, weight in _COVERAGE_FIELDS.items():
        value = getattr(company, field_name, None)
        if field_name == "current_director_count":
            # NLC's own director rows are not proof of the RJSC-verified count.
            if getattr(company, "directors_verified", False) is not True:
                continue
        if value is not None:
            known_weight += weight
    return min(1.0, known_weight / total_weight)


class NLCRuleEngine:
    _ESC_RULE_IDS: frozenset = frozenset({"ESC-001", "ESC-002", "ESC-003"})

    def __init__(self, today: date | None = None):
        self._default_today = today
        self.today = today or date.today()
        self._flags: List[ComplianceFlag] = []

    def evaluate(self, company: CompanyProfile, today: date | None = None) -> EngineOutput:
        """Evaluate a company profile. Thread-safety: create a fresh NLCRuleEngine() per call — self._flags is instance state."""
        self._flags = []
        self.today = today or self._default_today or date.today()

        self._run_incorporation_rules(company)
        self._run_auditor_rules(company)
        self._run_agm_rules(company)
        self._run_annual_return_rules(company)
        self._run_director_rules(company)
        self._run_shareholder_rules(company)
        self._run_transfer_rules(company)
        self._run_register_rules(company)
        self._run_office_rules(company)
        self._run_capital_rules(company)
        self._run_insolvency_rules(company)
        self._run_labour_rules(company)
        self._run_companies_act_extended_rules(company)
        self._run_bsec_rules(company)
        self._run_fx_rules(company)
        self._run_tax_rules(company)
        self._run_board_meeting_rules(company)
        self._run_accounts_rules(company)
        self._run_structural_change_rules(company)
        self._run_escalation_rules(company)

        # Coverage is calculated in _calculate_score via _input_coverage(company)

        stage = self._determine_lifecycle_stage(company)
        score = self._calculate_score(self._flags, company)
        rescue = self._generate_rescue_sequence(company, self._flags, score)

        fdi_active = company.has_foreign_shareholder or company.is_fdi_registered
        tax_active = not company.tin_obtained or not company.vat_registered

        return EngineOutput(
            company_id=company.company_id,
            evaluation_date=self.today,
            engine_version=RULE_ENGINE_VERSION,
            ilrmf_version=ILRMF_VERSION,
            flags=list(self._flags),
            score_breakdown=score,
            lifecycle_stage=stage,
            rescue_sequence=rescue,
            fdi_module_active=fdi_active,
            tax_module_active=tax_active,
        )

    # ───────────────────────────────────────────────────────────────────
    # MODULE 0: INCORPORATION
    # ───────────────────────────────────────────────────────────────────
    def _is_old_enough_to_assess(self, c: CompanyProfile) -> bool:
        """Issue 2 fix: returns True if company is >30 days old (enough to assess MoA filing).
        Returns False for fresh companies where False may just mean 'not yet assessed'."""
        if c.incorporation_date is None:
            return True  # If no incorporation date, allow the rule to fire
        days_old = (self.today - c.incorporation_date).days
        return days_old > 30

    def _run_incorporation_rules(self, c: CompanyProfile) -> None:
        # Issue 2 fix: only fire INC-001 if company is >30 days old.
        # P0 EVIDENCE SEMANTICS: MoA/AoA absence in NLC records is a DATA GAP,
        # not a confirmed legal breach. RJSC cannot register a company without
        # MoA/AoA (Section 23), so absence in NLC's database means the
        # documents haven't been uploaded/verified — not that they don't exist.
        # The correct state is NOT_EVALUATED, not RED.
        if not (
            c.moa_aoa_verified is True
            and bool(c.moa_aoa_evidence_ref)
            and c.moa_aoa_verified_at is not None
            and bool(c.moa_aoa_verified_by)
        ) and c.moa_aoa_filed is not True:
            self._add_flag(ComplianceFlag(
                rule_id="INC-001",
                flag_code="MOA_AOA_NOT_VERIFIED",
                severity=Severity.NOT_EVALUATED,
                score_impact=0,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description="MoA/AoA status has not been explicitly verified against RJSC or authenticated company records. Stored values alone are not proof.",
                statutory_basis="Section 23, Companies Act 1994 (Bangladesh)",
                state=RuleState.UNKNOWN,
                eval_state="UNKNOWN",
                detail={"verification_status": "not_verified"},
            ))
        elif c.moa_aoa_filed is None:
            self._add_flag(ComplianceFlag(
                rule_id="INC-001",
                flag_code="MOA_AOA_VERIFIED_STATUS_MISSING",
                severity=Severity.NOT_EVALUATED,
                score_impact=0,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description="A reviewer recorded a verification event but did not record whether the MoA/AoA was filed.",
                statutory_basis="Section 23, Companies Act 1994 (Bangladesh)",
                state=RuleState.UNKNOWN,
                eval_state="UNKNOWN",
                detail={"verification_status": "incomplete"},
            ))
        elif c.moa_aoa_filed is False and self._is_old_enough_to_assess(c):
            self._add_flag(ComplianceFlag(
                rule_id="INC-001",
                flag_code="MOA_AOA_CONFIRMED_MISSING",
                severity=Severity.RED,
                score_impact=15,
                revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
                description="MoA/AoA absence was explicitly verified against RJSC or authenticated company records. Confirm the underlying registry record and history.",
                statutory_basis="Section 23, Companies Act 1994 (Bangladesh)",
                detail={"verification_status": "confirmed_missing"},
            ))


        if c.company_type in ("PRIVATE_LIMITED", "PUBLIC_LIMITED") and c.directors_verified is True and bool(c.directors_verification_evidence_ref) and c.directors_verified_at is not None and bool(c.directors_verified_by) and c.current_director_count is not None:
            count = c.current_director_count
            if (c.company_type == "PRIVATE_LIMITED" and count == 2
                    and (c.subsidiary_status_verified is not True
                         or not c.subsidiary_status_evidence_ref
                         or c.subsidiary_status_verified_at is None
                         or not c.subsidiary_status_verified_by)):
                self._add_flag(ComplianceFlag(
                    rule_id="INC-003",
                    flag_code="DIRECTOR_MINIMUM_APPLICABILITY_UNKNOWN",
                    severity=Severity.NOT_EVALUATED,
                    score_impact=0,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description="Two directors are verified, but private-subsidiary status is unknown; Section 90(1) may require three.",
                    statutory_basis="Sections 90(1) and 90(2), Companies Act 1994 (Bangladesh)",
                    state=RuleState.UNKNOWN,
                    eval_state="UNKNOWN",
                    detail={"current_count": count, "subsidiary_status": "UNKNOWN"},
                ))
            else:
                required = 3 if (
                    c.company_type == "PUBLIC_LIMITED"
                    or (c.company_type == "PRIVATE_LIMITED" and c.is_private_subsidiary_of_public_company is True)
                ) else 2
                if count < required:
                    self._add_flag(ComplianceFlag(
                        rule_id="INC-003",
                        flag_code="MINIMUM_DIRECTORS_NOT_MET",
                        severity=Severity.BLACK,
                        score_impact=15,
                        is_black_override=True,
                        revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
                        description=f"RJSC-verified {c.company_type.lower().replace('_', ' ')} has {count} director(s); Section 90 requires at least {required}.",
                        statutory_basis="Sections 90(1) and 90(2), Companies Act 1994 (Bangladesh)",
                        detail={"current_count": count, "required": required,
                                "private_subsidiary_of_public_company": c.is_private_subsidiary_of_public_company},
                    ))
        if (c.company_type == "PRIVATE_LIMITED" and c.directors_verified
                and c.current_director_count is not None
                and c.current_director_count < 2):  # RULE-001: only fire when verified against RJSC
            self._add_flag(ComplianceFlag(
                rule_id="INC-003",
                flag_code="MINIMUM_DIRECTORS_NOT_MET",
                severity=Severity.BLACK,
                score_impact=15,
                is_black_override=True,
                revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
                description="Private company has insufficient directors. Section 90(2) requires minimum 2 directors.",
                statutory_basis="Sections 90(1) and 90(2), Companies Act 1994 (Bangladesh)",
                detail={"current_count": c.current_director_count, "required": 2}
            ))

        if c.paid_up_capital_bdt > c.authorized_capital_bdt:
            self._add_flag(ComplianceFlag(
                rule_id="INC-004",
                flag_code="PAID_UP_AUTHORIZED_CAPITAL_MISMATCH",
                severity=Severity.NOT_EVALUATED,
                score_impact=0,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description="Paid-up capital exceeds the recorded authorised capital. This is a data/legal review trigger, not an automatic finding that excess allotments are void. Verify the current capital register, special/ordinary resolutions, Form IV filing and RJSC record under Section 56.",
                statutory_basis="Section 56, Companies Act 1994 (Bangladesh) — applicability and consequences require lawyer review",
                state=RuleState.REQUIRES_LAWYER_JUDGMENT,
                eval_state="UNKNOWN",
                detail={"paid_up": c.paid_up_capital_bdt, "authorized": c.authorized_capital_bdt}
            ))

        if c.has_foreign_shareholder:
            if c.encashment_certificate_uploaded is False:
                self._add_flag(ComplianceFlag(
                    rule_id="INC-005",
                    flag_code="ENCASHMENT_CERTIFICATE_MISSING",
                    severity=Severity.NOT_EVALUATED,
                    score_impact=0,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description=("No AD-bank encashment-certificate record is present. This is an internal evidence-review signal only; "
                                 "it does not prove a breach. Verify the applicable GFET paragraph, current Bangladesh Bank circulars, "
                                 "foreign-currency-account retention rules and zone-specific exceptions."),
                    statutory_basis=("GFET-2018 Vol.1, Chapter 9, paragraph 2(A); FE Circular No.10 (21 June 2023); "
                                     "FEID Circular No.01 (27 January 2025) and subsequent applicable circulars"),
                    detail={
                        "foreign_pct": c.foreign_shareholding_pct,
                        "evidence_status": "NOT_VERIFIED",
                        "breach_determined": False,
                    },
                    state=RuleState.UNKNOWN,
                    eval_state="UNKNOWN",
                    conditional_applies=True,
                ))
            if (c.remittance_amount_usd is not None
                    and c.remittance_amount_usd < FOREIGN_WORK_PERMIT_THRESHOLD_USD
                    and c.bida_registered):
                self._add_flag(ComplianceFlag(
                    rule_id="INC-006",
                    flag_code="REMITTANCE_BELOW_WORK_PERMIT_THRESHOLD",
                    severity=Severity.NOT_EVALUATED,
                    score_impact=0,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description=("Reported initial-establishment remittance is below the USD 50,000 reference amount. "
                                 "This is a screening prompt only, not a statutory breach or automatic work-permit refusal. "
                                 "Verify the operative BIDA 2023 work-permit guideline, applicant category, date, exceptions and evidence."),
                    statutory_basis=("BIDA Guidelines for permission to establish foreign commercial offices and issue work permits in Bangladesh (2023); "
                                     "exact operative clause/version and current amendments require verification"),
                    detail={
                        "remittance_usd": c.remittance_amount_usd,
                        "threshold": FOREIGN_WORK_PERMIT_THRESHOLD_USD,
                        "guideline_applicability_verified": False,
                        "breach_determined": False,
                    },
                    state=RuleState.UNKNOWN,
                    eval_state="UNKNOWN",
                    conditional_applies=True,
                ))

        # MEM-001: Company operating with fewer than minimum members (Section 222)
        member_count = c.member_count or 0
        if member_count > 0:
            min_members = 2 if c.company_type == "PRIVATE_LIMITED" else 7
            if member_count < min_members:
                self._add_flag(ComplianceFlag(
                    rule_id="MEM-001",
                    flag_code="BELOW_MINIMUM_MEMBERS",
                    severity=Severity.RED,
                    score_impact=10,
                    revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
                    description=f"Company has {member_count} members, below minimum {min_members}. Section 222: members personally liable.",
                    statutory_basis="Section 222, Companies Act 1994 (Bangladesh)",
                    detail={"member_count": member_count, "minimum": min_members}
                ))

        # INC-007: Section 150 is not universal. It does not apply to
        # private companies or to companies that do not issue a prospectus
        # inviting public subscription (s.150(6)). Require verified scope.
        if (
            c.company_type == "PUBLIC_LIMITED"
            and c.section150_prospectus_issued is True
            and c.section150_applicability_verified
            and bool(c.section150_applicability_evidence_ref)
            and c.business_commencement_declaration_verified
            and bool(c.business_commencement_declaration_evidence_ref)
            and c.business_commencement_declaration_filed is False
        ):
            self._add_flag(ComplianceFlag(
                rule_id="INC-007",
                flag_code="SECTION_150_COMMENCEMENT_DECLARATION_REQUIRES_REVIEW",
                severity=Severity.NOT_EVALUATED,
                score_impact=0,
                revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
                description=(
                    "Internal review signal only: verified Section 150 applicability "
                    "and a reported missing commencement declaration require counsel "
                    "review of every statutory condition, exemption and filing record. "
                    "No legal breach is determined."
                ),
                statutory_basis="Section 150(1) and (6), Companies Act 1994 (Bangladesh)",
                state=RuleState.REQUIRES_LAWYER_JUDGMENT,
                eval_state="UNKNOWN",
                detail={"applicability_evidence_ref": c.section150_applicability_evidence_ref},
            ))

        if c.trade_license_obtained is False:
            self._add_flag(ComplianceFlag(
                rule_id="TL-001",
                flag_code="TRADE_LICENSE_NOT_OBTAINED",
                severity=Severity.YELLOW,
                score_impact=5,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description="Trade License not obtained from City Corporation/Municipality.",
                statutory_basis="Local Government (City Corporation) Act 2009 / Local Government (Paurashava) Act 2009",
                detail={"trade_license": False},
            ))
        elif c.trade_license_expiry and c.trade_license_expiry < self.today:
            days_expired = (self.today - c.trade_license_expiry).days
            sev = Severity.RED if days_expired > 90 else Severity.YELLOW
            imp = 10 if days_expired > 90 else 5
            self._add_flag(ComplianceFlag(
                rule_id="TL-002",
                flag_code="TRADE_LICENSE_EXPIRED",
                severity=sev,
                score_impact=imp,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description=f"Trade License expired {days_expired} days ago. Must renew by 31 March annually.",
                statutory_basis="Local Government (City Corporation) Act 2009 / Local Government (Paurashava) Act 2009",
                detail={"expired_days": days_expired},
            ))

    # ───────────────────────────────────────────────────────────────────
    # MODULE 1: AUDITOR
    # ───────────────────────────────────────────────────────────────────
    @staticmethod
    def _add_months(d: date, months: int) -> date:
        """Add calendar months, clamping to the last valid day of the target month."""
        import calendar as _cal
        month_index = d.year * 12 + d.month - 1 + months
        target_year, zero_month = divmod(month_index, 12)
        target_month = zero_month + 1
        last_day = _cal.monthrange(target_year, target_month)[1]
        return date(target_year, target_month, min(d.day, last_day))

    @staticmethod
    def _add_one_month(d: date) -> date:
        """Section 210(6): one calendar month, not a fixed 30-day period."""
        return NLCRuleEngine._add_months(d, 1)

    def _run_auditor_rules(self, c: CompanyProfile) -> None:
        # P0 LEGAL FIX: Section 210(6) requires first auditor appointment
        # "within one month" of registration. "One month" = CALENDAR MONTH,
        # not 30 days. Using 30 days is legally incorrect for months with
        # 28/29/31 days.
        reg_date = c.incorporation_date
        appointment_verified = (
            c.first_auditor_appointment_verified is True
            and bool(c.first_auditor_appointment_evidence_ref)
            and c.first_auditor_appointment_verified_at is not None
            and bool(c.first_auditor_appointment_verified_by)
        )

        def add_aud001_unknown(code: str, description: str) -> None:
            self._add_flag(ComplianceFlag(
                rule_id="AUD-001",
                flag_code=code,
                severity=Severity.NOT_EVALUATED,
                score_impact=0,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description=description,
                statutory_basis="Section 210(6), Companies Act 1994 (Bangladesh)",
                state=RuleState.UNKNOWN,
                eval_state="UNKNOWN",
            ))

        if not appointment_verified or reg_date is None:
            add_aud001_unknown(
                "FIRST_AUDITOR_EVIDENCE_UNVERIFIED",
                "First-auditor appointment status or incorporation date lacks verified source evidence; no statutory default is inferred.",
            )
        else:
            deadline = self._add_one_month(reg_date)

            def add_aud001_flag(flag_code: str, delay: int, appointment_date: date | None = None) -> None:
                self._add_flag(ComplianceFlag(
                    rule_id="AUD-001",
                    flag_code=flag_code,
                    severity=Severity.YELLOW,
                    score_impact=10,
                    revenue_tier=(
                        RevenueTier.COMPLIANCE_PACKAGE
                        if delay <= 365
                        else RevenueTier.STRUCTURED_REGULARIZATION
                    ),
                    description=(
                        f"First auditor was not appointed within one calendar month "
                        f"of registration (Section 210(6)). Deadline: {deadline.isoformat()}. "
                        f"Overdue by {delay} days."
                    ),
                    statutory_basis="Section 210(6), Companies Act 1994 (Bangladesh)",
                    detail={
                        "delay_days": delay,
                        "registration_date": str(reg_date),
                        "deadline": str(deadline),
                        "appointment_date": str(appointment_date) if appointment_date else None,
                        "calculation_method": "calendar_month",
                    },
                ))

            if c.first_auditor_appointed is None:
                add_aud001_unknown("FIRST_AUDITOR_STATUS_UNKNOWN", "First auditor appointment status is missing.")
            elif c.first_auditor_appointment_date is not None:
                if c.first_auditor_appointed is False:
                    self._add_flag(ComplianceFlag(
                        rule_id="AUD-001",
                        flag_code="FIRST_AUDITOR_EVIDENCE_CONTRADICTORY",
                        severity=Severity.NOT_EVALUATED,
                        score_impact=0,
                        revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                        description="A first-auditor appointment date is recorded but appointment status is marked false. Reconcile the source evidence.",
                        statutory_basis="Section 210(6), Companies Act 1994 (Bangladesh)",
                        state=RuleState.CONTRADICTORY,
                        eval_state="UNKNOWN",
                        detail={"appointment_date": str(c.first_auditor_appointment_date), "registration_date": str(reg_date)},
                    ))
                elif c.first_auditor_appointment_date > deadline:
                    delay = (c.first_auditor_appointment_date - deadline).days
                    add_aud001_flag("FIRST_AUDITOR_APPOINTED_LATE", delay, c.first_auditor_appointment_date)
            elif c.first_auditor_appointed is False and self.today > deadline:
                delay = (self.today - deadline).days
                add_aud001_flag("FIRST_AUDITOR_NOT_APPOINTED", delay)
            elif c.first_auditor_appointed is True:
                add_aud001_unknown(
                    "FIRST_AUDITOR_APPOINTMENT_DATE_UNKNOWN",
                    "First auditor is recorded as appointed, but the appointment date is missing; timeliness cannot be verified.",
                )

        if c.agm_scheduled_date and c.audit_complete is False:
            audit_status_verified = (
                c.audit_completion_verified is True
                and bool(c.audit_completion_evidence_ref)
                and c.audit_completion_verified_at is not None
                and bool(c.audit_completion_verified_by)
            )
            warning = c.agm_scheduled_date - timedelta(days=AGM_NOTICE_MINIMUM_DAYS)
            if self.today >= warning:
                days_to = (c.agm_scheduled_date - self.today).days
                if not audit_status_verified:
                    self._add_flag(ComplianceFlag(
                        rule_id="AUD-002",
                        flag_code="AUDIT_COMPLETION_STATUS_UNVERIFIED",
                        severity=Severity.NOT_EVALUATED,
                        score_impact=0,
                        revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                        description="Audit completion is recorded as false but lacks reviewer, timestamp and evidence provenance.",
                        statutory_basis="Section 183, Companies Act 1994 (Bangladesh)",
                        state=RuleState.UNKNOWN,
                        eval_state="UNKNOWN",
                    ))
                else:
                    severity = Severity.RED if days_to < 14 else Severity.YELLOW
                    self._add_flag(ComplianceFlag(
                        rule_id="AUD-002",
                        flag_code="AUDIT_MISSING_PRE_AGM",
                        severity=severity,
                        score_impact=12,
                        revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                        description=f"Verified audit completion is absent. AGM in {days_to} days. Section 183 requires accounts to be laid before the AGM.",
                        statutory_basis="Section 183, Companies Act 1994 (Bangladesh)",
                        detail={"days_to_agm": days_to}
                    ))

        if c.agm_held_this_cycle and c.audit_complete is False:
            audit_status_verified = (
                c.audit_completion_verified is True
                and bool(c.audit_completion_evidence_ref)
                and c.audit_completion_verified_at is not None
                and bool(c.audit_completion_verified_by)
            )
            if not audit_status_verified:
                self._add_flag(ComplianceFlag(
                    rule_id="AUD-003",
                    flag_code="AUDIT_COMPLETION_STATUS_UNVERIFIED",
                    severity=Severity.NOT_EVALUATED,
                    score_impact=0,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description="AGM record indicates an incomplete audit, but the audit status lacks reviewer, timestamp and evidence provenance.",
                    statutory_basis="Sections 183 and 210, Companies Act 1994 (Bangladesh)",
                    state=RuleState.UNKNOWN,
                    eval_state="UNKNOWN",
                ))
            else:
                self._add_flag(ComplianceFlag(
                    rule_id="AUD-003",
                    flag_code="AGM_HELD_WITHOUT_COMPLETED_AUDIT",
                    severity=Severity.RED,
                    score_impact=0,
                    revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
                    description=(
                        "Verified audit completion is absent for an AGM. Section 183 governs "
                        "accounts laid before the AGM; a lawyer must assess the actual accounts, "
                        "auditor appointment and applicable exceptions before determining consequences."
                    ),
                    statutory_basis="Sections 183 and 210, Companies Act 1994 (Bangladesh)",
                    detail={"legal_review_required": True, "override_to_black": False},
                    state=RuleState.REQUIRES_LAWYER_JUDGMENT,
                    eval_state="UNKNOWN",
                ))

        if c.agm_held_this_cycle and c.auditor_reappointed_at_agm is None:
            self._add_flag(ComplianceFlag(
                rule_id="AUD-005",
                flag_code="SUBSEQUENT_AUDITOR_STATUS_UNKNOWN",
                severity=Severity.NOT_EVALUATED,
                score_impact=0,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description="No verified record establishes whether the retiring auditor was reappointed or a statutory exception applied. This is an evidence-status finding, not a 120-day statutory deadline.",
                statutory_basis="Section 210(3), Companies Act 1994 (Bangladesh)",
                state=RuleState.UNKNOWN,
                eval_state="UNKNOWN",
            ))

        if (c.agm_held_this_cycle and c.auditor_reappointed_at_agm is False
                and c.auditor_reappointment_verified is True
                and bool(c.auditor_reappointment_evidence_ref)):
            self._add_flag(ComplianceFlag(
                rule_id="AUD-004",
                flag_code="AUDITOR_NOT_REAPPOINTED",
                severity=Severity.NOT_EVALUATED,
                score_impact=0,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description="Auditor reappointment is recorded as declined. Check the statutory exceptions and notice requirements under Section 210(3) before determining non-compliance.",
                statutory_basis="Section 210(3), Companies Act 1994 (Bangladesh)",
                state=RuleState.REQUIRES_LAWYER_JUDGMENT,
                eval_state="UNKNOWN",
            ))

    # ───────────────────────────────────────────────────────────────────
    # MODULE 2: AGM
    # ───────────────────────────────────────────────────────────────────
    def _agm_history_is_verified(self, c: CompanyProfile) -> bool:
        return (
            c.agm_history_verified is True
            and bool(c.agm_history_evidence_ref)
            and c.agm_history_verified_at is not None
            and bool(c.agm_history_verified_by)
        )

    def _subsequent_agm_deadline_components(
        self, c: CompanyProfile
    ) -> tuple[date, date, date, str] | None:
        if not self._agm_history_is_verified(c) or c.last_agm_date is None:
            return None

        interval_deadline = self._add_months(c.last_agm_date, 15)
        first_agm_in_incorporation_year = (
            c.agm_count == 1
            and c.incorporation_date is not None
            and c.last_agm_date.year == c.incorporation_date.year
            and c.last_agm_date <= self._add_months(c.incorporation_date, 18)
        )
        if first_agm_in_incorporation_year and c.incorporation_date is not None:
            calendar_year_deadline = date(c.incorporation_date.year + 2, 12, 31)
            # The first-AGM proviso removes the need for another meeting in
            # the incorporation year or the following year. If the 15-month
            # date falls in that exempt following year, defer the calendar
            # obligation to the end of the next year; otherwise the 15-month
            # interval remains the earlier controlling deadline.
            if interval_deadline.year <= c.incorporation_date.year + 1:
                base_deadline = calendar_year_deadline
                basis = "FIRST_AGM_PROVISO"
            else:
                base_deadline = min(interval_deadline, calendar_year_deadline)
                basis = (
                    "15_MONTH_INTERVAL"
                    if interval_deadline <= calendar_year_deadline
                    else "CALENDAR_YEAR"
                )
        else:
            calendar_year_deadline = date(c.last_agm_date.year + 1, 12, 31)
            base_deadline = min(interval_deadline, calendar_year_deadline)
            basis = (
                "15_MONTH_INTERVAL"
                if interval_deadline <= calendar_year_deadline
                else "CALENDAR_YEAR"
            )
        return interval_deadline, calendar_year_deadline, base_deadline, basis

    def _subsequent_agm_deadline(self, c: CompanyProfile) -> date | None:
        components = self._subsequent_agm_deadline_components(c)
        if components is None:
            return None
        _, calendar_year_deadline, base_deadline, _ = components

        if c.agm_extension_granted_until is None:
            return base_deadline
        extension_verified = (
            c.agm_extension_verified is True
            and bool(c.agm_extension_evidence_ref)
            and c.agm_extension_verified_at is not None
            and bool(c.agm_extension_verified_by)
        )
        if not extension_verified or c.agm_extension_application_date is None:
            return None
        application_days_after_deadline = (
            c.agm_extension_application_date - base_deadline
        ).days
        if application_days_after_deadline < 0 or application_days_after_deadline > 30:
            return None
        statutory_limit = min(
            base_deadline + timedelta(days=90),
            calendar_year_deadline,
        )
        if c.agm_extension_granted_until < base_deadline:
            return base_deadline
        if c.agm_extension_granted_until > statutory_limit:
            return None
        return c.agm_extension_granted_until

    def _run_agm_rules(self, c: CompanyProfile) -> None:
        # Section 81 deadlines depend on a complete, verified AGM history.
        # Missing history is an explicit UNKNOWN review state, not an assumed
        # absence of meetings and not a deadline breach.
        if not self._agm_history_is_verified(c):
            self._add_flag(ComplianceFlag(
                rule_id="AGM-001",
                flag_code="AGM_HISTORY_REQUIRES_VERIFICATION",
                severity=Severity.NOT_EVALUATED,
                score_impact=0,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description="AGM history has not been independently verified; no first- or subsequent-AGM default is inferred.",
                statutory_basis="Section 81(1), Companies Act 1994 (Bangladesh)",
                detail={"agm_count": c.agm_count, "last_agm_date": str(c.last_agm_date) if c.last_agm_date else None},
                state=RuleState.UNKNOWN,
                eval_state="UNKNOWN",
            ))
        if self._agm_history_is_verified(c):
            if c.agm_count is None:
                self._add_flag(ComplianceFlag(
                    rule_id="AGM-001", flag_code="AGM_COUNT_UNKNOWN",
                    severity=Severity.NOT_EVALUATED, score_impact=0,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description="AGM history is marked verified but the AGM count is missing.",
                    statutory_basis="Section 81(1), Companies Act 1994 (Bangladesh)",
                    state=RuleState.UNKNOWN, eval_state="UNKNOWN",
                ))
            elif c.agm_count == 0:
                if c.incorporation_date is None:
                    self._add_flag(ComplianceFlag(
                        rule_id="AGM-001", flag_code="INCORPORATION_DATE_UNKNOWN",
                        severity=Severity.NOT_EVALUATED, score_impact=0,
                        revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                        description="First-AGM deadline cannot be calculated without a verified incorporation date.",
                        statutory_basis="Section 81(1), Companies Act 1994 (Bangladesh)",
                        state=RuleState.UNKNOWN, eval_state="UNKNOWN",
                    ))
                else:
                    deadline = self._add_months(c.incorporation_date, 18)
                    if self.today > deadline:
                        delay = (self.today - deadline).days
                        severity = Severity.BLACK if delay > 365 else Severity.RED
                        self._add_flag(ComplianceFlag(
                            rule_id="AGM-001", flag_code="FIRST_AGM_DEFAULT",
                            severity=severity,
                            score_impact=self._graduated_agm_deduction(delay),
                            revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
                            description=f"First AGM not held within 18 calendar months. Section 81(1): overdue by {delay} days.",
                            statutory_basis="Section 81(1), Companies Act 1994 (Bangladesh)",
                            detail={
                                "delay_days": delay,
                                "deadline": deadline.isoformat(),
                                "deadline_basis": "18_CALENDAR_MONTHS_FROM_INCORPORATION",
                                "statutory_period_months": 18,
                                "incorporation_date": c.incorporation_date.isoformat(),
                            },
                        ))
            elif c.agm_count > 0:
                if c.last_agm_date is None:
                    self._add_flag(ComplianceFlag(
                        rule_id="AGM-002", flag_code="LAST_AGM_DATE_UNVERIFIED",
                        severity=Severity.NOT_EVALUATED, score_impact=0,
                        revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                        description="AGM history is marked verified but the last AGM date is missing.",
                        statutory_basis="Section 81(1), Companies Act 1994 (Bangladesh)",
                        state=RuleState.UNKNOWN, eval_state="UNKNOWN",
                    ))
                elif c.agm_held_this_cycle is None:
                    self._add_flag(ComplianceFlag(
                        rule_id="AGM-002",
                        flag_code="CURRENT_YEAR_AGM_STATUS_UNKNOWN",
                        severity=Severity.NOT_EVALUATED,
                        score_impact=0,
                        revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                        description="Whether an AGM was held in the current calendar year is not verified; no subsequent-AGM default is inferred.",
                        statutory_basis="Section 81(1), Companies Act 1994 (Bangladesh)",
                        state=RuleState.UNKNOWN,
                        eval_state="UNKNOWN",
                    ))
                elif c.agm_held_this_cycle is False:
                    agm_deadline = self._subsequent_agm_deadline(c)
                    deadline_components = self._subsequent_agm_deadline_components(c)
                    if deadline_components is None:
                        interval_deadline = calendar_year_deadline = base_deadline = None
                        deadline_basis = "UNKNOWN"
                    else:
                        (
                            interval_deadline,
                            calendar_year_deadline,
                            base_deadline,
                            deadline_basis,
                        ) = deadline_components
                    if agm_deadline is None:
                        self._add_flag(ComplianceFlag(
                            rule_id="AGM-002", flag_code="AGM_EXTENSION_REQUIRES_REVIEW",
                            severity=Severity.NOT_EVALUATED, score_impact=0,
                            revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                            description="A recorded AGM extension is not supported by verified, timely application and grant evidence. No automatic default determination is made.",
                            statutory_basis="Section 81(1), Companies Act 1994 (Bangladesh)",
                            state=RuleState.REQUIRES_LAWYER_JUDGMENT, eval_state="UNKNOWN",
                            detail={"extension_until": str(c.agm_extension_granted_until)},
                        ))
                    elif self.today > agm_deadline:
                        delay = (self.today - agm_deadline).days
                        severity = Severity.BLACK if delay > 365 else Severity.RED
                        basis = (
                            "VALIDATED_EXTENSION"
                            if (
                                c.agm_extension_granted_until is not None
                                and c.agm_extension_granted_until == agm_deadline
                                and base_deadline is not None
                                and agm_deadline is not None
                                and agm_deadline > base_deadline
                            )
                            else deadline_basis
                        )
                        self._add_flag(ComplianceFlag(
                            rule_id="AGM-002", flag_code="SUBSEQUENT_AGM_DEFAULT",
                            severity=severity,
                            score_impact=self._graduated_agm_deduction(delay),
                            revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
                            description=f"AGM overdue by {delay} days. Section 81(1): deadline determined by {basis}.",
                            statutory_basis="Section 81(1), Companies Act 1994 (Bangladesh)",
                            detail={
                                "delay_days": delay,
                                "deadline": str(agm_deadline),
                                "basis": basis,
                                "interval_deadline": str(interval_deadline) if interval_deadline else None,
                                "calendar_year_deadline": (
                                    calendar_year_deadline.isoformat() if calendar_year_deadline else None
                                ),
                                "statutory_base_deadline": (
                                    base_deadline.isoformat() if base_deadline else None
                                ),
                                "extension_application_date": (
                                    c.agm_extension_application_date.isoformat()
                                    if c.agm_extension_application_date else None
                                ),
                                "extension_granted_until": (
                                    c.agm_extension_granted_until.isoformat()
                                    if c.agm_extension_granted_until else None
                                ),
                                "extension_evidence_ref": c.agm_extension_evidence_ref,
                                "extension_verified": c.agm_extension_verified is True,
                                "extension_statutory_limit": min(
                                    base_deadline + timedelta(days=90),
                                    calendar_year_deadline,
                                ).isoformat() if base_deadline and calendar_year_deadline else None,
                            },
                        ))
        # Unverified AGM history is not converted into a deadline breach.
        # Notice, quorum and minutes checks below use their own evidence requirements.

        consent_verified = (
            c.short_notice_consent_verified is True
            and bool(c.short_notice_consent_evidence_ref)
        )
        if c.agm_scheduled_date and c.notice_sent_date:
            notice_days = (c.agm_scheduled_date - c.notice_sent_date).days
            if notice_days < AGM_NOTICE_MINIMUM_DAYS:
                if not consent_verified:
                    self._add_flag(ComplianceFlag(
                        rule_id="AGM-003",
                        flag_code="AGM_SHORT_NOTICE_CONSENT_UNVERIFIED",
                        severity=Severity.NOT_EVALUATED,
                        score_impact=0,
                        revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                        description="AGM notice was shorter than 21 days, but written consent from all members entitled to attend and vote has not been verified.",
                        statutory_basis="Section 85(1)(a), Companies Act 1994 (Bangladesh)",
                        state=RuleState.UNKNOWN,
                        eval_state="UNKNOWN",
                        detail={"notice_days": notice_days},
                    ))
                elif c.short_notice_consent_obtained is False:
                    self._add_flag(ComplianceFlag(
                        rule_id="AGM-003",
                        flag_code="AGM_NOTICE_DEFECTIVE",
                        severity=Severity.YELLOW,
                        score_impact=5,
                        revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                        description=f"AGM notice issued with {notice_days} days and verified absence of written short-notice consent.",
                        statutory_basis="Section 85(1)(a), Companies Act 1994 (Bangladesh)",
                        detail={"notice_days": notice_days, "short_notice_consent": False},
                    ))

        if c.agm_scheduled_date and c.notice_sent_date is None:
            warn = c.agm_scheduled_date - timedelta(days=AGM_NOTICE_MINIMUM_DAYS)
            if self.today >= warn:
                days_rem = (c.agm_scheduled_date - self.today).days
                if not consent_verified:
                    self._add_flag(ComplianceFlag(
                        rule_id="AGM-004",
                        flag_code="AGM_NOTICE_OR_CONSENT_UNVERIFIED",
                        severity=Severity.NOT_EVALUATED,
                        score_impact=0,
                        revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                        description="No notice date is recorded and any written short-notice consent has not been verified.",
                        statutory_basis="Section 85(1)(a), Companies Act 1994 (Bangladesh)",
                        state=RuleState.UNKNOWN,
                        eval_state="UNKNOWN",
                        detail={"days_to_agm": days_rem},
                    ))
                elif c.short_notice_consent_obtained is False:
                    self._add_flag(ComplianceFlag(
                        rule_id="AGM-004",
                        flag_code="AGM_NOTICE_NOT_ISSUED",
                        severity=Severity.RED,
                        score_impact=15,
                        revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                        description=f"AGM notice not issued and written short-notice consent is verified absent. {days_rem} days to AGM.",
                        statutory_basis="Section 85(1)(a), Companies Act 1994 (Bangladesh)",
                        detail={"days_to_agm": days_rem, "short_notice_consent": False},
                    ))

        attendance_verified = (
            c.agm_attendance_verified is True
            and bool(c.agm_attendance_evidence_ref)
        )
        quorum_basis_verified = (
            c.agm_quorum_basis_verified is True
            and bool(c.agm_quorum_evidence_ref)
            and c.agm_quorum_required is not None
        )
        if c.agm_held_this_cycle and attendance_verified and not quorum_basis_verified:
            self._add_flag(ComplianceFlag(
                rule_id="AGM-005",
                flag_code="AGM_QUORUM_BASIS_UNKNOWN",
                severity=Severity.NOT_EVALUATED,
                score_impact=0,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description="Attendance is verified, but the applicable quorum has not been verified against the Articles and Section 85(2)(b).",
                statutory_basis="Section 85(2)(b), Companies Act 1994 (Bangladesh), read with the Articles",
                state=RuleState.UNKNOWN,
                eval_state="UNKNOWN",
            ))
        if (
            c.agm_held_this_cycle
            and c.members_present_at_agm is not None
            and attendance_verified
            and quorum_basis_verified
            and c.agm_quorum_required is not None
            and c.members_present_at_agm < c.agm_quorum_required
        ):
            self._add_flag(ComplianceFlag(
                rule_id="AGM-005",
                flag_code="AGM_QUORUM_DEFECTIVE",
                severity=Severity.RED,
                score_impact=15,
                revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
                description=f"Recorded attendance ({c.members_present_at_agm}) is below verified quorum ({c.agm_quorum_required}).",
                statutory_basis="Section 85(2)(b), Companies Act 1994 (Bangladesh), read with the Articles",
                detail={"present": c.members_present_at_agm, "required": c.agm_quorum_required, "member_count": c.member_count},
            ))
        if c.agm_held_this_cycle and c.agm_minutes_prepared is False:
            self._add_flag(ComplianceFlag(
                rule_id="AGM-006",
                flag_code="AGM_MINUTES_STATUS_UNVERIFIED",
                severity=Severity.NOT_EVALUATED,
                score_impact=0,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description="The record indicates minutes may be absent, but the minute book and contemporaneous records have not been independently verified.",
                statutory_basis="Section 89, Companies Act 1994 (Bangladesh)",
                state=RuleState.UNKNOWN,
                eval_state="UNKNOWN",
            ))

    # ───────────────────────────────────────────────────────────────────
    # MODULE 3: ANNUAL RETURNS
    # ───────────────────────────────────────────────────────────────────
    def _run_annual_return_rules(self, c: CompanyProfile) -> None:
        if c.last_agm_date and c.annual_return_filed is False:
            deadline = c.last_agm_date + timedelta(days=ANNUAL_RETURN_DEADLINE_DAYS)
            if self.today > deadline:
                delay = (self.today - deadline).days
                severity = Severity.RED if delay > 90 else Severity.YELLOW
                self._add_flag(ComplianceFlag(
                    rule_id="AR-001",
                    flag_code="ANNUAL_RETURN_DEFAULT",
                    severity=severity,
                    score_impact=self._graduated_ar_deduction(delay),
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description=f"Schedule X (Annual Return) not filed within 21 days of AGM. Overdue by {delay} days.",
                    statutory_basis="Section 36 (Schedule X), Companies Act 1994 (Bangladesh)",
                    detail={"delay_days": delay}
                ))

        if c.unfiled_returns_count is not None and c.unfiled_returns_count >= 2:
            self._add_flag(ComplianceFlag(
                rule_id="AR-002",
                flag_code="ANNUAL_RETURN_BACKLOG_REVIEW_REQUIRED",
                severity=Severity.NOT_EVALUATED,
                score_impact=0,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description=(
                    f"{c.unfiled_returns_count} annual returns are reported outstanding. "
                    "This is an internal review signal only; backlog alone does not "
                    "establish Registrar strike-off, dissolution or director liability."
                ),
                statutory_basis=(
                    "Section 36 and Schedule X (annual-return duty); Section 346 "
                    "governs a separate Registrar strike-off procedure."
                ),
                state=RuleState.REQUIRES_LAWYER_JUDGMENT,
                eval_state="UNKNOWN",
                is_black_override=False,
                escalation_pending=True,
                detail={"unfiled_count": c.unfiled_returns_count},
            ))

        if c.unfiled_returns_count is not None and c.unfiled_returns_count >= 3:
            self._add_flag(ComplianceFlag(
                rule_id="AR-003",
                flag_code="ANNUAL_RETURN_BACKLOG_REVIEW_REQUIRED",
                severity=Severity.NOT_EVALUATED,
                score_impact=0,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description=(
                    f"{c.unfiled_returns_count} annual returns are reported outstanding. "
                    "A three-year backlog does not itself prove that RJSC has begun "
                    "Section 346 proceedings, that the company is dissolved, or that "
                    "a director has incurred a separate penalty."
                ),
                statutory_basis=(
                    "Section 36 and Schedule X (annual-return duty); Section 346 "
                    "requires separate Registrar grounds and statutory notice steps."
                ),
                state=RuleState.REQUIRES_LAWYER_JUDGMENT,
                eval_state="UNKNOWN",
                is_black_override=False,
                escalation_pending=True,
                detail={"unfiled_count": c.unfiled_returns_count},
            ))

        if c.annual_return_filed and c.annual_return_content_complete is False:
            missing = []
            if c.schedule_x_attached is False:
                missing.append("Schedule X")
            if c.balance_sheet_attached is False:
                missing.append("Balance Sheet")
            if c.profit_loss_attached is False:
                missing.append("P&L Account")
            if c.directors_list_attached is False:
                missing.append("Directors List")
            if c.shareholders_list_attached is False:
                missing.append("Shareholders List")
            self._add_flag(ComplianceFlag(
                rule_id="AR-004",
                flag_code="ANNUAL_RETURN_INCOMPLETE",
                severity=Severity.YELLOW,
                score_impact=8,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description=f"Annual Return incomplete. Missing: {', '.join(missing)}. Section 36 + Schedule X require complete disclosure.",
                statutory_basis="Section 36, Schedule X, Companies Act 1994 (Bangladesh)",
                detail={"missing": missing}
            ))

    # ───────────────────────────────────────────────────────────────────
    # MODULE 4: DIRECTORS
    # ───────────────────────────────────────────────────────────────────
    def _run_director_rules(self, c: CompanyProfile) -> None:
        for change in c.director_changes:
            delay = (self.today - change.event_date).days

            if (
                change.form_filed is None
                or not change.form_filed_verified
                or not change.form_filed_evidence_ref
            ):
                self._add_flag(ComplianceFlag(
                    rule_id="DIR-001",
                    flag_code="DIRECTOR_FORM_XII_STATUS_UNKNOWN",
                    severity=Severity.NOT_EVALUATED,
                    score_impact=0,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description=(
                        "Director Form XII filing status is unknown. Obtain the "
                        "authenticated RJSC filing record or registry response; "
                        "non-production is not proof of non-filing."
                    ),
                    statutory_basis="Section 115(2), Companies Act 1994 (Bangladesh)",
                    detail={"director_id": change.director_id},
                    state=RuleState.UNKNOWN,
                    eval_state="UNKNOWN",
                ))

            if (
                change.form_filed is False
                and change.form_filed_verified
                and bool(change.form_filed_evidence_ref)
                and delay > DIRECTOR_FILING_DEADLINE_DAYS
            ):
                if change.event_type == "appointment":
                    rule_id = "DIR-001"
                    flag_code = "FORM_XII_APPOINTMENT_REQUIRES_REVIEW"
                elif change.event_type in ("resignation", "removal", "death"):
                    rule_id = "DIR-002"
                    flag_code = "FORM_XII_CESSATION_REQUIRES_REVIEW"
                else:
                    rule_id = "DIR-001"
                    flag_code = "FORM_XII_CHANGE_REQUIRES_REVIEW"

                self._add_flag(ComplianceFlag(
                    rule_id=rule_id,
                    flag_code=flag_code,
                    severity=Severity.NOT_EVALUATED,
                    score_impact=0,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description=(
                        f"Reported Form XII filing is not verified {delay} days after "
                        f"the {change.event_type} event. Section 115(2) provides a "
                        "14-day filing period; verify the event, liable filer, actual "
                        "RJSC record, extension/correction and current law before any "
                        "default or penalty conclusion."
                    ),
                    statutory_basis="Section 115(2), Companies Act 1994 (Bangladesh)",
                    detail={"director_id": change.director_id, "delay": delay, "type": change.event_type},
                    state=RuleState.REQUIRES_LAWYER_JUDGMENT,
                    eval_state="UNKNOWN",
                ))

                # >365 days is an NLC internal escalation threshold, not a
                # separate statutory deadline or a continuing-offence rule.
                if delay > 365:
                    self._add_flag(ComplianceFlag(
                        rule_id="DIR-003",
                        flag_code="DIRECTOR_FILING_LONG_DELAY_INTERNAL_ESCALATION",
                        severity=Severity.NOT_EVALUATED,
                        score_impact=0,
                        revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
                        description=(
                            f"NLC internal follow-up threshold exceeded ({delay} days). "
                            "This is a commercial escalation policy, not an additional "
                            "statutory offence or daily penalty. The underlying filing "
                            "duty and any consequence require separate legal review."
                        ),
                        statutory_basis="Section 115(2), Companies Act 1994 (Bangladesh); 365-day threshold is NLC policy only",
                        detail={"director_id": change.director_id, "delay": delay, "policy_threshold_days": 365},
                        state=RuleState.REQUIRES_LAWYER_JUDGMENT,
                        eval_state="UNKNOWN",
                    ))

                if change.event_type in ("resignation", "removal", "death"):
                    self._add_flag(ComplianceFlag(
                        rule_id="DIR-004",
                        flag_code="DIRECTOR_CESSATION_LEGAL_EFFECT_REVIEW",
                        severity=Severity.NOT_EVALUATED,
                        score_impact=0,
                        revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                        description=(
                            "Cessation particulars are reported late or unfiled. The "
                            "effect on third-party reliance and any continuing liability "
                            "requires case-specific legal review; non-filing alone does "
                            "not automatically establish continuing director liability."
                        ),
                        statutory_basis="Section 115, Companies Act 1994 (Bangladesh)",
                        detail={"director_id": change.director_id, "legal_review_required": True},
                        state=RuleState.REQUIRES_LAWYER_JUDGMENT,
                        eval_state="UNKNOWN",
                    ))

            # Section 93(2) consent is a distinct filing from Form XII. Do not
            # infer it from form_filed; require its own verified status.
            if (
                change.event_type == "appointment"
                and change.consent_filed is False
                and change.consent_verified
                and bool(change.consent_evidence_ref)
                and delay > 30
            ):
                self._add_flag(ComplianceFlag(
                    rule_id="DIR-007",
                    flag_code="DIRECTOR_CONSENT_FILING_REQUIRES_REVIEW",
                    severity=Severity.NOT_EVALUATED,
                    score_impact=0,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description=(
                        f"Written director consent is reported unfiled {delay} days "
                        "after appointment. Section 93(2) provides a 30-day filing "
                        "period; reconcile the pre-appointment consent/form requirements "
                        "under section 92 and current RJSC Form IX instructions. "
                        "No default is determined without authenticated filing evidence."
                    ),
                    statutory_basis="Section 93(2), Companies Act 1994 (Bangladesh); section 92/Form IX mapping requires review",
                    detail={"director_id": change.director_id, "delay": delay},
                    state=RuleState.REQUIRES_LAWYER_JUDGMENT,
                    eval_state="UNKNOWN",
                ))

    # ───────────────────────────────────────────────────────────────────
    # MODULE 5: SHAREHOLDING
    # ───────────────────────────────────────────────────────────────────
    def _run_shareholder_rules(self, c: CompanyProfile) -> None:
        # SH-001: every verified allotment has its own Form XV filing clock.
        # SH-002: section 158 is triggered by both allotment and registered transfer.
        # SH-003: Form IV clock starts from a verified capital-increase resolution.
        # Unverified events or filing/certificate states remain UNKNOWN, never FAIL.
        events = [
            event for event in c.share_compliance_events
            if event.event_verified and event.event_evidence_ref
        ]

        overdue_allotments = []
        overdue_certificates = []
        overdue_capital_increases = []
        for event in events:
            delay = (self.today - event.event_date).days
            if delay < 0:
                continue

            if (
                event.event_type == "ALLOTMENT"
                and event.filing_form == "FORM_XV"
                and event.filing_status_verified
                and event.filing_status is False
                and delay > ALLOTMENT_FILING_DEADLINE_DAYS
            ):
                overdue_allotments.append((event, delay))

            if (
                event.event_type in {"ALLOTMENT", "TRANSFER_REGISTERED"}
                and event.certificate_status_verified
                and event.certificate_issued is False
                and delay > SHARE_CERTIFICATE_DEADLINE_DAYS
            ):
                overdue_certificates.append((event, delay))

            if (
                event.event_type == "CAPITAL_INCREASE_RESOLUTION"
                and event.filing_form == "FORM_IV"
                and event.filing_status_verified
                and event.filing_status is False
                and delay > CAPITAL_INCREASE_NOTICE_DEADLINE_DAYS
            ):
                overdue_capital_increases.append((event, delay))

        if overdue_allotments:
            event, delay = max(overdue_allotments, key=lambda item: item[1])
            self._add_flag(ComplianceFlag(
                rule_id="SH-001",
                flag_code="FORM_XV_ALLOTMENT_NOT_FILED",
                severity=Severity.YELLOW if delay < 90 else Severity.RED,
                score_impact=8,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description=(
                    f"Verified allotment event {event.event_reference} has no verified "
                    f"Form XV filing after the 60-day section 151 period; {delay} days elapsed."
                ),
                statutory_basis="Section 151, Companies Act 1994 (Bangladesh)",
                detail={
                    "event_reference": event.event_reference,
                    "event_date": event.event_date.isoformat(),
                    "delay_days": delay,
                    "filing_evidence_ref": event.filing_evidence_ref,
                    "overdue_event_count": len(overdue_allotments),
                },
            ))

        if overdue_certificates:
            event, delay = max(overdue_certificates, key=lambda item: item[1])
            self._add_flag(ComplianceFlag(
                rule_id="SH-002",
                flag_code="SHARE_CERTIFICATES_NOT_ISSUED",
                severity=Severity.YELLOW if delay <= 120 else Severity.RED,
                score_impact=5,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description=(
                    f"Verified {event.event_type.lower()} event {event.event_reference} "
                    f"has no verified share-certificate issue within 90 days under section 158; "
                    f"{delay - SHARE_CERTIFICATE_DEADLINE_DAYS} days overdue."
                ),
                statutory_basis="Section 158, Companies Act 1994 (Bangladesh)",
                detail={
                    "event_reference": event.event_reference,
                    "event_type": event.event_type,
                    "event_date": event.event_date.isoformat(),
                    "delay_days": delay,
                    "certificate_evidence_ref": event.certificate_evidence_ref,
                    "overdue_event_count": len(overdue_certificates),
                },
            ))

        if overdue_capital_increases:
            event, delay = max(overdue_capital_increases, key=lambda item: item[1])
            self._add_flag(ComplianceFlag(
                rule_id="SH-003",
                flag_code="FORM_IV_CAPITAL_INCREASE_NOT_FILED",
                severity=Severity.YELLOW if delay < 90 else Severity.RED,
                score_impact=8,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description=(
                    f"Verified capital-increase resolution {event.event_reference} has no "
                    f"verified Form IV filing within 15 days under section 56; {delay - CAPITAL_INCREASE_NOTICE_DEADLINE_DAYS} days overdue."
                ),
                statutory_basis="Section 56, Companies Act 1994 (Bangladesh)",
                detail={
                    "event_reference": event.event_reference,
                    "event_date": event.event_date.isoformat(),
                    "delay_days": delay,
                    "filing_evidence_ref": event.filing_evidence_ref,
                    "overdue_event_count": len(overdue_capital_increases),
                },
            ))

    # ───────────────────────────────────────────────────────────────────
    # MODULE 6: SHARE TRANSFERS
    # ───────────────────────────────────────────────────────────────────
    def _run_transfer_rules(self, c: CompanyProfile) -> None:
        for transfer in c.share_transfers:
            transfer_review_flags = []

            # Section 38(3): verify a duly executed/stamped transfer instrument.
            # Missing or unproduced records are review prompts, not proof of absence.
            if transfer.instrument_recorded is False or transfer.form_117_filed is False:
                flag = ComplianceFlag(
                    rule_id="TR-001",
                    flag_code="TRANSFER_INSTRUMENT_REQUIRES_VERIFICATION",
                    severity=Severity.NOT_EVALUATED,
                    score_impact=0,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description=(
                        "Internal review signal only: verify the prescribed transfer "
                        "instrument, signatures, stamping, share certificate and any "
                        "statutory exception under section 38(3). A missing upload is "
                        "not proof that no valid instrument exists."
                    ),
                    statutory_basis="Section 38(3), Companies Act 1994 (Bangladesh)",
                    state=RuleState.REQUIRES_LAWYER_JUDGMENT,
                    eval_state="UNKNOWN",
                    detail={"transfer_id": transfer.transfer_id},
                )
                self._add_flag(flag)
                transfer_review_flags.append(flag)

            # Stamp duty depends on the instrument, execution facts and current
            # Schedule I. Never infer non-payment from a missing receipt alone.
            if transfer.stamp_duty_applicability_verified and transfer.stamp_duty_paid is False:
                flag = ComplianceFlag(
                    rule_id="TR-002",
                    flag_code="STAMP_DUTY_REQUIRES_INSTRUMENT_REVIEW",
                    severity=Severity.NOT_EVALUATED,
                    score_impact=0,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description=(
                        "Internal review signal only: verify instrument category, "
                        "execution/registration facts, current Stamp Act Schedule I "
                        "rate, exemption/adjudication and authenticated payment evidence. "
                        "No inadmissibility or invalidity is determined."
                    ),
                    statutory_basis="Stamp Act 1899, current Schedule I and applicable amendments",
                    state=RuleState.REQUIRES_LAWYER_JUDGMENT,
                    eval_state="UNKNOWN",
                    detail={"transfer_id": transfer.transfer_id},
                )
                self._add_flag(flag)
                transfer_review_flags.append(flag)

            # Board approval is not universal. It is relevant only where the
            # company's actual Articles impose a valid restriction.
            restriction_applies = (
                transfer.aoa_restriction_apply is True
                and bool(transfer.articles_clause_evidence_ref)
            )
            board_approval_missing = (
                restriction_applies and transfer.board_approval_obtained is False
            )
            if board_approval_missing:
                flag = ComplianceFlag(
                    rule_id="TR-003",
                    flag_code="ARTICLES_TRANSFER_RESTRICTION_REQUIRES_REVIEW",
                    severity=Severity.NOT_EVALUATED,
                    score_impact=0,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description=(
                        "Internal review signal only: an Articles transfer restriction "
                        "is reported and board approval is not verified. Review the "
                        "operative Articles, transfer class, notice, board powers and "
                        "section 38(7). Board approval is not a universal statutory requirement."
                    ),
                    statutory_basis="Section 38(7), Companies Act 1994 (Bangladesh), and the company's Articles",
                    state=RuleState.REQUIRES_LAWYER_JUDGMENT,
                    eval_state="UNKNOWN",
                    detail={"transfer_id": transfer.transfer_id},
                )
                self._add_flag(flag)
                transfer_review_flags.append(flag)

            # Section 38(4): where registration is refused, the company
            # must notify both transferor and transferee within 30 days of
            # lodgement. Do not infer refusal or non-notice from missing data.
            if (
                transfer.registration_refused is True
                and transfer.refusal_notice_sent is False
                and transfer.instrument_lodged_date is not None
                and bool(transfer.refusal_decision_evidence_ref)
            ):
                refusal_delay = (self.today - transfer.instrument_lodged_date).days
                if refusal_delay > 30:
                    flag = ComplianceFlag(
                        rule_id="TR-004",
                        flag_code="TRANSFER_REFUSAL_NOTICE_REQUIRES_REVIEW",
                        severity=Severity.NOT_EVALUATED,
                        score_impact=0,
                        revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                        description=(
                            f"A refusal to register is reported but notice to both "
                            f"parties is not verified {refusal_delay} days after the "
                            "instrument was lodged. Section 38(4) requires notice "
                            "within 30 days; verify lodgement, refusal, dispatch and "
                            "receipt evidence before any default conclusion."
                        ),
                        statutory_basis="Section 38(4), Companies Act 1994 (Bangladesh)",
                        state=RuleState.REQUIRES_LAWYER_JUDGMENT,
                        eval_state="UNKNOWN",
                        detail={"transfer_id": transfer.transfer_id, "delay": refusal_delay},
                    )
                    self._add_flag(flag)
                    transfer_review_flags.append(flag)

            # Section 38(7) preserves the company's power under its Articles
            # to refuse registration; it does not make every restricted transfer
            # automatically void. Require proof it was registered despite the restriction.
            if (
                transfer.transfer_registered is True
                and bool(transfer.transfer_registration_evidence_ref)
                and board_approval_missing
            ):
                flag = ComplianceFlag(
                    rule_id="TR-005",
                    flag_code="REGISTERED_TRANSFER_DESPITE_REPORTED_ARTICLES_RESTRICTION",
                    severity=Severity.NOT_EVALUATED,
                    score_impact=0,
                    revenue_tier=RevenueTier.CORPORATE_RESCUE,
                    description=(
                        "Internal review signal only: a transfer is reported registered "
                        "despite an Articles restriction and missing board approval. "
                        "Section 38(7) concerns the company's power to refuse registration; "
                        "do not declare the transfer void or title absent without counsel "
                        "review of the Articles, registration, notices and remedies."
                    ),
                    statutory_basis="Section 38(7), Companies Act 1994 (Bangladesh), and the company's Articles",
                    state=RuleState.REQUIRES_LAWYER_JUDGMENT,
                    eval_state="UNKNOWN",
                    detail={"transfer_id": transfer.transfer_id},
                )
                self._add_flag(flag)
                transfer_review_flags.append(flag)

            if len(transfer_review_flags) >= 2:
                self._add_flag(ComplianceFlag(
                    rule_id="TR-006",
                    flag_code="TRANSFER_RECORD_REVIEW_COMPOSITE",
                    severity=Severity.NOT_EVALUATED,
                    score_impact=0,
                    revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
                    description=(
                        f"{len(transfer_review_flags)} transfer-record review signals "
                        "require document and Articles reconciliation. This composite "
                        "is not a statutory breach or invalidity finding."
                    ),
                    statutory_basis="Sections 34 and 38, Companies Act 1994 (Bangladesh), and applicable Articles",
                    state=RuleState.REQUIRES_LAWYER_JUDGMENT,
                    eval_state="UNKNOWN",
                    detail={"transfer_id": transfer.transfer_id, "count": len(transfer_review_flags)},
                ))

    # ───────────────────────────────────────────────────────────────────
    # MODULE 7: STATUTORY REGISTERS
    # ───────────────────────────────────────────────────────────────────
    def _run_register_rules(self, c: CompanyProfile) -> None:
        aliases = {
            "register_of_members": "members", "register_of_directors": "directors",
            "register_of_share_transfers": "transfers", "register_of_charges": "charges",
            "register_of_debenture_holders": "debentures",
            "minutes_book_agm": "minutes_agm", "minutes_book_board": "minutes_board",
        }
        normalized = {aliases.get(r, r) for r in c.maintained_registers}
        missing = [r for r in REQUIRED_REGISTERS if r not in normalized]
        core_missing = [r for r in CORE_REGISTERS if r not in normalized]
        non_core_missing = [r for r in missing if r not in CORE_REGISTERS]
        
        if non_core_missing and not core_missing:
            self._add_flag(ComplianceFlag(
                rule_id="REG-001",
                flag_code="STATUTORY_REGISTER_INCOMPLETE",
                severity=Severity.YELLOW,
                score_impact=5,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description=f"{len(non_core_missing)} non-core register(s) missing: {', '.join(non_core_missing)}.",
                statutory_basis="Section 34, Companies Act 1994 (Bangladesh)",
                detail={"missing": non_core_missing}
            ))

        if core_missing:
            # P1 LEGAL FIX: Distinguish internal register-keeping from RJSC filing.
            # The audit flagged that Section 115 is a FILING obligation (particulars
            # of directors to RJSC), NOT an internal register-keeping provision.
            # We now separate the two concepts in the description.
            severity = Severity.RED  # legal: REG-002 downgraded BLACK -> RED

            # Categorize missing items by legal obligation type
            internal_registers = []
            rjsc_filings = []
            for r in core_missing:
                if r in ("members", "charges", "minutes_agm", "minutes_board"):
                    internal_registers.append(r)
                elif r == "directors":
                    rjsc_filings.append(r)

            parts = []
            if "members" in internal_registers:
                parts.append("Members register (Sec 34 — internal)")
            if "charges" in internal_registers:
                parts.append("Charges register (Sec 174 — internal)")
            if "minutes_agm" in internal_registers or "minutes_board" in internal_registers:
                parts.append("Meeting minutes (Sec 89 — internal)")
            if "directors" in rjsc_filings:
                parts.append("Director particulars filing (Sec 115 — RJSC filing)")

            self._add_flag(ComplianceFlag(
                rule_id="REG-002",
                flag_code="CORE_REGISTERS_MISSING",
                severity=severity,
                score_impact=12,
                revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
                description=(
                    f"Core statutory records missing: {', '.join(core_missing)}. "
                    f"Legal basis: {'; '.join(parts)}. "
                    f"Note: internal register-keeping (Sec 34/89/174) is distinct "
                    f"from RJSC filing obligations (Sec 115/163-165). "
                    f"Each missing item is an independent legal obligation."
                ),
                statutory_basis="Sections 34, 89, 115, 174, Companies Act 1994 (Bangladesh)",
                detail={
                    "missing_core": core_missing,
                    "internal_registers": internal_registers,
                    "rjsc_filings": rjsc_filings,
                    "obligation_types_distinguished": True,
                }
            ))

        if c.register_location != "registered_office":
            self._add_flag(ComplianceFlag(
                rule_id="REG-003",
                flag_code="REGISTERS_NOT_AT_REGISTERED_OFFICE",
                severity=Severity.YELLOW,
                score_impact=3,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description=f"Registers at '{c.register_location}', not registered office. Section 34(2): must be at registered office.",
                statutory_basis="Section 34(2), Companies Act 1994 (Bangladesh)",
                detail={"location": c.register_location}
            ))

    # ───────────────────────────────────────────────────────────────────
    # MODULE 8: REGISTERED OFFICE
    # ───────────────────────────────────────────────────────────────────
    def _run_office_rules(self, c: CompanyProfile) -> None:
        if c.registered_office_change_date and c.form_vi_filed is False:
            delay = (self.today - c.registered_office_change_date).days
            if delay > REGISTERED_OFFICE_DEADLINE_DAYS:
                self._add_flag(ComplianceFlag(
                    rule_id="OFF-001",
                    flag_code="REGISTERED_OFFICE_CHANGE_NOT_FILED",
                    severity=Severity.YELLOW if delay < 90 else Severity.RED,
                    score_impact=3,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description=f"Office change not filed via Form VI. Section 77: 28-day deadline. Overdue by {delay} days.",
                    statutory_basis="Section 77, Companies Act 1994 (Bangladesh)",
                    detail={"delay": delay, "form": "Form VI"}
                ))

    # ───────────────────────────────────────────────────────────────────
    # MODULE 9: CAPITAL & CHARGES
    # ───────────────────────────────────────────────────────────────────
    def _run_capital_rules(self, c: CompanyProfile) -> None:
        if c.capital_increase_date and c.capital_increase_resolution is False:
            self._add_flag(ComplianceFlag(
                rule_id="CAP-001",
                flag_code="CAPITAL_ALTERATION_AUTHORITY_REQUIRES_REVIEW",
                severity=Severity.NOT_EVALUATED,
                score_impact=0,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description=(
                    "Internal review signal only: verify the exact capital alteration "
                    "type, Articles authority and resolution required by section 53. "
                    "Section 54 addresses specified consolidation/conversion/subdivision "
                    "notices; increase of registered share capital is separately governed "
                    "by section 56. Do not assume a special resolution without the Act "
                    "and the company's Articles."
                ),
                statutory_basis="Sections 53, 54 and 56, Companies Act 1994 (Bangladesh)",
                state=RuleState.REQUIRES_LAWYER_JUDGMENT,
                eval_state="UNKNOWN",
            ))

        for charge in c.charges:
            registration_unknown = []
            if not charge.creation_date_verified or not charge.creation_date_evidence_ref:
                registration_unknown.append("CHARGE_CREATION_DATE_UNVERIFIED")
            if (
                charge.registrable_under_s159 is None
                or not charge.registrability_verified
                or not charge.registrability_evidence_ref
            ):
                registration_unknown.append("SECTION_159_REGISTRABILITY_UNKNOWN")
            elif charge.registrable_under_s159 is False:
                registration_unknown = []
            if (
                charge.form_xviii_filed is None
                or not charge.form_xviii_filing_status_verified
                or not charge.form_xviii_filing_evidence_ref
            ):
                registration_unknown.append("RJSC_FORM_XVIII_STATUS_UNVERIFIED")
            if charge.form_xviii_filed is True and charge.form_xviii_filed_date is None:
                registration_unknown.append("FORM_XVIII_FILING_DATE_UNKNOWN")
            if charge.form_xviii_filed is False and charge.form_xviii_filed_date is not None:
                registration_unknown.append("FORM_XVIII_STATUS_DATE_CONFLICT")

            registrability_verified_not_applicable = (
                charge.registrable_under_s159 is False
                and charge.registrability_verified
                and bool(charge.registrability_evidence_ref)
            )
            if registration_unknown and not registrability_verified_not_applicable:
                self._add_flag(ComplianceFlag(
                    rule_id="CAP-002",
                    flag_code="CHARGE_REGISTRATION_REQUIRES_EVIDENCE_REVIEW",
                    severity=Severity.NOT_EVALUATED,
                    score_impact=0,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description="Charge registration status, creation date or Section 159 applicability is not sufficiently evidenced. Missing evidence is UNKNOWN, not proof of non-registration.",
                    statutory_basis="Section 159(1), Companies Act 1994 (Bangladesh)",
                    detail={"charge_id": charge.charge_id, "unknown_reasons": registration_unknown},
                    state=RuleState.UNKNOWN,
                    eval_state="UNKNOWN",
                ))
            elif charge.registrable_under_s159 is True:
                registration_deadline = (
                    charge.creation_date + timedelta(days=CHARGE_REGISTRATION_DEADLINE_DAYS)
                )
                if charge.form_xviii_filed is False:
                    days_overdue = (self.today - registration_deadline).days
                    if self.today > registration_deadline:
                        self._add_flag(ComplianceFlag(
                            rule_id="CAP-002",
                            flag_code="CHARGE_NOT_REGISTERED",
                            severity=Severity.YELLOW if days_overdue < 90 else Severity.RED,
                            score_impact=5,
                            revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                            description=f"{charge.charge_type} charge (Tk {charge.amount_bdt:,.2f}) was not registered within 21 days of creation under Section 159(1). Overdue by {days_overdue} days.",
                            statutory_basis="Section 159(1), Companies Act 1994 (Bangladesh)",
                            detail={
                                "charge_id": charge.charge_id,
                                "creation_date": charge.creation_date.isoformat(),
                                "statutory_deadline": registration_deadline.isoformat(),
                                "statutory_period_days": CHARGE_REGISTRATION_DEADLINE_DAYS,
                                "days_overdue": days_overdue,
                                "form": "Form XVIII",
                                "amount": charge.amount_bdt,
                            },
                            state=RuleState.NON_COMPLIANT,
                            eval_state="VIOLATION",
                        ))
                elif (
                    charge.form_xviii_filed is True
                    and charge.form_xviii_filed_date is not None
                    and charge.form_xviii_filed_date > registration_deadline
                ):
                    days_late = (charge.form_xviii_filed_date - registration_deadline).days
                    self._add_flag(ComplianceFlag(
                        rule_id="CAP-002",
                        flag_code="CHARGE_REGISTERED_LATE_REQUIRES_REVIEW",
                        severity=Severity.NOT_EVALUATED,
                        score_impact=0,
                        revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                        description="Form XVIII filing is evidenced after the Section 159(1) 21-day period. Review any Registrar extension and the legal effect of late registration; do not infer cure or voidness automatically.",
                        statutory_basis="Section 159(1), Companies Act 1994 (Bangladesh)",
                        detail={
                            "charge_id": charge.charge_id,
                            "creation_date": charge.creation_date.isoformat(),
                            "statutory_deadline": registration_deadline.isoformat(),
                            "filed_date": charge.form_xviii_filed_date.isoformat(),
                            "days_late": days_late,
                            "form": "Form XVIII",
                            "registrar_extension_evidence_required": True,
                        },
                        state=RuleState.REQUIRES_LAWYER_JUDGMENT,
                        eval_state="UNKNOWN",
                    ))

            if charge.satisfied is None or charge.satisfied is True:
                unknown_reasons = []
                if charge.satisfied is None:
                    unknown_reasons.append("SATISFACTION_STATUS_UNKNOWN")
                if not charge.satisfaction_verified or not charge.satisfaction_evidence_ref:
                    unknown_reasons.append("SATISFACTION_NOT_AUTHENTICATED")
                if charge.satisfaction_date is None:
                    unknown_reasons.append("SATISFACTION_DATE_UNKNOWN")
                if (
                    charge.registrable_under_s159 is None
                    or not charge.registrability_verified
                    or not charge.registrability_evidence_ref
                ):
                    unknown_reasons.append("SECTION_159_REGISTRABILITY_UNKNOWN")
                elif charge.registrable_under_s159 is False:
                    # Section 172 does not apply to a charge outside s.159.
                    continue
                if (
                    charge.satisfaction_filed is None
                    or not charge.satisfaction_filing_status_verified
                    or not charge.satisfaction_filing_evidence_ref
                ):
                    unknown_reasons.append("RJSC_FILING_STATUS_UNVERIFIED")
                if charge.satisfaction_filed is True and charge.satisfaction_filed_date is None:
                    unknown_reasons.append("SATISFACTION_FILING_DATE_UNKNOWN")
                if charge.satisfaction_filed is False and charge.satisfaction_filed_date is not None:
                    unknown_reasons.append("SATISFACTION_FILING_STATUS_DATE_CONFLICT")
                if unknown_reasons:
                    self._add_flag(ComplianceFlag(
                        rule_id="CHG-001",
                        flag_code="CHARGE_SATISFACTION_REQUIRES_EVIDENCE_REVIEW",
                        severity=Severity.NOT_EVALUATED,
                        score_impact=0,
                        revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                        description=(
                            "Charge satisfaction is reported, but Section 172 applicability, "
                            "satisfaction date, or RJSC filing status is not independently "
                            "verified. This is a review prompt, not a finding of default."
                        ),
                        statutory_basis="Section 172(1), read with Section 159, Companies Act 1994 (Bangladesh)",
                        detail={"charge_id": charge.charge_id, "unknown_reasons": unknown_reasons},
                        state=RuleState.UNKNOWN,
                        eval_state="UNKNOWN",
                    ))
                elif (
                    charge.satisfaction_filed is True
                    and charge.satisfaction_date is not None
                    and charge.satisfaction_filed_date is not None
                ):
                    satisfaction_deadline = charge.satisfaction_date + timedelta(days=21)
                    if charge.satisfaction_filed_date > satisfaction_deadline:
                        days_late = (charge.satisfaction_filed_date - satisfaction_deadline).days
                        self._add_flag(ComplianceFlag(
                            rule_id="CHG-001",
                            flag_code="CHARGE_SATISFACTION_FILED_LATE_REQUIRES_REVIEW",
                            severity=Severity.NOT_EVALUATED,
                            score_impact=0,
                            revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                            description="Form XXVIII filing is evidenced after the Section 172(1) 21-day period. Review any Registrar extension and the legal effect of late filing; do not infer cure or voidness automatically.",
                            statutory_basis="Section 172(1), read with Section 159, Companies Act 1994 (Bangladesh)",
                            detail={
                                "charge_id": charge.charge_id,
                                "satisfaction_date": charge.satisfaction_date.isoformat(),
                                "statutory_deadline": satisfaction_deadline.isoformat(),
                                "filed_date": charge.satisfaction_filed_date.isoformat(),
                                "days_late": days_late,
                                "form": "Form XXVIII",
                                "registrar_extension_evidence_required": True,
                            },
                            state=RuleState.REQUIRES_LAWYER_JUDGMENT,
                            eval_state="UNKNOWN",
                        ))
                elif (
                    charge.satisfaction_filed is False
                    and charge.satisfaction_date is not None
                ):
                    satisfaction_deadline = charge.satisfaction_date + timedelta(days=21)
                    satisfaction_delay = (self.today - charge.satisfaction_date).days
                    days_overdue = (self.today - satisfaction_deadline).days
                    if self.today > satisfaction_deadline:
                        self._add_flag(ComplianceFlag(
                            rule_id="CHG-001",
                            flag_code="CHARGE_SATISFACTION_NOT_FILED",
                            severity=Severity.YELLOW,
                            score_impact=3,
                            revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                            description=f"Verified s.159-registrable charge satisfaction was not notified to RJSC within 21 days under Section 172(1). Form XXVIII is the satisfaction filing. Overdue by {days_overdue} days.",
                            statutory_basis="Section 172(1), read with Section 159, Companies Act 1994 (Bangladesh)",
                            detail={
                                "charge_id": charge.charge_id,
                                "charge_type": charge.charge_type,
                                "satisfaction_date": charge.satisfaction_date.isoformat(),
                                "statutory_deadline": satisfaction_deadline.isoformat(),
                                "statutory_period_days": 21,
                                "elapsed_days": satisfaction_delay,
                                "delay_days": satisfaction_delay,
                                "days_overdue": days_overdue,
                                "form": "Form XXVIII",
                                "statutory_basis": "Section 172(1), read with Section 159",
                            },
                            state=RuleState.NON_COMPLIANT,
                            eval_state="VIOLATION",
                        ))

        if c.capital_reduction_pending and c.capital_reduction_court_order_obtained is False:
            self._add_flag(ComplianceFlag(
                rule_id="CAP-003",
                flag_code="CAPITAL_REDUCTION_REQUIRES_LEGAL_REVIEW",
                severity=Severity.NOT_EVALUATED,
                score_impact=0,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description="A capital-reduction workflow is marked pending without a verified court-confirmation and registration record. A pending workflow alone does not prove an unlawful completed reduction; review the resolution, court process, creditor notices and registration evidence under Sections 59-60.",
                statutory_basis="Sections 59-60, Companies Act 1994 (Bangladesh)",
                state=RuleState.REQUIRES_LAWYER_JUDGMENT,
                eval_state="UNKNOWN",
            ))

        if c.special_resolution_date and c.special_resolution_filed is False:
            delay = (self.today - c.special_resolution_date).days
            if delay > 15:
                self._add_flag(ComplianceFlag(
                    rule_id="CAP-004",
                    flag_code="SPECIAL_RESOLUTION_NOT_FILED",
                    severity=Severity.YELLOW if delay < 90 else Severity.RED,
                    score_impact=8,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description="Special resolution filing not evidenced within 15 days. Section 88(1); determine the resolution date and filing receipt.",
                    statutory_basis="Section 88(1), Companies Act 1994 (Bangladesh) — 15 days",
                    detail={"delay": delay}
                ))

    # ───────────────────────────────────────────────────────────────────
    # MODULE 10: TAX COMPLIANCE
    # ───────────────────────────────────────────────────────────────────
    def _run_tax_rules(self, c: CompanyProfile) -> None:
        if c.tin_obtained is False:
            # A profile boolean is not authenticated evidence of TIN absence or
            # proof that the company falls within a specific return/proof duty.
            # Keep this as a non-scoring review prompt until identity, s.166
            # filing duty, s.261 registration and s.264 proof requirements are
            # independently verified for this company and assessment period.
            self._add_flag(ComplianceFlag(
                rule_id="TAX-001",
                flag_code="TIN_STATUS_REQUIRES_VERIFICATION",
                severity=Severity.NOT_EVALUATED,
                score_impact=0,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description="The company profile records no TIN. Verify the legal entity and taxpayer identity, return-filing duty under section 166, registration under section 261, and any proof-of-return requirement under section 264. A profile entry alone is not a finding of breach.",
                statutory_basis="Income Tax Act 2023, sections 166, 261 and 264; company-specific duty and evidence require verification",
                state=RuleState.UNKNOWN,
                eval_state="UNKNOWN",
                detail={"profile_tin_status": "reported_absent", "identity_verified": False, "statutory_duty_verified": False},
            ))

        if c.vat_registered is False and c.annual_turnover_bdt > _VAT_TURNOVER_TAX_ENLISTMENT_THRESHOLD_BDT:
            self._add_flag(ComplianceFlag(
                rule_id="TAX-002",
                flag_code="VAT_REGISTRATION_OR_ENLISTMENT_STATUS_REQUIRES_VERIFICATION",
                severity=Severity.NOT_EVALUATED,
                score_impact=0,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description="Reported turnover exceeds the BDT 30 lakh turnover-tax enlistment threshold. This is only a review prompt: determine whether the verified rolling 12-month taxable turnover exceeds BDT 30 lakh but does not exceed the BDT 50 lakh registration threshold (enlistment), or exceeds BDT 50 lakh (registration), and check mandatory-registration categories under section 4(2), taxpayer activity, effective date and current status before finding a breach.",
                statutory_basis="Value Added Tax and Supplementary Duty Act 2012, sections 2(48), 2(57), 4 and 10, as amended by Act No. 77 of 2026 and Finance Act No. 96 of 2026; exact current section and taxpayer-specific instruments require counsel verification",
                state=RuleState.UNKNOWN,
                eval_state="UNKNOWN",
                detail={"reported_annual_turnover_bdt": c.annual_turnover_bdt, "registration_threshold_bdt": _VAT_REGISTRATION_THRESHOLD_BDT, "turnover_tax_enlistment_threshold_bdt": _VAT_TURNOVER_TAX_ENLISTMENT_THRESHOLD_BDT, "rolling_12_month_turnover_verified": False, "mandatory_category_verified": False, "turnover_tax_enlistment_application_window_days": 30}
            ))

        if c.tin_obtained and c.tax_return_filed_for_current_fy is False and c.financial_year_end:
            # VERIFY against ITA 2023: company return due 15th day of 7th month after FY end (30 Jun -> 15 Jan)
            fy_end = c.financial_year_end
            # Finance Act 2026 (Act 96/2026) substituted Income Tax Act
            # s.170. For non-individuals, use the 15th day of the ninth
            # month after income-year end, but not earlier than the following
            # 15 September. Section 171 now cross-refers to s.170.
            ninth_month = fy_end.month + 9
            ninth_year = fy_end.year
            if ninth_month > 12:
                ninth_month -= 12
                ninth_year += 1
            ninth_month_date = date(ninth_year, ninth_month, 15)
            september_floor = date(fy_end.year + (1 if fy_end.month >= 9 else 0), 9, 15)
            deadline = max(ninth_month_date, september_floor)
            # Public-holiday roll-forward, taxpayer-specific extension,
            # applicable income-year classification and later notices are
            # not yet verified; keep this as a non-scoring review prompt.
            if self.today > deadline:
                delay = (self.today - deadline).days
                self._add_flag(ComplianceFlag(
                    rule_id="TAX-003",
                    flag_code="ANNUAL_TAX_RETURN_OVERDUE",
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description=f"Potential company return delay of {delay} days using the provisional section 170(2) formula. Verify the applicable income year, taxpayer category, holiday roll-forward, written extension and subsequent amendments before determining default.",
                    statutory_basis="Income Tax Act 2023, Sections 170(2) and 171, as amended by Finance Act 2026 (Act No. 96 of 2026); taxpayer-specific and holiday verification required",
                    detail={"delay_days": delay, "fy_year": fy_end.year, "ninth_month_date": ninth_month_date.isoformat(), "september_15_floor": september_floor.isoformat(), "provisional_deadline": deadline.isoformat(), "holiday_adjustment_verified": False, "extension_verified": False},
                    state=RuleState.REQUIRES_LAWYER_JUDGMENT,
                    eval_state="UNKNOWN",
                    score_impact=0,
                    severity=Severity.NOT_EVALUATED,
                ))

        if c.tin_obtained:
            missed = []
            t = self.today
            # Income Tax Act 2023 s.155(2): four 25% instalments on
            # 15 September, 15 December, 15 March and 15 June. If a date is
            # a public holiday, payment is due on the next working day under
            # s.155(3); holiday adjustment must be confirmed before a breach.
            if t.month >= 7:
                q1_deadline = date(t.year, 9, 15)
                q2_deadline = date(t.year, 12, 15)
                q3_deadline = date(t.year + 1, 3, 15)
                q4_deadline = date(t.year + 1, 6, 15)
            else:
                q1_deadline = date(t.year - 1, 9, 15)
                q2_deadline = date(t.year - 1, 12, 15)
                q3_deadline = date(t.year, 3, 15)
                q4_deadline = date(t.year, 6, 15)
                
            if t > q1_deadline and c.advance_tax_q1_paid is False:
                missed.append("Q1")
            if t > q2_deadline and c.advance_tax_q2_paid is False:
                missed.append("Q2")
            if t > q3_deadline and c.advance_tax_q3_paid is False:
                missed.append("Q3")
            if t > q4_deadline and c.advance_tax_q4_paid is False:
                missed.append("Q4")
            
            if missed:
                self._add_flag(ComplianceFlag(
                    rule_id="TAX-004",
                    flag_code="ADVANCE_TAX_MISSED",
                    severity=Severity.NOT_EVALUATED,
                    score_impact=0,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description=f"Potential advance-tax instalment delay requiring review: {', '.join(missed)}. Finance Act 2026 (Act 96/2026), sections 87-88, raises the section 154(1) threshold to BDT 10 lakh and amends section 155(2) and (5). Verify section 156 new-assessee treatment (separate BDT 6 lakh threshold), A-B liability after source deductions, estimate, exclusions, holiday roll-forward and payment evidence.",
                    statutory_basis="Income Tax Act 2023, sections 154-157, as amended by Finance Act 2026 (Act 96/2026), sections 87-88; NOT_EVALUATED pending taxpayer-specific verification",
                    detail={"quarters": missed},
                    state=RuleState.REQUIRES_LAWYER_JUDGMENT,
                    eval_state="UNKNOWN",
                ))

        if c.vat_registered is True:
            # Registration alone does not establish the taxpayer's filing
            # cadence, special 20-day category, current s.64 period, holiday,
            # extension or actual filing evidence. This is a review prompt only.
            self._add_flag(ComplianceFlag(
                rule_id="VAT-002",
                flag_code="VAT_RETURN_OBLIGATION_REQUIRES_VERIFICATION",
                severity=Severity.NOT_EVALUATED,
                score_impact=0,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description="VAT return obligation and filing status require verification. Determine the applicable version of section 64, tax period, taxpayer category, holiday rule, extension/order and return evidence. This is not a finding of default.",
                statutory_basis="Value Added Tax and Supplementary Duty Act 2012, section 64 as amended by Finance Act 2026 and VAT Amendment Ordinance 2026, with applicable VAT Rules/SROs",
                state=RuleState.UNKNOWN,
                eval_state="UNKNOWN",
                detail={"last_vat_return_filed": c.last_vat_return_filed.isoformat() if c.last_vat_return_filed else None, "tax_period_verified": False, "applicable_due_date_verified": False, "extension_status_verified": False},
            ))

        # VAT-003 remains a non-scoring evidence/review state. The current
        # corpus has not established one universal annual VAT return due date
        # for every registered company. Do not infer a breach from a False or
        # missing profile field without the taxpayer's return type, tax period,
        # applicable NBR instrument and effective date.
        if c.vat_registered is True and c.vat_annual_return_filed_for_fy is not True:
            self._add_flag(ComplianceFlag(
                rule_id="VAT-003",
                flag_code="ANNUAL_VAT_RETURN_STATUS_REQUIRES_REVIEW",
                severity=Severity.NOT_EVALUATED,
                score_impact=0,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description="Annual VAT return status is incomplete or recorded as not filed. Confirm the taxpayer's applicable return type, tax period, filing obligation and effective NBR instrument before determining any default.",
                statutory_basis="Value Added Tax Act 2012 (Bangladesh); specific annual-return obligation and due date require current-law verification",
                state=RuleState.UNKNOWN,
                eval_state="UNKNOWN",
                detail={"annual_return_filed_for_fy": c.vat_annual_return_filed_for_fy},
            ))

        unresolved = (c.penalty_notices_received or 0) - (c.penalty_notices_resolved or 0)  # type: ignore
        if unresolved > 0:
            self._add_flag(ComplianceFlag(
                rule_id="DEF-002",
                flag_code="PENALTY_NOTICE_REQUIRES_CASE_REVIEW",
                severity=Severity.NOT_EVALUATED,
                score_impact=0,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description=f"{unresolved} penalty/prosecution notice item(s) are unresolved. Each notice must be matched to its alleged offence, enabling section, issuing authority, response deadline, appeal/stay and current disposition; no universal Companies Act penalty provision applies.",
                statutory_basis="Case-specific enabling provision required; not a universal section",
                state=RuleState.REQUIRES_LAWYER_JUDGMENT,
                eval_state="UNKNOWN",
                detail={"unresolved": unresolved}
            ))

    # ───────────────────────────────────────────────────────────────────
    # MODULE 11: STRUCTURAL CHANGE
    # ───────────────────────────────────────────────────────────────────
    def _run_structural_change_rules(self, c: CompanyProfile) -> None:
        if c.name_change_pending and c.name_change_date and c.name_change_sr_passed is False:
            delay = (self.today - c.name_change_date).days
            if delay > SPECIAL_RESOLUTION_DEADLINE_DAYS:
                sev = Severity.RED if delay > 90 else Severity.YELLOW
                self._add_flag(ComplianceFlag(
                    rule_id="STR-001", flag_code="NAME_CHANGE_NOT_FILED",
                    severity=sev, score_impact=8 if delay > 90 else 3,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description=f"Name change not filed. Section 11 applies to change of company name; special-resolution filing under Section 88(1) is within 15 days. Overdue {delay} days.",
                    statutory_basis="Sections 11 and 88(1), Companies Act 1994 (Bangladesh)",
                    detail={"delay_days": delay}
                ))

        if c.object_clause_change_pending and c.object_clause_change_date:
            delay = (self.today - c.object_clause_change_date).days
            if delay > SPECIAL_RESOLUTION_DEADLINE_DAYS:
                sev = Severity.RED if delay > 90 else Severity.YELLOW
                self._add_flag(ComplianceFlag(
                    rule_id="STR-002", flag_code="OBJECT_CLAUSE_CHANGE_NOT_FILED",
                    severity=sev, score_impact=8 if delay > 90 else 3,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description=f"Memorandum object-clause alteration not filed. Sections 12 and 88(1) apply to the resolution filing; court confirmation/registration requirements under Sections 15-16 must be assessed separately. Overdue {delay} days.",
                    statutory_basis="Sections 12, 15-16 and 88(1), Companies Act 1994 (Bangladesh)",
                    detail={"delay_days": delay}
                ))

        if c.aoa_alteration_pending and c.aoa_alteration_date:
            delay = (self.today - c.aoa_alteration_date).days
            if delay > SPECIAL_RESOLUTION_DEADLINE_DAYS:
                sev = Severity.RED if delay > 90 else Severity.YELLOW
                self._add_flag(ComplianceFlag(
                    rule_id="STR-003", flag_code="AOA_ALTERATION_NOT_FILED",
                    severity=sev, score_impact=8 if delay > 90 else 3,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description=f"Articles alteration not filed. Section 20 and the special-resolution filing requirement in Section 88(1) apply; confirm any further registration steps before calculating a deadline. Overdue {delay} days.",
                    statutory_basis="Sections 20 and 88(1), Companies Act 1994 (Bangladesh)",
                    detail={"delay_days": delay}
                ))

    # ───────────────────────────────────────────────────────────────────
    # MODULE 12: ESCALATION
    # ───────────────────────────────────────────────────────────────────
    # MODULE 12: COMPANY WINDING-UP PROCEEDINGS (Companies Act 1994).
    # Do not conflate corporate winding-up with personal bankruptcy.
    # These booleans are reported facts only; each requires authenticated
    # court/RJSC records and route-specific counsel classification.
    def _run_insolvency_rules(self, c: CompanyProfile) -> None:
        if c.winding_up_petition_filed:
            self._add_flag(ComplianceFlag(
                rule_id="BNK-001",
                flag_code="WINDING_UP_PETITION_REQUIRES_CASE_VERIFICATION",
                severity=Severity.NOT_EVALUATED,
                score_impact=0,
                revenue_tier=RevenueTier.CORPORATE_RESCUE,
                description=(
                    "Reported company winding-up petition. Verify the Companies Act "
                    "1994 petition, grounds, court, case number, service, current status, "
                    "withdrawal/dismissal/stay and authenticated court record. "
                    "This is not a Bankruptcy Act finding or an automatic liability conclusion."
                ),
                statutory_basis="Companies Act 1994 (Bangladesh), Part V, including sections 241–244; exact petition provision requires case review",
                state=RuleState.REQUIRES_LAWYER_JUDGMENT,
                eval_state="UNKNOWN",
                detail={"petition_filed": True},
            ))

        if c.liquidator_appointed:
            self._add_flag(ComplianceFlag(
                rule_id="BNK-002",
                flag_code="LIQUIDATOR_APPOINTMENT_REQUIRES_ROUTE_VERIFICATION",
                severity=Severity.NOT_EVALUATED,
                score_impact=0,
                revenue_tier=RevenueTier.CORPORATE_RESCUE,
                description=(
                    "Reported liquidator appointment. Verify whether the appointment "
                    "arises from a court winding-up order, voluntary winding-up or "
                    "another statutory route; obtain the appointment instrument and "
                    "confirm the appointee's authority and current status."
                ),
                statutory_basis="Companies Act 1994 (Bangladesh), Part V; section 255 applies to court-appointed Official Liquidators; route-specific provision requires review",
                state=RuleState.REQUIRES_LAWYER_JUDGMENT,
                eval_state="UNKNOWN",
                detail={"liquidator_appointed": True},
            ))

        if c.court_ordered_winding_up:
            self._add_flag(ComplianceFlag(
                rule_id="BNK-003",
                flag_code="COURT_WINDING_UP_ORDER_REQUIRES_VERIFICATION",
                severity=Severity.NOT_EVALUATED,
                score_impact=0,
                revenue_tier=RevenueTier.CORPORATE_RESCUE,
                description=(
                    "Reported court winding-up order. Verify the authenticated order, "
                    "operative date, court jurisdiction, appeal/stay, correction, "
                    "suspension or discharge, and current liquidation status."
                ),
                statutory_basis="Companies Act 1994 (Bangladesh), Part V, including sections 241–246; exact order provision requires case review",
                state=RuleState.REQUIRES_LAWYER_JUDGMENT,
                eval_state="UNKNOWN",
                detail={"court_ordered": True},
            ))

    # MODULE 13: LABOUR COMPLIANCE (Labour Act 2006)
    @staticmethod
    def _manufacturing_applicability(c: CompanyProfile) -> ApplicabilityDecision:
        """Resolve factory-license applicability without treating missing facts as false."""
        if c.is_manufacturing is True:
            return ApplicabilityDecision(
                ApplicabilityState.APPLICABLE,
                "Manufacturing activity is affirmatively established.",
            )
        if c.is_manufacturing is False:
            return ApplicabilityDecision(
                ApplicabilityState.NOT_APPLICABLE,
                "Company is affirmatively recorded as non-manufacturing.",
            )
        return ApplicabilityDecision(
            ApplicabilityState.UNKNOWN,
            "Manufacturing status has not been established.",
        )

    def _run_labour_rules(self, c: CompanyProfile) -> None:
        applicability = self._manufacturing_applicability(c)

        # Factory-license obligations are evaluated only for established
        # manufacturing entities. UNKNOWN and NOT_APPLICABLE never create
        # a statutory breach or score deduction.
        if applicability.state is ApplicabilityState.APPLICABLE and c.factory_license_required_by_direction is True:
            # The profile does not yet bind a Government direction, class,
            # licence record and renewal terms to verified source evidence.
            # Never turn a user-entered boolean or expiry date into a breach.
            if c.factory_license_obtained is False:
                self._add_flag(ComplianceFlag(
                    rule_id="LBR-001",
                    flag_code="FACTORY_LICENSE_STATUS_REQUIRES_VERIFICATION",
                    severity=Severity.NOT_EVALUATED,
                    score_impact=0,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description="A factory/establishment licence may be required under section 326 only if the applicable Government direction covers this establishment/class. Verify the direction, class, commencement, exemption and authentic licence search before finding a default.",
                    statutory_basis="Bangladesh Labour Act 2006, Section 326, as amended by Act No. 43 of 2026",
                    state=RuleState.UNKNOWN,
                    eval_state="UNKNOWN",
                ))

            if c.factory_license_expiry and self.today > c.factory_license_expiry:
                delay = (self.today - c.factory_license_expiry).days
                self._add_flag(ComplianceFlag(
                    rule_id="LBR-002",
                    flag_code="FACTORY_LICENSE_EXPIRY_REQUIRES_VERIFICATION",
                    severity=Severity.NOT_EVALUATED,
                    score_impact=0,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description=f"Recorded licence expiry is {delay} days in the past. Verify the licence class, section 326 Government direction, five-year/contractor one-year term, renewal application, extension and operative status before finding a breach.",
                    statutory_basis="Bangladesh Labour Act 2006, Section 326, as amended by Act No. 43 of 2026",
                    state=RuleState.UNKNOWN,
                    eval_state="UNKNOWN",
                ))

        # LBR-003 is not gated by manufacturing status: applicability of an
        # existing labour-court order depends on the order's parties and scope.
        if c.labour_court_order_pending:
            # The current profile stores only a boolean, not the order,
            # parties, service, operative status, appeal or stay. Do not infer
            # a statutory breach or adverse score from that boolean.
            self._add_flag(ComplianceFlag(
                rule_id="LBR-003",
                flag_code="LABOUR_COURT_ORDER_STATUS_REQUIRES_VERIFICATION",
                severity=Severity.NOT_EVALUATED,
                score_impact=0,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description="The profile reports a pending Labour Court order. Verify the certified order, parties and company identity, service, operative directions, appeal/revision and any stay before determining applicability or non-compliance.",
                statutory_basis="Bangladesh Labour Act 2006 and the specific Labour Court order; enabling provision and operative status require case-specific verification",
                state=RuleState.UNKNOWN,
                eval_state="UNKNOWN",
                detail={"profile_order_status": "reported_pending", "order_evidence_verified": False, "stay_or_appeal_checked": False},
            ))

    # MODULE 14: ADDITIONAL COMPANIES ACT 1994
    def _run_companies_act_extended_rules(self, c: CompanyProfile) -> None:
        if c.agm_adjourned_without_notice:
            self._add_flag(ComplianceFlag(
                rule_id="AGM-007", flag_code="AGM_ADJOURNMENT_NOTICE_REQUIRES_REVIEW",
                severity=Severity.NOT_EVALUATED, score_impact=0,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description="An adjourned-AGM notice issue is reported. The applicable Articles, meeting resolution, adjournment terms, notice method and exact statutory consequence must be reviewed before classifying a breach.",
                statutory_basis="Companies Act 1994, Section 85 and the company Articles; exact adjournment provision requires counsel verification",
                state=RuleState.REQUIRES_LAWYER_JUDGMENT, eval_state="UNKNOWN",
                detail={"legal_review_required": True, "source_evidence_required": True}))
        if c.register_of_directors_interests is False:
            self._add_flag(ComplianceFlag(
                rule_id="DIR-005", flag_code="DIRECTOR_INTEREST_REGISTER_REQUIRES_REVIEW",
                severity=Severity.NOT_EVALUATED, score_impact=0,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description="The profile reports no director-interest register. Section 130 concerns disclosure of a director's interest in a company contract or arrangement; it does not by itself establish this generic register obligation. Verify the actual disclosure duty, Articles and records.",
                statutory_basis="Companies Act 1994, Section 130 (director-interest disclosure); generic register duty/title requires legal reconciliation",
                state=RuleState.REQUIRES_LAWYER_JUDGMENT, eval_state="UNKNOWN"))
        if c.register_of_contracts is False:
            self._add_flag(ComplianceFlag(
                rule_id="DIR-006", flag_code="REGISTER_OF_CONTRACTS_REQUIRES_REVIEW",
                severity=Severity.NOT_EVALUATED, score_impact=0,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description="The profile reports no register of contracts. No universal register duty has been established for this generic rule; verify the exact statutory provision, company Articles, contract category and evidence before any finding.",
                statutory_basis="Companies Act 1994 and applicable Articles; exact register obligation requires counsel verification",
                state=RuleState.REQUIRES_LAWYER_JUDGMENT, eval_state="UNKNOWN"))
        if c.voluntary_winding_up:
            self._add_flag(ComplianceFlag(
                rule_id="ESC-004", flag_code="VOLUNTARY_WINDING_UP_REQUIRES_STATUS_VERIFICATION",
                severity=Severity.NOT_EVALUATED, score_impact=0,
                revenue_tier=RevenueTier.CORPORATE_RESCUE,
                description=(
                    "Reported voluntary winding-up resolution. Verify the statutory "
                    "ground, special/extraordinary resolution, solvency declaration "
                    "where applicable, liquidator appointment, creditor process and "
                    "current status under Part V. No automatic BLACK classification."
                ),
                statutory_basis="Section 286 and following provisions, Companies Act 1994 (Bangladesh)",
                state=RuleState.REQUIRES_LAWYER_JUDGMENT, eval_state="UNKNOWN"))
        if c.investigation_order:
            self._add_flag(ComplianceFlag(
                rule_id="ESC-005", flag_code="INVESTIGATION_APPOINTMENT_REQUIRES_VERIFICATION",
                severity=Severity.NOT_EVALUATED, score_impact=0,
                revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
                description=(
                    "Reported company investigation. Verify the Government inspector "
                    "appointment under section 195 or 197, the scope of any section 199 "
                    "related-entity investigation, authenticated order, parties, status "
                    "and any resulting proceedings. A report or inquiry is not itself a finding of liability."
                ),
                statutory_basis="Sections 195 and 197; section 199 where related entities are included, Companies Act 1994 (Bangladesh)",
                state=RuleState.REQUIRES_LAWYER_JUDGMENT, eval_state="UNKNOWN"))

        # DIR-008: Section 104 contains role-specific exclusions. A bare
        # profile boolean does not establish the office category or absence of
        # general-meeting consent, so this remains a review prompt.
        if c.director_office_of_profit:
            self._add_flag(ComplianceFlag(
                rule_id="DIR-008", flag_code="DIRECTOR_OFFICE_OF_PROFIT_REQUIRES_REVIEW",
                severity=Severity.NOT_EVALUATED, score_impact=0,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description="Verify the exact office held, whether it falls within a statutory exception, the relevant company relationship and whether general-meeting consent was obtained. A profile boolean alone cannot establish a Section 104 breach.",
                statutory_basis="Section 104, Companies Act 1994 (Bangladesh)",
                state=RuleState.REQUIRES_LAWYER_JUDGMENT, eval_state="UNKNOWN"))
        # DIR-010: Section 110 limits appointment for more than five years
        # at a time; an old start date alone does not establish the current
        # appointment term or absence of a valid subsequent appointment.
        if c.managing_director_appointment_date:
            md_years = (self.today - c.managing_director_appointment_date).days // 365
            if md_years > 5:
                self._add_flag(ComplianceFlag(
                    rule_id="DIR-010", flag_code="MD_TERM_REQUIRES_REVIEW",
                    severity=Severity.NOT_EVALUATED, score_impact=0,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description=f"Managing director appointment record is {md_years} years old. Verify the current appointment instrument, term, reappointment, approval and continuity before assessing Section 110.",
                    statutory_basis="Section 110, Companies Act 1994 (Bangladesh)",
                    state=RuleState.REQUIRES_LAWYER_JUDGMENT, eval_state="UNKNOWN",
                    detail={"years_since_recorded_appointment": md_years}))

    # MODULE 15: BSEC CG CODE 2023
    def _run_bsec_rules(self, c: CompanyProfile) -> None:
        # The Code is not a universal private-company obligation. Even where
        # listed status is asserted, each condition requires verified scope,
        # current instrument version and condition-specific evidence. Until
        # those facts are verified, emit review prompts only.
        if c.bsec_listed:
            candidates = (
                ("BSEC-001", "QUARTERLY_REPORT_STATUS_REQUIRES_SOURCE_VERIFICATION",
                 c.bsec_quarterly_report_filed,
                 "Quarterly-report status requires the exact applicable BSEC reporting instrument, reporting period, issuer category and due date; it is not Condition 8 of the Corporate Governance Code."),
                ("BSEC-002", "CG_CERTIFICATE_STATUS_REQUIRES_VERIFICATION",
                 c.cg_certificate_obtained,
                 "Corporate-governance compliance certification is associated with Condition 9; verify listed-issuer scope, auditor/certifier, reporting year and filing evidence."),
                ("BSEC-003", "BOARD_COMPOSITION_STATUS_REQUIRES_VERIFICATION",
                 c.board_independent_director,
                 "Board composition is governed by Condition 1 as amended; verify board size, independent-director ratio, female independent-director requirement, eligibility and effective date."),
                ("BSEC-004", "AUDIT_COMMITTEE_STATUS_REQUIRES_VERIFICATION",
                 c.audit_committee_established,
                 "Audit Committee is addressed by Condition 5; verify committee composition, terms, meetings, independence and issuer applicability."),
            )
            for rule_id, flag_code, supplied_status, description in candidates:
                if supplied_status is False:
                    basis = (
                        "Applicable BSEC financial-reporting instrument; exact notification, issuer class, reporting period and due date require verification"
                        if rule_id == "BSEC-001"
                        else "BSEC Corporate Governance Code 2018, as amended by applicable 2023 and 2024 notifications; exact condition-specific applicability and evidence require verification"
                    )
                    self._add_flag(ComplianceFlag(
                        rule_id=rule_id,
                        flag_code=flag_code,
                        severity=Severity.NOT_EVALUATED,
                        score_impact=0,
                        revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                        description=description,
                        statutory_basis=basis,
                        state=RuleState.UNKNOWN,
                        eval_state="UNKNOWN",
                    ))

    # MODULE 16: FOREIGN EXCHANGE
    def _run_fx_rules(self, c: CompanyProfile) -> None:
        if c.foreign_exchange_violation:
            self._add_flag(ComplianceFlag(
                rule_id="FX-001", flag_code="FOREIGN_EXCHANGE_VIOLATION",
                severity=Severity.RED, score_impact=15,
                revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
                description="Foreign exchange violation. FE Regulation Act 1947.",
                statutory_basis="Foreign Exchange Regulation Act 1947 (Bangladesh)"))

    # ───────────────────────────────────────────────────────────────────
    # MODULE: BOARD MEETINGS (Section 95, 96, 89)
    # ───────────────────────────────────────────────────────────────────
    def _run_board_meeting_rules(self, c: CompanyProfile) -> None:
        # Companies Act 1994 section 96 applies to every company: at least one
        # Board meeting every three months and at least four in each year.
        # This profile currently lacks a complete, verified meeting-history
        # ledger, so it cannot prove either compliance or breach. Keep the rule
        # visible as NOT_EVALUATED rather than infer a violation from a single
        # date or from an unverified profile boolean.
        days_since = (
            (self.today - c.last_board_meeting_date).days
            if c.last_board_meeting_date is not None
            else None
        )
        self._add_flag(ComplianceFlag(
            rule_id="BOD-001",
            flag_code="BOARD_MEETING_HISTORY_REQUIRES_VERIFICATION",
            severity=Severity.NOT_EVALUATED,
            score_impact=0,
            revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
            description=(
                "Section 96 requires at least one Board meeting every three months "
                "and at least four meetings per year. The complete, verified meeting "
                "history and applicable period are not available in this profile; "
                "no breach or compliance conclusion can be made."
            ),
            statutory_basis="Section 96, Companies Act 1994 (Bangladesh)",
            state=RuleState.REQUIRES_LAWYER_JUDGMENT,
            eval_state="UNKNOWN",
            detail={
                "last_board_meeting_date": c.last_board_meeting_date.isoformat()
                if c.last_board_meeting_date else None,
                "days_since_last_meeting": days_since,
                "complete_verified_history_required": True,
            },
        ))

        # Section 95 requires written notice to every director then in Bangladesh.
        # The current boolean has no service/evidence binding, so retain a review
        # prompt rather than issue a confirmed breach.
        if c.last_board_meeting_date and c.board_meeting_notice_given is False:
            self._add_flag(ComplianceFlag(
                rule_id="BOD-002",
                flag_code="BOARD_NOTICE_REQUIRES_VERIFICATION",
                severity=Severity.NOT_EVALUATED,
                score_impact=0,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description="The profile reports that Board notice was not given. Verify the meeting notice, service to each director then in Bangladesh, address, dispatch/receipt evidence and any applicable Articles before classifying a breach.",
                statutory_basis="Section 95, Companies Act 1994 (Bangladesh)",
                state=RuleState.REQUIRES_LAWYER_JUDGMENT,
                eval_state="UNKNOWN",
            ))

        # Section 89 requires minutes, but absence of an uploaded record is not
        # proof that minutes were never prepared. Require documentary review.
        if c.last_board_meeting_date and c.board_minutes_prepared is False:
            self._add_flag(ComplianceFlag(
                rule_id="BOD-003",
                flag_code="BOARD_MINUTES_REQUIRES_VERIFICATION",
                severity=Severity.NOT_EVALUATED,
                score_impact=0,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description="The profile reports that Board minutes were not prepared. Verify the minute book, subsequent approval/signature, custody and inspection records; missing upload alone does not establish non-creation.",
                statutory_basis="Section 89, Companies Act 1994 (Bangladesh)",
                state=RuleState.REQUIRES_LAWYER_JUDGMENT,
                eval_state="UNKNOWN",
            ))

    # ───────────────────────────────────────────────────────────────────
    # MODULE: ACCOUNTS & AUDIT FILING (Section 181, 183, 190)
    # ───────────────────────────────────────────────────────────────────
    def _run_accounts_rules(self, c: CompanyProfile) -> None:
        # ACC-001: Financial statements not presented at AGM (Section 183)
        if c.agm_held_this_cycle and c.financial_statements_presented is False:
            self._add_flag(ComplianceFlag(
                rule_id="ACC-001",
                flag_code="FINANCIAL_STATEMENTS_NOT_PRESENTED",
                severity=Severity.RED,
                score_impact=15,
                revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
                description="AGM held but balance sheet and P&L not presented. Section 183: Board shall lay before AGM.",
                statutory_basis="Section 183, Companies Act 1994 (Bangladesh)",
            ))

        # ACC-002: Section 190 allows 30 days after the AGM, or if no AGM
        # was held, 30 days after the latest date on which it should have been held.
        if c.financial_statements_filed is False and self._agm_history_is_verified(c):
            filing_deadline: date | None = None
            deadline_basis: str | None = None
            agm_due: date | None = None
            if c.agm_held_this_cycle is True and c.last_agm_date is not None:
                filing_deadline = c.last_agm_date + timedelta(days=30)
                deadline_basis = "30 days after AGM"
            elif c.agm_held_this_cycle is False:
                if c.agm_count == 0 and c.incorporation_date is not None:
                    agm_due = self._add_months(c.incorporation_date, 18)
                elif c.agm_count is not None and c.agm_count > 0 and c.last_agm_date is not None:
                    agm_due = self._subsequent_agm_deadline(c)
                if agm_due is not None:
                    filing_deadline = agm_due + timedelta(days=30)
                    deadline_basis = "30 days after latest date AGM should have been held"
            if filing_deadline is not None and self.today > filing_deadline:
                delay = (self.today - filing_deadline).days
                self._add_flag(ComplianceFlag(
                    rule_id="ACC-002",
                    flag_code="FINANCIAL_STATEMENTS_NOT_FILED",
                    severity=Severity.RED,
                    score_impact=15,
                    revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
                    description=f"Financial statements not filed with Registrar within 30 days of {deadline_basis}. Overdue by {delay} days. Section 190.",
                    statutory_basis="Section 190, Companies Act 1994 (Bangladesh)",
                    detail={"delay": delay, "filing_deadline": str(filing_deadline), "deadline_basis": deadline_basis},
                ))

        # ACC-003: Books of account not kept (Section 181)
        if c.books_of_account_kept is False:
            self._add_flag(ComplianceFlag(
                rule_id="ACC-003",
                flag_code="BOOKS_NOT_KEPT",
                severity=Severity.RED,
                score_impact=15,
                revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
                description="Proper books of account not maintained. Section 181: every company shall keep proper books.",
                statutory_basis="Section 181, Companies Act 1994 (Bangladesh)",
            ))

    def _run_escalation_rules(self, c: CompanyProfile) -> None:
        agm_years = self._calculate_agm_default_years(c)
        ar_years = c.unfiled_returns_count or 0  # defensive: None → 0

        # ═════════════════════════════════════════════════════════════════
        # P0 LEGAL FIX: DEF-001 — Director Disqualified (Section 94)
        # ═════════════════════════════════════════════════════════════════
        # Section 94 of the Companies Act 1994 (Bangladesh) lists these
        # disqualification grounds:
        #   (a) Declared of unsound mind by competent court (while in force)
        #   (b) Undischarged insolvent
        #   (c) Applied to be adjudicated insolvent & application pending
        #   (d) Unpaid call on shares 6+ months after deadline
        #   (e) Minor (under 18)
        # Section 94(2): AoA may prescribe additional grounds.
        #
        # CRITICAL: Section 94 does NOT specify a "5-year" disqualification
        # period. The previous description claiming "Cannot act as director
        # for 5 years" was legally unsupported and has been removed.
        #
        # Evidence gating: Section 94 findings require structured grounds,
        # director identity, authoritative evidence, effective date and current
        # status. DEF-001 is not a BLACK override and is excluded from scoring
        # pending independent legal approval. Unpaid-call threshold is DISPUTED
        # across official Bengali and English/case materials.
        # ═════════════════════════════════════════════════════════════════

        VALID_GROUNDS = {
            "UNSOUND_MIND", "UNDISCHARGED_INSOLVENT", "PENDING_INSOLVENCY",
            "UNPAID_CALL", "MINOR", "AOA_PRESCRIBED",
        }

        # Check for verified, structured disqualification grounds
        verified_grounds = []
        unverified_allegations: list[dict[str, Any] | str] = []
        disputed_grounds = []

        if c.disqualification_grounds:
            for g in c.disqualification_grounds:
                ground_type = g.get("ground_type", "")
                evidence_ref = g.get("evidence_ref")
                authority = g.get("authority")
                director_name = g.get("director_name")
                effective_date = g.get("effective_date")
                continuing = g.get("continuing_status")
                base_evidence_complete = (
                    isinstance(director_name, str) and director_name.strip()
                    and isinstance(evidence_ref, str) and evidence_ref.strip()
                    and isinstance(authority, str) and authority.strip()
                    and bool(effective_date)
                    and continuing is True
                )
                if ground_type == "UNPAID_CALL" and base_evidence_complete:
                    # BDLaws Bengali text states 180 days; English materials and
                    # some case materials describe six months. Keep this disputed
                    # until a Bangladesh company-law reviewer resolves the text.
                    disputed_grounds.append(g)
                elif (
                    ground_type in VALID_GROUNDS
                    and base_evidence_complete
                    and (
                        ground_type != "AOA_PRESCRIBED"
                        or bool(g.get("aoa_provision_ref"))
                    )
                ):
                    verified_grounds.append(g)
                else:
                    unverified_allegations.append(g)

        # Legacy path: disqualification_details (free-text) without structured grounds
        # → treat as unverified allegations, NOT as BLACK override
        if not c.disqualification_grounds and c.disqualification_details:
            unverified_allegations.extend(c.disqualification_details)

        if disputed_grounds:
            self._add_flag(ComplianceFlag(
                rule_id="DEF-001",
                flag_code="DIRECTOR_DISQUALIFICATION_GROUND_DISPUTED",
                severity=Severity.NOT_EVALUATED,
                score_impact=0,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description="Unpaid-call disqualification evidence is recorded, but statutory materials differ on the threshold (180 days versus six months). Legal review is required before classifying this as a confirmed disqualification.",
                statutory_basis="Section 94(1)(d), Companies Act 1994 (Bangladesh)",
                state=RuleState.DISPUTED,
                eval_state="UNKNOWN",
                detail={"disputed_grounds": disputed_grounds, "legal_review_required": True},
            ))

        if verified_grounds:
            disq_count = len(verified_grounds)
            # Disqualification is a statutory finding; automatic BLACK is an
            # NLC risk-policy choice, not a consequence prescribed by Section 94.
            impact = 10
            ground_summary = "; ".join(
                f"{g.get('director_name', 'Director')}: {g.get('ground_type', 'unknown')}"
                for g in verified_grounds
            )
            self._add_flag(ComplianceFlag(
                rule_id="DEF-001",
                flag_code="DIRECTOR_DISQUALIFIED",
                severity=Severity.RED,
                score_impact=impact,
                revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
                description=(
                    f"{disq_count} director(s) disqualified under Section 94 "
                    f"({ground_summary}). Verified evidence on file. "
                    f"Director(s) cannot act until disqualification ceases per S94."
                ),
                statutory_basis="Section 94, Companies Act 1994 (Bangladesh)",
                detail={
                    "disqualifications": verified_grounds,
                    "count": disq_count,
                    "evidence_verified": True,
                },
                is_black_override=False,
            ))
        elif unverified_allegations:
            # P0 EVIDENCE SEMANTICS: Unverified disqualification allegations
            # must NOT trigger BLACK override. Emit as NOT_EVALUATED to
            # signal that legal verification is required before any
            # compliance determination can be made.
            self._add_flag(ComplianceFlag(
                rule_id="DEF-001",
                flag_code="DIRECTOR_DISQUALIFICATION_UNVERIFIED",
                severity=Severity.NOT_EVALUATED,
                score_impact=0,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description=(
                    "Disqualification allegation(s) received for director(s) "
                    "but evidence NOT verified. Section 94 requires a "
                    "competent court declaration, insolvency certificate, "
                    "or other authoritative determination. Cannot determine "
                    "compliance status until evidence is reviewed."
                ),
                statutory_basis="Section 94, Companies Act 1994 (Bangladesh)",
                detail={
                    "allegations": unverified_allegations,
                    "evidence_verified": False,
                    "action_required": "Obtain court order or authoritative evidence per S94 ground",
                },
                state=RuleState.UNKNOWN,
            ))

        if agm_years >= 2 and ar_years >= 2:  # type: ignore
            self._add_flag(ComplianceFlag(
                rule_id="ESC-001",
                flag_code="STRIKE_OFF_STATUS_REQUIRES_REVIEW",
                severity=Severity.NOT_EVALUATED,
                score_impact=0,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description="A multi-year AGM/annual-return backlog is an internal escalation indicator only. It does not establish that RJSC has commenced strike-off. Verify the Section 346 grounds, Registrar notice, service, procedural stage, appeal, restoration and current company status.",
                statutory_basis="Section 346, Companies Act 1994 (Bangladesh); Registrar process and case-specific evidence required",
                state=RuleState.REQUIRES_LAWYER_JUDGMENT,
                eval_state="UNKNOWN",
                detail={"agm_years": agm_years, "ar_years": ar_years, "official_notice_required": True}
            ))

        if (
            agm_years >= 3
            or ar_years >= 3
            or c.rjsc_strike_off_notice_date is not None
            or c.on_rjsc_strike_off_list
        ):
            # Suppress ESC-001 if ESC-002 is firing
            self._flags = [f for f in self._flags if f.rule_id != "ESC-001"]
            self._add_flag(ComplianceFlag(
                rule_id="ESC-002",
                flag_code="STRIKE_OFF_RISK_REVIEW_REQUIRED",
                severity=Severity.NOT_EVALUATED,
                score_impact=0,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description="Three or more years of apparent filing default or an RJSC strike-off-list indicator requires case-specific lawyer review. This is not a finding that strike-off is imminent or that dissolution has occurred.",
                statutory_basis="Section 346, Companies Act 1994 (Bangladesh); Registrar process and case-specific evidence required",
                detail={"agm_years": agm_years, "ar_years": ar_years, "notice_date": c.rjsc_strike_off_notice_date, "on_list": c.on_rjsc_strike_off_list},
                state=RuleState.REQUIRES_LAWYER_JUDGMENT,
                eval_state="UNKNOWN",
                is_black_override=False,
                escalation_pending=True,
            ))

        pre_score = self._calculate_raw_score(self._flags)
        has_black_override = any(
            f.rule_id in VERIFIED_RULE_IDS
            and f.rule_id in AUTHORIZED_BLACK_OVERRIDE_RULE_IDS
            and f.is_black_override
            and f.severity == Severity.BLACK
            and f.state in (RuleState.NON_COMPLIANT, RuleState.VERIFIED_ABSENT)
            and f.eval_state == "VIOLATION"
            for f in self._flags if not f.resolved and f.conditional_applies
        )

        if legal_score_is_released() and (pre_score <= 29 or has_black_override):
            black_count = len([
                f for f in self._flags
                if f.rule_id in VERIFIED_RULE_IDS
                and f.rule_id in AUTHORIZED_BLACK_OVERRIDE_RULE_IDS
                and f.is_black_override
                and f.severity == Severity.BLACK
                and f.state in (RuleState.NON_COMPLIANT, RuleState.VERIFIED_ABSENT)
                and f.eval_state == "VIOLATION"
                and not f.resolved and f.conditional_applies
                and f.rule_id not in self._ESC_RULE_IDS
            ])
            esc003_impact = 10 if black_count <= 2 else (25 if black_count == 3 else 35)
            self._add_flag(ComplianceFlag(
                rule_id="ESC-003",
                flag_code="RESCUE_REQUIRED_MANDATORY",
                severity=Severity.BLACK,
                score_impact=esc003_impact,
                revenue_tier=RevenueTier.CORPORATE_RESCUE,
                description="NLC risk policy: rescue workflow recommended. Systemic failure detected.",
                statutory_basis="NLC internal risk policy; not a statutory risk band under the Companies Act 1994.",
                detail={"black_count": black_count, "pre_score": pre_score},
                is_black_override=True,
                state=RuleState.NON_COMPLIANT
            ))

    # ───────────────────────────────────────────────────────────────────
    # SCORING ENGINE
    # ───────────────────────────────────────────────────────────────────
    def _score_to_band(self, raw: int, *, force_black: bool = False, coverage: float = 1.0) -> str:
        """Map a raw score to a risk band string.
        coverage is weighted company-profile input completeness (0.0 to 1.0),
        not statutory-rule coverage or legal verification completeness.
        Below 0.5 → NOT_EVALUATED — UNLESS force_black is set, in which case
        we have confirmed BLACK findings and the company is definitively in
        trouble, not 'unknown'. Prevents the rescue_sequence generator from
        skipping BLACK-override companies with sparse profile data."""
        if force_black:
            return "BLACK"
        if coverage < 0.5:
            return "NOT_EVALUATED"
        if raw <= 29:
            return "BLACK"
        if raw <= 49:
            return "RED"
        if raw <= 69:
            return "YELLOW"
        return "GREEN"


    def _eligible_scoring_flags(
        self, flags: List[ComplianceFlag]
    ) -> List[ComplianceFlag]:
        """Return only active, confirmed findings admitted by the legal gate."""
        return [
            flag for flag in flags
            if not flag.resolved
            and flag.conditional_applies
            and flag.state in (RuleState.NON_COMPLIANT, RuleState.VERIFIED_ABSENT)
            and flag.eval_state == "VIOLATION"
            and legal_score_is_released()
            and flag.rule_id in VERIFIED_RULE_IDS
        ]

    @staticmethod
    def _category_deductions(
        scored: List[ComplianceFlag],
    ) -> Dict[str, int]:
        """Apply one authoritative prefix map and per-category cap."""
        totals = {category: 0 for category in CATEGORY_CAPS}
        for flag in scored:
            matches = [
                category
                for category, (_, prefixes) in CATEGORY_CAPS.items()
                if flag.rule_id.startswith(prefixes)
            ]
            if len(matches) > 1:
                raise ValueError(
                    f"Rule {flag.rule_id} maps to multiple scoring categories: {matches}"
                )
            if matches:
                totals[matches[0]] += flag.score_impact
        return {
            category: min(total, CATEGORY_CAPS[category][0])
            for category, total in totals.items()
        }

    @staticmethod
    def _score_from_deductions(deductions: Dict[str, int]) -> int:
        return max(0, min(100, 100 - sum(deductions.values())))

    def _calculate_raw_score(self, flags: List[ComplianceFlag]) -> int:
        """Calculate the pre-escalation score using the authoritative formula."""
        scored = self._eligible_scoring_flags(flags)
        return self._score_from_deductions(self._category_deductions(scored))

    def _calculate_score(self, flags: List[ComplianceFlag], company: CompanyProfile) -> ScoreBreakdown:
        active = [f for f in flags if not f.resolved and f.conditional_applies]

        # One eligibility filter and one category-cap implementation are
        # shared with the pre-escalation score to prevent calculation drift.
        scored = self._eligible_scoring_flags(flags)
        deductions = self._category_deductions(scored)
        tax_ded = deductions["TAX"]
        agm_ded = deductions["AGM"]
        aud_ded = deductions["AUD"]
        ret_ded = deductions["RET"]
        dir_ded = deductions["DIR"]
        shr_ded = deductions["SHR"]
        cap_ded = deductions["CAP"]
        off_ded = deductions["OFF"]
        reg_ded = deductions["REG"]
        bnk_ded = deductions["BNK"]
        lbr_ded = deductions["LBR"]
        bsec_ded = deductions["BSEC"]
        fx_ded = deductions["FX"]
        esc_ded = deductions["ESC"]
        raw = self._score_from_deductions(deductions)
        
        override = False
        reason = None
        final = raw if legal_score_is_released() else 100
        critical = []
        if legal_score_is_released():
            critical = [
                f for f in active
                if f.rule_id in VERIFIED_RULE_IDS
                and f.rule_id in AUTHORIZED_BLACK_OVERRIDE_RULE_IDS
                and f.is_black_override
                and f.severity == Severity.BLACK
                and f.state in (RuleState.NON_COMPLIANT, RuleState.VERIFIED_ABSENT)
                and f.eval_state == "VIOLATION"
            ]
        if critical:
            override = True
            reason = f"BLACK: {', '.join(f.rule_id for f in critical)}"
            final = 0

        coverage = _input_coverage(company)
        # A 100-point arithmetic placeholder is not a compliance certification.
        # Keep the band NOT_EVALUATED until the full legal corpus is independently approved.
        score_band = (
            Severity(self._score_to_band(final, force_black=bool(critical), coverage=coverage))
            if legal_score_is_released() else Severity.NOT_EVALUATED
        )

        # Band = worst of (score-based band, highest active flag severity)
        # Prevents false GREEN when a RED-severity rule fires (BLACK handled above)'t override
        if legal_score_is_released() and not critical:
            severity_rank = {Severity.GREEN: 0, Severity.YELLOW: 1, Severity.RED: 2, Severity.BLACK: 3}
            max_flag_severity = Severity.GREEN
            for f in active:
                if (
                    f.rule_id in VERIFIED_RULE_IDS
                    and (
                        f.severity == Severity.RED
                        or (
                            f.severity == Severity.BLACK
                            and f.rule_id in AUTHORIZED_BLACK_OVERRIDE_RULE_IDS
                            and f.is_black_override
                        )
                    )
                    and f.state in (RuleState.NON_COMPLIANT, RuleState.VERIFIED_ABSENT)
                    and f.eval_state == "VIOLATION"
                ):
                    if severity_rank[f.severity] > severity_rank.get(max_flag_severity, 0):
                        max_flag_severity = f.severity
            band_rank = severity_rank.get(score_band, 0)
            flag_rank = severity_rank.get(max_flag_severity, 0)
            band = max_flag_severity if flag_rank > band_rank else score_band
        else:
            band = score_band

        if band == Severity.NOT_EVALUATED or band in (Severity.GREEN, Severity.YELLOW):
            exposure = ExposureBand.LOW
        elif band == Severity.RED:
            exposure = ExposureBand.HIGH
        else:
            exposure = ExposureBand.SEVERE

        flag_signatures = sorted(
            f"{f.rule_id}:{f.state!s}:{f.eval_state}:{f.severity!s}:{f.score_impact}:{f.rule_version}"
            for f in active
        )
        hash_payload = {
            "company_profile": asdict(company),
            "evaluation_date": self.today.isoformat(),
            "engine_version": RULE_ENGINE_VERSION,
            "ilrmf_version": ILRMF_VERSION,
            "verified_rule_ids": sorted(VERIFIED_RULE_IDS),
            "category_caps": {
                key: {"max_deduction": cap, "prefixes": list(prefixes)}
                for key, (cap, prefixes) in sorted(CATEGORY_CAPS.items())
            },
            "profile_coverage_weights": dict(sorted(_COVERAGE_FIELDS.items())),
            "coverage_basis": "WEIGHTED_PROFILE_INPUT_COMPLETENESS",
            "category_deductions": deductions,
            "legal_score_release_switch": LEGAL_SCORE_RELEASED,
            "legal_score_released": legal_score_is_released(),
            "flags": flag_signatures,
            "final_score": final,
        }
        hash_str = json.dumps(
            hash_payload, sort_keys=True, separators=(",", ":"),
            default=lambda value: value.value if isinstance(value, Enum) else value.isoformat() if isinstance(value, date) else str(value),
        )
        score_hash = hashlib.sha256(hash_str.encode("utf-8")).hexdigest()

        return ScoreBreakdown(
            agm_score=max(0, 20 - agm_ded),
            audit_score=max(0, 20 - aud_ded),
            return_score=max(0, 20 - ret_ded),
            director_score=max(0, 10 - dir_ded),
            shareholding_score=max(0, 10 - shr_ded),
            capital_score=max(0, 5 - cap_ded),
            office_score=max(0, 5 - off_ded),
            register_score=max(0, 5 - reg_ded),
            tax_score=max(0, 5 - tax_ded),
            raw_total=raw,
            final_score=final,
            override_applied=override,
            override_reason=reason,
            risk_band=band,
            exposure_band=exposure,
            revenue_tier=REVENUE_TIER_MAP[band],
            active_flag_count=len(active),
            coverage=coverage,
            black_flag_count=len([f for f in active if legal_score_is_released() and f.rule_id in VERIFIED_RULE_IDS and f.severity == Severity.BLACK and f.state in (RuleState.NON_COMPLIANT, RuleState.VERIFIED_ABSENT) and f.eval_state == "VIOLATION"]),
            red_flag_count=len([f for f in active if legal_score_is_released() and f.rule_id in VERIFIED_RULE_IDS and f.severity == Severity.RED and f.state in (RuleState.NON_COMPLIANT, RuleState.VERIFIED_ABSENT) and f.eval_state == "VIOLATION"]),
            yellow_flag_count=len([f for f in active if f.severity == Severity.YELLOW and f.state in (RuleState.NON_COMPLIANT, RuleState.VERIFIED_ABSENT) and f.eval_state == "VIOLATION"]),
            green_flag_count=len([f for f in active if f.severity == Severity.GREEN and f.state in (RuleState.NON_COMPLIANT, RuleState.VERIFIED_ABSENT) and f.eval_state == "VIOLATION"]),
            bankruptcy_score=max(0, 5 - bnk_ded),
            labour_score=max(0, 5 - lbr_ded),
            bsec_score=max(0, 5 - bsec_ded),
            fx_score=max(0, 5 - fx_ded),
            escalation_score=max(0, 5 - esc_ded),
            score_hash=score_hash,
            category_deductions=deductions,
            coverage_basis="WEIGHTED_PROFILE_INPUT_COMPLETENESS",
        )

    # ───────────────────────────────────────────────────────────────────
    # RESCUE & LIFECYCLE SEQUENCING
    # ───────────────────────────────────────────────────────────────────
    def _generate_rescue_sequence(self, c: CompanyProfile, flags: List[ComplianceFlag], score: ScoreBreakdown) -> List[Dict[str, Any]]:
        flags = [f for f in flags if getattr(f, "eval_state", "VIOLATION") != "UNKNOWN"]  # F3: exclude UNKNOWN from rescue
        """R-014: Generate rescue steps only from active, verified findings.

        TAX-004 is aggregated into one step because its missed-quarter details
        describe one remediation item. Missing quarter evidence does not itself
        establish a missed payment.
        """
        active = [
            f for f in flags
            if not f.resolved and f.conditional_applies
        ]
        if score.risk_band not in (Severity.RED, Severity.BLACK):
            return []

        # Rescue is generated only for confirmed RED/BLACK findings.
        # YELLOW findings remain visible in compliance reporting and do not
        # receive a rescue workflow under the current policy.
        actionable = [
            f for f in active
            if legal_score_is_released()
            and f.rule_id in VERIFIED_RULE_IDS
            and f.state in (RuleState.NON_COMPLIANT, RuleState.VERIFIED_ABSENT)
            and f.eval_state == "VIOLATION"
            and f.severity in (Severity.RED, Severity.BLACK)
        ]
        if not actionable:
            return []

        try:
            from canonical_architecture.statutory_rescue import (
                STATUTORY_RESCUE_REGISTRY,
            )
        except ImportError as e:
            import logging
            logging.getLogger(__name__).error(
                f"Failed to import STATUTORY_RESCUE_REGISTRY: {e}"
            )
            return []

        steps = []
        tax004_processed = False

        for flag in actionable:
            if flag.rule_id == "TAX-004":
                if tax004_processed:
                    continue
                tax004_processed = True

                tax_flags = [
                    f for f in actionable if f.rule_id == "TAX-004"
                ]
                missed_quarters = []
                seen_quarters = set()

                for tax_flag in tax_flags:
                    detail = tax_flag.detail or {}
                    quarters = detail.get("quarters", [])
                    if not isinstance(quarters, (list, tuple, set)):
                        continue
                    for quarter in quarters:
                        if quarter is None:
                            continue
                        quarter_label = str(quarter).strip()
                        if quarter_label and quarter_label not in seen_quarters:
                            seen_quarters.add(quarter_label)
                            missed_quarters.append(quarter_label)

                # No documented missed quarter means no TAX-004 rescue step.
                if not missed_quarters:
                    continue

                rescue = STATUTORY_RESCUE_REGISTRY.get("TAX-004")
                if not rescue:
                    raise ValueError(
                        "Missing statutory rescue mapping for actionable "
                        "finding: TAX-004"
                    )

                priority = (
                    "CRITICAL"
                    if any(f.severity == Severity.BLACK for f in tax_flags)
                    else "HIGH"
                )
                actions = rescue.get("statutory_actions", [])
                desc = "; ".join(actions) if actions else rescue.get(
                    "objective", "Remediate TAX-004"
                )
                desc = f"Missed quarters: {', '.join(missed_quarters)}. {desc}"

                steps.append({
                    "title": rescue.get("objective", "Remediate TAX-004"),
                    "description": desc,
                    "related_rules": ["TAX-004"],
                    "priority": priority,
                    "min_days": 7,
                    "max_days": 30,
                    "rescue_id": rescue.get("rescue_id", ""),
                    "authority": rescue.get("authority", ""),
                    "closure_condition": rescue.get("closure_condition", ""),
                    "statutory_basis": rescue.get("statutory_basis") or getattr(tax_flags[0], "statutory_basis", "") if tax_flags else "",
                    "complexity": rescue.get("complexity"),
                    "estimated_days_min": rescue.get("estimated_days_min"),
                    "estimated_days_max": rescue.get("estimated_days_max"),
                })
                continue

            rescue = STATUTORY_RESCUE_REGISTRY.get(flag.rule_id)
            if not rescue:
                raise ValueError(
                    "Missing statutory rescue mapping for actionable finding: "
                    f"{flag.rule_id}"
                )

            priority = (
                "CRITICAL" if flag.severity == Severity.BLACK else "HIGH"
            )
            actions = rescue.get("statutory_actions", [])
            desc = "; ".join(actions) if actions else rescue.get(
                "objective", f"Remediate {flag.rule_id}"
            )

            steps.append({
                "title": rescue.get("objective", f"Remediate: {flag.rule_id}"),
                "description": desc,
                "related_rules": [flag.rule_id],
                "priority": priority,
                "min_days": 7,
                "max_days": 30,
                "rescue_id": rescue.get("rescue_id", ""),
                "authority": rescue.get("authority", ""),
                "closure_condition": rescue.get("closure_condition", ""),
                "statutory_basis": rescue.get("statutory_basis") or getattr(flag, "statutory_basis", ""),
                "complexity": rescue.get("complexity"),
                "estimated_days_min": rescue.get("estimated_days_min"),
                "estimated_days_max": rescue.get("estimated_days_max"),
            })

        priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        steps.sort(key=lambda step: (
            priority_order.get(step["priority"], 9),
            step["min_days"],
        ))
        return steps

    def _determine_lifecycle_stage(self, c: CompanyProfile) -> LifecycleStage:
        if c.on_rjsc_strike_off_list or c.is_dormant:
            return LifecycleStage.DORMANT_STRIKE_OFF
        has_black = any(f.severity == Severity.BLACK and not f.resolved for f in self._flags)
        has_red = any(f.severity == Severity.RED and not f.resolved for f in self._flags)

        if has_black:
            return LifecycleStage.STATUTORY_DEFAULT
        if c.agm_count == 0:
            return LifecycleStage.PRE_FIRST_AGM
        if has_red:
            return LifecycleStage.IRREGULAR_STATUS
            
        return LifecycleStage.ANNUAL_COMPLIANCE_CYCLE

    # ───────────────────────────────────────────────────────────────────
    # HELPERS
    # ───────────────────────────────────────────────────────────────────
    def _fiscal_quarter(self) -> int:
        """Return current fiscal quarter (1-4) for Bangladesh FY (Jul-Jun)."""
        m = self.today.month
        if m <= 3:
            return 3  # Jan-Mar = Q3
        if m <= 6:
            return 4  # Apr-Jun = Q4
        if m <= 9:
            return 1  # Jul-Sep = Q1
        return 2              # Oct-Dec = Q2

    def _add_flag(self, flag: ComplianceFlag) -> None:
        self._flags.append(flag)

    def _graduated_agm_deduction(self, delay: int) -> int:
        if delay <= 90:
            return 5
        if delay <= 180:
            return 10
        if delay <= 365:
            return 15
        return 20

    def _graduated_ar_deduction(self, delay: int) -> int:
        if delay <= 60:
            return 3
        if delay <= 180:
            return 5
        return 10

    def _get_fy_end_deadline(self, c: CompanyProfile) -> date:
        # FIX Defect 20: Use company's actual financial_year_end instead of hardcoded 30 June.
        fy_end = c.financial_year_end
        if fy_end is None:
            # Fallback: use 6 months after incorporation, or today if no incorporation date
            base = c.incorporation_date or self.today
            fy_end = date(base.year, base.month, base.day)
        while c.last_agm_date and c.last_agm_date > fy_end:
            fy_end = date(fy_end.year + 1, fy_end.month, fy_end.day)
        return fy_end + timedelta(days=FY_END_AGM_DEADLINE_DAYS)

    def _calculate_agm_default_years(self, c: CompanyProfile) -> int:
        if not self._agm_history_is_verified(c) or c.agm_count is None:
            return 0
        if c.agm_count == 0:
            if c.incorporation_date is None:
                return 0
            deadline: date | None = self._add_months(c.incorporation_date, 18)
        else:
            if c.last_agm_date is None:
                return 0
            deadline = self._subsequent_agm_deadline(c)
            deadline = self._subsequent_agm_deadline(c)
        if deadline is None:
            return 0
        if self.today > deadline:
            return (self.today - deadline).days // 365
        return 0
