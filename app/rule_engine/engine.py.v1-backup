# ═══════════════════════════════════════════════════════════════════════
# NEUM LEX COUNSEL — RJSC COMPLIANCE INTELLIGENCE PLATFORM
# LAYER C: LEGAL RULE ENGINE — COMPLETE IMPLEMENTATION
# All 30 ILRMF v1.0 Rules | Deterministic | AI-Non-Editable
# Version: 1.0 | Classification: PROPRIETARY IP — NEUM LEX COUNSEL
# Governed by: Internal AI Constitution v1.0
# ═══════════════════════════════════════════════════════════════════════
#
# GOVERNANCE MANDATE:
# This engine is a compliance intelligence instrument.
# AI cannot override, modify, or bypass any rule in this engine.
# Every rule references its ILRMF rule_id and statutory basis.
# All outputs are logged with rule_id + rule_version for legal defensibility.
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
# Every score snapshot records this version for legal defensibility
# ───────────────────────────────────────────────────────────────────────
RULE_ENGINE_VERSION = "1.0"
ILRMF_VERSION = "1.0"


# ═══════════════════════════════════════════════════════════════════════
# ENUMERATIONS
# ═══════════════════════════════════════════════════════════════════════

class Severity(str, Enum):
    GREEN  = "GREEN"
    YELLOW = "YELLOW"
    RED    = "RED"
    BLACK  = "BLACK"


class RevenueTier(str, Enum):
    COMPLIANCE_PACKAGE          = "COMPLIANCE_PACKAGE"
    STRUCTURED_REGULARIZATION   = "STRUCTURED_REGULARIZATION"
    CORPORATE_RESCUE            = "CORPORATE_RESCUE"


class ExposureBand(str, Enum):
    LOW      = "LOW"
    MODERATE = "MODERATE"
    HIGH     = "HIGH"
    SEVERE   = "SEVERE"


class RuleType(str, Enum):
    DEADLINE    = "DEADLINE"
    DEPENDENCY  = "DEPENDENCY"
    THRESHOLD   = "THRESHOLD"
    CASCADE     = "CASCADE"
    ESCALATION  = "ESCALATION"


class LifecycleStage(str, Enum):
    INCORPORATION           = "INCORPORATION"
    PRE_FIRST_AGM           = "PRE_FIRST_AGM"
    POST_FIRST_AGM          = "POST_FIRST_AGM"
    ANNUAL_COMPLIANCE_CYCLE = "ANNUAL_COMPLIANCE_CYCLE"
    STRUCTURAL_CHANGE       = "STRUCTURAL_CHANGE"
    IRREGULAR_STATUS        = "IRREGULAR_STATUS"
    STATUTORY_DEFAULT       = "STATUTORY_DEFAULT"
    DORMANT_STRIKE_OFF      = "DORMANT_STRIKE_OFF"


# ═══════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class ComplianceFlag:
    """
    Structured output of a fired rule.
    Every flag contains full traceability for legal defensibility.
    """
    rule_id:            str
    flag_code:          str
    severity:           Severity
    score_impact:       int         # Points deducted from base 100
    revenue_tier:       RevenueTier
    description:        str
    statutory_basis:    str
    rule_version:       str = RULE_ENGINE_VERSION
    triggered_date:     date = field(default_factory=date.today)
    detail:             Dict[str, Any] = field(default_factory=dict)
    resolved:           bool = False
    is_black_override: bool = False
    escalation_pending: bool = False


@dataclass
class DirectorChange:
    director_id:        str
    event_type:         str     # 'appointment' | 'resignation' | 'removal'
    event_date:         date
    form_filed:         bool = False
    form_filed_date:    Optional[date] = None


@dataclass
class ShareTransfer:
    transfer_id:            str
    transfer_date:          date
    instrument_recorded:    bool = False
    stamp_duty_paid:        bool = False
    stamp_duty_amount:      Optional[float] = None
    board_approval:         bool = False
    share_register_updated: bool = False
    aoa_restriction_apply:  bool = False
    board_approval_obtained:bool = False


@dataclass
class CompanyProfile:
    """
    Complete input data model for the rule engine.
    All fields sourced from the database — no AI involvement in data.
    """
    # Identity
    company_id:                 str
    company_name:               str
    company_type:               str         # PRIVATE_LIMITED etc.

    # Dates
    incorporation_date:         date
    financial_year_end:         date        # The day/month matters

    # AGM State
    agm_count:                  int         # Total AGMs held to date
    last_agm_date:              Optional[date]
    agm_held_this_cycle:        bool = False
    agm_held_without_audit:     bool = False
    agm_scheduled_date:         Optional[date] = None
    notice_sent_date:           Optional[date] = None
    members_present_at_agm:     int = 0
    auditor_reappointed_at_agm: bool = False
    accounts_adopted_at_agm:    bool = False

    # Audit State
    first_auditor_appointed:    bool = False
    audit_complete:             bool = False
    last_audit_signed_date:     Optional[date] = None
    audit_in_progress:          bool = False

    # Annual Return State
    last_return_filed_year:     Optional[int] = None
    unfiled_returns_count:      int = 0
    annual_return_filed:        bool = False
    annual_return_content_complete: bool = False
    last_agm_filing_date:       Optional[date] = None

    # Director Changes (this compliance cycle)
    director_changes:           List[DirectorChange] = field(default_factory=list)

    # Shareholder Changes
    shareholder_change_date:    Optional[date] = None
    form_xv_filed:              bool = False

    # Share Transfers
    share_transfers:            List[ShareTransfer] = field(default_factory=list)

    # Registered Office
    registered_office_change_date: Optional[date] = None
    form_ix_filed:              bool = False

    # Corporate Structure
    aoa_transfer_restriction:   bool = True
    has_foreign_shareholder:    bool = False
    is_dormant:                 bool = False
    is_fdi_registered:          bool = False

    # Statutory Registers
    maintained_registers:       List[str] = field(default_factory=list)

    # Share Certificates
    last_allotment_date:        Optional[date] = None
    share_certificate_issued:   bool = True

    # Capital Events
    capital_increase_date:      Optional[date] = None
    capital_increase_resolution:bool = False

    # Charge Events
    charge_creation_date:       Optional[date] = None
    form_viii_filed:            bool = False


@dataclass
class ScoreBreakdown:
    """
    Detailed score breakdown for explainability.
    AI Constitution 2.3: Every flag must show calculation logic.
    """
    agm_score:          int     # out of 25
    audit_score:        int     # out of 25
    return_score:       int     # out of 20
    director_score:     int     # out of 15
    shareholding_score: int     # out of 15
    raw_total:          int     # Sum before override
    final_score:        int     # After override
    override_applied:   bool
    override_reason:    Optional[str]
    risk_band:          Severity
    exposure_band:      ExposureBand
    revenue_tier:       RevenueTier
    active_flag_count:  int
    black_flag_count:   int
    red_flag_count:     int
    yellow_flag_count:  int
    score_hash:         str     # Tamper-evident hash


@dataclass
class EngineOutput:
    """
    Complete output of a single rule engine evaluation run.
    """
    company_id:         str
    evaluation_date:    date
    engine_version:     str
    ilrmf_version:      str
    flags:              List[ComplianceFlag]
    score_breakdown:    ScoreBreakdown
    lifecycle_stage:    LifecycleStage
    rescue_sequence:    List[Dict[str, Any]]
    fdi_module_active:  bool


# ═══════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════

# Statutory deadlines in days (Companies Act 1994, Section 81)
FIRST_AGM_DEADLINE_DAYS         = 548   # 18 months
SUBSEQUENT_AGM_DEADLINE_DAYS    = 456   # 15 months
FY_END_AGM_DEADLINE_DAYS        = 182   # 6 months after FY end
ANNUAL_RETURN_DEADLINE_DAYS     = 30    # After AGM
DIRECTOR_FILING_DEADLINE_DAYS   = 30    # After event
SHARE_CERTIFICATE_DEADLINE_DAYS = 60    # After allotment
REGISTERED_OFFICE_DEADLINE_DAYS = 30    # After change
FIRST_AUDITOR_DEADLINE_DAYS     = 30    # After incorporation
AGM_NOTICE_MINIMUM_DAYS         = 21    # Before AGM
PRIVATE_COMPANY_QUORUM          = 2     # Members

