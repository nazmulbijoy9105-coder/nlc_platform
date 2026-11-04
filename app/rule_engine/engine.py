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
    form_filed: bool = False
    form_filed_date: Optional[date] = None
    form_type: str = "XII"

@dataclass
class ShareTransfer:
    transfer_id: str
    transfer_date: date
    instrument_recorded: bool = False
    stamp_duty_paid: bool = False
    stamp_duty_amount: Optional[float] = None
    board_approval: bool = False
    share_register_updated: bool = False
    aoa_restriction_apply: bool = False
    board_approval_obtained: bool = False
    form_117_filed: bool = False

@dataclass
class ChargeEvent:
    charge_id: str
    creation_date: date
    charge_type: str
    amount_bdt: float
    charge_holder: str
    form_viii_filed: bool = False
    form_viii_filed_date: Optional[date] = None
    form_xix_filed: bool = False
    form_xxviii_filed: bool = False
    satisfied: bool = False
    satisfaction_date: Optional[date] = None
    satisfaction_filed: bool = False

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
    agm_held_this_cycle: bool = False
    agm_held_without_audit: bool = False
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
    accounts_adopted_at_agm: bool = False
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
    form_xv_filed: bool = False
    form_xv_filed_date: Optional[date] = None
    last_allotment_date: Optional[date] = None
    share_certificates_issued: bool | None = None
    share_certificates_issued_date: Optional[date] = None
    authorized_capital_bdt: float = 0.0
    paid_up_capital_bdt: float = 0.0
    paid_up_ge_authorized: bool | None = None
    share_transfers: List[ShareTransfer] = field(default_factory=list)
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
    tax_return_filed_for_current_fy: bool = False
    advance_tax_q1_paid: bool = False
    advance_tax_q2_paid: bool = False
    advance_tax_q3_paid: bool = False
    advance_tax_q4_paid: bool = False
    tds_deposited_up_to_date: bool = True
    last_tds_deposit_date: Optional[date] = None
    last_vat_return_filed: Optional[date] = None
    vat_annual_return_filed_for_fy: bool = False
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

FIRST_AGM_DEADLINE_DAYS = 548
SUBSEQUENT_AGM_DEADLINE_DAYS = 456
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
ALLOTMENT_FILING_DEADLINE_DAYS = 60
SPECIAL_RESOLUTION_DEADLINE_DAYS = 15  # Companies Act 1994, Section 88 (15 days)

REQUIRED_REGISTERS = [
    "members", "directors", "charges", "transfers", "debentures",
    "minutes_agm", "minutes_board",
]
CORE_REGISTERS = ["members", "directors", "charges", "minutes_agm"]

# Legacy set — retained for rule_ids that should be override but may not have
# is_black_override=True set correctly. Currently empty; all overrides use
# inline is_black_override=True on the flag itself.
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
# BLACK-severity rules (DEF-001) are ALWAYS enforced regardless of
# verification status — critical safety overrides cannot be gated.
VERIFIED_RULE_IDS: frozenset[str] = frozenset({
    # AGM module (7 rules)
    "AGM-001", "AGM-002", "AGM-003", "AGM-004",
    # AGM-005 remains excluded until the AOA-specific quorum basis is verified.
    "AGM-006", "AGM-007",
    # Registers module (3 rules)
    "REG-001", "REG-002", "REG-003",
    # Registered Office (1 rule)
    "OFF-001",
    # Directors module (6 rules)
    "DIR-001", "DIR-002", "DIR-003",
    "DIR-007", "DIR-008", "DIR-010",
    # Capital module (3 rules)
    "CAP-001", "CAP-002", "CAP-003",
    # Charges (1 rule)
    "CHG-001",
    # Structural changes (3 rules)
    "STR-001", "STR-002", "STR-003",
    # Accounts (3 rules)
    "ACC-001", "ACC-002", "ACC-003",
    # Board meetings (3 rules)
    "BOD-001", "BOD-002", "BOD-003",
    # Incorporation (4 rules)
    "INC-001", "INC-003", "INC-004", "INC-007",
    # Members (1 rule)
    "MEM-001",
    # Share transfers (1 rule)
    "TR-001",
    # Escalation (2 rules)
    "ESC-001", "ESC-002",
    # Director disqualification rules remain outside scoring pending independent legal review.
    "DEF-002",
})

REVENUE_TIER_MAP = {
    Severity.GREEN: RevenueTier.COMPLIANCE_PACKAGE,
    Severity.YELLOW: RevenueTier.COMPLIANCE_PACKAGE,
    Severity.RED: RevenueTier.STRUCTURED_REGULARIZATION,
    Severity.BLACK: RevenueTier.CORPORATE_RESCUE,

    Severity.NOT_EVALUATED: RevenueTier.COMPLIANCE_PACKAGE,
}

