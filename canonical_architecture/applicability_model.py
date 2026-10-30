"""
NLC Rule Applicability & Exception Model

Maps each verified rule to:
- Applicability conditions (which companies the rule applies to)
- Exceptions (conditions that make the rule NOT_APPLICABLE)
- Scope limitations (company type, lifecycle stage, etc.)

Based on Companies Act 1994 (Bangladesh) section text.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple

@dataclass(frozen=True)
class ApplicabilityRule:
    """Defines when a rule applies and when it doesn't."""
    rule_id: str
    applies_to: Tuple[str, ...]  # company types: ALL, PRIVATE, PUBLIC, etc.
    conditions: Tuple[str, ...]  # facts that must be True for the rule to apply
    exceptions: Tuple[str, ...]  # facts that, if True, make the rule NOT_APPLICABLE
    notes: str = ""

# ═════════════════════════════════════════════════════════════════════
# APPLICABILITY MODEL — 35 verified rules
# ═════════════════════════════════════════════════════════════════════

APPLICABILITY_REGISTRY: dict[str, ApplicabilityRule] = {
    # ── AGM Module (Section 81) ──────────────────────────────────────
    "AGM-001": ApplicabilityRule(
        "AGM-001", ("ALL",), ("is_active",), (),
        "S81: No exception for private companies. First AGM within 18 months."
    ),
    "AGM-002": ApplicabilityRule(
        "AGM-002", ("ALL",), ("is_active", "has_held_first_agm"), (),
        "S81: Subsequent AGMs within 15 months. No size/dormancy exception."
    ),
    "AGM-003": ApplicabilityRule(
        "AGM-003", ("ALL",), ("agm_scheduled",), (),
        "S85: 21 clear days notice required. Shorter notice OK if all members agree in writing."
    ),
    "AGM-004": ApplicabilityRule(
        "AGM-004", ("ALL",), ("agm_scheduled",), (),
        "S85: Written notice with date/time/place/business required."
    ),
    "AGM-005": ApplicabilityRule(
        "AGM-005", ("ALL",), ("agm_held",), (),
        "S85(2)(b): Private company needs 2 members present (if <=7 total); "
        "3 if >7. Public company needs 5."
    ),
    "AGM-006": ApplicabilityRule(
        "AGM-006", ("ALL",), ("agm_held",), (),
        "S89: Minutes must be entered in books, signed by chairman."
    ),
    "AGM-007": ApplicabilityRule(
        "AGM-007", ("ALL",), ("agm_held",), (),
        "S84: EGM requisition rules. Adjournment requires proper notice."
    ),

    # ── Registers Module (Sections 34-36, 89, 115, 159, 174) ────────
    "REG-001": ApplicabilityRule(
        "REG-001", ("ALL",), ("is_active",), (),
        "S34: Every company must maintain register of members."
    ),
    "REG-002": ApplicabilityRule(
        "REG-002", ("ALL",), ("is_active",), (),
        "S34-36, 89, 115, 159, 174: Core registers: members, directors, "
        "charges, minutes. No exceptions for company type."
    ),
    "REG-003": ApplicabilityRule(
        "REG-003", ("ALL",), ("is_active",), ("register_at_approved_location",),
        "S34(2): Registers at registered office. Alternative location OK "
        "if Board-approved and in Bangladesh."
    ),

    # ── Office Module (Section 77) ───────────────────────────────────
    "OFF-001": ApplicabilityRule(
        "OFF-001", ("ALL",), ("registered_office_changed",), (),
        "S77: 28-day filing requirement. No exceptions. Annual return "
        "inclusion does NOT satisfy this obligation."
    ),

    # ── Directors Module (Sections 92, 93, 94, 104, 110, 115) ──────
    "DIR-001": ApplicabilityRule(
        "DIR-001", ("ALL",), ("director_appointed", "directors_verified"), (),
        "S92: 14-day filing of director appointment via Form XII. "
        "NOT 30 days — the 14-day deadline is statutory."
    ),
    "DIR-002": ApplicabilityRule(
        "DIR-002", ("ALL",), ("director_departed",), (),
        "S92: 14-day filing of director departure. Same deadline as appointment."
    ),
    "DIR-003": ApplicabilityRule(
        "DIR-003", ("ALL",), ("director_change_unfiled_over_1_year",), (),
        "S92: Continuing offence. Each day of default adds to fine."
    ),
    "DIR-004": ApplicabilityRule(
        "DIR-004", ("ALL",), ("departed_director_on_register",), (),
        "S115: Register of directors must be updated. Departed director "
        "remains liable until Form XII filed."
    ),
    "DIR-007": ApplicabilityRule(
        "DIR-007", ("ALL",), ("director_appointed",), (),
        "S93(2): Consent must be filed within 30 days of appointment."
    ),
    "DIR-008": ApplicabilityRule(
        "DIR-008", ("ALL",), ("director_holds_office_of_profit",), ("company_consent_given",),
        "S104: Office of profit requires company consent in general meeting. "
        "Exception: managing director, manager, legal/technical adviser, banker."
    ),
    "DIR-010": ApplicabilityRule(
        "DIR-010", ("ALL",), ("managing_director_appointed",), (),
        "S110: MD term cannot exceed 5 years at a time. Reappointment "
        "requires general meeting consent."
    ),

    # ── Capital & Charges (Sections 53, 59, 87, 159) ────────────────
    "CAP-001": ApplicabilityRule(
        "CAP-001", ("ALL",), ("capital_increase",), (),
        "S53: Capital alteration requires special resolution. "
        "S54: Notice to Registrar within 15 days."
    ),
    "CAP-002": ApplicabilityRule(
        "CAP-002", ("ALL",), ("charge_created",), (),
        "S159: Charge registration within 21 days. Unregistered charge "
        "void against liquidator and creditors."
    ),
    "CAP-003": ApplicabilityRule(
        "CAP-003", ("ALL",), ("capital_reduction",), ("court_order_obtained",),
        "S59: Capital reduction requires Court confirmation. "
        "Exception: Court order obtained."
    ),
    "CHG-001": ApplicabilityRule(
        "CHG-001", ("ALL",), ("charge_created",), (),
        "S159: Same as CAP-002. Charge must be registered with RJSC."
    ),

    # ── Structural (Sections 11, 17, 18) ────────────────────────────
    "STR-001": ApplicabilityRule(
        "STR-001", ("ALL",), ("name_change",), (),
        "S11: Name change requires special resolution + Registrar approval. "
        "Filing within 30 days."
    ),
    "STR-002": ApplicabilityRule(
        "STR-002", ("ALL",), ("object_clause_change",), (),
        "S17: AoA alteration filing. MoA object clause requires Court confirmation (S12)."
    ),
    "STR-003": ApplicabilityRule(
        "STR-003", ("ALL",), ("aoa_alteration",), (),
        "S18: Schedule I application. AoA alteration by special resolution."
    ),

    # ── Accounts (Sections 181, 183, 190) ───────────────────────────
    "ACC-001": ApplicabilityRule(
        "ACC-001", ("ALL",), ("agm_held",), (),
        "S183: Annual balance sheet must be presented at AGM."
    ),
    "ACC-002": ApplicabilityRule(
        "ACC-002", ("ALL",), ("agm_held",), (),
        "S190: Balance sheet filed with Registrar within 30 days of AGM."
    ),
    "ACC-003": ApplicabilityRule(
        "ACC-003", ("ALL",), ("is_active",), (),
        "S181: Books of account must be maintained at registered office."
    ),

    # ── Board (Sections 89, 95, 96) ─────────────────────────────────
    "BOD-001": ApplicabilityRule(
        "BOD-001", ("ALL",), ("is_active",), (),
        "S96: Board meeting at least once every 3 months. "
        "Minimum 4 meetings per year."
    ),
    "BOD-002": ApplicabilityRule(
        "BOD-002", ("ALL",), ("board_meeting_held",), (),
        "S95: Written notice to all directors in Bangladesh."
    ),
    "BOD-003": ApplicabilityRule(
        "BOD-003", ("ALL",), ("board_meeting_held",), (),
        "S89: Minutes of all proceedings must be entered."
    ),

    # ── Incorporation (Sections 23, 90, 53, 150) ────────────────────
    "INC-001": ApplicabilityRule(
        "INC-001", ("ALL",), ("is_active",), ("moa_aoa_filed",),
        "S23: MoA and AoA must be filed with Registrar within 30 days."
    ),
    "INC-003": ApplicabilityRule(
        "INC-003", ("PRIVATE",), ("directors_verified",), (),
        "S90(2): Private company minimum 2 directors. "
        "Public company minimum 3 (S90(1))."
    ),
    "INC-004": ApplicabilityRule(
        "INC-004", ("ALL",), ("shares_allotted",), (),
        "S53: Paid-up capital cannot exceed authorized capital."
    ),
    "INC-007": ApplicabilityRule(
        "INC-007", ("PUBLIC",), ("business_commenced",), ("declaration_filed",),
        "S150: Public company must file declaration before commencing business. "
        "Exception: Private companies exempt (S150(6))."
    ),

    # ── Membership (Section 222) ────────────────────────────────────
    "MEM-001": ApplicabilityRule(
        "MEM-001", ("ALL",), ("is_active",), (),
        "S222: Private company <2 members, public <7. "
        "Liability after 6 months of reduced membership."
    ),

    # ── Transfers (Section 38) ──────────────────────────────────────
    "TR-001": ApplicabilityRule(
        "TR-001", ("ALL",), ("share_transfer",), (),
        "S38: Transfer requires proper instrument, duly stamped, "
        "executed by both parties."
    ),

    # ── Escalation (Section 346) ────────────────────────────────────
    "ESC-001": ApplicabilityRule(
        "ESC-001", ("ALL",), ("is_active",), (),
        "S346: Strike-off risk for non-filing/non-trading."
    ),
    "ESC-002": ApplicabilityRule(
        "ESC-002", ("ALL",), ("is_active",), (),
        "S346: Strike-off imminent. 3+ years non-filing or notice received."
    ),

    # ── Default (Sections 94, 397) ──────────────────────────────────
    "DEF-001": ApplicabilityRule(
        "DEF-001", ("ALL",), ("any_director_disqualified",), (),
        "S94: Disqualification grounds: unsound mind, undischarged insolvent, "
        "pending insolvency application, unpaid calls >6 months, minor."
    ),
    "DEF-002": ApplicabilityRule(
        "DEF-002", ("ALL",), ("penalty_notices_received",), ("penalty_notices_resolved",),
        "S397: Penalty for false statement. Fine up to Tk 10,000."
    ),
}