# Required statutory registers
REQUIRED_REGISTERS = [
    "members",
    "directors",
    "charges",
    "transfers",
    "debentures",
    "mortgages",
]

# Score weight table (ILRMF Article 4, AI Constitution)
SCORE_WEIGHTS = {
    "agm":          25,
    "audit":        25,
    "annual_return":20,
    "director":     15,
    "shareholding": 15,
}

# Risk band boundaries
RISK_BANDS = {
    Severity.GREEN:  (70, 100),
    Severity.YELLOW: (50, 69),
    Severity.RED:    (30, 49),
    Severity.BLACK:  (0, 29),
}

# Rules that force BLACK override regardless of score
BLACK_OVERRIDE_RULES = {"AUD-003", "TR-005", "ESC-002", "ESC-003"}

# Revenue tier mapping
REVENUE_TIER_MAP = {
    Severity.GREEN:  RevenueTier.COMPLIANCE_PACKAGE,
    Severity.YELLOW: RevenueTier.COMPLIANCE_PACKAGE,
    Severity.RED:    RevenueTier.STRUCTURED_REGULARIZATION,
    Severity.BLACK:  RevenueTier.CORPORATE_RESCUE,
}


# ═══════════════════════════════════════════════════════════════════════
# RULE ENGINE — MAIN CLASS
# ═══════════════════════════════════════════════════════════════════════