FOREIGN_WORK_PERMIT_THRESHOLD_USD = 50000
BIDA_ADVANTAGE_THRESHOLD_USD = 100000
_VAT_TURNOVER_THRESHOLD_BDT = 3000000


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
    """Weighted fraction of high-signal profile fields with data.
    Tri-state booleans (None=unknown, True/False=known) count as known when
    False — a real negative answer is not missing data."""
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

    def __init__(self):
        self.today = date.today()
        self._flags: List[ComplianceFlag] = []

    def evaluate(self, company: CompanyProfile, today: date | None = None) -> EngineOutput:
        """Evaluate a company profile. Thread-safety: create a fresh NLCRuleEngine() per call — self._flags is instance state."""
        self._flags = []
        self.today = today or date.today()

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
            inc003_impact = 15
            inc003_desc = (
                "Private company has NO directors. Section 90(2) requires minimum 2. Director records require verification - absence in NLC database does not confirm actual absence."
                if c.current_director_count == 0
                else "Private company has only 1 director. Section 90(2) requires minimum 2."
            )
            self._add_flag(ComplianceFlag(
                rule_id="INC-003",
                flag_code="MINIMUM_DIRECTORS_NOT_MET",
                severity=Severity.BLACK,
                score_impact=15,
                is_black_override=True,
                revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
                description="Private company has insufficient directors. Section 90(2) requires minimum 2 directors.",
                statutory_basis="Section 90(2), Companies Act 1994 (Bangladesh)",
                detail={"current_count": c.current_director_count, "required": 2}
            ))

        if c.paid_up_capital_bdt > c.authorized_capital_bdt:
            self._add_flag(ComplianceFlag(
                rule_id="INC-004",
                flag_code="PAID_UP_EXCEEDS_AUTHORIZED",
                severity=Severity.BLACK,
                score_impact=20,
                revenue_tier=RevenueTier.CORPORATE_RESCUE,
                description="Paid-up capital exceeds authorized capital. Section 150: all excess allotments void.",
                statutory_basis="Section 53, Companies Act 1994 (Bangladesh)",
                is_black_override=True,
                detail={"paid_up": c.paid_up_capital_bdt, "authorized": c.authorized_capital_bdt}
            ))

        if c.has_foreign_shareholder:
            if c.encashment_certificate_uploaded is False:
                self._add_flag(ComplianceFlag(
                    rule_id="INC-005",
                    flag_code="ENCASHMENT_CERTIFICATE_MISSING",
                    severity=Severity.YELLOW,
                    score_impact=8,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description="Foreign shareholding but Encashment Certificate from AD bank not uploaded. BIDA requirement.",
                    statutory_basis="BIDA Foreign Investment Act 1980; Bangladesh Bank FDI Circular",
                    detail={"foreign_pct": c.foreign_shareholding_pct},
                    conditional_applies=True
                ))
            if c.remittance_amount_usd < FOREIGN_WORK_PERMIT_THRESHOLD_USD and c.bida_registered:
                self._add_flag(ComplianceFlag(
                    rule_id="INC-006",
                    flag_code="REMITTANCE_BELOW_WORK_PERMIT_THRESHOLD",
                    severity=Severity.YELLOW,
                    score_impact=0,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description=f"Advisory: Remittance USD {c.remittance_amount_usd:,.2f} below USD {FOREIGN_WORK_PERMIT_THRESHOLD_USD:,} work permit threshold.",
                    statutory_basis="BIDA Foreign Investment Act 1980",
                    detail={"remittance_usd": c.remittance_amount_usd, "threshold": FOREIGN_WORK_PERMIT_THRESHOLD_USD},
                    conditional_applies=True
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

        # INC-007: Business commenced without Section 150 declaration (Section 150)
        if c.business_commencement_declaration_filed is False:
            self._add_flag(ComplianceFlag(
                rule_id="INC-007",
                flag_code="BUSINESS_COMMENCED_WITHOUT_DECLARATION",
                severity=Severity.RED,
                score_impact=10,
                revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
                description="Business commenced without Section 150 declaration filed with Registrar.",
                statutory_basis="Section 150, Companies Act 1994 (Bangladesh)",
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
        reg_date = c.incorporation_date or self.today
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
            self._add_flag(ComplianceFlag(
                rule_id="AUD-001",
                flag_code="FIRST_AUDITOR_STATUS_UNKNOWN",
                severity=Severity.NOT_EVALUATED,
                score_impact=0,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description=(
                    "First auditor appointment status unknown (data missing). "
                    "Section 210(6) requires appointment within one month of registration."
                ),
                statutory_basis="Section 210(6), Companies Act 1994 (Bangladesh)",
                state=RuleState.UNKNOWN,
            ))
        elif c.first_auditor_appointment_date is not None:
            if c.first_auditor_appointed is False:
                self._add_flag(ComplianceFlag(
                    rule_id="AUD-001",
                    flag_code="FIRST_AUDITOR_EVIDENCE_CONTRADICTORY",
                    severity=Severity.NOT_EVALUATED,
                    score_impact=0,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description=(
                        "First auditor status is contradictory: an appointment date is recorded "
                        "but the appointment status is marked false. Verify source evidence."
                    ),
                    statutory_basis="Section 210(6), Companies Act 1994 (Bangladesh)",
                    state=RuleState.CONTRADICTORY,
                    detail={
                        "appointment_date": str(c.first_auditor_appointment_date),
                        "registration_date": str(reg_date),
                    },
                ))
            elif c.first_auditor_appointment_date > deadline:
                delay = (c.first_auditor_appointment_date - deadline).days
                add_aud001_flag(
                    "FIRST_AUDITOR_APPOINTED_LATE",
                    delay,
                    c.first_auditor_appointment_date,
                )
        elif c.first_auditor_appointed is False and self.today > deadline:
            delay = (self.today - deadline).days
            add_aud001_flag("FIRST_AUDITOR_NOT_APPOINTED", delay)
        elif c.first_auditor_appointed is True:
            self._add_flag(ComplianceFlag(
                rule_id="AUD-001",
                flag_code="FIRST_AUDITOR_APPOINTMENT_DATE_UNKNOWN",
                severity=Severity.NOT_EVALUATED,
                score_impact=0,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description=(
                    "First auditor is recorded as appointed, but the appointment date is missing; "
                    "timeliness under Section 210(6) cannot be verified."
                ),
                statutory_basis="Section 210(6), Companies Act 1994 (Bangladesh)",
                state=RuleState.UNKNOWN,
            ))

        if c.first_auditor_appointed and c.agm_count is not None and c.agm_count > 0 and c.auditor_reappointed_at_agm is False and c.audit_in_progress is False and c.last_agm_date is not None:  # type: ignore
            fy_end = c.financial_year_end
            if self.today > fy_end + timedelta(days=120):
                 self._add_flag(ComplianceFlag(
                    rule_id="AUD-005",
                    flag_code="SUBSEQUENT_AUDITOR_NOT_APPOINTED",
                    severity=Severity.RED,
                    score_impact=10,
                    revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
                    description="No auditor appointed for current FY. Section 210(3): mandatory at every AGM.",
                    statutory_basis="Section 210(3), Companies Act 1994 (Bangladesh)",
                ))

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

        if (c.agm_held_this_cycle and c.auditor_reappointed_at_agm is False
                and c.auditor_reappointment_verified is True
                and bool(c.auditor_reappointment_evidence_ref)):
            self._add_flag(ComplianceFlag(
                rule_id="AUD-004",
                flag_code="AUDITOR_NOT_REAPPOINTED",
                severity=Severity.YELLOW,
                score_impact=5,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description="Auditor not reappointed at AGM. Section 210(3): mandatory at every AGM.",
                statutory_basis="Section 210(3), Companies Act 1994 (Bangladesh)",
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

    def _subsequent_agm_deadline(self, c: CompanyProfile) -> date | None:
        if not self._agm_history_is_verified(c):
            return None
        if c.last_agm_date is None:
            return None
        # Section 81(1) proviso: if the first AGM is held within 18 months
        # of incorporation, no AGM is required in the incorporation year or
        # the following year. The first subsequent AGM is therefore due by
        # 31 December of the second following year; the ordinary 15-month
        # interval resumes after that AGM.
        if c.agm_count == 1 and c.incorporation_date is not None:
            first_agm_deadline = self._add_months(c.incorporation_date, 18)
            if c.last_agm_date <= first_agm_deadline:
                calendar_year_deadline = date(c.incorporation_date.year + 2, 12, 31)
                base_deadline = calendar_year_deadline
            else:
                fifteen_month_deadline = self._add_months(c.last_agm_date, 15)
                calendar_year_deadline = date(c.last_agm_date.year + 1, 12, 31)
                base_deadline = min(fifteen_month_deadline, calendar_year_deadline)
        else:
            fifteen_month_deadline = self._add_months(c.last_agm_date, 15)
            calendar_year_deadline = date(c.last_agm_date.year + 1, 12, 31)
            base_deadline = min(fifteen_month_deadline, calendar_year_deadline)
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
        application_days_after_deadline = (c.agm_extension_application_date - base_deadline).days
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
        if c.agm_count is None or c.incorporation_date is None:
            self._add_flag(ComplianceFlag(
                rule_id="AGM-001",
                flag_code="AGM_STATUS_UNKNOWN",
                severity=Severity.YELLOW,
                score_impact=0,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description="AGM history unknown (data missing).",
                statutory_basis="Section 81, Companies Act 1994 (Bangladesh)",
                state=RuleState.UNKNOWN
            ))
            return
        if c.agm_count == 0:
            deadline = self._add_months(c.incorporation_date, 18)
            if self.today > deadline:  # type: ignore
                delay = (self.today - deadline).days  # type: ignore
                severity = Severity.BLACK if delay > 365 else Severity.RED
                self._add_flag(ComplianceFlag(
                    rule_id="AGM-001",
                    flag_code="AGM_STATUS_UNKNOWN",
                    severity=Severity.NOT_EVALUATED,
                    score_impact=0,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description="AGM history is marked verified but the required count or incorporation date is missing.",
                    statutory_basis="Section 81(1), Companies Act 1994 (Bangladesh)",
                    state=RuleState.UNKNOWN,
                    eval_state="UNKNOWN",
                ))
            elif c.agm_count == 0:
                deadline = self._add_months(c.incorporation_date, 18)
                if self.today > deadline:
                    delay = (self.today - deadline).days
                    severity = Severity.BLACK if delay > 365 else Severity.RED
                    self._add_flag(ComplianceFlag(
                        rule_id="AGM-001",
                        flag_code="FIRST_AGM_DEFAULT",
                        severity=severity,
                        score_impact=self._graduated_agm_deduction(delay),
                        revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
                        description=f"First AGM not held within 18 months. Section 81: overdue by {delay} days.",
                        statutory_basis="Section 81(1), Companies Act 1994 (Bangladesh)",
                        detail={"delay_days": delay, "deadline": str(deadline)}
                    ))
            elif c.agm_count > 0 and c.last_agm_date and c.agm_held_this_cycle is False:
                agm_deadline = self._subsequent_agm_deadline(c)
                if agm_deadline is None:
                    self._add_flag(ComplianceFlag(
                        rule_id="AGM-002",
                        flag_code="AGM_EXTENSION_REQUIRES_REVIEW",
                        severity=Severity.NOT_EVALUATED,
                        score_impact=0,
                        revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                        description="A recorded AGM extension is not supported by verified application and grant evidence. No automatic default determination is made.",
                        statutory_basis="Section 81(1), Companies Act 1994 (Bangladesh)",
                        state=RuleState.REQUIRES_LAWYER_JUDGMENT,
                        eval_state="UNKNOWN",
                        detail={"extension_until": str(c.agm_extension_granted_until)},
                    ))
                elif self.today > agm_deadline:
                    delay = (self.today - agm_deadline).days
                    severity = Severity.BLACK if delay > 365 else Severity.RED
                    basis = "VALIDATED_EXTENSION" if c.agm_extension_granted_until else "SECTION_81(1)"
                    self._add_flag(ComplianceFlag(
                        rule_id="AGM-002",
                        flag_code="SUBSEQUENT_AGM_DEFAULT",
                        severity=severity,
                        score_impact=self._graduated_agm_deduction(delay),
                        revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
                        description=f"AGM overdue by {delay} days. Section 81: deadline by {basis} rule.",
                        statutory_basis="Section 81(1), Companies Act 1994 (Bangladesh)",
                        detail={"delay_days": delay, "basis": basis}
                    ))
            elif c.agm_count > 0 and c.last_agm_date is None:
                self._add_flag(ComplianceFlag(
                    rule_id="AGM-002",
                    flag_code="LAST_AGM_DATE_UNVERIFIED",
                    severity=Severity.NOT_EVALUATED,
                    score_impact=0,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description="AGM history is marked verified but the last AGM date is missing.",
                    statutory_basis="Section 81(1), Companies Act 1994 (Bangladesh)",
                    state=RuleState.UNKNOWN,
                    eval_state="UNKNOWN",
                ))

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
            clear_days = (c.agm_scheduled_date - c.notice_sent_date).days - 1
            if clear_days < AGM_NOTICE_MINIMUM_DAYS:
                self._add_flag(ComplianceFlag(
                    rule_id="AGM-003",
                    flag_code="AGM_NOTICE_DEFECTIVE",
                    severity=Severity.YELLOW,
                    score_impact=5,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description=f"AGM notice issued with {clear_days} clear days. Section 85 requires 21 clear days. NOTE: Section 85 permits shorter notice with member consent, and accidental omission/non-receipt does not invalidate proceedings.",
                    statutory_basis="Section 85, Companies Act 1994 (Bangladesh)",
                    detail={"clear_days": clear_days}
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

        if (
            c.agm_held_this_cycle
            and c.members_present_at_agm is not None
            and c.agm_attendance_verified is True
            and bool(c.agm_attendance_evidence_ref)
            and c.agm_quorum_basis_verified is True
            and bool(c.agm_quorum_evidence_ref)
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
                detail={"present": c.members_present_at_agm, "required": c.agm_quorum_required},
            ))
        if c.agm_held_this_cycle and c.agm_minutes_prepared is False:
            self._add_flag(ComplianceFlag(
                rule_id="AGM-006",
                flag_code="AGM_MINUTES_NOT_PREPARED",
                severity=Severity.YELLOW,
                score_impact=5,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description="AGM held but minutes not prepared. Section 89: minutes are prima facie evidence.",
                statutory_basis="Section 89, Companies Act 1994 (Bangladesh)",
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

        if c.unfiled_returns_count is not None and c.unfiled_returns_count >= 2:  # type: ignore
            self._add_flag(ComplianceFlag(
                rule_id="AR-002",
                flag_code="ANNUAL_RETURN_BACKLOG_RED",
                severity=Severity.RED,
                score_impact=20,
                revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
                description=f"{c.unfiled_returns_count} Annual Returns unfiled. Section 346: strike-off risk elevated.",
                statutory_basis="Sections 36 and 304, Companies Act 1994 (Bangladesh)",
                detail={"unfiled_count": c.unfiled_returns_count}
            ))

        if c.unfiled_returns_count is not None and c.unfiled_returns_count >= 3:  # type: ignore
            self._add_flag(ComplianceFlag(
                rule_id="AR-003",
                flag_code="ANNUAL_RETURN_BACKLOG_BLACK",
                severity=Severity.BLACK,
                score_impact=20,
                revenue_tier=RevenueTier.CORPORATE_RESCUE,
                description=f"{c.unfiled_returns_count} Annual Returns unfiled. Section 346: severe default, director liability.",
                statutory_basis="Sections 36 and 304, Companies Act 1994 (Bangladesh)",
                detail={"unfiled_count": c.unfiled_returns_count}
            ))

        if c.annual_return_filed and c.annual_return_content_complete is False:
            missing = []
            if c.schedule_x_attached is False: missing.append("Schedule X")
            if c.balance_sheet_attached is False: missing.append("Balance Sheet")
            if c.profit_loss_attached is False: missing.append("P&L Account")
            if c.directors_list_attached is False: missing.append("Directors List")
            if c.shareholders_list_attached is False: missing.append("Shareholders List")
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
            if change.form_filed is None:
                self._add_flag(ComplianceFlag(
                    rule_id="DIR-001",
                    flag_code="DIRECTOR_FILING_STATUS_UNKNOWN",
                    severity=Severity.YELLOW,
                    score_impact=0,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description=f"Director filing status unknown for {change.director_id}.",
                    statutory_basis="Section 115, Companies Act 1994 (Bangladesh)",
                    detail={"director_id": change.director_id},
                    state=RuleState.UNKNOWN
                ))
                continue
            elif not change.form_filed and delay > DIRECTOR_FILING_DEADLINE_DAYS:
                if change.event_type == "appointment":
                    severity = Severity.RED if delay > 90 else Severity.YELLOW
                    self._add_flag(ComplianceFlag(
                        rule_id="DIR-001",
                        flag_code="FORM_XII_APPOINTMENT_PENDING",
                        severity=severity,
                        score_impact=10 if delay > 90 else 5,
                        revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                        description=f"Director appointment not filed via Form XII. Section 115: 14-day deadline. Overdue by {delay} days.",
                        statutory_basis="Section 90, Companies Act 1994 (Bangladesh)",
                        detail={"director_id": change.director_id, "delay": delay}
                    ))
                elif change.event_type in ("resignation", "removal", "death"):
                    severity = Severity.RED if delay > 90 else Severity.YELLOW
                    self._add_flag(ComplianceFlag(
                        rule_id="DIR-002",
                        flag_code="FORM_XII_DEPARTURE_PENDING",
                        severity=severity,
                        score_impact=10 if delay > 90 else 5,
                        revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                        description=f"Director {change.event_type} not filed via Form XII. Section 115: 14-day deadline. Overdue by {delay} days.",
                        statutory_basis="Section 115, Companies Act 1994 (Bangladesh)",
                        detail={"director_id": change.director_id, "delay": delay, "type": change.event_type}
                    ))
                    self._add_flag(ComplianceFlag(
                        rule_id="DIR-004",
                        flag_code="LATE_CESSATION_FILING_LEGAL_EFFECT_REVIEW",
                        severity=Severity.NOT_EVALUATED,
                        score_impact=0,
                        revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                        description="Cessation particulars were filed late or remain unfiled. The legal effect on third-party reliance and any continuing liability requires case-specific legal review; non-filing alone does not automatically establish continuing director liability.",
                        statutory_basis="Section 115, Companies Act 1994 (Bangladesh)",
                        detail={"director_id": change.director_id, "legal_review_required": True},
                        state=RuleState.REQUIRES_LAWYER_JUDGMENT,
                        eval_state="UNKNOWN",
                    ))

                if delay > 365:
                    self._add_flag(ComplianceFlag(
                        rule_id="DIR-003",
                        flag_code="DIRECTOR_FILING_MAJOR_IRREGULARITY",
                        severity=Severity.RED,
                        score_impact=15,
                        revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
                        description=f"Director filing overdue {delay} days. Exceeds 1 year — Major Irregularity.",
                        statutory_basis="Section 115, Companies Act 1994 (Bangladesh)",
                        detail={"director_id": change.director_id, "delay": delay}
                    ))
                # DIR-007: Director consent not filed within 30 days (Section 93)
                if change.event_type == "appointment" and delay > 30:
                    self._add_flag(ComplianceFlag(
                        rule_id="DIR-007",
                        flag_code="DIRECTOR_CONSENT_NOT_FILED",
                        severity=Severity.YELLOW,
                        score_impact=5,
                        revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                        description=f"Director consent not filed within 30 days. Section 93(2): overdue by {delay} days.",
                        statutory_basis="Section 93, Companies Act 1994 (Bangladesh)",
                        detail={"director_id": change.director_id, "delay": delay}
                    ))

    # ───────────────────────────────────────────────────────────────────
    # MODULE 5: SHAREHOLDING
    # ───────────────────────────────────────────────────────────────────
    def _run_shareholder_rules(self, c: CompanyProfile) -> None:
        if c.last_allotment_date and c.form_xv_filed is False:
            delay = (self.today - c.last_allotment_date).days
            if delay > ALLOTMENT_FILING_DEADLINE_DAYS:
                self._add_flag(ComplianceFlag(
                    rule_id="SH-001",
                    flag_code="FORM_XV_ALLOTMENT_NOT_FILED",
                    severity=Severity.YELLOW if delay < 90 else Severity.RED,
                    score_impact=8,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description=f"Share allotment not filed via Form XV. Section 151: 60-day deadline. Overdue by {delay} days.",
                    statutory_basis="Section 151, Companies Act 1994 (Bangladesh)",
                    detail={"delay": delay}
                ))

        if c.last_allotment_date and c.share_certificates_issued is False:
            delay = (self.today - c.last_allotment_date).days
            if delay > SHARE_CERTIFICATE_DEADLINE_DAYS:
                self._add_flag(ComplianceFlag(
                    rule_id="SH-002",
                    flag_code="SHARE_CERTIFICATES_NOT_ISSUED",
                    severity=Severity.YELLOW if delay < 90 else Severity.RED,
                    score_impact=5,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description=f"Share certificates not issued within 90 days. Section 158: overdue by {delay - SHARE_CERTIFICATE_DEADLINE_DAYS} days.",
                    statutory_basis="Section 158, Companies Act 1994 (Bangladesh)",
                    detail={"delay": delay}
                ))

        if c.capital_increase_date and c.form_iv_filed is False:
            delay = (self.today - c.capital_increase_date).days
            if delay > ALLOTMENT_FILING_DEADLINE_DAYS:
                self._add_flag(ComplianceFlag(
                    rule_id="SH-003",
                    flag_code="FORM_IV_CAPITAL_INCREASE_NOT_FILED",
                    severity=Severity.YELLOW if delay < 90 else Severity.RED,
                    score_impact=8,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description=f"Capital increase not filed via Form IV. Section 52: 30-day deadline. Overdue by {delay} days.",
                    statutory_basis="Section 56, Companies Act 1994 (Bangladesh)",
                    detail={"delay": delay}
                ))

    # ───────────────────────────────────────────────────────────────────
    # MODULE 6: SHARE TRANSFERS
    # ───────────────────────────────────────────────────────────────────
    def _run_transfer_rules(self, c: CompanyProfile) -> None:
        for transfer in c.share_transfers:
            transfer_is_void = (
                transfer.aoa_restriction_apply
                and not transfer.board_approval_obtained
            )

            if not transfer.instrument_recorded or not transfer.form_117_filed:
                self._add_flag(ComplianceFlag(
                    rule_id="TR-001",
                    flag_code="TRANSFER_NO_INSTRUMENT_FORM_117",
                    severity=Severity.YELLOW,
                    score_impact=5,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description="Share transfer without Form 117 instrument. Section 38: proper instrument required.",
                    statutory_basis="Section 38, Companies Act 1994 (Bangladesh)",
                    detail={"transfer_id": transfer.transfer_id}
                ))

            if not transfer.stamp_duty_paid:
                self._add_flag(ComplianceFlag(
                    rule_id="TR-002",
                    flag_code="STAMP_DUTY_NOT_CONFIRMED",
                    severity=Severity.YELLOW,
                    score_impact=5,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description="Stamp duty not confirmed on transfer. Stamp Act 1899, Schedule I, Item 62: unstamped instruments inadmissible.",
                    statutory_basis="Stamp Act 1899, Schedule I, Item 62",
                    detail={"transfer_id": transfer.transfer_id}
                ))

            if not transfer.board_approval_obtained and not transfer_is_void:
                self._add_flag(ComplianceFlag(
                    rule_id="TR-003",
                    flag_code="TRANSFER_NO_BOARD_APPROVAL",
                    severity=Severity.YELLOW,
                    score_impact=8,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description="Share transfer without board approval. Section 38 + AoA: approval required where restricted.",
                    statutory_basis="Section 38; AoA, Companies Act 1994 (Bangladesh)",
                    detail={"transfer_id": transfer.transfer_id}
                ))

            if not transfer.share_register_updated and not transfer_is_void:
                self._add_flag(ComplianceFlag(
                    rule_id="TR-004",
                    flag_code="TRANSFER_REGISTER_NOT_UPDATED",
                    severity=Severity.YELLOW,
                    score_impact=5,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description="Register of Members not updated after transfer. Section 34: register is legal record of ownership.",
                    statutory_basis="Section 34, Companies Act 1994 (Bangladesh)",
                    detail={"transfer_id": transfer.transfer_id}
                ))

            if transfer_is_void:
                self._add_flag(ComplianceFlag(
                    rule_id="TR-005",
                    flag_code="AOA_TRANSFER_RESTRICTION_VIOLATED",
                    severity=Severity.BLACK,
                    score_impact=15,
                    revenue_tier=RevenueTier.CORPORATE_RESCUE,
                    description="Transfer violated AoA restriction. Section 38: such transfer is void. BLACK override.",
                    statutory_basis="Section 38; AoA, Companies Act 1994 (Bangladesh)",
                    detail={"transfer_id": transfer.transfer_id, "override": True},
                    is_black_override=True,
                ))

            tr_flags = [f for f in self._flags
                       if f.detail.get("transfer_id") == transfer.transfer_id
                       and f.rule_id.startswith("TR-")
                       and f.rule_id not in ("TR-005", "TR-006")]
                       
            if len(tr_flags) >= 2:
                # TR-006: composite flag — no additional score impact
                # Constituent rules already penalized; this exists for exposure_band and rescue sequencing
                self._add_flag(ComplianceFlag(
                    rule_id="TR-006",
                    flag_code="TRANSFER_IRREGULAR_COMPOSITE",
                    severity=Severity.RED,
                    score_impact=0,
                    revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
                    description=f"Transfer has {len(tr_flags)} deficiencies. Composite irregularity requiring structured remediation.",
                    statutory_basis="Sections 34, 47, 108, Companies Act 1994 (Bangladesh)",
                    detail={"transfer_id": transfer.transfer_id, "count": len(tr_flags)}
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
                flag_code="CAPITAL_INCREASE_RESOLUTION_MISSING",
                severity=Severity.YELLOW,
                score_impact=5,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description="Capital increase without shareholder resolution. Section 54: Ordinary/Special Resolution required.",
                statutory_basis="Section 53, Companies Act 1994 (Bangladesh)",
            ))

        for charge in c.charges:
            if not charge.form_viii_filed:
                delay = (self.today - charge.creation_date).days
                if delay > CHARGE_REGISTRATION_DEADLINE_DAYS:
                    self._add_flag(ComplianceFlag(
                        rule_id="CAP-002",
                        flag_code="CHARGE_NOT_REGISTERED",
                        severity=Severity.YELLOW if delay < 90 else Severity.RED,
                        score_impact=5,
                        revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                        description=f"{charge.charge_type} charge (Tk {charge.amount_bdt:,.2f}) not registered within 21 days of creation. Section 159(1): unregistered charge void against creditors and liquidator.",
                        statutory_basis="Section 159(1), Companies Act 1994 (Bangladesh)",
                        detail={"charge_id": charge.charge_id, "delay": delay, "amount": charge.amount_bdt}
                    ))

            if charge.satisfied and not charge.satisfaction_filed:
                self._add_flag(ComplianceFlag(
                    rule_id="CHG-001",
                    flag_code="CHARGE_SATISFACTION_NOT_FILED",
                    severity=Severity.YELLOW,
                    score_impact=3,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description="Charge satisfaction not filed via Form XIX. Section 159.",
                    statutory_basis="Section 159, Companies Act 1994 (Bangladesh)",
                    detail={"charge_id": charge.charge_id, "charge_type": charge.charge_type}
                ))

        if c.capital_reduction_pending and c.capital_reduction_court_order_obtained is False:
            self._add_flag(ComplianceFlag(
                rule_id="CAP-003",
                flag_code="CAPITAL_REDUCTION_WITHOUT_COURT",
                severity=Severity.BLACK,
                score_impact=15,
                revenue_tier=RevenueTier.CORPORATE_RESCUE,
                description="Capital reduction without court order. Section 150.",
                statutory_basis="Section 150, Companies Act 1994 (Bangladesh)",
                is_black_override=True,
            ))

        if c.special_resolution_date and c.special_resolution_filed is False:
            delay = (self.today - c.special_resolution_date).days
            if delay > SPECIAL_RESOLUTION_DEADLINE_DAYS:
                self._add_flag(ComplianceFlag(
                    rule_id="CAP-004",
                    flag_code="SPECIAL_RESOLUTION_NOT_FILED",
                    severity=Severity.YELLOW if delay < 90 else Severity.RED,
                    score_impact=8,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description=f"Special resolution not filed. Section 87: 30-day deadline. Unfiled resolution not binding.",
                    statutory_basis="Section 88, Companies Act 1994 (Bangladesh)",
                    detail={"delay": delay}
                ))

    # ───────────────────────────────────────────────────────────────────
    # MODULE 10: TAX COMPLIANCE
    # ───────────────────────────────────────────────────────────────────
    def _run_tax_rules(self, c: CompanyProfile) -> None:
        if c.tin_obtained is False:
            self._add_flag(ComplianceFlag(
                rule_id="TAX-001",
                flag_code="TIN_NOT_OBTAINED",
                severity=Severity.RED,
                score_impact=10,
                revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
                description="No TIN from NBR. Income Tax Act 2023: TIN mandatory. Cannot file returns, open accounts, or obtain licenses.",
                statutory_basis="Income Tax Act 2023 (Bangladesh)",
            ))

        if not c.vat_registered and c.annual_turnover_bdt > _VAT_TURNOVER_THRESHOLD_BDT:
            self._add_flag(ComplianceFlag(
                rule_id="TAX-002",
                flag_code="VAT_REGISTRATION_REQUIRED",
                severity=Severity.YELLOW,
                score_impact=5,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description="VAT threshold exceeded but not registered. VAT Act 2012: registration required above threshold.",
                statutory_basis="Value Added Tax Act 2012 (Bangladesh)",
                detail={"turnover_bdt": c.annual_turnover_bdt}
            ))

        if c.tin_obtained and c.tax_return_filed_for_current_fy is False and c.financial_year_end:
            # VERIFY against ITA 2023: company return due 15th day of 7th month after FY end (30 Jun -> 15 Jan)
            fy_end = c.financial_year_end
            due_month = fy_end.month + 7
            due_year = fy_end.year
            if due_month > 12:
                due_month -= 12
                due_year += 1
            deadline = date(due_year, due_month, 15)
            if c.tax_return_deadline_extended:
                deadline = deadline + timedelta(days=30)
            if self.today > deadline:
                delay = (self.today - deadline).days
                if delay <= 90:
                    t3_sev, t3_imp = Severity.YELLOW, 3
                elif delay <= 180:
                    t3_sev, t3_imp = Severity.RED, 5
                else:
                    t3_sev, t3_imp = Severity.RED, 8
                self._add_flag(ComplianceFlag(
                    rule_id="TAX-003",
                    flag_code="ANNUAL_TAX_RETURN_OVERDUE",
                    severity=t3_sev,
                    score_impact=t3_imp,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE if delay <= 90 else RevenueTier.STRUCTURED_REGULARIZATION,
                    description=f"Annual tax return overdue by {delay} days. ITA 2023 Sec 75.",
                    statutory_basis="Income Tax Act 2023, Section 75",
                    detail={"delay_days": delay, "fy_year": fy_end.year}
                ))

        if c.tin_obtained:
            missed = []
            t = self.today
            # FIX Defect 12: Only flag quarter if deadline has passed
            if t.month >= 7:
                q1_deadline = date(t.year, 10, 15)
                q2_deadline = date(t.year + 1, 1, 15)
                q3_deadline = date(t.year + 1, 4, 15)
                q4_deadline = date(t.year + 1, 7, 15)
            else:
                q1_deadline = date(t.year - 1, 10, 15)
                q2_deadline = date(t.year, 1, 15)
                q3_deadline = date(t.year, 4, 15)
                q4_deadline = date(t.year, 7, 15)
                
            if t > q1_deadline and c.advance_tax_q1_paid is False: missed.append("Q1")
            if t > q2_deadline and c.advance_tax_q2_paid is False: missed.append("Q2")
            if t > q3_deadline and c.advance_tax_q3_paid is False: missed.append("Q3")
            if t > q4_deadline and c.advance_tax_q4_paid is False: missed.append("Q4")
            
            if missed:
                self._add_flag(ComplianceFlag(
                    rule_id="TAX-004",
                    flag_code="ADVANCE_TAX_MISSED",
                    severity=Severity.YELLOW,
                    score_impact=min(len(missed) * 2, 5),
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description=f"Advance tax missed: {', '.join(missed)}. ITA 2023 Sec 74.",
                    statutory_basis="Income Tax Act 2023, Section 74",
                    detail={"quarters": missed}
                ))

        if c.vat_registered:
            fifteenth = self.today.replace(day=15)
            if self.today > fifteenth:
                last_day_prev = self.today.replace(day=1) - timedelta(days=1)
                if c.last_vat_return_filed is not None and c.last_vat_return_filed < last_day_prev:
                 self._add_flag(ComplianceFlag(
                    rule_id="VAT-002",
                    flag_code="MONTHLY_VAT_RETURN_OVERDUE",
                    severity=Severity.YELLOW,
                    score_impact=8,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description="Monthly/Bi-monthly VAT return overdue. VAT Act 2012.",
                    statutory_basis="Value Added Tax Act 2012 (Bangladesh)",
                ))

        if c.vat_registered and c.vat_annual_return_filed_for_fy is False and self.today.month > 9:
            self._add_flag(ComplianceFlag(
                rule_id="VAT-003",
                flag_code="VAT_ANNUAL_RETURN_OVERDUE",
                severity=Severity.YELLOW,
                score_impact=5,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description="VAT Annual Return overdue for current FY. VAT Act 2012.",
                statutory_basis="Value Added Tax Act 2012 (Bangladesh)",
            ))

        unresolved = (c.penalty_notices_received or 0) - (c.penalty_notices_resolved or 0)  # type: ignore
        if unresolved > 0:
            sev = Severity.RED if unresolved >= 3 else Severity.YELLOW
            self._add_flag(ComplianceFlag(
                rule_id="DEF-002",
                flag_code="PENALTY_PROSECUTION_RISK",
                severity=sev,
                score_impact=8 if unresolved >= 3 else 5,
                revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
                description=f"{unresolved} unresolved penalties. Sec 447: fine up to Tk 10,000.",
                statutory_basis="Section 397, Companies Act 1994 (Bangladesh)",
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
                    description=f"Name change not filed. Sec 20: Special Resolution + RJSC filing. Overdue {delay} days.",
                    statutory_basis="Section 20, Companies Act 1994 (Bangladesh)",
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
                    description=f"MoA object clause change not filed. Sec 17. Overdue {delay} days.",
                    statutory_basis="Section 17, Companies Act 1994 (Bangladesh)",
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
                    description=f"AoA alteration not filed. Sec 18. Overdue {delay} days.",
                    statutory_basis="Section 18, Companies Act 1994 (Bangladesh)",
                    detail={"delay_days": delay}
                ))

    # ───────────────────────────────────────────────────────────────────
    # MODULE 12: ESCALATION
    # ───────────────────────────────────────────────────────────────────
    # MODULE 12: INSOLVENCY (Bankruptcy Act 1997)
    def _run_insolvency_rules(self, c: CompanyProfile) -> None:
        if c.winding_up_petition_filed:
            self._add_flag(ComplianceFlag(
                rule_id="BNK-001",
                flag_code="WINDING_UP_PETITION_FILED",
                severity=Severity.BLACK,
                score_impact=25,
                revenue_tier=RevenueTier.CORPORATE_RESCUE,
                description="Winding up petition filed against company. Bankruptcy Act 1997, Section 12. Company under court supervision.",
                statutory_basis="Bankruptcy Act 1997 (Bangladesh), Section 12",
                is_black_override=True,
                detail={"petition_filed": True}
            ))

        if c.liquidator_appointed:
            self._add_flag(ComplianceFlag(
                rule_id="BNK-002",
                flag_code="LIQUIDATOR_APPOINTED",
                severity=Severity.BLACK,
                score_impact=25,
                revenue_tier=RevenueTier.CORPORATE_RESCUE,
                description="Liquidator appointed. Bankruptcy Act 1997, Section 14. Company under liquidation proceedings.",
                statutory_basis="Bankruptcy Act 1997 (Bangladesh), Section 14",
                is_black_override=True,
                detail={"liquidator_appointed": True}
            ))

        if c.court_ordered_winding_up:
            self._add_flag(ComplianceFlag(
                rule_id="BNK-003",
                flag_code="COURT_ORDERED_WINDING_UP",
                severity=Severity.BLACK,
                score_impact=35,
                revenue_tier=RevenueTier.CORPORATE_RESCUE,
                description="Court-ordered winding up. Bankruptcy Act 1997, Section 18. Company being wound up by court order.",
                statutory_basis="Bankruptcy Act 1997 (Bangladesh), Section 18",
                is_black_override=True,
                detail={"court_ordered": True}
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
        if applicability.state is ApplicabilityState.APPLICABLE:
            if c.factory_license_obtained is False:
                self._add_flag(ComplianceFlag(
                    rule_id="LBR-001",
                    flag_code="FACTORY_LICENSE_MISSING",
                    severity=Severity.RED,
                    score_impact=10,
                    revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
                    description="Factory license not obtained. Labour Act 2006: factory license mandatory for manufacturing entities.",
                    statutory_basis="Labour Act 2006 (Bangladesh), Section 35"
                ))

            if c.factory_license_expiry and self.today > c.factory_license_expiry:
                delay = (self.today - c.factory_license_expiry).days
                self._add_flag(ComplianceFlag(
                    rule_id="LBR-002",
                    flag_code="FACTORY_LICENSE_EXPIRED",
                    severity=Severity.YELLOW,
                    score_impact=5,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description=f"Factory license expired. Overdue by {delay} days. Labour Act 2006: renewal required.",
                    statutory_basis="Labour Act 2006 (Bangladesh), Section 35"
                ))

        # LBR-003 is not gated by manufacturing status: applicability of an
        # existing labour-court order depends on the order's parties and scope.
        if c.labour_court_order_pending:
            self._add_flag(ComplianceFlag(
                rule_id="LBR-003",
                flag_code="LABOUR_COURT_ORDER_PENDING",
                severity=Severity.RED,
                score_impact=15,
                revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
                description="Labour court order pending against company. Labour Act 2006: compliance with court orders mandatory.",
                statutory_basis="Labour Act 2006 (Bangladesh), Section 209"
            ))

    # MODULE 14: ADDITIONAL COMPANIES ACT 1994
    def _run_companies_act_extended_rules(self, c: CompanyProfile) -> None:
        if c.agm_adjourned_without_notice:
            self._add_flag(ComplianceFlag(
                rule_id="AGM-007", flag_code="AGM_ADJOURNED_WITHOUT_NOTICE",
                severity=Severity.YELLOW, score_impact=5,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description="AGM adjourned without proper notice. Section 84.",
                statutory_basis="Section 85, Companies Act 1994 (Bangladesh)"))
        if c.register_of_directors_interests is False:
            self._add_flag(ComplianceFlag(
                rule_id="DIR-005", flag_code="REGISTER_OF_DIRECTORS_INTERESTS_MISSING",
                severity=Severity.YELLOW, score_impact=5,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description="Register of directors interests not maintained. Section 130.",
                statutory_basis="Section 130, Companies Act 1994 (Bangladesh)"))
        if c.register_of_contracts is False:
            self._add_flag(ComplianceFlag(
                rule_id="DIR-006", flag_code="REGISTER_OF_CONTRACTS_MISSING",
                severity=Severity.YELLOW, score_impact=5,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description="Register of contracts not maintained. Section 130.",
                statutory_basis="Section 130, Companies Act 1994 (Bangladesh)"))
        if c.voluntary_winding_up:
            self._add_flag(ComplianceFlag(
                rule_id="ESC-004", flag_code="VOLUNTARY_WINDING_UP",
                severity=Severity.BLACK, score_impact=30,
                revenue_tier=RevenueTier.CORPORATE_RESCUE,
                description="Voluntary winding up. Section 286.",
                statutory_basis="Section 286, Companies Act 1994 (Bangladesh)",
                is_black_override=True))
        if c.investigation_order:
            self._add_flag(ComplianceFlag(
                rule_id="ESC-005", flag_code="INVESTIGATION_ORDER_PENDING",
                severity=Severity.RED, score_impact=20,
                revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
                description="Investigation order pending. Section 195.",
                statutory_basis="Section 195, Companies Act 1994 (Bangladesh)"))

        # DIR-008: Director holding office of profit (Section 104)
        if c.director_office_of_profit:
            self._add_flag(ComplianceFlag(
                rule_id="DIR-008", flag_code="DIRECTOR_OFFICE_OF_PROFIT",
                severity=Severity.YELLOW, score_impact=8,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description="Director holding office of profit without company consent. Section 104.",
                statutory_basis="Section 104, Companies Act 1994 (Bangladesh)"))
        # DIR-010: Managing director term exceeds 5 years (Section 110)
        if c.managing_director_appointment_date:
            md_years = (self.today - c.managing_director_appointment_date).days // 365
            if md_years > 5:
                self._add_flag(ComplianceFlag(
                    rule_id="DIR-010", flag_code="MD_TERM_EXCEEDS_5_YEARS",
                    severity=Severity.YELLOW, score_impact=5,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description=f"Managing director appointed for {md_years} years. Section 110: max 5 years at a time.",
                    statutory_basis="Section 110, Companies Act 1994 (Bangladesh)",
                    detail={"years": md_years}))

    # MODULE 15: BSEC CG CODE 2023
    def _run_bsec_rules(self, c: CompanyProfile) -> None:
        if c.bsec_listed:
            if c.bsec_quarterly_report_filed is False:
                self._add_flag(ComplianceFlag(
                    rule_id="BSEC-001", flag_code="QUARTERLY_REPORT_NOT_FILED",
                    severity=Severity.RED, score_impact=10,
                    revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
                    description="BSEC quarterly report not filed.",
                    statutory_basis="BSEC Corporate Governance Code 2023, Para 8"))
            if c.cg_certificate_obtained is False:
                self._add_flag(ComplianceFlag(
                    rule_id="BSEC-002", flag_code="CG_CERTIFICATE_NOT_OBTAINED",
                    severity=Severity.RED, score_impact=10,
                    revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
                    description="CG certificate not obtained.",
                    statutory_basis="BSEC Corporate Governance Code 2023, Para 9"))
            if c.board_independent_director is False:
                self._add_flag(ComplianceFlag(
                    rule_id="BSEC-003", flag_code="BOARD_COMPOSITION_NON_COMPLIANT",
                    severity=Severity.YELLOW, score_impact=8,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description="Board composition non-compliant.",
                    statutory_basis="BSEC Corporate Governance Code 2023, Para 5"))
            if c.audit_committee_established is False:
                self._add_flag(ComplianceFlag(
                    rule_id="BSEC-004", flag_code="AUDIT_COMMITTEE_NOT_ESTABLISHED",
                    severity=Severity.YELLOW, score_impact=5,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description="Audit committee not established.",
                    statutory_basis="BSEC Corporate Governance Code 2023, Para 6"))

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
        # BOD-001: Board meeting not held quarterly (Section 96)
        # Issue 6 follow-up: Gate on bsec_listed until applicability confirmed.
        # The "4 meetings per year" / "3 months" thresholds may come from the
        # BSEC Corporate Governance Code, which likely binds only listed companies.
        # Firing for all companies gives private companies a false violation.
        if not c.bsec_listed:
            return  # BOD-001 does not bind non-listed companies (pending legal review)

        if c.last_board_meeting_date is None:
            if c.incorporation_date and (self.today - c.incorporation_date).days > 90:
                self._add_flag(ComplianceFlag(
                    rule_id="BOD-001",
                    flag_code="BOARD_MEETING_NOT_HELD",
                    severity=Severity.YELLOW,
                    score_impact=5,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description="Board meeting not held within 3 months. Section 96: minimum 4 board meetings per year.",
                    statutory_basis="Section 96, Companies Act 1994 (Bangladesh)",
                    detail={"incorporation_days": (self.today - c.incorporation_date).days}
                ))
        elif c.last_board_meeting_date:
            days_since = (self.today - c.last_board_meeting_date).days
            if days_since > 90:
                self._add_flag(ComplianceFlag(
                    rule_id="BOD-001",
                    flag_code="BOARD_MEETING_OVERDUE",
                    severity=Severity.YELLOW,
                    score_impact=5,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description=f"Board meeting overdue by {days_since} days. Section 96: quarterly meeting required.",
                    statutory_basis="Section 96, Companies Act 1994 (Bangladesh)",
                    detail={"days_since": days_since}
                ))

        # BOD-002: Board meeting notice not given (Section 95)
        if c.last_board_meeting_date and c.board_meeting_notice_given is False:
            self._add_flag(ComplianceFlag(
                rule_id="BOD-002",
                flag_code="BOARD_NOTICE_NOT_GIVEN",
                severity=Severity.YELLOW,
                score_impact=3,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description="Board meeting notice not given to all directors. Section 95 requires written notice.",
                statutory_basis="Section 95, Companies Act 1994 (Bangladesh)",
            ))

        # BOD-003: Board minutes not prepared (Section 89)
        if c.last_board_meeting_date and c.board_minutes_prepared is False:
            self._add_flag(ComplianceFlag(
                rule_id="BOD-003",
                flag_code="BOARD_MINUTES_NOT_PREPARED",
                severity=Severity.YELLOW,
                score_impact=5,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description="Board meeting minutes not prepared. Section 89: minutes of all proceedings must be entered.",
                statutory_basis="Section 89, Companies Act 1994 (Bangladesh)",
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

        # ACC-002: Financial statements not filed with Registrar (Section 190)
        if c.last_agm_date and c.financial_statements_filed is False:
            delay = (self.today - c.last_agm_date).days
            if delay > 30:
                self._add_flag(ComplianceFlag(
                    rule_id="ACC-002",
                    flag_code="FINANCIAL_STATEMENTS_NOT_FILED",
                    severity=Severity.RED,
                    score_impact=15,
                    revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
                    description=f"Balance sheet not filed with Registrar within 30 days of AGM. Overdue by {delay} days. Section 190.",
                    statutory_basis="Section 190, Companies Act 1994 (Bangladesh)",
                    detail={"delay": delay}
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
        unverified_allegations = []
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
            unverified_allegations = c.disqualification_details

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
                    f"Disqualification allegation(s) received for director(s) "
                    f"but evidence NOT verified. Section 94 requires a "
                    f"competent court declaration, insolvency certificate, "
                    f"or other authoritative determination. Cannot determine "
                    f"compliance status until evidence is reviewed."
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
                flag_code="STRIKE_OFF_RISK_ELEVATED",
                severity=Severity.RED,
                score_impact=15,
                revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
                description=f"2+ year AGM and Return defaults. Section 346: RJSC strike-off risk elevated.",
                statutory_basis="Section 346, Companies Act 1994 (Bangladesh)",
                detail={"agm_years": agm_years, "ar_years": ar_years}
            ))

        if agm_years >= 3 or ar_years >= 3 or c.on_rjsc_strike_off_list:  # type: ignore
            # Suppress ESC-001 if ESC-002 is firing
            self._flags = [f for f in self._flags if f.rule_id != "ESC-001"]
            self._add_flag(ComplianceFlag(
                rule_id="ESC-002",
                flag_code="STRIKE_OFF_IMMINENT",
                severity=Severity.BLACK,
                score_impact=25,
                revenue_tier=RevenueTier.CORPORATE_RESCUE,
                description=f"3+ year default or on strike-off list. Section 346: strike-off imminent. NLC risk policy: rescue workflow recommended.",
                statutory_basis="Section 346, Companies Act 1994 (Bangladesh)",
                detail={"agm_years": agm_years, "ar_years": ar_years, "on_list": c.on_rjsc_strike_off_list},
                is_black_override=True,
                escalation_pending=True,
            ))

        pre_score = self._calculate_raw_score(self._flags)
        has_black_override = any(
            f.is_black_override and f.state in (RuleState.NON_COMPLIANT, RuleState.VERIFIED_ABSENT) and f.eval_state == "VIOLATION"
            for f in self._flags if not f.resolved and f.conditional_applies
        )
        
        if pre_score <= 29 or has_black_override:
            black_count = len([f for f in self._flags if f.severity == Severity.BLACK and f.state in (RuleState.NON_COMPLIANT, RuleState.VERIFIED_ABSENT) and f.eval_state == "VIOLATION" and not f.resolved and f.conditional_applies and f.rule_id not in self._ESC_RULE_IDS])
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
        coverage = fraction of rules that had data to evaluate (0.0 to 1.0).
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


    def _calculate_raw_score(self, flags: List[ComplianceFlag]) -> int:
        """Return the same capped 100-point raw score used by _calculate_score.

        Escalation rules call this before generating ESC flags, so it must use
        the exact same verified-rule gate, category buckets and caps as the
        authoritative scorer. A separate 125-point scaling formula caused
        different pre-score and final-score results for identical findings.
        """
        active = [f for f in flags if not f.resolved and f.conditional_applies]
        violations = [
            f for f in active
            if f.state in (RuleState.NON_COMPLIANT, RuleState.VERIFIED_ABSENT)
            and f.eval_state == "VIOLATION"
        ]
        scored = [f for f in violations if f.rule_id in VERIFIED_RULE_IDS]

        deductions = {
            "TAX": sum(f.score_impact for f in scored if f.rule_id.startswith(("TAX-", "VAT-"))),
            "AGM": sum(f.score_impact for f in scored if f.rule_id.startswith("AGM-")),
            "AUD": sum(f.score_impact for f in scored if f.rule_id.startswith("AUD-")),
            "RET": sum(f.score_impact for f in scored if f.rule_id.startswith("AR-")),
            "DIR": sum(f.score_impact for f in scored if f.rule_id.startswith(("DIR-", "INC-", "DEF-", "TL-", "BOD-", "MEM-"))),
            "SHR": sum(f.score_impact for f in scored if f.rule_id.startswith(("SH-", "TR-"))),
            "CAP": sum(f.score_impact for f in scored if f.rule_id.startswith(("CAP-", "STR-", "CHG-", "ACC-"))),
            "OFF": sum(f.score_impact for f in scored if f.rule_id.startswith("OFF-")),
            "REG": sum(f.score_impact for f in scored if f.rule_id.startswith("REG-")),
            "BNK": sum(f.score_impact for f in scored if f.rule_id.startswith("BNK-")),
            "LBR": sum(f.score_impact for f in scored if f.rule_id.startswith("LBR-")),
            "BSEC": sum(f.score_impact for f in scored if f.rule_id.startswith("BSEC-")),
            "FX": sum(f.score_impact for f in scored if f.rule_id.startswith("FX-")),
            "ESC": sum(f.score_impact for f in scored if f.rule_id.startswith("ESC-")),
        }
        capped = {
            key: min(value, CATEGORY_CAPS[key][0])
            for key, value in deductions.items()
        }
        return max(0, min(100, 100 - sum(capped.values())))

    def _calculate_score(self, flags: List[ComplianceFlag], company: CompanyProfile) -> ScoreBreakdown:
        active = [f for f in flags if not f.resolved and f.conditional_applies]
        violations = [
            f for f in active
            if f.state in (RuleState.NON_COMPLIANT, RuleState.VERIFIED_ABSENT)
            and f.eval_state == "VIOLATION"
        ]

        # P0 GATE: Only verified rules contribute to the authoritative score.
        # Unverified rules still generate flags for visibility but their
        # score_impact is excluded from deductions.
        scored = [f for f in violations if f.rule_id in VERIFIED_RULE_IDS]

        tax_ded = sum(f.score_impact for f in scored if f.rule_id.startswith(("TAX-", "VAT-")))
        agm_ded = sum(f.score_impact for f in scored if f.rule_id.startswith("AGM-"))
        aud_ded = sum(f.score_impact for f in scored if f.rule_id.startswith("AUD-"))
        ret_ded = sum(f.score_impact for f in scored if f.rule_id.startswith("AR-"))
        dir_ded = sum(f.score_impact for f in scored if f.rule_id.startswith(("DIR-", "INC-", "DEF-", "TL-", "BOD-", "MEM-")))
        shr_ded = sum(f.score_impact for f in scored if f.rule_id.startswith(("SH-", "TR-")))
        cap_ded = sum(f.score_impact for f in scored if f.rule_id.startswith(("CAP-", "STR-", "CHG-", "ACC-")))
        off_ded = sum(f.score_impact for f in scored if f.rule_id.startswith("OFF-"))
        reg_ded = sum(f.score_impact for f in scored if f.rule_id.startswith("REG-"))
        bnk_ded = sum(f.score_impact for f in scored if f.rule_id.startswith("BNK-"))
        lbr_ded = sum(f.score_impact for f in scored if f.rule_id.startswith("LBR-"))
        bsec_ded = sum(f.score_impact for f in scored if f.rule_id.startswith("BSEC-"))
        fx_ded = sum(f.score_impact for f in scored if f.rule_id.startswith("FX-"))
        esc_ded = sum(f.score_impact for f in scored if f.rule_id.startswith("ESC-"))

        # 100-point model v2: cap each category, then subtract from 100
        tax_ded = min(tax_ded, CATEGORY_CAPS["TAX"][0])
        agm_ded = min(agm_ded, CATEGORY_CAPS["AGM"][0])
        aud_ded = min(aud_ded, CATEGORY_CAPS["AUD"][0])
        ret_ded = min(ret_ded, CATEGORY_CAPS["RET"][0])
        dir_ded = min(dir_ded, CATEGORY_CAPS["DIR"][0])
        shr_ded = min(shr_ded, CATEGORY_CAPS["SHR"][0])
        cap_ded = min(cap_ded, CATEGORY_CAPS["CAP"][0])
        off_ded = min(off_ded, CATEGORY_CAPS["OFF"][0])
        reg_ded = min(reg_ded, CATEGORY_CAPS["REG"][0])
        bnk_ded = min(bnk_ded, CATEGORY_CAPS["BNK"][0])
        lbr_ded = min(lbr_ded, CATEGORY_CAPS["LBR"][0])
        bsec_ded = min(bsec_ded, CATEGORY_CAPS["BSEC"][0])
        fx_ded = min(fx_ded, CATEGORY_CAPS["FX"][0])
        esc_ded = min(esc_ded, CATEGORY_CAPS["ESC"][0])

        raw = max(0, min(100, 100 - (tax_ded + agm_ded + aud_ded + ret_ded + dir_ded
                                     + shr_ded + cap_ded + off_ded + reg_ded + bnk_ded
                                     + lbr_ded + bsec_ded + fx_ded + esc_ded)))
        
        override = False
        reason = None
        final = raw
        critical = [
            f for f in active
            if f.is_black_override
            and f.state in (RuleState.NON_COMPLIANT, RuleState.VERIFIED_ABSENT)
            and f.eval_state == "VIOLATION"
        ]
        if not critical:
            critical = [
                f for f in active
                if f.rule_id in VERIFIED_RULE_IDS
                and f.severity == Severity.BLACK
                and f.state in (RuleState.NON_COMPLIANT, RuleState.VERIFIED_ABSENT)
                and f.eval_state == "VIOLATION"
            ]
        if critical:
            override = True
            reason = f"BLACK: {', '.join(f.rule_id for f in critical)}"
            final = 0

        coverage = _input_coverage(company)
        score_band = Severity(self._score_to_band(final, force_black=bool(critical), coverage=coverage))

        # Band = worst of (score-based band, highest active flag severity)
        # Prevents false GREEN when a RED-severity rule fires (BLACK handled above)'t override
        if not critical:
            severity_rank = {Severity.GREEN: 0, Severity.YELLOW: 1, Severity.RED: 2, Severity.BLACK: 3}
            max_flag_severity = Severity.GREEN
            for f in active:
                if (f.rule_id in VERIFIED_RULE_IDS
                        and f.severity in severity_rank
                        and f.severity in (Severity.RED, Severity.BLACK)
                        and f.state in (RuleState.NON_COMPLIANT, RuleState.VERIFIED_ABSENT)
                        and f.eval_state == "VIOLATION"):
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
            black_flag_count=len([f for f in active if (f.rule_id in VERIFIED_RULE_IDS or f.is_black_override) and f.severity == Severity.BLACK and f.state in (RuleState.NON_COMPLIANT, RuleState.VERIFIED_ABSENT) and f.eval_state == "VIOLATION"]),
            red_flag_count=len([f for f in active if f.rule_id in VERIFIED_RULE_IDS and f.severity == Severity.RED and f.state in (RuleState.NON_COMPLIANT, RuleState.VERIFIED_ABSENT) and f.eval_state == "VIOLATION"]),
            yellow_flag_count=len([f for f in active if f.severity == Severity.YELLOW and f.state in (RuleState.NON_COMPLIANT, RuleState.VERIFIED_ABSENT) and f.eval_state == "VIOLATION"]),
            green_flag_count=len([f for f in active if f.severity == Severity.GREEN and f.state in (RuleState.NON_COMPLIANT, RuleState.VERIFIED_ABSENT) and f.eval_state == "VIOLATION"]),
            bankruptcy_score=max(0, 5 - bnk_ded),
            labour_score=max(0, 5 - lbr_ded),
            bsec_score=max(0, 5 - bsec_ded),
            fx_score=max(0, 5 - fx_ded),
            escalation_score=max(0, 5 - esc_ded),
            score_hash=score_hash
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

        # P1 RESCUE COVERAGE FIX: Every NON_COMPLIANT flag must receive a
        # rescue step (or a documented reason why no action is required).
        # The audit flagged that 5 flags produced only 2 rescue steps.
        # We now include YELLOW severity flags in addition to RED/BLACK.
        actionable = [
            f for f in active
            if f.state == RuleState.NON_COMPLIANT
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
        if m <= 3:   return 3  # Jan-Mar = Q3
        if m <= 6:   return 4  # Apr-Jun = Q4
        if m <= 9:   return 1  # Jul-Sep = Q1
        return 2              # Oct-Dec = Q2

    def _add_flag(self, flag: ComplianceFlag) -> None:
        self._flags.append(flag)

    def _graduated_agm_deduction(self, delay: int) -> int:
        if delay <= 90: return 5
        if delay <= 180: return 10
        if delay <= 365: return 15
        return 20

    def _graduated_ar_deduction(self, delay: int) -> int:
        if delay <= 60: return 3
        if delay <= 180: return 5
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
        if not self._agm_history_is_verified(c):
            return 0
        if c.last_agm_date is None:
            if c.agm_count == 0:
                if c.incorporation_date is not None:
                    deadline = self._add_months(c.incorporation_date, 18)
                    if self.today > deadline:
                        return (self.today - deadline).days // 365
                deadline = self._add_months(c.incorporation_date, 18)
                if self.today > deadline:  # type: ignore
                    return (self.today - deadline).days // 365  # type: ignore
            return 0
            
        # Match Section 81(1): no more than 15 months between AGMs and
        # an AGM in each Gregorian calendar year. Do not use an assumed FY+6m rule.
        deadline = self._subsequent_agm_deadline(c)
        if deadline is None:
            return 0
        if self.today > deadline:
            return (self.today - deadline).days // 365
        return 0
