# ═══════════════════════════════════════════════════════════════════════
# NEUM LEX COUNSEL — RJSC COMPLIANCE INTELLIGENCE PLATFORM
# LAYER C: LEGAL RULE ENGINE — BANGLADESH CA 1994 COMPLIANT v2.1
# All ILRMF v2.1 Rules | Deterministic | AI-Non-Editable
# Version: 2.1 | Classification: PROPRIETARY IP — NEUM LEX COUNSEL
# Governed by: Internal AI Constitution v2.0
# ═══════════════════════════════════════════════════════════════════════

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("nlc.rule_engine")

# ───────────────────────────────────────────────────────────────────────
# RULE ENGINE VERSION — Immutable in production
# ───────────────────────────────────────────────────────────────────────
RULE_ENGINE_VERSION = "2.1"
ILRMF_VERSION = "2.1"

# ═══════════════════════════════════════════════════════════════════════
# ENUMERATIONS
# ═══════════════════════════════════════════════════════════════════════

class Severity(str, Enum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"
    BLACK = "BLACK"

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
    conditional_applies: bool = True

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
    incorporation_date: date = field(default_factory=date.today)
    financial_year_end: date = field(default_factory=date.today)
    agm_count: int = 0
    last_agm_date: Optional[date] = None
    agm_held_this_cycle: bool = False
    agm_held_without_audit: bool = False
    agm_scheduled_date: Optional[date] = None
    notice_sent_date: Optional[date] = None
    members_present_at_agm: int = 0
    auditor_reappointed_at_agm: bool = False
    accounts_adopted_at_agm: bool = False
    agm_minutes_prepared: bool = False
    first_auditor_appointed: bool = False
    first_auditor_appointment_date: Optional[date] = None
    audit_complete: bool = False
    last_audit_signed_date: Optional[date] = None
    audit_in_progress: bool = False
    auditor_name: Optional[str] = None
    auditor_firm_reg_no: Optional[str] = None
    last_return_filed_year: Optional[int] = None
    unfiled_returns_count: int = 0
    annual_return_filed: bool = False
    annual_return_content_complete: bool = False
    annual_return_filed_date: Optional[date] = None
    schedule_x_attached: bool = False
    balance_sheet_attached: bool = False
    profit_loss_attached: bool = False
    directors_list_attached: bool = False
    shareholders_list_attached: bool = False
    director_changes: List[DirectorChange] = field(default_factory=list)
    current_director_count: int = 2
    minimum_directors_met: bool = True
    shareholder_change_date: Optional[date] = None
    form_xv_filed: bool = False
    form_xv_filed_date: Optional[date] = None
    last_allotment_date: Optional[date] = None
    share_certificates_issued: bool = True
    share_certificates_issued_date: Optional[date] = None
    authorized_capital_bdt: float = 0.0
    paid_up_capital_bdt: float = 0.0
    paid_up_ge_authorized: bool = True
    share_transfers: List[ShareTransfer] = field(default_factory=list)
    registered_office_address: str = ""
    registered_office_change_date: Optional[date] = None
    form_vi_filed: bool = False
    form_vi_filed_date: Optional[date] = None
    aoa_transfer_restriction: bool = True
    has_foreign_shareholder: bool = False
    foreign_shareholding_pct: float = 0.0
    is_dormant: bool = False
    is_fdi_registered: bool = False
    fdi_registration_date: Optional[date] = None
    bida_registered: bool = False
    maintained_registers: List[str] = field(default_factory=list)
    register_of_members_maintained: bool = False
    register_of_directors_maintained: bool = False
    register_of_charges_maintained: bool = False
    minutes_book_agm_maintained: bool = False
    minutes_book_board_maintained: bool = False
    register_location: str = "registered_office"
    capital_increase_date: Optional[date] = None
    capital_increase_resolution: bool = False
    capital_increase_special_resolution: bool = False
    form_iv_filed: bool = False
    form_iv_filed_date: Optional[date] = None
    form_iii_filed: bool = False
    form_iii_filed_date: Optional[date] = None
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
    tin_obtained: bool = False
    tin_number: Optional[str] = None
    vat_registered: bool = False
    vat_number: Optional[str] = None
    last_tax_return_filed: Optional[date] = None
    trade_license_obtained: bool = False
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
    penalty_notices_received: int = 0
    penalty_notices_resolved: int = 0
    moa_aoa_filed: bool = True
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
    black_flag_count: int
    red_flag_count: int
    yellow_flag_count: int
    green_flag_count: int
    score_hash: str

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
PRIVATE_COMPANY_QUORUM = 2
ANNUAL_RETURN_DEADLINE_DAYS = 30
DIRECTOR_FILING_DEADLINE_DAYS = 14
SHARE_CERTIFICATE_DEADLINE_DAYS = 60
REGISTERED_OFFICE_DEADLINE_DAYS = 28
FIRST_AUDITOR_DEADLINE_DAYS = 30
CHARGE_REGISTRATION_DEADLINE_DAYS = 30
ALLOTMENT_FILING_DEADLINE_DAYS = 30
SPECIAL_RESOLUTION_DEADLINE_DAYS = 30

REQUIRED_REGISTERS = [
    "members", "directors", "charges", "transfers", "debentures",
    "minutes_agm", "minutes_board",
]
CORE_REGISTERS = ["members", "directors", "charges", "minutes_agm"]

# Legacy set — retained for rule_ids that should be override but may not have
# is_black_override=True set correctly. Currently empty; all overrides use
# inline is_black_override=True on the flag itself.
BLACK_OVERRIDE_RULES: set[str] = set()

REVENUE_TIER_MAP = {
    Severity.GREEN: RevenueTier.COMPLIANCE_PACKAGE,
    Severity.YELLOW: RevenueTier.COMPLIANCE_PACKAGE,
    Severity.RED: RevenueTier.STRUCTURED_REGULARIZATION,
    Severity.BLACK: RevenueTier.CORPORATE_RESCUE,
}

FOREIGN_WORK_PERMIT_THRESHOLD_USD = 50000
BIDA_ADVANTAGE_THRESHOLD_USD = 100000
_VAT_TURNOVER_THRESHOLD_BDT = 3000000


class NLCRuleEngine:
    _ESC_RULE_IDS: frozenset = frozenset({"ESC-001", "ESC-002", "ESC-003"})

    def __init__(self):
        self.today = date.today()
        self._flags: List[ComplianceFlag] = []

    def evaluate(self, company: CompanyProfile) -> EngineOutput:
        self._flags = []
        self.today = date.today()

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
        self._run_tax_rules(company)
        self._run_structural_change_rules(company)
        self._run_escalation_rules(company)

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
    def _run_incorporation_rules(self, c: CompanyProfile) -> None:
        if not c.moa_aoa_filed:
            self._add_flag(ComplianceFlag(
                rule_id="INC-001",
                flag_code="MOA_AOA_NOT_FILED",
                severity=Severity.RED,
                score_impact=15,
                revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
                description="Memorandum and Articles of Association not filed with RJSC.",
                statutory_basis="Companies Act 1994, Section 11",
            ))

        if c.paid_up_capital_bdt > 0 and not c.form_iii_filed:
            delay = (self.today - c.incorporation_date).days
            if delay > REGISTERED_OFFICE_DEADLINE_DAYS:
                self._add_flag(ComplianceFlag(
                    rule_id="INC-002",
                    flag_code="SITURATION_NOTICE_NOT_FILED",
                    severity=Severity.YELLOW if delay < 90 else Severity.RED,
                    score_impact=5,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description=f"Form III (Situation Notice) not filed. Sec 81: 28-day deadline. Overdue by {delay} days.",
                    statutory_basis="Companies Act 1994, Section 81",
                    detail={"delay_days": delay}
                ))

        if c.current_director_count < 2:
            inc003_impact = 20 if c.current_director_count == 0 else 15
            inc003_desc = (
                "Private company has NO directors. Section 90(2) requires minimum 2. Company cannot legally act."
                if c.current_director_count == 0
                else "Private company has only 1 director. Section 90(2) requires minimum 2."
            )
            self._add_flag(ComplianceFlag(
                rule_id="INC-003",
                flag_code="MINIMUM_DIRECTORS_NOT_MET",
                severity=Severity.BLACK,
                score_impact=inc003_impact,
                is_black_override=True,
                revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
                description=inc003_desc,
                statutory_basis="Companies Act 1994, Section 90(2)",
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
                statutory_basis="Companies Act 1994, Section 150",
                detail={"paid_up": c.paid_up_capital_bdt, "authorized": c.authorized_capital_bdt}
            ))

        if c.has_foreign_shareholder:
            if not c.encashment_certificate_uploaded:
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
                    score_impact=5,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description=f"Remittance USD {c.remittance_amount_usd:,.2f} below USD {FOREIGN_WORK_PERMIT_THRESHOLD_USD:,} work permit threshold.",
                    statutory_basis="BIDA Foreign Investment Act 1980",
                    detail={"remittance_usd": c.remittance_amount_usd, "threshold": FOREIGN_WORK_PERMIT_THRESHOLD_USD},
                    conditional_applies=True
                ))

        if not c.trade_license_obtained:
            self._add_flag(ComplianceFlag(
                rule_id="TL-001",
                flag_code="TRADE_LICENSE_NOT_OBTAINED",
                severity=Severity.YELLOW,
                score_impact=5,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description="Trade License not obtained from City Corporation/Municipality.",
                statutory_basis="City Corporation Ordinance 1983 / Pourashava Act 2009",
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
                statutory_basis="City Corporation Ordinance 1983 / Pourashava Act 2009",
                detail={"expired_days": days_expired},
            ))

    # ───────────────────────────────────────────────────────────────────
    # MODULE 1: AUDITOR
    # ───────────────────────────────────────────────────────────────────
    def _run_auditor_rules(self, c: CompanyProfile) -> None:
        if not c.first_auditor_appointed:
            deadline = c.incorporation_date + timedelta(days=FIRST_AUDITOR_DEADLINE_DAYS)
            if self.today > deadline:
                delay = (self.today - deadline).days
                if delay <= 60: aud_impact, aud_sev = 5, Severity.YELLOW
                elif delay <= 365: aud_impact, aud_sev = 10, Severity.RED
                elif delay <= 730: aud_impact, aud_sev = 15, Severity.RED
                else: aud_impact, aud_sev = 20, Severity.BLACK
                self._add_flag(ComplianceFlag(
                    rule_id="AUD-001",
                    flag_code="FIRST_AUDITOR_NOT_APPOINTED",
                    severity=aud_sev,
                    score_impact=aud_impact,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE if delay <= 365 else RevenueTier.STRUCTURED_REGULARIZATION,
                    description="First auditor not appointed within 30 days. Section 210(1): overdue by " + str(delay) + " days.",
                    statutory_basis="Companies Act 1994, Section 210(1)",
                    detail={"delay_days": delay}
                ))

        if c.first_auditor_appointed and c.agm_count > 0 and not c.auditor_reappointed_at_agm and not c.audit_in_progress and not c.last_agm_date is None:
            fy_end = c.last_agm_date - timedelta(days=90)
            if self.today > fy_end + timedelta(days=120):
                 self._add_flag(ComplianceFlag(
                    rule_id="AUD-005",
                    flag_code="SUBSEQUENT_AUDITOR_NOT_APPOINTED",
                    severity=Severity.RED,
                    score_impact=10,
                    revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
                    description="No auditor appointed for current FY. Section 210(2): mandatory at every AGM.",
                    statutory_basis="Companies Act 1994, Section 210(2)",
                ))

        if c.agm_scheduled_date and not c.audit_complete:
            warning = c.agm_scheduled_date - timedelta(days=AGM_NOTICE_MINIMUM_DAYS)
            if self.today >= warning:
                days_to = (c.agm_scheduled_date - self.today).days
                severity = Severity.RED if days_to < 14 else Severity.YELLOW
                self._add_flag(ComplianceFlag(
                    rule_id="AUD-002",
                    flag_code="AUDIT_MISSING_PRE_AGM",
                    severity=severity,
                    score_impact=12,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description=f"Audit not complete. AGM in {days_to} days. Section 151 requires audited accounts at AGM.",
                    statutory_basis="Companies Act 1994, Section 151",
                    detail={"days_to_agm": days_to}
                ))

        if c.agm_held_this_cycle and not c.audit_complete:
            self._add_flag(ComplianceFlag(
                rule_id="AUD-003",
                flag_code="AGM_HELD_WITHOUT_VALID_AUDIT",
                severity=Severity.BLACK,
                score_impact=25,
                revenue_tier=RevenueTier.CORPORATE_RESCUE,
                description="AGM held without completed audit. Section 151: AGM procedurally defective, potentially void.",
                statutory_basis="Companies Act 1994, Sections 151, 210",
                detail={"override_to_black": True},
                is_black_override=True,
            ))

        if c.agm_held_this_cycle and not c.auditor_reappointed_at_agm:
            self._add_flag(ComplianceFlag(
                rule_id="AUD-004",
                flag_code="AUDITOR_NOT_REAPPOINTED",
                severity=Severity.YELLOW,
                score_impact=5,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description="Auditor not reappointed at AGM. Section 210(2): mandatory at every AGM.",
                statutory_basis="Companies Act 1994, Section 210(2)",
            ))

    # ───────────────────────────────────────────────────────────────────
    # MODULE 2: AGM
    # ───────────────────────────────────────────────────────────────────
    def _run_agm_rules(self, c: CompanyProfile) -> None:
        if c.agm_count == 0:
            deadline = c.incorporation_date + timedelta(days=FIRST_AGM_DEADLINE_DAYS)
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
                    statutory_basis="Companies Act 1994, Section 81",
                    detail={"delay_days": delay, "deadline": str(deadline)}
                ))
            return

        if c.last_agm_date and not c.agm_held_this_cycle:
            cond_a = c.last_agm_date + timedelta(days=SUBSEQUENT_AGM_DEADLINE_DAYS)
            cond_b = self._get_fy_end_deadline(c)
            agm_deadline = min(cond_a, cond_b)
            basis = "15_MONTH" if cond_a <= cond_b else "6_MONTH_FY"

            if self.today > agm_deadline:
                delay = (self.today - agm_deadline).days
                severity = Severity.BLACK if delay > 365 else Severity.RED
                self._add_flag(ComplianceFlag(
                    rule_id="AGM-002",
                    flag_code="SUBSEQUENT_AGM_DEFAULT",
                    severity=severity,
                    score_impact=self._graduated_agm_deduction(delay),
                    revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
                    description=f"AGM overdue by {delay} days. Section 81: deadline by {basis} rule.",
                    statutory_basis="Companies Act 1994, Section 81",
                    detail={"delay_days": delay, "basis": basis}
                ))

        if c.agm_scheduled_date and c.notice_sent_date:
            clear_days = (c.agm_scheduled_date - c.notice_sent_date).days - 1
            if clear_days < AGM_NOTICE_MINIMUM_DAYS:
                self._add_flag(ComplianceFlag(
                    rule_id="AGM-003",
                    flag_code="AGM_NOTICE_DEFECTIVE",
                    severity=Severity.YELLOW,
                    score_impact=5,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description=f"AGM notice issued with {clear_days} clear days. Section 85 requires 21 clear days.",
                    statutory_basis="Companies Act 1994, Section 85",
                    detail={"clear_days": clear_days}
                ))

        if c.agm_scheduled_date and not c.notice_sent_date:
            warn = c.agm_scheduled_date - timedelta(days=AGM_NOTICE_MINIMUM_DAYS)
            if self.today >= warn:
                days_rem = (c.agm_scheduled_date - self.today).days
                self._add_flag(ComplianceFlag(
                    rule_id="AGM-004",
                    flag_code="AGM_NOTICE_NOT_ISSUED",
                    severity=Severity.YELLOW,
                    score_impact=3,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description=f"AGM notice not issued. {days_rem} days to AGM. Section 85 requires 21 clear days notice.",
                    statutory_basis="Companies Act 1994, Section 85",
                    detail={"days_to_agm": days_rem}
                ))

        if c.agm_held_this_cycle and c.members_present_at_agm < PRIVATE_COMPANY_QUORUM:
            self._add_flag(ComplianceFlag(
                rule_id="AGM-005",
                flag_code="AGM_QUORUM_DEFECTIVE",
                severity=Severity.RED,
                score_impact=15,
                revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
                description=f"AGM quorum not met. {c.members_present_at_agm} present, need {PRIVATE_COMPANY_QUORUM}. Section 83.",
                statutory_basis="Companies Act 1994, Section 83",
                detail={"present": c.members_present_at_agm, "required": PRIVATE_COMPANY_QUORUM}
            ))

        if c.agm_held_this_cycle and not c.agm_minutes_prepared:
            self._add_flag(ComplianceFlag(
                rule_id="AGM-006",
                flag_code="AGM_MINUTES_NOT_PREPARED",
                severity=Severity.YELLOW,
                score_impact=5,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description="AGM held but minutes not prepared. Section 83: minutes are prima facie evidence.",
                statutory_basis="Companies Act 1994, Section 83",
            ))

    # ───────────────────────────────────────────────────────────────────
    # MODULE 3: ANNUAL RETURNS
    # ───────────────────────────────────────────────────────────────────
    def _run_annual_return_rules(self, c: CompanyProfile) -> None:
        if c.last_agm_date and not c.annual_return_filed:
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
                    description=f"Annual Return not filed within 30 days of AGM. Overdue by {delay} days.",
                    statutory_basis="Companies Act 1994, Section 119; RJSC Filing Guidelines",
                    detail={"delay_days": delay}
                ))

        if c.unfiled_returns_count >= 2:
            self._add_flag(ComplianceFlag(
                rule_id="AR-002",
                flag_code="ANNUAL_RETURN_BACKLOG_RED",
                severity=Severity.RED,
                score_impact=20,
                revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
                description=f"{c.unfiled_returns_count} Annual Returns unfiled. Section 304: strike-off risk elevated.",
                statutory_basis="Companies Act 1994, Sections 119, 304",
                detail={"unfiled_count": c.unfiled_returns_count}
            ))

        if c.unfiled_returns_count >= 3:
            self._add_flag(ComplianceFlag(
                rule_id="AR-003",
                flag_code="ANNUAL_RETURN_BACKLOG_BLACK",
                severity=Severity.BLACK,
                score_impact=20,
                revenue_tier=RevenueTier.CORPORATE_RESCUE,
                description=f"{c.unfiled_returns_count} Annual Returns unfiled. Section 304: severe default, director liability.",
                statutory_basis="Companies Act 1994, Sections 119, 304",
                detail={"unfiled_count": c.unfiled_returns_count}
            ))

        if c.annual_return_filed and not c.annual_return_content_complete:
            missing = []
            if not c.schedule_x_attached: missing.append("Schedule X")
            if not c.balance_sheet_attached: missing.append("Balance Sheet")
            if not c.profit_loss_attached: missing.append("P&L Account")
            if not c.directors_list_attached: missing.append("Directors List")
            if not c.shareholders_list_attached: missing.append("Shareholders List")
            self._add_flag(ComplianceFlag(
                rule_id="AR-004",
                flag_code="ANNUAL_RETURN_INCOMPLETE",
                severity=Severity.YELLOW,
                score_impact=8,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description=f"Annual Return incomplete. Missing: {', '.join(missing)}. Section 119 + Schedule X require complete disclosure.",
                statutory_basis="Companies Act 1994, Section 119, Schedule X",
                detail={"missing": missing}
            ))

    # ───────────────────────────────────────────────────────────────────
    # MODULE 4: DIRECTORS
    # ───────────────────────────────────────────────────────────────────
    def _run_director_rules(self, c: CompanyProfile) -> None:
        for change in c.director_changes:
            delay = (self.today - change.event_date).days
            if not change.form_filed and delay > DIRECTOR_FILING_DEADLINE_DAYS:
                if change.event_type == "appointment":
                    severity = Severity.RED if delay > 90 else Severity.YELLOW
                    self._add_flag(ComplianceFlag(
                        rule_id="DIR-001",
                        flag_code="FORM_XII_APPOINTMENT_PENDING",
                        severity=severity,
                        score_impact=10 if delay > 90 else 5,
                        revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                        description=f"Director appointment not filed via Form XII. Section 92: 14-day deadline. Overdue by {delay} days.",
                        statutory_basis="Companies Act 1994, Section 92",
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
                        description=f"Director {change.event_type} not filed via Form XII. Section 92: 14-day deadline. Overdue by {delay} days.",
                        statutory_basis="Companies Act 1994, Section 92",
                        detail={"director_id": change.director_id, "delay": delay, "type": change.event_type}
                    ))
                    self._add_flag(ComplianceFlag(
                        rule_id="DIR-004",
                        flag_code="DEPARTED_DIRECTOR_STILL_LIABLE",
                        severity=Severity.RED,
                        score_impact=10,
                        revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
                        description="Departed director still liable until Form XII filed. Section 92: filing required to release liability.",
                        statutory_basis="Companies Act 1994, Section 92",
                        detail={"director_id": change.director_id}
                    ))

                if delay > 365:
                    self._add_flag(ComplianceFlag(
                        rule_id="DIR-003",
                        flag_code="DIRECTOR_FILING_MAJOR_IRREGULARITY",
                        severity=Severity.RED,
                        score_impact=15,
                        revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
                        description=f"Director filing overdue {delay} days. Exceeds 1 year — Major Irregularity.",
                        statutory_basis="Companies Act 1994, Section 92",
                        detail={"director_id": change.director_id, "delay": delay}
                    ))

    # ───────────────────────────────────────────────────────────────────
    # MODULE 5: SHAREHOLDING
    # ───────────────────────────────────────────────────────────────────
    def _run_shareholder_rules(self, c: CompanyProfile) -> None:
        if c.last_allotment_date and not c.form_xv_filed:
            delay = (self.today - c.last_allotment_date).days
            if delay > ALLOTMENT_FILING_DEADLINE_DAYS:
                self._add_flag(ComplianceFlag(
                    rule_id="SH-001",
                    flag_code="FORM_XV_ALLOTMENT_NOT_FILED",
                    severity=Severity.YELLOW if delay < 90 else Severity.RED,
                    score_impact=8,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description=f"Share allotment not filed via Form XV. Section 50: 30-day deadline. Overdue by {delay} days.",
                    statutory_basis="Companies Act 1994, Section 50",
                    detail={"delay": delay}
                ))

        if c.last_allotment_date and not c.share_certificates_issued:
            delay = (self.today - c.last_allotment_date).days
            if delay > SHARE_CERTIFICATE_DEADLINE_DAYS:
                self._add_flag(ComplianceFlag(
                    rule_id="SH-002",
                    flag_code="SHARE_CERTIFICATES_NOT_ISSUED",
                    severity=Severity.YELLOW if delay < 90 else Severity.RED,
                    score_impact=5,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description=f"Share certificates not issued within 60 days. Section 46: overdue by {delay - SHARE_CERTIFICATE_DEADLINE_DAYS} days.",
                    statutory_basis="Companies Act 1994, Section 46",
                    detail={"delay": delay}
                ))

        if c.capital_increase_date and not c.form_iv_filed:
            delay = (self.today - c.capital_increase_date).days
            if delay > ALLOTMENT_FILING_DEADLINE_DAYS:
                self._add_flag(ComplianceFlag(
                    rule_id="SH-003",
                    flag_code="FORM_IV_CAPITAL_INCREASE_NOT_FILED",
                    severity=Severity.YELLOW if delay < 90 else Severity.RED,
                    score_impact=8,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description=f"Capital increase not filed via Form IV. Section 52: 30-day deadline. Overdue by {delay} days.",
                    statutory_basis="Companies Act 1994, Section 52",
                    detail={"delay": delay}
                ))

    # ───────────────────────────────────────────────────────────────────
    # MODULE 6: SHARE TRANSFERS
    # ───────────────────────────────────────────────────────────────────
    def _run_transfer_rules(self, c: CompanyProfile) -> None:
        for transfer in c.share_transfers:
            transfer_is_void = (
                c.aoa_transfer_restriction 
                and transfer.aoa_restriction_apply 
                and not transfer.board_approval_obtained
            )

            if not transfer.instrument_recorded or not transfer.form_117_filed:
                self._add_flag(ComplianceFlag(
                    rule_id="TR-001",
                    flag_code="TRANSFER_NO_INSTRUMENT_FORM_117",
                    severity=Severity.YELLOW,
                    score_impact=5,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description="Share transfer without Form 117 instrument. Section 108: proper instrument required.",
                    statutory_basis="Companies Act 1994, Section 108",
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

            if not transfer.board_approval_obtained and c.aoa_transfer_restriction and not transfer.aoa_restriction_apply:
                self._add_flag(ComplianceFlag(
                    rule_id="TR-003",
                    flag_code="TRANSFER_NO_BOARD_APPROVAL",
                    severity=Severity.YELLOW,
                    score_impact=8,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description="Share transfer without board approval. Section 47 + AoA: approval required where restricted.",
                    statutory_basis="Companies Act 1994, Section 47; AoA",
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
                    statutory_basis="Companies Act 1994, Section 34",
                    detail={"transfer_id": transfer.transfer_id}
                ))

            if transfer_is_void:
                self._add_flag(ComplianceFlag(
                    rule_id="TR-005",
                    flag_code="AOA_TRANSFER_RESTRICTION_VIOLATED",
                    severity=Severity.BLACK,
                    score_impact=15,
                    revenue_tier=RevenueTier.CORPORATE_RESCUE,
                    description="Transfer violated AoA restriction. Section 47: such transfer is void. BLACK override.",
                    statutory_basis="Companies Act 1994, Section 47; AoA",
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
                    statutory_basis="Companies Act 1994, Sections 34, 47, 108",
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
                statutory_basis="Companies Act 1994, Sections 34, 90, 87",
                detail={"missing": non_core_missing}
            ))

        if core_missing:
            severity = Severity.RED if len(core_missing) <= 2 else Severity.BLACK
            self._add_flag(ComplianceFlag(
                rule_id="REG-002",
                flag_code="CORE_REGISTERS_MISSING",
                severity=severity,
                score_impact=10 if len(core_missing) <= 2 else 20,
                revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION if severity == Severity.RED else RevenueTier.CORPORATE_RESCUE,
                description=f"Core registers missing: {', '.join(core_missing)}. Members (Sec 34), Directors (Sec 90), Charges (Sec 87), AGM Minutes (Sec 83).",
                statutory_basis="Companies Act 1994, Sections 34, 83, 87, 90",
                detail={"missing_core": core_missing}
            ))

        if c.register_location != "registered_office":
            self._add_flag(ComplianceFlag(
                rule_id="REG-003",
                flag_code="REGISTERS_NOT_AT_REGISTERED_OFFICE",
                severity=Severity.YELLOW,
                score_impact=3,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description=f"Registers at '{c.register_location}', not registered office. Section 34(2): must be at registered office.",
                statutory_basis="Companies Act 1994, Section 34(2)",
                detail={"location": c.register_location}
            ))

    # ───────────────────────────────────────────────────────────────────
    # MODULE 8: REGISTERED OFFICE
    # ───────────────────────────────────────────────────────────────────
    def _run_office_rules(self, c: CompanyProfile) -> None:
        if c.registered_office_change_date and not c.form_vi_filed:
            delay = (self.today - c.registered_office_change_date).days
            if delay > REGISTERED_OFFICE_DEADLINE_DAYS:
                self._add_flag(ComplianceFlag(
                    rule_id="OFF-001",
                    flag_code="REGISTERED_OFFICE_CHANGE_NOT_FILED",
                    severity=Severity.YELLOW if delay < 90 else Severity.RED,
                    score_impact=3,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description=f"Office change not filed via Form VI. Section 81: 28-day deadline. Overdue by {delay} days.",
                    statutory_basis="Companies Act 1994, Section 81",
                    detail={"delay": delay, "form": "Form VI"}
                ))

    # ───────────────────────────────────────────────────────────────────
    # MODULE 9: CAPITAL & CHARGES
    # ───────────────────────────────────────────────────────────────────
    def _run_capital_rules(self, c: CompanyProfile) -> None:
        if c.capital_increase_date and not c.capital_increase_resolution:
            self._add_flag(ComplianceFlag(
                rule_id="CAP-001",
                flag_code="CAPITAL_INCREASE_RESOLUTION_MISSING",
                severity=Severity.YELLOW,
                score_impact=5,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description="Capital increase without shareholder resolution. Section 54: Ordinary/Special Resolution required.",
                statutory_basis="Companies Act 1994, Section 54",
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
                        description=f"{charge.charge_type} charge (Tk {charge.amount_bdt:,.2f}) not registered. Section 87: 30-day deadline. Unregistered charge void against liquidator.",
                        statutory_basis="Companies Act 1994, Section 87",
                        detail={"charge_id": charge.charge_id, "delay": delay, "amount": charge.amount_bdt}
                    ))

            if charge.satisfied and not charge.satisfaction_filed:
                self._add_flag(ComplianceFlag(
                    rule_id="CHG-001",
                    flag_code="CHARGE_SATISFACTION_NOT_FILED",
                    severity=Severity.YELLOW,
                    score_impact=3,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description="Charge satisfaction not filed via Form XIX. Sec 87.",
                    statutory_basis="Companies Act 1994, Section 87",
                    detail={"charge_id": charge.charge_id, "charge_type": charge.charge_type}
                ))

        if c.capital_reduction_pending:
            self._add_flag(ComplianceFlag(
                rule_id="CAP-003",
                flag_code="CAPITAL_REDUCTION_WITHOUT_COURT",
                severity=Severity.BLACK,
                score_impact=15,
                revenue_tier=RevenueTier.CORPORATE_RESCUE,
                description="Capital reduction without court order. Sec 100.",
                statutory_basis="Companies Act 1994, Section 100",
                is_black_override=True,
            ))

        if c.special_resolution_date and not c.special_resolution_filed:
            delay = (self.today - c.special_resolution_date).days
            if delay > SPECIAL_RESOLUTION_DEADLINE_DAYS:
                self._add_flag(ComplianceFlag(
                    rule_id="CAP-004",
                    flag_code="SPECIAL_RESOLUTION_NOT_FILED",
                    severity=Severity.YELLOW if delay < 90 else Severity.RED,
                    score_impact=8,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description=f"Special resolution not filed. Section 87: 30-day deadline. Unfiled resolution not binding.",
                    statutory_basis="Companies Act 1994, Section 87",
                    detail={"delay": delay}
                ))

    # ───────────────────────────────────────────────────────────────────
    # MODULE 10: TAX COMPLIANCE
    # ───────────────────────────────────────────────────────────────────
    def _run_tax_rules(self, c: CompanyProfile) -> None:
        if not c.tin_obtained:
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

        if c.tin_obtained and not c.tax_return_filed_for_current_fy:
            if self.today.month <= 6:
                fy_end_year = self.today.year - 1
            else:
                fy_end_year = self.today.year
            if c.tax_return_deadline_extended:
                deadline = date(fy_end_year + 1, 11, 30)
            else:
                deadline = date(fy_end_year + 1, 7, 31)
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
                    detail={"delay_days": delay, "fy_year": fy_end_year}
                ))

        if c.tin_obtained:
            fiscal_q = self._fiscal_quarter()
            missed = []
            if fiscal_q > 1 and not c.advance_tax_q1_paid: missed.append("Q1")
            if fiscal_q > 2 and not c.advance_tax_q2_paid: missed.append("Q2")
            if fiscal_q > 3 and not c.advance_tax_q3_paid: missed.append("Q3")
            if fiscal_q == 1 and not c.advance_tax_q4_paid: missed.append("Q4")
            
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

        if c.vat_registered and c.last_vat_return_filed:
            expected_month_end = (self.today.replace(day=1) - timedelta(days=1)).replace(day=15)
            if self.today > expected_month_end and c.last_vat_return_filed < expected_month_end:
                 self._add_flag(ComplianceFlag(
                    rule_id="VAT-002",
                    flag_code="MONTHLY_VAT_RETURN_OVERDUE",
                    severity=Severity.YELLOW,
                    score_impact=5,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description="Monthly/Bi-monthly VAT return overdue. VAT Act 2012.",
                    statutory_basis="Value Added Tax Act 2012 (Bangladesh)",
                ))

        if c.vat_registered and not c.vat_annual_return_filed_for_fy and self.today.month > 9:
            self._add_flag(ComplianceFlag(
                rule_id="VAT-003",
                flag_code="VAT_ANNUAL_RETURN_OVERDUE",
                severity=Severity.YELLOW,
                score_impact=5,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description="VAT Annual Return overdue for current FY. VAT Act 2012.",
                statutory_basis="Value Added Tax Act 2012 (Bangladesh)",
            ))

        unresolved = c.penalty_notices_received - c.penalty_notices_resolved
        if unresolved > 0:
            sev = Severity.RED if unresolved >= 3 else Severity.YELLOW
            self._add_flag(ComplianceFlag(
                rule_id="DEF-002",
                flag_code="PENALTY_PROSECUTION_RISK",
                severity=sev,
                score_impact=8 if unresolved >= 3 else 5,
                revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
                description=f"{unresolved} unresolved penalties. Sec 447: fine up to Tk 10,000.",
                statutory_basis="Companies Act 1994, Section 447",
                detail={"unresolved": unresolved}
            ))

    # ───────────────────────────────────────────────────────────────────
    # MODULE 11: STRUCTURAL CHANGE
    # ───────────────────────────────────────────────────────────────────
    def _run_structural_change_rules(self, c: CompanyProfile) -> None:
        if c.name_change_pending and c.name_change_date:
            delay = (self.today - c.name_change_date).days
            if delay > SPECIAL_RESOLUTION_DEADLINE_DAYS:
                sev = Severity.RED if delay > 90 else Severity.YELLOW
                self._add_flag(ComplianceFlag(
                    rule_id="STR-001", flag_code="NAME_CHANGE_NOT_FILED",
                    severity=sev, score_impact=8 if delay > 90 else 3,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description=f"Name change not filed. Sec 20: Special Resolution + RJSC filing. Overdue {delay} days.",
                    statutory_basis="Companies Act 1994, Section 20",
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
                    statutory_basis="Companies Act 1994, Section 17",
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
                    statutory_basis="Companies Act 1994, Section 18",
                    detail={"delay_days": delay}
                ))

    # ───────────────────────────────────────────────────────────────────
    # MODULE 12: ESCALATION
    # ───────────────────────────────────────────────────────────────────
    def _run_escalation_rules(self, c: CompanyProfile) -> None:
        agm_years = self._calculate_agm_default_years(c)
        ar_years = c.unfiled_returns_count

        # DEF-001 must be evaluated BEFORE ESC-003 black-count snapshot
        if c.any_director_disqualified:
            disq_count = len(c.disqualification_details)
            impact = 20 if disq_count == 1 else 25
            is_override = disq_count >= (c.current_director_count - 1)
            self._add_flag(ComplianceFlag(
                rule_id="DEF-001",
                flag_code="DIRECTOR_DISQUALIFIED",
                severity=Severity.BLACK,
                score_impact=impact,
                revenue_tier=RevenueTier.CORPORATE_RESCUE,
                description=f"{disq_count} director(s) disqualified under Sec 297. Cannot act as director for 5 years.",
                statutory_basis="Companies Act 1994, Section 297",
                detail={"disqualifications": c.disqualification_details, "count": disq_count},
                is_black_override=is_override,
            ))

        if agm_years >= 2 and ar_years >= 2:
            self._add_flag(ComplianceFlag(
                rule_id="ESC-001",
                flag_code="STRIKE_OFF_RISK_ELEVATED",
                severity=Severity.RED,
                score_impact=15,
                revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
                description=f"2+ year AGM and Return defaults. Section 304: RJSC strike-off risk elevated.",
                statutory_basis="Companies Act 1994, Section 304",
                detail={"agm_years": agm_years, "ar_years": ar_years}
            ))

        if agm_years >= 3 or ar_years >= 3 or c.on_rjsc_strike_off_list:
            # Suppress ESC-001 if ESC-002 is firing
            self._flags = [f for f in self._flags if f.rule_id != "ESC-001"]
            self._add_flag(ComplianceFlag(
                rule_id="ESC-002",
                flag_code="STRIKE_OFF_IMMINENT",
                severity=Severity.BLACK,
                score_impact=25,
                revenue_tier=RevenueTier.CORPORATE_RESCUE,
                description=f"3+ year default or on strike-off list. Section 304: strike-off imminent. Corporate Rescue mandatory.",
                statutory_basis="Companies Act 1994, Section 304",
                detail={"agm_years": agm_years, "ar_years": ar_years, "on_list": c.on_rjsc_strike_off_list},
                is_black_override=True,
                escalation_pending=True,
            ))

        black_flags = [f for f in self._flags if f.severity == Severity.BLACK and f.rule_id not in self._ESC_RULE_IDS]
        if len(black_flags) >= 2:
            esc003_impact = 10 if len(black_flags) == 2 else (25 if len(black_flags) == 3 else 35)
            self._add_flag(ComplianceFlag(
                rule_id="ESC-003",
                flag_code="RESCUE_REQUIRED_MANDATORY",
                severity=Severity.BLACK,
                score_impact=esc003_impact,
                revenue_tier=RevenueTier.CORPORATE_RESCUE,
                description="Multiple BLACK flags (" + str(len(black_flags)) + "). Corporate Rescue mandatory. Systemic failure detected.",
                statutory_basis="Companies Act 1994, Sections 81, 92, 119, 304 (aggregate)",
                detail={"black_count": len(black_flags)},
                is_black_override=True,
            ))

    # ───────────────────────────────────────────────────────────────────
    # SCORING ENGINE
    # ───────────────────────────────────────────────────────────────────
    def _calculate_score(self, flags: List[ComplianceFlag], company: CompanyProfile) -> ScoreBreakdown:
        active = [f for f in flags if not f.resolved and f.conditional_applies]

        tax_ded = sum(f.score_impact for f in active if f.rule_id.startswith(("TAX-", "VAT-")))
        agm_ded = sum(f.score_impact for f in active if f.rule_id.startswith("AGM-"))
        aud_ded = sum(f.score_impact for f in active if f.rule_id.startswith("AUD-"))
        ret_ded = sum(f.score_impact for f in active if f.rule_id.startswith("AR-"))
        dir_ded = sum(f.score_impact for f in active if f.rule_id.startswith(("DIR-", "INC-", "DEF-", "TL-")))
        shr_ded = sum(f.score_impact for f in active if f.rule_id.startswith(("SH-", "TR-")))
        cap_ded = sum(f.score_impact for f in active if f.rule_id.startswith(("CAP-", "STR-", "CHG-")))
        off_ded = sum(f.score_impact for f in active if f.rule_id.startswith("OFF-"))
        reg_ded = sum(f.score_impact for f in active if f.rule_id.startswith("REG-"))

        raw = 100 - (tax_ded + agm_ded + aud_ded + ret_ded + dir_ded + shr_ded + cap_ded + off_ded + reg_ded)
        raw = max(0, raw)
        
        override = False
        reason = None
        final = raw
        critical = [f for f in active if f.is_black_override]
        if critical:
            override = True
            reason = f"BLACK override: {', '.join(f.rule_id for f in critical)}"
            final = 0

        if final >= 85: band = Severity.GREEN
        elif final >= 60: band = Severity.YELLOW
        elif final > 0: band = Severity.RED
        else: band = Severity.BLACK

        if band in (Severity.GREEN, Severity.YELLOW): exposure = ExposureBand.LOW
        elif band == Severity.RED: exposure = ExposureBand.HIGH
        else: exposure = ExposureBand.SEVERE

        active_rules = {f.rule_id for f in active}
        hash_str = f"{final}:{','.join(sorted(active_rules))}:{RULE_ENGINE_VERSION}"
        score_hash = hashlib.sha256(hash_str.encode()).hexdigest()[:16]

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
            black_flag_count=len([f for f in active if f.severity == Severity.BLACK]),
            red_flag_count=len([f for f in active if f.severity == Severity.RED]),
            yellow_flag_count=len([f for f in active if f.severity == Severity.YELLOW]),
            green_flag_count=len([f for f in active if f.severity == Severity.GREEN]),
            score_hash=score_hash
        )

    # ───────────────────────────────────────────────────────────────────
    # RESCUE & LIFECYCLE SEQUENCING
    # ───────────────────────────────────────────────────────────────────
    def _generate_rescue_sequence(self, c: CompanyProfile, flags: List[ComplianceFlag], score: ScoreBreakdown) -> List[Dict[str, Any]]:
        active = [f for f in flags if not f.resolved and f.conditional_applies]
        active_rules = {f.rule_id for f in active}
        steps = []

        def add_step(title: str, desc: str, rules: List[str], priority: str, min_days: int, max_days: int):
            steps.append({"title": title, "description": desc, "related_rules": rules, "priority": priority, "min_days": min_days, "max_days": max_days})

        if score.risk_band not in (Severity.RED, Severity.BLACK):
            return []

        if any(r in active_rules for r in {"AGM-001", "AGM-002"}):
            add_step("Hold Overdue AGM", "Convene AGM immediately. Section 81.", ["AGM-001", "AGM-002"], "CRITICAL", 14, 30)

        if any(r in active_rules for r in {"AUD-001", "AUD-002", "AUD-003"}):
            add_step("Retrospective Audit", "Engage auditors for all defaulted years. Section 210.", ["AUD-001", "AUD-002", "AUD-003"], "HIGH", 30, 45)

        # TAX-004: Advance Tax Payment Missed — read directly from flags
        tax004_flags = [f for f in active if f.rule_id == "TAX-004"]
        if tax004_flags:
            all_missed = []
            for f in tax004_flags:
                all_missed.extend(f.detail.get("quarters", []))
            if all_missed:
                add_step("Pay Advance Tax", f"Missed quarters: {', '.join(all_missed)}. ITA 2023 Sec 74.", ["TAX-004"], "MEDIUM", 7, 14)

        if any(r in active_rules for r in {"TR-005", "TR-006"}):
            add_step("Ratify Irregular Transfers", "Board ratify irregular transfers. Section 47: AoA violations may need court rectification.", ["TR-001", "TR-002", "TR-003", "TR-004", "TR-005"], "HIGH", 10, 21)

        if "ESC-002" in active_rules:
            add_step("Defend Strike-Off", "File immediate application to set aside strike-off. Section 304.", ["ESC-002", "AR-002", "AR-003"], "CRITICAL", 1, 7)

        return steps

    def _determine_lifecycle_stage(self, c: CompanyProfile) -> LifecycleStage:
        if c.on_rjsc_strike_off_list or c.is_dormant:
            return LifecycleStage.DORMANT_STRIKE_OFF
        if c.agm_count == 0:
            return LifecycleStage.PRE_FIRST_AGM
        
        # Check for active defaults
        has_black = any(f.severity == Severity.BLACK and not f.resolved for f in self._flags)
        has_red = any(f.severity == Severity.RED and not f.resolved for f in self._flags)
        
        if has_black:
            return LifecycleStage.STATUTORY_DEFAULT
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
        fy_year = c.last_agm_date.year if c.last_agm_date.month > 6 else c.last_agm_date.year - 1
        fy_end = date(fy_year, 6, 30)
        return fy_end + timedelta(days=FY_END_AGM_DEADLINE_DAYS)

    def _calculate_agm_default_years(self, c: CompanyProfile) -> int:
        if not c.last_agm_date:
            if c.agm_count == 0:
                deadline = c.incorporation_date + timedelta(days=FIRST_AGM_DEADLINE_DAYS)
                if self.today > deadline:
                    return (self.today - deadline).days // 365
            return 0
            
        deadline = min(
            c.last_agm_date + timedelta(days=SUBSEQUENT_AGM_DEADLINE_DAYS),
            self._get_fy_end_deadline(c)
        )
        if self.today > deadline:
            return (self.today - deadline).days // 365
        return 0