class NLCRuleEngine:
    """
    NEUM LEX COUNSEL — Deterministic Legal Rule Engine
    
    GOVERNANCE MANDATE (Internal AI Constitution v1.0):
    ─────────────────────────────────────────────────────
    1. This engine is deterministic. No probabilistic outputs.
    2. AI cannot call, modify, or override any method in this class.
    3. Every rule references its ILRMF rule_id.
    4. Every output includes rule_version for legal defensibility.
    5. This engine is the single source of compliance truth.
    
    STATUTORY BASIS: Companies Act 1994 (Bangladesh)
    """

    def __init__(self):
        self.today = date.today()
        self._flags: List[ComplianceFlag] = []

    def evaluate(self, company: CompanyProfile) -> EngineOutput:
        """
        Master evaluation entry point.
        Runs all rule modules in dependency-aware sequence.
        Returns complete EngineOutput with flags, score, and rescue plan.
        """
        self._flags = []
        self.today = date.today()

        logger.info(
            f"[RuleEngine v{RULE_ENGINE_VERSION}] Evaluating: "
            f"{company.company_id} | {company.company_name}"
        )

        # ── Rule Modules (in dependency order) ─────────────────────────
        self._run_auditor_rules(company)        # Auditor must fire first (dependency)
        self._run_agm_rules(company)            # AGM depends on audit
        self._run_annual_return_rules(company)  # Return depends on AGM
        self._run_director_rules(company)       # Independent chain
        self._run_shareholder_rules(company)    # Independent chain
        self._run_transfer_rules(company)       # Independent chain
        self._run_register_rules(company)       # Independent chain
        self._run_office_rules(company)         # Independent chain
        self._run_capital_rules(company)        # Independent chain
        self._run_escalation_rules(company)     # Must run LAST

        # ── Lifecycle Stage ─────────────────────────────────────────────
        stage = self._determine_lifecycle_stage(company)

        # ── Score Calculation ───────────────────────────────────────────
        score = self._calculate_score(self._flags, company)

        # ── Rescue Sequence ─────────────────────────────────────────────
        rescue = self._generate_rescue_sequence(company, self._flags, score)

        # ── FDI Module ──────────────────────────────────────────────────
        fdi_active = company.has_foreign_shareholder or company.is_fdi_registered

        logger.info(
            f"[RuleEngine] Score: {score.final_score} | "
            f"Band: {score.risk_band} | "
            f"Flags: {len(self._flags)} | "
            f"Stage: {stage}"
        )

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
        )

    # ═══════════════════════════════════════════════════════════════════
    # RULE MODULE 1: AUDITOR RULES
    # Runs first — audit is a precondition for AGM validity
    # ═══════════════════════════════════════════════════════════════════

    def _run_auditor_rules(self, c: CompanyProfile) -> None:

        # ── AUD-002: First Auditor Not Appointed ───────────────────────
        # Statutory basis: Companies Act 1994, Section 210
        if not c.first_auditor_appointed:
            deadline = c.incorporation_date + timedelta(days=FIRST_AUDITOR_DEADLINE_DAYS)
            if self.today > deadline:
                delay = (self.today - deadline).days
                severity = Severity.RED if delay > 60 else Severity.YELLOW
                self._add_flag(ComplianceFlag(
                    rule_id="AUD-002",
                    flag_code="FIRST_AUDITOR_NOT_APPOINTED",
                    severity=severity,
                    score_impact=10,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description=(
                        f"First auditor not appointed within 30 days of incorporation. "
                        f"Overdue by {delay} days."
                    ),
                    statutory_basis="Companies Act 1994, Section 210",
                    detail={"delay_days": delay, "deadline": str(deadline)}
                ))

        # ── AUD-001: Audit Missing Pre-AGM ────────────────────────────
        # Statutory basis: Companies Act 1994, Section 151
        if c.agm_scheduled_date and not c.audit_complete:
            warning_threshold = c.agm_scheduled_date - timedelta(days=AGM_NOTICE_MINIMUM_DAYS)
            if self.today >= warning_threshold:
                days_to_agm = (c.agm_scheduled_date - self.today).days
                severity = Severity.RED if days_to_agm < 14 else Severity.YELLOW
                self._add_flag(ComplianceFlag(
                    rule_id="AUD-001",
                    flag_code="AUDIT_MISSING_PRE_AGM",
                    severity=severity,
                    score_impact=12,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description=(
                        f"Audit not complete. AGM scheduled in {days_to_agm} days. "
                        f"Audited accounts must be available before AGM."
                    ),
                    statutory_basis="Companies Act 1994, Section 151",
                    detail={"days_to_agm": days_to_agm}
                ))

        # ── AUD-003: AGM Held Without Valid Audit — BLACK OVERRIDE ──────
        # This is the most severe audit violation.
        # AGM held without completed audit = AGM may be legally void.
        if c.agm_held_this_cycle and not c.audit_complete:
            self._add_flag(ComplianceFlag(
                rule_id="AUD-003",
                flag_code="AGM_HELD_WITHOUT_VALID_AUDIT",
                severity=Severity.BLACK,
                score_impact=25,
                revenue_tier=RevenueTier.CORPORATE_RESCUE,
                description=(
                    "AGM was held without a completed audit. "
                    "Financial statements could not have been properly adopted. "
                    "AGM is procedurally defective and may be legally void."
                ),
                statutory_basis="Companies Act 1994, Sections 151, 210",
                detail={"override_to_black": True},
                is_black_override=True,
            ))

    # ═══════════════════════════════════════════════════════════════════
    # RULE MODULE 2: AGM RULES
    # Depends on: AUD-003 (audit must be evaluated first)
    # ═══════════════════════════════════════════════════════════════════

    def _run_agm_rules(self, c: CompanyProfile) -> None:

        # ── AGM-001: First AGM Default ────────────────────────────────
        # Statutory basis: Companies Act 1994, Section 81
        # Deadline: 18 months (548 days) from incorporation
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
                    description=(
                        f"First AGM not held within 18 months of incorporation. "
                        f"Overdue by {delay} days."
                    ),
                    statutory_basis="Companies Act 1994, Section 81",
                    detail={"delay_days": delay, "deadline": str(deadline)}
                ))
            return  # No subsequent AGM rules apply if first AGM not yet held

        # ── AGM-002: Subsequent AGM Default ───────────────────────────
        # DUAL CONDITION — the earlier deadline governs
        # Condition A: within 15 months of last AGM
        # Condition B: within 6 months of financial year end
        if c.last_agm_date and not c.agm_held_this_cycle:
            condition_a = c.last_agm_date + timedelta(days=SUBSEQUENT_AGM_DEADLINE_DAYS)
            condition_b = self._get_fy_end_deadline(c)
            agm_deadline = min(condition_a, condition_b)
            basis = "15_MONTH" if condition_a <= condition_b else "6_MONTH_FY"

            if self.today > agm_deadline:
                delay = (self.today - agm_deadline).days
                severity = Severity.BLACK if delay > 365 else Severity.RED
                self._add_flag(ComplianceFlag(
                    rule_id="AGM-002",
                    flag_code="AGM_DEFAULT",
                    severity=severity,
                    score_impact=self._graduated_agm_deduction(delay),
                    revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
                    description=(
                        f"AGM overdue by {delay} days. "
                        f"Deadline governed by {basis} rule."
                    ),
                    statutory_basis="Companies Act 1994, Section 81",
                    detail={
                        "delay_days": delay,
                        "deadline": str(agm_deadline),
                        "deadline_basis": basis,
                        "condition_a": str(condition_a),
                        "condition_b": str(condition_b),
                    }
                ))

        # ── AGM-003: AGM Notice Defective ─────────────────────────────
        # Statutory basis: Companies Act 1994, Section 86
        if c.agm_scheduled_date and c.notice_sent_date:
            gap = (c.agm_scheduled_date - c.notice_sent_date).days
            if gap < AGM_NOTICE_MINIMUM_DAYS:
                self._add_flag(ComplianceFlag(
                    rule_id="AGM-003",
                    flag_code="AGM_NOTICE_DEFECTIVE",
                    severity=Severity.YELLOW,
                    score_impact=5,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description=(
                        f"AGM notice issued only {gap} days before meeting. "
                        f"Minimum {AGM_NOTICE_MINIMUM_DAYS} days required. "
                        f"AGM is procedurally defective."
                    ),
                    statutory_basis="Companies Act 1994, Section 86",
                    detail={"notice_gap_days": gap, "required_days": AGM_NOTICE_MINIMUM_DAYS}
                ))

        # ── AGM-004: AGM Notice Not Issued ────────────────────────────
        if c.agm_scheduled_date and not c.notice_sent_date:
            warning_date = c.agm_scheduled_date - timedelta(days=AGM_NOTICE_MINIMUM_DAYS)
            if self.today >= warning_date:
                days_remaining = (c.agm_scheduled_date - self.today).days
                self._add_flag(ComplianceFlag(
                    rule_id="AGM-004",
                    flag_code="AGM_NOTICE_NOT_ISSUED",
                    severity=Severity.YELLOW,
                    score_impact=3,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description=(
                        f"AGM notice not yet issued. {days_remaining} days to AGM. "
                        f"Notice must reach all members at least 21 days before meeting."
                    ),
                    statutory_basis="Companies Act 1994, Section 86",
                    detail={"days_to_agm": days_remaining}
                ))

        # ── AGM-005: AGM Quorum Defective ─────────────────────────────
        # Private company: minimum 2 members personally present
        if c.agm_held_this_cycle and c.members_present_at_agm < PRIVATE_COMPANY_QUORUM:
            self._add_flag(ComplianceFlag(
                rule_id="AGM-005",
                flag_code="AGM_QUORUM_DEFECTIVE",
                severity=Severity.RED,
                score_impact=15,
                revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
                description=(
                    f"AGM quorum not met. {c.members_present_at_agm} member(s) present. "
                    f"Minimum {PRIVATE_COMPANY_QUORUM} required for private company. "
                    f"AGM must be reconvened."
                ),
                statutory_basis="Companies Act 1994, Section 96",
                detail={
                    "members_present": c.members_present_at_agm,
                    "quorum_required": PRIVATE_COMPANY_QUORUM
                }
            ))

        # ── AGM-006: Auditor Not Reappointed at AGM ───────────────────
        if c.agm_held_this_cycle and not c.auditor_reappointed_at_agm:
            self._add_flag(ComplianceFlag(
                rule_id="AGM-006",
                flag_code="AUDITOR_REAPPOINTMENT_MISSING",
                severity=Severity.YELLOW,
                score_impact=5,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description=(
                    "Auditor not reappointed at AGM. "
                    "Annual reappointment is mandatory under Section 210."
                ),
                statutory_basis="Companies Act 1994, Section 210",
            ))

    # ═══════════════════════════════════════════════════════════════════
    # RULE MODULE 3: ANNUAL RETURN RULES
    # Depends on: AGM must be held first
    # ═══════════════════════════════════════════════════════════════════

    def _run_annual_return_rules(self, c: CompanyProfile) -> None:

        # ── AR-001: Annual Return Default ─────────────────────────────
        # Deadline: 30 days after AGM date
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
                    description=(
                        f"Annual Return (Schedule X) not filed. "
                        f"Overdue by {delay} days. "
                        f"Required within 30 days of AGM."
                    ),
                    statutory_basis="Companies Act 1994, Section 148",
                    detail={"delay_days": delay, "deadline": str(deadline)}
                ))

        # ── AR-002: Annual Return Backlog — RED ───────────────────────
        if c.unfiled_returns_count >= 2:
            self._add_flag(ComplianceFlag(
                rule_id="AR-002",
                flag_code="ANNUAL_RETURN_BACKLOG_RED",
                severity=Severity.RED,
                score_impact=20,
                revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
                description=(
                    f"{c.unfiled_returns_count} Annual Returns unfiled. "
                    f"2+ year backlog constitutes Statutory Default. "
                    f"RJSC strike-off risk elevated."
                ),
                statutory_basis="Companies Act 1994, Section 148",
                detail={"unfiled_count": c.unfiled_returns_count}
            ))

        # ── AR-003: Annual Return Backlog — BLACK ─────────────────────
        if c.unfiled_returns_count >= 3:
            self._add_flag(ComplianceFlag(
                rule_id="AR-003",
                flag_code="ANNUAL_RETURN_BACKLOG_BLACK",
                severity=Severity.BLACK,
                score_impact=20,
                revenue_tier=RevenueTier.CORPORATE_RESCUE,
                description=(
                    f"{c.unfiled_returns_count} Annual Returns unfiled. "
                    f"3+ year Severe Default. Corporate Rescue required. "
                    f"Director personal liability likely activated."
                ),
                statutory_basis="Companies Act 1994, Sections 148, 304",
                detail={"unfiled_count": c.unfiled_returns_count, "override_to_black": True}
            ))

        # ── AR-004: Annual Return Content Incomplete ───────────────────
        if c.annual_return_filed and not c.annual_return_content_complete:
            self._add_flag(ComplianceFlag(
                rule_id="AR-004",
                flag_code="ANNUAL_RETURN_INCOMPLETE",
                severity=Severity.YELLOW,
                score_impact=8,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description=(
                    "Annual Return filed but Schedule X content is incomplete. "
                    "Incomplete filing is treated as non-filing by RJSC."
                ),
                statutory_basis="Companies Act 1994, Section 148, Schedule X",
            ))

    # ═══════════════════════════════════════════════════════════════════
    # RULE MODULE 4: DIRECTOR RULES
    # Independent chain from AGM/Return
    # ═══════════════════════════════════════════════════════════════════

    def _run_director_rules(self, c: CompanyProfile) -> None:
        for change in c.director_changes:
            delay = (self.today - change.event_date).days

            if not change.form_filed and delay > DIRECTOR_FILING_DEADLINE_DAYS:

                if change.event_type == "appointment":
                    # ── DIR-001: Director Appointment Not Filed ────────
                    severity = Severity.RED if delay > 90 else Severity.YELLOW
                    score_impact = 10 if delay > 90 else 5
                    self._add_flag(ComplianceFlag(
                        rule_id="DIR-001",
                        flag_code="FORM_XII_PENDING_DIRECTOR_APPT",
                        severity=severity,
                        score_impact=score_impact,
                        revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                        description=(
                            f"Director appointment not filed via Form XII. "
                            f"Overdue by {delay} days."
                        ),
                        statutory_basis="Companies Act 1994, Sections 81–84",
                        detail={"director_id": change.director_id, "delay_days": delay}
                    ))

                elif change.event_type == "resignation":
                    # ── DIR-002: Director Resignation Not Filed ────────
                    severity = Severity.RED if delay > 90 else Severity.YELLOW
                    score_impact = 10 if delay > 90 else 5
                    self._add_flag(ComplianceFlag(
                        rule_id="DIR-002",
                        flag_code="FORM_XIV_PENDING",
                        severity=severity,
                        score_impact=score_impact,
                        revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                        description=(
                            f"Director resignation not filed via Form XIV. "
                            f"Overdue by {delay} days."
                        ),
                        statutory_basis="Companies Act 1994, Section 84",
                        detail={"director_id": change.director_id, "delay_days": delay}
                    ))

                    # ── DIR-004: Departed Director Still Liable ────────
                    # Until Form XIV is filed, the resigned director remains
                    # legally liable for company actions
                    self._add_flag(ComplianceFlag(
                        rule_id="DIR-004",
                        flag_code="DEPARTED_DIRECTOR_STILL_LIABLE",
                        severity=Severity.RED,
                        score_impact=10,
                        revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
                        description=(
                            "Resigned director remains legally liable for company actions "
                            "until Form XIV is filed with RJSC. "
                            "Immediate filing required to release director liability."
                        ),
                        statutory_basis="Companies Act 1994, Section 84",
                        detail={"director_id": change.director_id}
                    ))

                # ── DIR-003: Director Filing Major Irregularity (>1 year)
                if delay > 365:
                    self._add_flag(ComplianceFlag(
                        rule_id="DIR-003",
                        flag_code="DIRECTOR_FILING_MAJOR_IRREGULARITY",
                        severity=Severity.RED,
                        score_impact=15,
                        revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
                        description=(
                            f"Director filing overdue by {delay} days. "
                            f"Exceeds 1-year threshold. Classified as Major Irregularity."
                        ),
                        statutory_basis="Companies Act 1994, Sections 81–84",
                        detail={"director_id": change.director_id, "delay_days": delay}
                    ))

    # ═══════════════════════════════════════════════════════════════════
    # RULE MODULE 5: SHAREHOLDER RULES
    # ═══════════════════════════════════════════════════════════════════

    def _run_shareholder_rules(self, c: CompanyProfile) -> None:

        # ── SH-001: Shareholder Change Not Filed ──────────────────────
        if (c.shareholder_change_date and not c.form_xv_filed):
            delay = (self.today - c.shareholder_change_date).days
            if delay > DIRECTOR_FILING_DEADLINE_DAYS:
                severity = Severity.RED if delay > 90 else Severity.YELLOW
                self._add_flag(ComplianceFlag(
                    rule_id="SH-001",
                    flag_code="FORM_XV_PENDING",
                    severity=severity,
                    score_impact=5,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description=(
                        f"Shareholder change not filed via Form XV. "
                        f"Overdue by {delay} days."
                    ),
                    statutory_basis="Companies Act 1994, Section 150",
                    detail={"delay_days": delay}
                ))

    # ═══════════════════════════════════════════════════════════════════
    # RULE MODULE 6: SHARE TRANSFER RULES
    # 5-point verification for every transfer (TR-001 to TR-005)
    # ═══════════════════════════════════════════════════════════════════

    def _run_transfer_rules(self, c: CompanyProfile) -> None:
        for transfer in c.share_transfers:

            # ── TR-001: No Proper Transfer Instrument ─────────────────
            if not transfer.instrument_recorded:
                self._add_flag(ComplianceFlag(
                    rule_id="TR-001",
                    flag_code="TRANSFER_NO_INSTRUMENT",
                    severity=Severity.YELLOW,
                    score_impact=5,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description=(
                        "Share transfer recorded without proper transfer instrument. "
                        "Instrument is required to evidence legal title transfer."
                    ),
                    statutory_basis="Companies Act 1994, Section 46",
                    detail={"transfer_id": transfer.transfer_id}
                ))

            # ── TR-002: Stamp Duty Not Confirmed ──────────────────────
            if not transfer.stamp_duty_paid or transfer.stamp_duty_amount is None:
                self._add_flag(ComplianceFlag(
                    rule_id="TR-002",
                    flag_code="STAMP_DUTY_NOT_CONFIRMED",
                    severity=Severity.YELLOW,
                    score_impact=5,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description=(
                        "Stamp duty not confirmed for share transfer. "
                        "Unstamped instruments are inadmissible in court proceedings."
                    ),
                    statutory_basis="Stamp Act (Bangladesh)",
                    detail={"transfer_id": transfer.transfer_id}
                ))

            # ── TR-003: No Board Approval Recorded ────────────────────
            if not transfer.board_approval:
                self._add_flag(ComplianceFlag(
                    rule_id="TR-003",
                    flag_code="TRANSFER_NO_BOARD_APPROVAL",
                    severity=Severity.YELLOW,
                    score_impact=8,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description=(
                        "Share transfer recorded without board approval resolution. "
                        "Board must approve transfer (or confirm AoA permits free transfer)."
                    ),
                    statutory_basis="Companies Act 1994, Section 47",
                    detail={"transfer_id": transfer.transfer_id}
                ))

            # ── TR-004: Share Register Not Updated ────────────────────
            if not transfer.share_register_updated:
                self._add_flag(ComplianceFlag(
                    rule_id="TR-004",
                    flag_code="TRANSFER_REGISTER_NOT_UPDATED",
                    severity=Severity.YELLOW,
                    score_impact=5,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description=(
                        "Register of Members not updated following share transfer. "
                        "Register is the legal record of ownership."
                    ),
                    statutory_basis="Companies Act 1994, Section 26",
                    detail={"transfer_id": transfer.transfer_id}
                ))

            # ── TR-005: AoA Transfer Restriction Violated — BLACK ──────
            # This is a structural governance breach. Transfer may be void.
            if (c.aoa_transfer_restriction and
                transfer.aoa_restriction_apply and
                not transfer.board_approval_obtained):
                self._add_flag(ComplianceFlag(
                    rule_id="TR-005",
                    flag_code="AoA_TRANSFER_RESTRICTION_VIOLATED",
                    severity=Severity.BLACK,
                    score_impact=15,
                    revenue_tier=RevenueTier.CORPORATE_RESCUE,
                    description=(
                        "Share transfer violated AoA restriction. "
                        "Transfer conducted without required board approval "
                        "where AoA mandates it. "
                        "Transfer may be legally void. Structural governance breach."
                    ),
                    statutory_basis="Companies Act 1994, Section 47; AoA Transfer Restriction",
                    detail={
                        "transfer_id": transfer.transfer_id,
                        "override_to_black": True
                    },
                    is_black_override=True,
                ))

            # ── TR-006: Transfer Composite Irregularity ────────────────
            tr_flags_for_transfer = [
                f for f in self._flags
                if f.detail.get("transfer_id") == transfer.transfer_id
                and f.rule_id.startswith("TR-")
            ]
            if len(tr_flags_for_transfer) >= 2:
                self._add_flag(ComplianceFlag(
                    rule_id="TR-006",
                    flag_code="TRANSFER_IRREGULAR",
                    severity=Severity.RED,
                    score_impact=0,  # Composite — individual flags already scored
                    revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
                    description=(
                        f"Share transfer has {len(tr_flags_for_transfer)} compliance "
                        f"deficiencies. Classified as Irregular Transfer requiring remediation."
                    ),
                    statutory_basis="Companies Act 1994, Sections 46–47",
                    detail={
                        "transfer_id": transfer.transfer_id,
                        "deficiency_count": len(tr_flags_for_transfer)
                    }
                ))

    # ═══════════════════════════════════════════════════════════════════
    # RULE MODULE 7: STATUTORY REGISTER RULES
    # ═══════════════════════════════════════════════════════════════════

    def _run_register_rules(self, c: CompanyProfile) -> None:

        # Normalize register naming conventions (alias handling)
        register_aliases = {
            "register_of_members": "members",
            "register_of_directors": "directors",
            "register_of_share_transfers": "transfers",
            "register_of_charges": "charges",
            "register_of_debenture_holders": "debentures",
            "minutes_book_board": "minutes_book_board",
            "minutes_book_general": "minutes_book_general",
        }
        normalized_maintained = {
            register_aliases.get(r, r) for r in c.maintained_registers
        }

        # ── REG-001: Statutory Register Incomplete ────────────────────
        missing = [r for r in REQUIRED_REGISTERS if r not in normalized_maintained]
        if missing:
            self._add_flag(ComplianceFlag(
                rule_id="REG-001",
                flag_code="STATUTORY_REGISTER_INCOMPLETE",
                severity=Severity.YELLOW,
                score_impact=5,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description=(
                    f"{len(missing)} statutory register(s) not maintained: "
                    f"{', '.join(missing)}."
                ),
                statutory_basis="Companies Act 1994, Section 26",
                detail={"missing_registers": missing}
            ))

        # ── REG-002: Share Certificate Not Issued ─────────────────────
        if (c.last_allotment_date and not c.share_certificate_issued):
            delay = (self.today - c.last_allotment_date).days
            if delay > SHARE_CERTIFICATE_DEADLINE_DAYS:
                self._add_flag(ComplianceFlag(
                    rule_id="REG-002",
                    flag_code="SHARE_CERTIFICATE_DEFAULT",
                    severity=Severity.YELLOW if delay < 90 else Severity.RED,
                    score_impact=5,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description=(
                        f"Share certificates not issued within 60 days of allotment. "
                        f"Overdue by {delay - 60} days."
                    ),
                    statutory_basis="Companies Act 1994, Section 46",
                    detail={"delay_days": delay, "deadline_days": SHARE_CERTIFICATE_DEADLINE_DAYS}
                ))

        # ── REG-004: Statutory Register Core Maintenance (Members/Directors/Charges) ─────
        core_registers = [
            "members",
            "directors",
            "charges",
        ]
        missing_core = [r for r in core_registers if r not in normalized_maintained]
        if missing_core:
            severity = Severity.RED if len(missing_core) == 1 else Severity.BLACK
            score_impact = 10 if len(missing_core) == 1 else 20
            self._add_flag(ComplianceFlag(
                rule_id="REG-004",
                flag_code="STATUTORY_REGISTER_CORE_DEFECT",
                severity=severity,
                score_impact=score_impact,
                revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION if severity in (Severity.RED, Severity.YELLOW) else RevenueTier.CORPORATE_RESCUE,
                description=(
                    "One or more core statutory registers for members, directors, or charges "
                    "are not maintained."
                ),
                statutory_basis="Companies Act 1994, Section 26",
                detail={"missing_core_registers": missing_core}
            ))

    # ═══════════════════════════════════════════════════════════════════
    # RULE MODULE 8: REGISTERED OFFICE RULES
    # ═══════════════════════════════════════════════════════════════════

    def _run_office_rules(self, c: CompanyProfile) -> None:

        # ── OFF-001: Registered Office Change Not Filed ───────────────
        if c.registered_office_change_date and not c.form_ix_filed:
            delay = (self.today - c.registered_office_change_date).days
            if delay > REGISTERED_OFFICE_DEADLINE_DAYS:
                self._add_flag(ComplianceFlag(
                    rule_id="OFF-001",
                    flag_code="REGISTERED_OFFICE_CHANGE_NOT_FILED",
                    severity=Severity.YELLOW if delay < 90 else Severity.RED,
                    score_impact=3,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description=(
                        f"Registered office change not filed via Form IX. "
                        f"Overdue by {delay} days."
                    ),
                    statutory_basis="Companies Act 1994, Section 27",
                    detail={"delay_days": delay}
                ))

    # ═══════════════════════════════════════════════════════════════════
    # RULE MODULE 9: CAPITAL RULES
    # ═══════════════════════════════════════════════════════════════════

    def _run_capital_rules(self, c: CompanyProfile) -> None:

        # ── CAP-001: Capital Increase Without Resolution ───────────────
        if c.capital_increase_date and not c.capital_increase_resolution:
            self._add_flag(ComplianceFlag(
                rule_id="CAP-001",
                flag_code="CAPITAL_INCREASE_RESOLUTION_MISSING",
                severity=Severity.YELLOW,
                score_impact=5,
                revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                description=(
                    "Capital increase recorded without shareholder resolution. "
                    "Ordinary or Special Resolution required before RJSC filing."
                ),
                statutory_basis="Companies Act 1994, Section 61",
            ))

        # ── CAP-002: Charge Not Filed ──────────────────────────────────
        if c.charge_creation_date and not c.form_viii_filed:
            delay = (self.today - c.charge_creation_date).days
            if delay > DIRECTOR_FILING_DEADLINE_DAYS:
                self._add_flag(ComplianceFlag(
                    rule_id="CAP-002",
                    flag_code="CHARGE_NOT_FILED",
                    severity=Severity.YELLOW if delay < 90 else Severity.RED,
                    score_impact=5,
                    revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
                    description=(
                        f"Charge/mortgage created but Form VIII not filed. "
                        f"Overdue by {delay} days. "
                        f"Unregistered charge may be void against liquidator."
                    ),
                    statutory_basis="Companies Act 1994, Section 120",
                    detail={"delay_days": delay}
                ))

    # ═══════════════════════════════════════════════════════════════════
    # RULE MODULE 10: ESCALATION RULES
    # Must run LAST — depends on all other modules completing
    # ═══════════════════════════════════════════════════════════════════

    def _run_escalation_rules(self, c: CompanyProfile) -> None:
        agm_default_years = self._calculate_agm_default_years(c)
        ar_default_years  = c.unfiled_returns_count

        # ── ESC-001: Strike-Off Risk Elevated ─────────────────────────
        if agm_default_years >= 2 and ar_default_years >= 2:
            self._add_flag(ComplianceFlag(
                rule_id="ESC-001",
                flag_code="STRIKE_OFF_RISK_ELEVATED",
                severity=Severity.RED,
                score_impact=0,  # Risk band override — not score deduction
                revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
                description=(
                    f"2+ year AGM and Annual Return defaults detected. "
                    f"RJSC strike-off risk elevated. "
                    f"Company at risk of losing legal standing."
                ),
                statutory_basis="Companies Act 1994, Section 304",
                detail={
                    "agm_default_years": agm_default_years,
                    "ar_default_years": ar_default_years
                }
            ))

        # ── ESC-002: Strike-Off Risk Imminent — BLACK OVERRIDE ─────────
        if agm_default_years >= 3 or ar_default_years >= 3:
            self._add_flag(ComplianceFlag(
                rule_id="ESC-002",
                flag_code="STRIKE_OFF_RISK_IMMINENT",
                severity=Severity.BLACK,
                score_impact=0,
                revenue_tier=RevenueTier.CORPORATE_RESCUE,
                description=(
                    f"3+ year default pattern. Strike-off by RJSC imminent. "
                    f"Immediate Corporate Rescue required. "
                    f"Directors personally liable for company obligations at strike-off."
                ),
                statutory_basis="Companies Act 1994, Sections 304–309",
                detail={
                    "agm_default_years": agm_default_years,
                    "ar_default_years": ar_default_years,
                    "override_to_black": True,
                },
                escalation_pending=True,
                is_black_override=True,
            ))

        # ── ESC-003: Rescue Required Mandatory — BLACK OVERRIDE ────────
        active_black = [
            f for f in self._flags if f.severity == Severity.BLACK
        ]
        if len(active_black) >= 2:
            self._add_flag(ComplianceFlag(
                rule_id="ESC-003",
                flag_code="RESCUE_REQUIRED_MANDATORY",
                severity=Severity.BLACK,
                score_impact=0,
                revenue_tier=RevenueTier.CORPORATE_RESCUE,
                description=(
                    "Multiple BLACK flags combined with strike-off risk. "
                    "Corporate Rescue engagement is mandatory, not optional."
                ),
                statutory_basis="Companies Act 1994, Sections 304–309",
                detail={"black_flag_count": len(active_black), "override_to_black": True},
                is_black_override=True,
            ))

    # ═══════════════════════════════════════════════════════════════════
    # SCORING ENGINE
    # AI Constitution Article 4: Score must be fixed, weight-based,
    # tamper-evident, and stored historically
    # ═══════════════════════════════════════════════════════════════════

    def _calculate_score(
        self,
        flags: List[ComplianceFlag],
        company: CompanyProfile
    ) -> ScoreBreakdown:
        """
        Graduated weighted scoring model.
        Base: 100 | Minimum: 0 | Maximum: 100
        Weights: AGM 25 | Audit 25 | Return 20 | Director 15 | Shareholding 15
        """
        active_flags = [f for f in flags if not f.resolved]

        # ── Component scores (start at max, deduct) ───────────────────
        agm_deduction   = sum(f.score_impact for f in active_flags if f.rule_id.startswith("AGM-"))
        audit_deduction = sum(f.score_impact for f in active_flags if f.rule_id.startswith("AUD-"))
        return_deduction= sum(f.score_impact for f in active_flags if f.rule_id.startswith("AR-"))
        director_deduction = sum(f.score_impact for f in active_flags if f.rule_id.startswith("DIR-"))
        share_deduction = sum(f.score_impact for f in active_flags if f.rule_id.startswith(("SH-", "TR-", "REG-")))

        # Cap at component maximums
        agm_score    = max(0, SCORE_WEIGHTS["agm"] - min(agm_deduction, SCORE_WEIGHTS["agm"]))
        audit_score  = max(0, SCORE_WEIGHTS["audit"] - min(audit_deduction, SCORE_WEIGHTS["audit"]))
        return_score = max(0, SCORE_WEIGHTS["annual_return"] - min(return_deduction, SCORE_WEIGHTS["annual_return"]))
        dir_score    = max(0, SCORE_WEIGHTS["director"] - min(director_deduction, SCORE_WEIGHTS["director"]))
        share_score  = max(0, SCORE_WEIGHTS["shareholding"] - min(share_deduction, SCORE_WEIGHTS["shareholding"]))

        raw_total = agm_score + audit_score + return_score + dir_score + share_score

        # ── BLACK Override ─────────────────────────────────────────────
        # Critical flags force score below 29 (BLACK band) regardless
        override_applied = False
        override_reason  = None
        final_score      = raw_total

        critical_active = [f for f in active_flags if f.rule_id in BLACK_OVERRIDE_RULES]
        if critical_active:
            override_applied = True
            override_reason  = (
                f"BLACK override applied: "
                f"{', '.join(f.rule_id for f in critical_active)}"
            )
            final_score = min(raw_total, 29)  # Force into BLACK band

        final_score = max(0, final_score)

        # ── Risk Band ──────────────────────────────────────────────────
        risk_band = self._score_to_band(final_score)

        # ── Exposure Band ──────────────────────────────────────────────
        black_count  = sum(1 for f in active_flags if f.severity == Severity.BLACK)
        red_count    = sum(1 for f in active_flags if f.severity == Severity.RED)
        yellow_count = sum(1 for f in active_flags if f.severity == Severity.YELLOW)
        exposure     = self._calculate_exposure(black_count, red_count, len(active_flags))

        # ── Revenue Tier ───────────────────────────────────────────────
        revenue_tier = REVENUE_TIER_MAP[risk_band]

        # ── Tamper-Evident Hash (AI Constitution Article 4) ────────────
        hash_input = (
            f"{company.company_id}|{final_score}|{risk_band}|"
            f"{self.today}|{RULE_ENGINE_VERSION}"
        )
        score_hash = hashlib.sha256(hash_input.encode()).hexdigest()

        return ScoreBreakdown(
            agm_score=agm_score,
            audit_score=audit_score,
            return_score=return_score,
            director_score=dir_score,
            shareholding_score=share_score,
            raw_total=raw_total,
            final_score=final_score,
            override_applied=override_applied,
            override_reason=override_reason,
            risk_band=risk_band,
            exposure_band=exposure,
            revenue_tier=revenue_tier,
            active_flag_count=len(active_flags),
            black_flag_count=black_count,
            red_flag_count=red_count,
            yellow_flag_count=yellow_count,
            score_hash=score_hash,
        )

    # ═══════════════════════════════════════════════════════════════════
    # RESCUE SEQUENCE GENERATOR
    # Mandatory dependency-aware sequence — steps cannot be reordered
    # ═══════════════════════════════════════════════════════════════════

    def _generate_rescue_sequence(
        self,
        company: CompanyProfile,
        flags: List[ComplianceFlag],
        score: ScoreBreakdown,
    ) -> List[Dict[str, Any]]:
        """
        Generates a dependency-aware rescue sequence.
        Order is legally mandated — cannot be rearranged.
        """
        if score.risk_band not in (Severity.RED, Severity.BLACK):
            return []

        steps = []
        step_num = 1
        active_rules = {f.rule_id for f in flags if not f.resolved}

        def add_step(title, description, rules, complexity, est_min, est_max):
            nonlocal step_num
            steps.append({
                "step_number":      step_num,
                "title":            title,
                "description":      description,
                "rule_references":  rules,
                "complexity":       complexity,
                "est_days_min":     est_min,
                "est_days_max":     est_max,
                "status":           "PENDING",
                "assigned_staff":   None,
            })
            step_num += 1

        # Step 1: Retrospective Audit (always first if audit missing)
        if any(r in active_rules for r in {"AUD-001", "AUD-002", "AUD-003"}):
            add_step(
                title="Retrospective Audit — All Defaulted Years",
                description=(
                    "Engage auditors to obtain retrospective audited financial "
                    "statements for all years in default. "
                    "Audit must complete before any AGM can be validly held."
                ),
                rules=["AUD-001", "AUD-002", "AUD-003"],
                complexity="HIGH",
                est_min=30, est_max=45
            )

        # Step 2: Ratify irregular transfers (if any)
        if any(r in active_rules for r in {"TR-005", "TR-006"}):
            add_step(
                title="Ratify Irregular Share Transfers",
                description=(
                    "Board must ratify all irregular transfers by resolution. "
                    "AoA violation transfers require legal opinion on validity."
                ),
                rules=["TR-001", "TR-002", "TR-003", "TR-004", "TR-005"],
                complexity="HIGH",
                est_min=10, est_max=21
            )

        # Step 3: Update statutory registers
        if "REG-001" in active_rules:
            add_step(
                title="Establish / Update Statutory Registers",
                description=(
                    "All required statutory registers must be established "
                    "and updated to current date before AGMs proceed."
                ),
                rules=["REG-001", "REG-002"],
                complexity="LOW",
                est_min=5, est_max=7
            )

        # Step 4: Hold backlog AGMs in sequence
        if any(r in active_rules for r in {"AGM-001", "AGM-002"}):
            backlog = max(company.unfiled_returns_count, 1)
            add_step(
                title=f"Hold Backlog AGMs — {backlog} Year(s) in Sequence",
                description=(
                    f"Conduct {backlog} AGM(s) in chronological order "
                    f"(oldest first). Each AGM requires 21-day notice. "
                    f"Auditor must be appointed/reappointed at each AGM."
                ),
                rules=["AGM-001", "AGM-002", "AGM-005", "AGM-006"],
                complexity="HIGH",
                est_min=25, est_max=45
            )

        # Step 5: File AGM minutes
        add_step(
            title="File AGM Minutes — Form XIII (All Backlog AGMs)",
            description=(
                "Lodge Form XIII for each AGM held. "
                "File within 30 days of each AGM date."
            ),
            rules=["AGM-003"],
            complexity="LOW",
            est_min=5, est_max=10
        )

        # Step 6: File Annual Returns
        if any(r in active_rules for r in {"AR-001", "AR-002", "AR-003"}):
            backlog = company.unfiled_returns_count
            add_step(
                title=f"File Annual Returns — Schedule X ({backlog} Years)",
                description=(
                    f"File {backlog} Annual Return(s) with RJSC. "
                    f"Each return requires the preceding AGM to have been held. "
                    f"Content must be complete per Schedule X requirements."
                ),
                rules=["AR-001", "AR-002", "AR-003", "AR-004"],
                complexity="MEDIUM",
                est_min=10, est_max=21
            )

        # Step 7: Director and shareholder filings
        if any(r in active_rules for r in {"DIR-001", "DIR-002", "DIR-003", "DIR-004", "SH-001"}):
            add_step(
                title="File Director & Shareholder Changes",
                description=(
                    "File all pending Form XII (appointments), Form XIV (resignations), "
                    "and Form XV (shareholder changes). "
                    "Resolves director liability exposure."
                ),
                rules=["DIR-001", "DIR-002", "DIR-003", "DIR-004", "SH-001"],
                complexity="LOW",
                est_min=3, est_max=7
            )

        # Step 8: RJSC acknowledgment
        add_step(
            title="Obtain RJSC Acknowledgment & Compliance Certificate",
            description=(
                "Confirm all filings received by RJSC. "
                "Apply for compliance certificate. "
                "Update company status in RJSC records."
            ),
            rules=["ESC-001", "ESC-002"],
            complexity="MEDIUM",
            est_min=15, est_max=30
        )

        return steps

    # ═══════════════════════════════════════════════════════════════════
    # LIFECYCLE STAGE DETERMINATION
    # ═══════════════════════════════════════════════════════════════════

    def _determine_lifecycle_stage(self, c: CompanyProfile) -> LifecycleStage:
        if c.unfiled_returns_count >= 3 or self._calculate_agm_default_years(c) >= 3:
            return LifecycleStage.STATUTORY_DEFAULT
        if any(f.severity in (Severity.RED, Severity.BLACK) for f in self._flags):
            return LifecycleStage.IRREGULAR_STATUS
        if c.agm_count == 0:
            return LifecycleStage.PRE_FIRST_AGM
        return LifecycleStage.ANNUAL_COMPLIANCE_CYCLE

    # ═══════════════════════════════════════════════════════════════════
    # PRIVATE HELPERS
    # ═══════════════════════════════════════════════════════════════════

    def _add_flag(self, flag: ComplianceFlag) -> None:
        """Add flag and log for audit trail."""
        self._flags.append(flag)
        logger.debug(
            f"[RuleEngine] Flag: {flag.rule_id} | {flag.flag_code} | "
            f"{flag.severity} | Impact: -{flag.score_impact}"
        )

    def _get_fy_end_deadline(self, c: CompanyProfile) -> date:
        """
        Calculate AGM deadline based on 6 months after financial year end.
        Must use the CURRENT year's FY end date.
        """
        current_year = self.today.year
        try:
            fy_end_this_year = c.financial_year_end.replace(year=current_year)
        except ValueError:
            fy_end_this_year = c.financial_year_end.replace(
                year=current_year, day=28
            )
        return fy_end_this_year + timedelta(days=FY_END_AGM_DEADLINE_DAYS)

    def _calculate_agm_default_years(self, c: CompanyProfile) -> int:
        """How many years has the company been in AGM default?"""
        if c.last_agm_date:
            return max(0, (self.today - c.last_agm_date).days // 365 - 1)
        return max(0, (self.today - c.incorporation_date).days // 365 - 1)

    def _graduated_agm_deduction(self, delay_days: int) -> int:
        """
        Graduated AGM deduction — delay severity matters.
        A 1-day miss ≠ a 5-year miss in scoring.
        """
        if delay_days <= 30:   return 5
        if delay_days <= 90:   return 12
        if delay_days <= 365:  return 20
        return 25  # Full deduction for > 1 year

    def _graduated_ar_deduction(self, delay_days: int) -> int:
        """Graduated Annual Return deduction."""
        if delay_days <= 90:   return 5
        if delay_days <= 365:  return 12
        return 20  # Full deduction for > 1 year

    def _score_to_band(self, score: int) -> Severity:
        """Map score to risk band."""
        if score >= 80: return Severity.GREEN
        if score >= 60: return Severity.YELLOW
        if score >= 30: return Severity.RED
        return Severity.BLACK

    def _calculate_exposure(
        self,
        black_count: int,
        red_count: int,
        total_count: int
    ) -> ExposureBand:
        """
        Statutory exposure band — used for client-facing risk communication.
        No numeric penalty amounts (protects Neum Lex from liability).
        """
        if black_count >= 1 or total_count >= 5: return ExposureBand.SEVERE
        if red_count >= 2 or total_count >= 3:   return ExposureBand.HIGH
        if red_count >= 1 or total_count >= 2:   return ExposureBand.MODERATE
        return ExposureBand.LOW


# ═══════════════════════════════════════════════════════════════════════
# DATABASE SEEDER — Load all 30 ILRMF rules into legal_rules table
# Run once on system initialization
# ═══════════════════════════════════════════════════════════════════════

ILRMF_RULE_SEED = [
    # AGM Rules
    {"rule_id": "AGM-001", "rule_name": "First AGM Default", "rule_type": "DEADLINE",
     "statutory_basis": "Companies Act 1994, Section 81", "default_severity": "RED",
     "score_impact": 25, "revenue_tier": "STRUCTURED_REGULARIZATION",
     "description": "First AGM not held within 18 months (548 days) of incorporation."},

    {"rule_id": "AGM-002", "rule_name": "Subsequent AGM Default", "rule_type": "DEADLINE",
     "statutory_basis": "Companies Act 1994, Section 81", "default_severity": "RED",
     "score_impact": 25, "revenue_tier": "STRUCTURED_REGULARIZATION",
     "description": "AGM not held within MIN(15 months of last AGM, 6 months of FY end)."},

    {"rule_id": "AGM-003", "rule_name": "AGM Notice Defective", "rule_type": "THRESHOLD",
     "statutory_basis": "Companies Act 1994, Section 86", "default_severity": "YELLOW",
     "score_impact": 5, "revenue_tier": "COMPLIANCE_PACKAGE",
     "description": "AGM notice issued less than 21 days before meeting."},

    {"rule_id": "AGM-004", "rule_name": "AGM Notice Not Issued", "rule_type": "DEADLINE",
     "statutory_basis": "Companies Act 1994, Section 86", "default_severity": "YELLOW",
     "score_impact": 3, "revenue_tier": "COMPLIANCE_PACKAGE",
     "description": "AGM notice not issued within warning window."},

    {"rule_id": "AGM-005", "rule_name": "AGM Quorum Defective", "rule_type": "THRESHOLD",
     "statutory_basis": "Companies Act 1994, Section 96", "default_severity": "RED",
     "score_impact": 15, "revenue_tier": "STRUCTURED_REGULARIZATION",
     "description": "AGM held without quorum (min 2 members, private company)."},

    {"rule_id": "AGM-006", "rule_name": "Auditor Not Reappointed at AGM", "rule_type": "DEPENDENCY",
     "statutory_basis": "Companies Act 1994, Section 210", "default_severity": "YELLOW",
     "score_impact": 5, "revenue_tier": "COMPLIANCE_PACKAGE",
     "description": "Auditor not reappointed at AGM."},

    # Audit Rules
    {"rule_id": "AUD-001", "rule_name": "Audit Missing Pre-AGM", "rule_type": "DEPENDENCY",
     "statutory_basis": "Companies Act 1994, Section 151", "default_severity": "YELLOW",
     "score_impact": 12, "revenue_tier": "COMPLIANCE_PACKAGE",
     "description": "Audit not complete with AGM approaching."},

    {"rule_id": "AUD-002", "rule_name": "First Auditor Not Appointed", "rule_type": "DEADLINE",
     "statutory_basis": "Companies Act 1994, Section 210", "default_severity": "YELLOW",
     "score_impact": 10, "revenue_tier": "COMPLIANCE_PACKAGE",
     "description": "First auditor not appointed within 30 days of incorporation."},

    {"rule_id": "AUD-003", "rule_name": "AGM Held Without Valid Audit", "rule_type": "DEPENDENCY",
     "statutory_basis": "Companies Act 1994, Sections 151, 210", "default_severity": "BLACK",
     "score_impact": 25, "revenue_tier": "CORPORATE_RESCUE",
     "description": "AGM held without completed audit. BLACK override. AGM may be void."},

    # Annual Return Rules
    {"rule_id": "AR-001", "rule_name": "Annual Return Default", "rule_type": "DEADLINE",
     "statutory_basis": "Companies Act 1994, Section 148", "default_severity": "YELLOW",
     "score_impact": 20, "revenue_tier": "COMPLIANCE_PACKAGE",
     "description": "Annual Return not filed within 30 days of AGM."},

    {"rule_id": "AR-002", "rule_name": "Annual Return Backlog — RED", "rule_type": "ESCALATION",
     "statutory_basis": "Companies Act 1994, Section 148", "default_severity": "RED",
     "score_impact": 20, "revenue_tier": "STRUCTURED_REGULARIZATION",
     "description": "2+ years Annual Returns unfiled. Statutory Default."},

    {"rule_id": "AR-003", "rule_name": "Annual Return Backlog — BLACK", "rule_type": "ESCALATION",
     "statutory_basis": "Companies Act 1994, Sections 148, 304", "default_severity": "BLACK",
     "score_impact": 20, "revenue_tier": "CORPORATE_RESCUE",
     "description": "3+ years Annual Returns unfiled. Severe Default. Director liability."},

    {"rule_id": "AR-004", "rule_name": "Annual Return Incomplete", "rule_type": "THRESHOLD",
     "statutory_basis": "Companies Act 1994, Section 148, Schedule X", "default_severity": "YELLOW",
     "score_impact": 8, "revenue_tier": "COMPLIANCE_PACKAGE",
     "description": "Annual Return filed but content incomplete. Treated as non-filing."},

    # Director Rules
    {"rule_id": "DIR-001", "rule_name": "Director Appointment Not Filed", "rule_type": "DEADLINE",
     "statutory_basis": "Companies Act 1994, Sections 81-84", "default_severity": "YELLOW",
     "score_impact": 5, "revenue_tier": "COMPLIANCE_PACKAGE",
     "description": "Director appointment not filed via Form XII within 30 days."},

    {"rule_id": "DIR-002", "rule_name": "Director Resignation Not Filed", "rule_type": "DEADLINE",
     "statutory_basis": "Companies Act 1994, Section 84", "default_severity": "YELLOW",
     "score_impact": 5, "revenue_tier": "COMPLIANCE_PACKAGE",
     "description": "Director resignation not filed via Form XIV within 30 days."},

    {"rule_id": "DIR-003", "rule_name": "Director Filing Major Irregularity", "rule_type": "ESCALATION",
     "statutory_basis": "Companies Act 1994, Sections 81-84", "default_severity": "RED",
     "score_impact": 15, "revenue_tier": "STRUCTURED_REGULARIZATION",
     "description": "Director filing overdue > 1 year. Major Irregularity."},

    {"rule_id": "DIR-004", "rule_name": "Departed Director Still Liable", "rule_type": "DEPENDENCY",
     "statutory_basis": "Companies Act 1994, Section 84", "default_severity": "RED",
     "score_impact": 10, "revenue_tier": "STRUCTURED_REGULARIZATION",
     "description": "Resigned director legally liable until Form XIV filed."},

    # Shareholder Rules
    {"rule_id": "SH-001", "rule_name": "Shareholder Change Not Filed", "rule_type": "DEADLINE",
     "statutory_basis": "Companies Act 1994, Section 150", "default_severity": "YELLOW",
     "score_impact": 5, "revenue_tier": "COMPLIANCE_PACKAGE",
     "description": "Shareholder change not filed via Form XV within 30 days."},

    # Transfer Rules
    {"rule_id": "TR-001", "rule_name": "Transfer — No Instrument", "rule_type": "THRESHOLD",
     "statutory_basis": "Companies Act 1994, Section 46", "default_severity": "YELLOW",
     "score_impact": 5, "revenue_tier": "COMPLIANCE_PACKAGE",
     "description": "Share transfer without proper transfer instrument."},

    {"rule_id": "TR-002", "rule_name": "Transfer — Stamp Duty Not Confirmed", "rule_type": "THRESHOLD",
     "statutory_basis": "Stamp Act (Bangladesh)", "default_severity": "YELLOW",
     "score_impact": 5, "revenue_tier": "COMPLIANCE_PACKAGE",
     "description": "Stamp duty not confirmed on transfer instrument."},

    {"rule_id": "TR-003", "rule_name": "Transfer — No Board Approval", "rule_type": "THRESHOLD",
     "statutory_basis": "Companies Act 1994, Section 47", "default_severity": "YELLOW",
     "score_impact": 8, "revenue_tier": "COMPLIANCE_PACKAGE",
     "description": "Share transfer without board approval resolution."},

    {"rule_id": "TR-004", "rule_name": "Transfer — Register Not Updated", "rule_type": "DEADLINE",
     "statutory_basis": "Companies Act 1994, Section 26", "default_severity": "YELLOW",
     "score_impact": 5, "revenue_tier": "COMPLIANCE_PACKAGE",
     "description": "Register of Members not updated following transfer."},

    {"rule_id": "TR-005", "rule_name": "AoA Transfer Restriction Violated", "rule_type": "THRESHOLD",
     "statutory_basis": "Companies Act 1994, Section 47; AoA", "default_severity": "BLACK",
     "score_impact": 15, "revenue_tier": "CORPORATE_RESCUE",
     "description": "Transfer in violation of AoA restriction. BLACK override. May be void."},

    {"rule_id": "TR-006", "rule_name": "Transfer Irregular — Composite", "rule_type": "CASCADE",
     "statutory_basis": "Companies Act 1994, Sections 46-47", "default_severity": "RED",
     "score_impact": 0, "revenue_tier": "STRUCTURED_REGULARIZATION",
     "description": "Multiple transfer deficiencies. Composite irregularity."},

    # Register Rules
    {"rule_id": "REG-001", "rule_name": "Statutory Register Incomplete", "rule_type": "THRESHOLD",
     "statutory_basis": "Companies Act 1994, Section 26", "default_severity": "YELLOW",
     "score_impact": 5, "revenue_tier": "COMPLIANCE_PACKAGE",
     "description": "Required statutory registers not maintained."},

    {"rule_id": "REG-002", "rule_name": "Share Certificate Default", "rule_type": "DEADLINE",
     "statutory_basis": "Companies Act 1994, Section 46", "default_severity": "YELLOW",
     "score_impact": 5, "revenue_tier": "COMPLIANCE_PACKAGE",
     "description": "Share certificates not issued within 60 days of allotment."},

    # Office Rules
    {"rule_id": "OFF-001", "rule_name": "Registered Office Change Not Filed", "rule_type": "DEADLINE",
     "statutory_basis": "Companies Act 1994, Section 27", "default_severity": "YELLOW",
     "score_impact": 3, "revenue_tier": "COMPLIANCE_PACKAGE",
     "description": "Registered office change not notified via Form IX within 30 days."},

    # Capital Rules
    {"rule_id": "CAP-001", "rule_name": "Capital Increase — Resolution Missing", "rule_type": "DEPENDENCY",
     "statutory_basis": "Companies Act 1994, Section 61", "default_severity": "YELLOW",
     "score_impact": 5, "revenue_tier": "COMPLIANCE_PACKAGE",
     "description": "Capital increase without shareholder resolution."},

    {"rule_id": "CAP-002", "rule_name": "Charge Not Filed", "rule_type": "DEADLINE",
     "statutory_basis": "Companies Act 1994, Section 120", "default_severity": "YELLOW",
     "score_impact": 5, "revenue_tier": "COMPLIANCE_PACKAGE",
     "description": "Charge/mortgage created but Form VIII not filed within 30 days."},

    # Escalation Rules
    {"rule_id": "ESC-001", "rule_name": "Strike-Off Risk Elevated", "rule_type": "ESCALATION",
     "statutory_basis": "Companies Act 1994, Section 304", "default_severity": "RED",
     "score_impact": 0, "revenue_tier": "STRUCTURED_REGULARIZATION",
     "description": "2+ year AGM and Return defaults. Strike-off risk elevated."},

    {"rule_id": "ESC-002", "rule_name": "Strike-Off Risk Imminent", "rule_type": "ESCALATION",
     "statutory_basis": "Companies Act 1994, Sections 304-309", "default_severity": "BLACK",
     "score_impact": 0, "revenue_tier": "CORPORATE_RESCUE",
     "description": "3+ year default. Strike-off imminent. BLACK override."},

    {"rule_id": "ESC-003", "rule_name": "Rescue Required Mandatory", "rule_type": "CASCADE",
     "statutory_basis": "Companies Act 1994, Sections 304-309", "default_severity": "BLACK",
     "score_impact": 0, "revenue_tier": "CORPORATE_RESCUE",
     "description": "Multiple BLACK flags + strike-off risk. Rescue is mandatory."},
]


# ═══════════════════════════════════════════════════════════════════════
# RULE ENGINE SUMMARY
# Total rules: 30
# Rule modules: 10
# BLACK override rules: 4 (AUD-003, TR-005, ESC-002, ESC-003)
# Scoring components: 5
# Score range: 0–100
# Rescue steps generated: up to 8 (dependency-ordered)
# ═══════════════════════════════════════════════════════════════════════
