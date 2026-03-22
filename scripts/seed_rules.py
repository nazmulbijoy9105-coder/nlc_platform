#!/usr/bin/env python3
"""
NEUM LEX COUNSEL — Legal Rules Seeder
scripts/seed_rules.py

Standalone script to seed all 32 ILRMF rules into the legal_rules table.
Safe to run multiple times — upserts by rule_id (ON CONFLICT UPDATE).

DIFFERENT FROM MIGRATION 0002:
  - Migration 0002 is for first-time DB setup (INSERT ... ON CONFLICT DO NOTHING)
  - This script is for: development resets, staging refreshes, rule updates
  - This script will UPDATE existing rules if definitions have changed
  - Useful when you change rule_engine_version and need to sync DB

USAGE:
  # From project root:
  python scripts/seed_rules.py

  # With explicit DB URL:
  DATABASE_URL=postgresql://user:pass@host/db python scripts/seed_rules.py

  # Dry run (print what would be inserted, don't write):
  python scripts/seed_rules.py --dry-run

  # Verbose output:
  python scripts/seed_rules.py --verbose

AI Constitution Article 1:
  All 32 rules must be present and active before the rule engine runs.
  This script verifies the count at the end and raises if wrong.

Release Governance Protocol:
  Changes to rule definitions must be documented in a new migration file.
  This script only reflects the current authoritative rule set.
  Do NOT edit rule definitions here without a corresponding legal_rule_versions entry.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ── Path setup — allow running from project root ──────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load .env if present before importing settings
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass  # python-dotenv optional for this script

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker


# ═══════════════════════════════════════════════════════════════════════
# RULE DEFINITIONS — The authoritative ILRMF rule set
# All 32 rules with full statutory basis, score impacts, and metadata.
#
# Format: (
#   rule_id, rule_name, rule_type, statutory_basis, description,
#   default_severity, score_impact, revenue_tier, is_black_override,
#   rule_condition_json, notes
# )
# ═══════════════════════════════════════════════════════════════════════

ILRMF_RULES: List[Dict[str, Any]] = [

    # ══════════════════════════════════════════════════════════════
    # MODULE 1: AGM — 6 rules
    # Statutory basis: Companies Act 1994 (Bangladesh) Sections 81–86
    # ══════════════════════════════════════════════════════════════
    {
        "rule_id":          "AGM-001",
        "rule_name":        "First AGM Default",
        "rule_type":        "AGM",
        "statutory_basis":  "Section 81, Companies Act 1994 (Bangladesh)",
        "description": (
            "First AGM not held within 18 months (548 days) of incorporation, "
            "or within 9 months of the close of the first financial year — whichever "
            "is the earlier date. Section 81 is mandatory; there is no waiver provision "
            "for private companies. Default counts from the day after the statutory deadline."
        ),
        "rule_condition": {
            "check_fn": "check_agm_001_first_agm_default",
            "trigger": "first_agm_held == False AND days_since_incorporation > 548",
            "data_points": ["incorporation_date", "first_agm_held", "agm_count"],
        },
        "default_severity":  "RED",
        "score_impact":      25,
        "revenue_tier":      "STRUCTURED_REGULARIZATION",
        "is_black_override": False,
    },
    {
        "rule_id":         "AGM-002",
        "rule_name":       "Subsequent AGM Default",
        "rule_type":       "AGM",
        "statutory_basis": "Section 81, Companies Act 1994 (Bangladesh)",
        "description": (
            "Subsequent AGM not held within 15 months of the preceding AGM, "
            "or within 6 months (182 days) of the close of the company's financial year — "
            "whichever falls earlier. Section 81 makes no exception for company size or dormancy. "
            "Applied per financial year cycle."
        ),
        "rule_condition": {
            "check_fn": "check_agm_002_subsequent_agm_default",
            "trigger": "days_since_last_agm > 456 OR days_since_fy_end > 182",
            "data_points": ["last_agm_date", "financial_year_end", "agm_count"],
        },
        "default_severity":  "YELLOW",
        "score_impact":      20,
        "revenue_tier":      "COMPLIANCE_PACKAGE",
        "is_black_override": False,
    },
    {
        "rule_id":         "AGM-003",
        "rule_name":       "AGM Notice Defective — Insufficient Days",
        "rule_type":       "AGM",
        "statutory_basis": "Section 86, Companies Act 1994 (Bangladesh)",
        "description": (
            "Written notice of the AGM was sent to members with fewer than 21 clear days "
            "before the meeting date. Section 86 requires 21 clear days' notice. "
            "'Clear days' means the day of service and the day of meeting are both excluded. "
            "Resolutions passed at an improperly noticed AGM may be void and unenforceable."
        ),
        "rule_condition": {
            "check_fn": "check_agm_003_notice_defective",
            "trigger": "notice_sent_date IS NOT NULL AND notice_days_before < 21",
            "data_points": ["notice_sent_date", "agm_date", "notice_days_before"],
        },
        "default_severity":  "YELLOW",
        "score_impact":      10,
        "revenue_tier":      "COMPLIANCE_PACKAGE",
        "is_black_override": False,
    },
    {
        "rule_id":         "AGM-004",
        "rule_name":       "AGM Notice Missing",
        "rule_type":       "AGM",
        "statutory_basis": "Section 86, Companies Act 1994 (Bangladesh)",
        "description": (
            "No written notice of the AGM was sent to members before the meeting. "
            "Section 86 requires written notice specifying the date, time, place, and "
            "business to be transacted. An AGM held without proper notice is a nullity — "
            "all resolutions passed are void, including financial adoption and auditor appointment."
        ),
        "rule_condition": {
            "check_fn": "check_agm_004_notice_missing",
            "trigger": "agm_held == True AND notice_sent_date IS NULL",
            "data_points": ["agm_held", "notice_sent_date"],
        },
        "default_severity":  "RED",
        "score_impact":      20,
        "revenue_tier":      "STRUCTURED_REGULARIZATION",
        "is_black_override": False,
    },
    {
        "rule_id":         "AGM-005",
        "rule_name":       "AGM Quorum Not Met",
        "rule_type":       "AGM",
        "statutory_basis": "Section 83, Companies Act 1994 (Bangladesh)",
        "description": (
            "The AGM was held but quorum requirements under Section 83 were not satisfied. "
            "For private companies with fewer than 6 members: minimum 2 members present in person. "
            "For larger companies: as set in the Articles. Resolutions passed without quorum "
            "have no legal effect, including appointment of auditors and adoption of accounts."
        ),
        "rule_condition": {
            "check_fn": "check_agm_005_quorum_not_met",
            "trigger": "agm_held == True AND members_present < quorum_required",
            "data_points": ["agm_held", "members_present_at_agm", "quorum_required"],
        },
        "default_severity":  "YELLOW",
        "score_impact":      15,
        "revenue_tier":      "COMPLIANCE_PACKAGE",
        "is_black_override": False,
    },
    {
        "rule_id":         "AGM-006",
        "rule_name":       "Auditor Not Reappointed at AGM",
        "rule_type":       "AGM",
        "statutory_basis": "Section 210, Companies Act 1994 (Bangladesh)",
        "description": (
            "The retiring auditor was not reappointed at the AGM, and no new auditor "
            "was formally appointed in their place by way of resolution. Section 210 requires "
            "that at every AGM where accounts are presented, an auditor is appointed or "
            "reappointed. A company without a properly appointed auditor cannot produce "
            "valid audited accounts."
        ),
        "rule_condition": {
            "check_fn": "check_agm_006_auditor_not_reappointed",
            "trigger": "agm_held == True AND auditor_reappointed_at_agm == False",
            "data_points": ["agm_held", "auditor_reappointed_at_agm"],
        },
        "default_severity":  "YELLOW",
        "score_impact":      15,
        "revenue_tier":      "COMPLIANCE_PACKAGE",
        "is_black_override": False,
    },

    # ══════════════════════════════════════════════════════════════
    # MODULE 2: AUDIT — 3 rules
    # Statutory basis: Section 210, Companies Act 1994 (Bangladesh)
    # ══════════════════════════════════════════════════════════════
    {
        "rule_id":         "AUD-001",
        "rule_name":       "Annual Audit Not Completed Before AGM",
        "rule_type":       "AUDIT",
        "statutory_basis": "Section 210, Companies Act 1994 (Bangladesh)",
        "description": (
            "The annual audit was not completed and signed by the auditor before the AGM "
            "was held. Under Section 210, the directors must lay audited accounts before "
            "the company at each AGM. Presenting unaudited or incomplete accounts at an "
            "AGM renders the accounts adoption invalid and exposes directors to personal liability."
        ),
        "rule_condition": {
            "check_fn": "check_aud_001_audit_not_complete_before_agm",
            "trigger": "agm_held == True AND audit_complete == False",
            "data_points": ["agm_held", "audit_complete", "last_agm_date", "last_audit_signed_date"],
        },
        "default_severity":  "RED",
        "score_impact":      20,
        "revenue_tier":      "STRUCTURED_REGULARIZATION",
        "is_black_override": False,
    },
    {
        "rule_id":         "AUD-002",
        "rule_name":       "First Auditor Not Appointed Within 30 Days",
        "rule_type":       "AUDIT",
        "statutory_basis": "Section 210, Companies Act 1994 (Bangladesh)",
        "description": (
            "The company's first auditor was not appointed by the Board of Directors "
            "within 30 days of incorporation. Section 210 requires the Board to appoint "
            "the first auditor within 30 days of incorporation. Failure means the company "
            "has no validly appointed auditor and cannot produce compliant accounts for the "
            "first AGM."
        ),
        "rule_condition": {
            "check_fn": "check_aud_002_first_auditor_not_appointed",
            "trigger": (
                "first_auditor_appointed == False AND "
                "days_since_incorporation > 30"
            ),
            "data_points": ["first_auditor_appointed", "incorporation_date"],
        },
        "default_severity":  "YELLOW",
        "score_impact":      15,
        "revenue_tier":      "COMPLIANCE_PACKAGE",
        "is_black_override": False,
    },
    {
        "rule_id":         "AUD-003",
        "rule_name":       "AGM Held Without Completed Audit — BLACK OVERRIDE",
        "rule_type":       "AUDIT",
        "statutory_basis": "Section 210, Companies Act 1994 (Bangladesh)",
        "description": (
            "An AGM has been recorded as held and complete, but no audit was completed "
            "or signed for that financial year. This is a fundamental statutory breach that "
            "invalidates the AGM itself, the accounts presented, and all resolutions passed. "
            "The company may be liable for holding a fraudulent AGM. "
            "BLACK OVERRIDE: forces the company's compliance score to BLACK band (≤29) "
            "regardless of all other scores. Corporate Rescue engagement is mandatory."
        ),
        "rule_condition": {
            "check_fn": "check_aud_003_agm_without_audit_black_override",
            "trigger": (
                "agm_held == True AND audit_complete == False AND "
                "agm_held_without_audit == True"
            ),
            "data_points": [
                "agm_held", "audit_complete", "agm_held_without_audit",
                "last_agm_date", "last_audit_signed_date"
            ],
        },
        "default_severity":  "BLACK",
        "score_impact":      25,
        "revenue_tier":      "CORPORATE_RESCUE",
        "is_black_override": True,
    },

    # ══════════════════════════════════════════════════════════════
    # MODULE 3: ANNUAL RETURNS — 4 rules
    # Statutory basis: Section 190, Companies Act 1994 (Bangladesh)
    # ══════════════════════════════════════════════════════════════
    {
        "rule_id":         "AR-001",
        "rule_name":       "Annual Return Default — Single Year",
        "rule_type":       "RETURN",
        "statutory_basis": "Section 190, Companies Act 1994 (Bangladesh)",
        "description": (
            "The annual return for a financial year has not been filed with the RJSC "
            "within 30 days of the date on which the AGM was held. Section 190 requires "
            "filing of Form XII (Annual Return) within this window. Every officer of the "
            "company in default is personally liable to a fine for each day of continuing "
            "default."
        ),
        "rule_condition": {
            "check_fn": "check_ar_001_annual_return_default",
            "trigger": (
                "annual_return_filed == False AND "
                "days_since_agm > 30 AND unfiled_returns_count == 1"
            ),
            "data_points": [
                "annual_return_filed", "last_agm_date", "last_return_filed_year",
                "unfiled_returns_count"
            ],
        },
        "default_severity":  "YELLOW",
        "score_impact":      20,
        "revenue_tier":      "COMPLIANCE_PACKAGE",
        "is_black_override": False,
    },
    {
        "rule_id":         "AR-002",
        "rule_name":       "Annual Return 2-Year Backlog",
        "rule_type":       "RETURN",
        "statutory_basis": "Section 190, Companies Act 1994 (Bangladesh)",
        "description": (
            "Annual returns remain unfiled for 2 or more consecutive financial years. "
            "Multi-year default significantly increases RJSC enforcement risk. The RJSC "
            "may commence administrative strike-off proceedings under Section 396 for "
            "companies with a pattern of non-filing. Directors face cumulative personal "
            "fines for each year of continuing default."
        ),
        "rule_condition": {
            "check_fn": "check_ar_002_two_year_backlog",
            "trigger": "unfiled_returns_count >= 2",
            "data_points": ["unfiled_returns_count", "last_return_filed_year"],
        },
        "default_severity":  "RED",
        "score_impact":      20,
        "revenue_tier":      "STRUCTURED_REGULARIZATION",
        "is_black_override": False,
    },
    {
        "rule_id":         "AR-003",
        "rule_name":       "Annual Return 3-Year Backlog — Strike-Off Risk",
        "rule_type":       "RETURN",
        "statutory_basis": "Sections 190 and 396, Companies Act 1994 (Bangladesh)",
        "description": (
            "Annual returns remain unfiled for 3 or more consecutive financial years. "
            "At this threshold, the RJSC has both the legal basis and established practice "
            "of initiating strike-off proceedings under Section 396. A struck-off company "
            "loses all legal personality; contracts become void and bank accounts are frozen. "
            "Corporate Rescue is mandatory at this stage. Escalates to BLACK band."
        ),
        "rule_condition": {
            "check_fn": "check_ar_003_three_year_backlog",
            "trigger": "unfiled_returns_count >= 3",
            "data_points": ["unfiled_returns_count", "last_return_filed_year"],
        },
        "default_severity":  "BLACK",
        "score_impact":      20,
        "revenue_tier":      "CORPORATE_RESCUE",
        "is_black_override": False,
    },
    {
        "rule_id":         "AR-004",
        "rule_name":       "Annual Return Filed But Incomplete",
        "rule_type":       "RETURN",
        "statutory_basis": "Section 190, Companies Act 1994 (Bangladesh)",
        "description": (
            "An annual return was filed with the RJSC but is missing one or more required "
            "attachments or disclosures: audited financial statements, updated list of "
            "directors and their personal details, updated list of members with shareholding, "
            "or secretary's certificate. An incomplete annual return does not satisfy the "
            "Section 190 filing requirement; the company remains in default."
        ),
        "rule_condition": {
            "check_fn": "check_ar_004_incomplete_filing",
            "trigger": (
                "annual_return_filed == True AND "
                "annual_return_content_complete == False"
            ),
            "data_points": [
                "annual_return_filed", "annual_return_content_complete",
                "last_return_filed_year"
            ],
        },
        "default_severity":  "YELLOW",
        "score_impact":      10,
        "revenue_tier":      "COMPLIANCE_PACKAGE",
        "is_black_override": False,
    },

    # ══════════════════════════════════════════════════════════════
    # MODULE 4: DIRECTORS — 4 rules
    # Statutory basis: Section 115, Companies Act 1994 (Bangladesh)
    # ══════════════════════════════════════════════════════════════
    {
        "rule_id":         "DIR-001",
        "rule_name":       "Director Appointment Not Filed Within 30 Days",
        "rule_type":       "DIRECTOR",
        "statutory_basis": "Section 115, Companies Act 1994 (Bangladesh)",
        "description": (
            "A director's appointment has not been notified to the RJSC by filing "
            "Form XII within 30 days of the appointment date. Section 115 requires "
            "notification within 30 days. Until filed, third parties who search the RJSC "
            "register cannot verify the director's authority, which can invalidate contracts "
            "and board resolutions executed by the director."
        ),
        "rule_condition": {
            "check_fn": "check_dir_001_appointment_not_filed",
            "trigger": (
                "director_change_type == APPOINTMENT AND "
                "appointment_delay_days > 30 AND "
                "appointment_filing_delayed == True"
            ),
            "data_points": [
                "director_changes", "appointment_date",
                "appointment_filed_date", "appointment_delay_days"
            ],
        },
        "default_severity":  "YELLOW",
        "score_impact":      10,
        "revenue_tier":      "COMPLIANCE_PACKAGE",
        "is_black_override": False,
    },
    {
        "rule_id":         "DIR-002",
        "rule_name":       "Director Resignation/Removal Not Filed Within 30 Days",
        "rule_type":       "DIRECTOR",
        "statutory_basis": "Section 115, Companies Act 1994 (Bangladesh)",
        "description": (
            "A director's resignation or removal has not been notified to the RJSC by "
            "filing Form XII within 30 days of the effective date. Section 115 requires "
            "notification within 30 days. Until filed, the departed director remains on "
            "the public record as an active director, creating potential liability for "
            "obligations incurred after their actual departure."
        ),
        "rule_condition": {
            "check_fn": "check_dir_002_departure_not_filed",
            "trigger": (
                "director_change_type == DEPARTURE AND "
                "departure_delay_days > 30 AND "
                "departure_filing_delayed == True"
            ),
            "data_points": [
                "director_changes", "departure_date",
                "departure_filed_date", "departure_delay_days"
            ],
        },
        "default_severity":  "YELLOW",
        "score_impact":      10,
        "revenue_tier":      "COMPLIANCE_PACKAGE",
        "is_black_override": False,
    },
    {
        "rule_id":         "DIR-003",
        "rule_name":       "Major Director Filing Irregularity — Over 1 Year",
        "rule_type":       "DIRECTOR",
        "statutory_basis": "Section 115, Companies Act 1994 (Bangladesh)",
        "description": (
            "A director change (appointment or departure) has remained unfiled with the "
            "RJSC for more than 1 year (365 days). This constitutes a continuing offence "
            "under Section 115. Prolonged non-filing creates compounding personal liability "
            "risk for all current directors, as each day of default adds to the statutory "
            "fine. Board resolutions may be challenged as invalid."
        ),
        "rule_condition": {
            "check_fn": "check_dir_003_over_one_year_unfiled",
            "trigger": (
                "director_filing_delay_days > 365"
            ),
            "data_points": [
                "director_changes", "appointment_delay_days", "departure_delay_days"
            ],
        },
        "default_severity":  "RED",
        "score_impact":      15,
        "revenue_tier":      "STRUCTURED_REGULARIZATION",
        "is_black_override": False,
    },
    {
        "rule_id":         "DIR-004",
        "rule_name":       "Departed Director Still Active on RJSC Register",
        "rule_type":       "DIRECTOR",
        "statutory_basis": "Section 115, Companies Act 1994 (Bangladesh)",
        "description": (
            "A director who has actually departed — whether by resignation, removal, "
            "disqualification, or death — is still recorded as an active director on "
            "the RJSC public register because no Form XII departure notification has been "
            "filed. The departed director continues to bear potential personal liability "
            "for all company obligations shown as arising while they appear on record. "
            "This also enables the departed director to fraudulently claim authority over "
            "company affairs."
        ),
        "rule_condition": {
            "check_fn": "check_dir_004_departed_still_active",
            "trigger": "departed_still_liable == True",
            "data_points": [
                "director_changes", "director_status",
                "departed_still_liable", "departure_filed_date"
            ],
        },
        "default_severity":  "RED",
        "score_impact":      15,
        "revenue_tier":      "STRUCTURED_REGULARIZATION",
        "is_black_override": False,
    },

    # ══════════════════════════════════════════════════════════════
    # MODULE 5: SHAREHOLDING — 1 rule
    # ══════════════════════════════════════════════════════════════
    {
        "rule_id":         "SH-001",
        "rule_name":       "Shareholder Change Not Reflected in Annual Return",
        "rule_type":       "DIRECTOR",
        "statutory_basis": "Section 190, Companies Act 1994 (Bangladesh)",
        "description": (
            "A change in shareholding (new allotment, transfer, or cancellation) "
            "has not been reflected in the list of members filed with the annual return. "
            "Section 190 requires the annual return to contain a complete and accurate "
            "list of all members with their current shareholding. An inaccurate annual "
            "return does not satisfy the Section 190 filing requirement."
        ),
        "rule_condition": {
            "check_fn": "check_sh_001_shareholder_change_not_filed",
            "trigger": (
                "shareholder_change_date IS NOT NULL AND "
                "form_xv_filed == False"
            ),
            "data_points": [
                "shareholder_change_date", "form_xv_filed",
                "last_return_filed_year"
            ],
        },
        "default_severity":  "YELLOW",
        "score_impact":      10,
        "revenue_tier":      "COMPLIANCE_PACKAGE",
        "is_black_override": False,
    },

    # ══════════════════════════════════════════════════════════════
    # MODULE 6: SHARE TRANSFERS — 6 rules
    # ══════════════════════════════════════════════════════════════
    {
        "rule_id":         "TR-001",
        "rule_name":       "No Share Transfer Instrument Executed",
        "rule_type":       "TRANSFER",
        "statutory_basis": "Section 82, Companies Act 1994 (Bangladesh)",
        "description": (
            "A share transfer was completed and recorded without a properly executed "
            "instrument of transfer (Form 117). Section 82 requires that every transfer "
            "of shares be made by a proper instrument of transfer, duly stamped, and "
            "executed by or on behalf of both the transferor and transferee. "
            "An unstamped or missing transfer instrument renders the transfer void "
            "and unregistrable."
        ),
        "rule_condition": {
            "check_fn": "check_tr_001_no_transfer_instrument",
            "trigger": "has_instrument == False",
            "data_points": ["share_transfers", "has_instrument"],
        },
        "default_severity":  "YELLOW",
        "score_impact":      10,
        "revenue_tier":      "COMPLIANCE_PACKAGE",
        "is_black_override": False,
    },
    {
        "rule_id":         "TR-002",
        "rule_name":       "Stamp Duty Not Paid on Share Transfer",
        "rule_type":       "TRANSFER",
        "statutory_basis": "Stamp Act 1899 (Bangladesh), Schedule I Item 62",
        "description": (
            "A share transfer instrument was executed but applicable stamp duty was "
            "not paid. Under the Stamp Act 1899, a transfer of shares in a company "
            "attracts ad valorem stamp duty. An unstamped instrument is inadmissible "
            "as evidence in any civil proceeding and cannot be presented for registration. "
            "The transferee's legal ownership is therefore unenforceable until duty is paid "
            "and the instrument properly stamped."
        ),
        "rule_condition": {
            "check_fn": "check_tr_002_stamp_duty_not_paid",
            "trigger": "has_instrument == True AND stamp_paid == False",
            "data_points": ["share_transfers", "stamp_paid", "stamp_duty_amount_bdt"],
        },
        "default_severity":  "YELLOW",
        "score_impact":      10,
        "revenue_tier":      "COMPLIANCE_PACKAGE",
        "is_black_override": False,
    },
    {
        "rule_id":         "TR-003",
        "rule_name":       "No Board Approval Obtained for Share Transfer",
        "rule_type":       "TRANSFER",
        "statutory_basis": "Articles of Association, Companies Act 1994 (Bangladesh)",
        "description": (
            "A share transfer was executed and registered without first obtaining the "
            "approval of the Board of Directors as required by the company's Articles of "
            "Association. Most private limited company Articles contain pre-emption rights "
            "and board approval requirements. A transfer made in breach of these provisions "
            "is void and the transferee acquires no legal title. The company's register of "
            "members cannot be validly updated."
        ),
        "rule_condition": {
            "check_fn": "check_tr_003_no_board_approval",
            "trigger": "board_approved == False AND aoa_transfer_restriction == True",
            "data_points": [
                "share_transfers", "board_approved",
                "aoa_transfer_restriction", "board_approval_date"
            ],
        },
        "default_severity":  "YELLOW",
        "score_impact":      10,
        "revenue_tier":      "COMPLIANCE_PACKAGE",
        "is_black_override": False,
    },
    {
        "rule_id":         "TR-004",
        "rule_name":       "Register of Members Not Updated After Transfer",
        "rule_type":       "TRANSFER",
        "statutory_basis": "Section 34, Companies Act 1994 (Bangladesh)",
        "description": (
            "A share transfer has been completed but the Register of Members has not "
            "been updated within 2 months of the instrument being lodged for registration. "
            "Section 34 requires the company to enter every transfer of shares in the "
            "register within this period. Until the register is updated, the transferee "
            "is not formally recognised as a member and cannot exercise member rights "
            "including voting, dividends, and attendance at general meetings."
        ),
        "rule_condition": {
            "check_fn": "check_tr_004_register_not_updated",
            "trigger": "register_updated == False AND transfer_date IS NOT NULL",
            "data_points": [
                "share_transfers", "register_updated",
                "register_update_date", "transfer_date"
            ],
        },
        "default_severity":  "YELLOW",
        "score_impact":      10,
        "revenue_tier":      "COMPLIANCE_PACKAGE",
        "is_black_override": False,
    },
    {
        "rule_id":         "TR-005",
        "rule_name":       "Share Transfer Violates AoA Restriction — BLACK OVERRIDE",
        "rule_type":       "TRANSFER",
        "statutory_basis": "Articles of Association, Companies Act 1994 (Bangladesh)",
        "description": (
            "A share transfer has been executed in direct violation of a restriction "
            "in the company's Articles of Association — including but not limited to: "
            "pre-emption rights not offered to existing members, transfer to a prohibited "
            "category of person, or board approval explicitly refused. Such a transfer "
            "is void ab initio under company law. The transferee has no legal title and "
            "the register entry is invalid. Rectification requires court order or unanimous "
            "member ratification. "
            "BLACK OVERRIDE: forces the compliance score to BLACK band regardless of all "
            "other scores. Immediate corporate rescue engagement is mandatory."
        ),
        "rule_condition": {
            "check_fn": "check_tr_005_aoa_violation_black_override",
            "trigger": "aoa_violated == True",
            "data_points": [
                "share_transfers", "aoa_violated",
                "aoa_transfer_restriction", "is_irregular"
            ],
        },
        "default_severity":  "BLACK",
        "score_impact":      25,
        "revenue_tier":      "CORPORATE_RESCUE",
        "is_black_override": True,
    },
    {
        "rule_id":         "TR-006",
        "rule_name":       "Composite Irregular Transfer",
        "rule_type":       "TRANSFER",
        "statutory_basis": "Multiple sections, Companies Act 1994 (Bangladesh)",
        "description": (
            "A share transfer has been flagged as irregular with 3 or more concurrent "
            "deficiencies from TR-001 through TR-005 (missing instrument, no stamp duty, "
            "no board approval, register not updated, or AoA violation). Composite "
            "irregularity compounds legal risk significantly: each deficiency independently "
            "may render the transfer void, and together they indicate a systemic failure "
            "in the company's share administration processes that typically requires "
            "structured remediation."
        ),
        "rule_condition": {
            "check_fn": "check_tr_006_composite_irregular_transfer",
            "trigger": "is_irregular == True AND irregularity_count >= 3",
            "data_points": ["share_transfers", "is_irregular", "irregularity_notes"],
        },
        "default_severity":  "RED",
        "score_impact":      20,
        "revenue_tier":      "STRUCTURED_REGULARIZATION",
        "is_black_override": False,
    },

    # ══════════════════════════════════════════════════════════════
    # MODULE 7: STATUTORY REGISTERS — 2 rules
    # ══════════════════════════════════════════════════════════════
    {
        "rule_id":         "REG-001",
        "rule_name":       "Statutory Registers Incomplete or Not Maintained",
        "rule_type":       "REGISTER",
        "statutory_basis": (
            "Sections 34, 115, 148, 157, 193, Companies Act 1994 (Bangladesh)"
        ),
        "description": (
            "One or more of the 6 mandatory statutory registers is not being maintained "
            "at the registered office or a permitted alternative location. The 6 required "
            "registers are: (1) Register of Members, (2) Register of Directors and "
            "Secretaries, (3) Register of Charges, (4) Register of Debenture Holders, "
            "(5) Register of Contracts with Directors, (6) Minutes Book (AGM and Board). "
            "Failure to maintain is a criminal offence and each officer in default is "
            "personally liable. Registers must be available for inspection."
        ),
        "rule_condition": {
            "check_fn": "check_reg_001_registers_incomplete",
            "trigger": "len(maintained_registers) < 6",
            "data_points": ["maintained_registers"],
        },
        "default_severity":  "YELLOW",
        "score_impact":      10,
        "revenue_tier":      "COMPLIANCE_PACKAGE",
        "is_black_override": False,
    },
    {
        "rule_id":         "REG-002",
        "rule_name":       "Share Certificate Not Issued Within Statutory Deadline",
        "rule_type":       "REGISTER",
        "statutory_basis": "Section 82, Companies Act 1994 (Bangladesh)",
        "description": (
            "A share certificate has not been issued to a shareholder within the "
            "statutory time limit: 2 months after allotment of shares, or 1 month after "
            "lodgement of a transfer instrument. Section 82 creates a personal obligation "
            "on the company and its officers to issue certificates promptly. "
            "Non-issuance means the shareholder has no document evidencing legal ownership, "
            "which can obstruct further transfers, pledges, and dividend claims."
        ),
        "rule_condition": {
            "check_fn": "check_reg_002_share_certificate_not_issued",
            "trigger": (
                "share_certificate_issued == False AND "
                "last_allotment_date IS NOT NULL"
            ),
            "data_points": [
                "share_certificate_issued", "last_allotment_date",
                "certificate_delay_days"
            ],
        },
        "default_severity":  "YELLOW",
        "score_impact":      10,
        "revenue_tier":      "COMPLIANCE_PACKAGE",
        "is_black_override": False,
    },

    # ══════════════════════════════════════════════════════════════
    # MODULE 8: REGISTERED OFFICE — 1 rule
    # ══════════════════════════════════════════════════════════════
    {
        "rule_id":         "OFF-001",
        "rule_name":       "Change of Registered Office Not Filed Within 30 Days",
        "rule_type":       "REGISTER",
        "statutory_basis": "Section 77, Companies Act 1994 (Bangladesh)",
        "description": (
            "A change of registered office address has not been notified to the RJSC "
            "by filing Form XIV within 30 days of the change. Section 77 requires "
            "notification within 30 days of the new office being established. "
            "Until notified, the old address remains the company's legal registered "
            "office — statutory notices served there are valid, and the company cannot "
            "defend a claim that it did not receive them."
        ),
        "rule_condition": {
            "check_fn": "check_off_001_office_change_not_filed",
            "trigger": (
                "registered_office_change_date IS NOT NULL AND "
                "form_ix_filed == False AND "
                "days_since_office_change > 30"
            ),
            "data_points": [
                "registered_office_change_date", "form_ix_filed",
                "filing_delay_days"
            ],
        },
        "default_severity":  "YELLOW",
        "score_impact":      5,
        "revenue_tier":      "COMPLIANCE_PACKAGE",
        "is_black_override": False,
    },

    # ══════════════════════════════════════════════════════════════
    # MODULE 9: CAPITAL — 2 rules
    # ══════════════════════════════════════════════════════════════
    {
        "rule_id":         "CAP-001",
        "rule_name":       "Capital Alteration Without Proper Resolutions",
        "rule_type":       "CASCADE",
        "statutory_basis": "Section 54, Companies Act 1994 (Bangladesh)",
        "description": (
            "An alteration to the company's authorized or paid-up capital has been "
            "made without the required board resolution and/or special resolution of "
            "members (where required by the Articles), or the relevant forms have not "
            "been filed with the RJSC. Section 54 governs the procedure for increasing "
            "capital. Unrecorded capital changes cause the issued capital on the RJSC "
            "register to differ from the actual capital, creating legal uncertainty for "
            "all shareholders."
        ),
        "rule_condition": {
            "check_fn": "check_cap_001_capital_alteration_no_resolution",
            "trigger": (
                "capital_increase_date IS NOT NULL AND "
                "capital_increase_resolution == False"
            ),
            "data_points": [
                "capital_increase_date", "capital_increase_resolution",
                "authorized_capital_bdt", "paid_up_capital_bdt"
            ],
        },
        "default_severity":  "YELLOW",
        "score_impact":      10,
        "revenue_tier":      "COMPLIANCE_PACKAGE",
        "is_black_override": False,
    },
    {
        "rule_id":         "CAP-002",
        "rule_name":       "Charge Not Registered with RJSC Within 30 Days",
        "rule_type":       "CASCADE",
        "statutory_basis": "Section 107, Companies Act 1994 (Bangladesh)",
        "description": (
            "A charge (mortgage, debenture, floating charge, or other security) has "
            "been created on the company's property or assets but has not been "
            "registered with the RJSC within 30 days of its creation. Section 107 "
            "is explicit: an unregistered charge is void against the liquidator and "
            "any creditor of the company. The lender who fails to register loses their "
            "security interest entirely and becomes an unsecured creditor. Officers of "
            "the company are also personally liable for non-compliance."
        ),
        "rule_condition": {
            "check_fn": "check_cap_002_charge_not_registered",
            "trigger": (
                "charge_creation_date IS NOT NULL AND "
                "form_viii_filed == False AND "
                "days_since_charge_creation > 30"
            ),
            "data_points": [
                "charge_creation_date", "form_viii_filed"
            ],
        },
        "default_severity":  "YELLOW",
        "score_impact":      10,
        "revenue_tier":      "COMPLIANCE_PACKAGE",
        "is_black_override": False,
    },

    # ══════════════════════════════════════════════════════════════
    # MODULE 10: ESCALATION — 3 rules
    # Applied after all module scores are calculated
    # ══════════════════════════════════════════════════════════════
    {
        "rule_id":         "ESC-001",
        "rule_name":       "Strike-Off Risk Elevated",
        "rule_type":       "ESCALATION",
        "statutory_basis": "Section 396, Companies Act 1994 (Bangladesh)",
        "description": (
            "The company's compliance profile shows a pattern consistent with RJSC "
            "strike-off criteria under Section 396: multiple years of missed filings, "
            "no evidence of recent trading, or cumulative RED flags across 3 or more "
            "compliance modules. Section 396 permits the RJSC to strike off companies "
            "that fail to file returns or are not carrying on business. Proactive "
            "intervention through Structured Regularization is required immediately "
            "to preserve the company's legal existence."
        ),
        "rule_condition": {
            "check_fn": "check_esc_001_strike_off_risk_elevated",
            "trigger": (
                "unfiled_returns_count >= 2 OR "
                "(active_red_flags >= 3 AND active_yellow_flags >= 4)"
            ),
            "data_points": [
                "unfiled_returns_count", "active_red_flags",
                "active_yellow_flags", "current_risk_band"
            ],
        },
        "default_severity":  "RED",
        "score_impact":      20,
        "revenue_tier":      "STRUCTURED_REGULARIZATION",
        "is_black_override": False,
    },
    {
        "rule_id":         "ESC-002",
        "rule_name":       "Strike-Off Imminent — BLACK OVERRIDE",
        "rule_type":       "ESCALATION",
        "statutory_basis": "Section 396, Companies Act 1994 (Bangladesh)",
        "description": (
            "The company is at immediate risk of RJSC strike-off action. One or more "
            "of the following criteria is met: (a) 3 or more consecutive years of "
            "annual return non-filing, (b) RJSC strike-off notice received, "
            "(c) company appearing on RJSC's published strike-off list. "
            "Once struck off, the company ceases to exist as a legal entity — all "
            "contracts become void, all bank accounts are frozen, and restoration "
            "requires court proceedings. Immediate Corporate Rescue engagement is "
            "the only option to prevent dissolution. "
            "BLACK OVERRIDE: forces compliance score to BLACK band."
        ),
        "rule_condition": {
            "check_fn": "check_esc_002_strike_off_imminent_black_override",
            "trigger": (
                "unfiled_returns_count >= 3 OR "
                "rjsc_strike_off_notice == True OR "
                "on_rjsc_strike_off_list == True"
            ),
            "data_points": [
                "unfiled_returns_count", "company_status"
            ],
        },
        "default_severity":  "BLACK",
        "score_impact":      30,
        "revenue_tier":      "CORPORATE_RESCUE",
        "is_black_override": True,
    },
    {
        "rule_id":         "ESC-003",
        "rule_name":       "Corporate Rescue Mandatory — Systemic Failure",
        "rule_type":       "ESCALATION",
        "statutory_basis": "Multiple sections, Companies Act 1994 (Bangladesh)",
        "description": (
            "The company's cumulative compliance score has fallen below the BLACK band "
            "threshold (≤29 points) due to systemic multi-module failures: BLACK override "
            "flags from AUD-003, TR-005, or ESC-002, or a combination of RED and YELLOW "
            "flags across 4 or more modules producing a terminal score. The company's "
            "legal status, contractual capacity, and director personal exposure are all "
            "at critical risk. The 8-step NLC Corporate Rescue sequence is mandatory and "
            "must be initiated within 30 days. "
            "BLACK OVERRIDE: forces and permanently maintains BLACK band until rescue "
            "sequence is complete and verified."
        ),
        "rule_condition": {
            "check_fn": "check_esc_003_rescue_mandatory_black_override",
            "trigger": "pre_override_score <= 29 OR has_black_override == True",
            "data_points": [
                "pre_override_score", "has_black_override",
                "active_red_flags", "active_black_flags"
            ],
        },
        "default_severity":  "BLACK",
        "score_impact":      30,
        "revenue_tier":      "CORPORATE_RESCUE",
        "is_black_override": True,
    },
]


# ═══════════════════════════════════════════════════════════════════════
# SEEDER
# ═══════════════════════════════════════════════════════════════════════

EXPECTED_RULE_COUNT = 32  # 6+3+4+4+1+6+2+1+2+3


def get_database_url() -> str:
    """Resolve and validate DATABASE_URL."""
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        raise RuntimeError(
            "DATABASE_URL environment variable not set.\n"
            "Set it in .env or export DATABASE_URL=postgresql+asyncpg://..."
        )
    # Ensure asyncpg driver
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


async def seed_rules(dry_run: bool = False, verbose: bool = False) -> int:
    """
    Seed all ILRMF rules into legal_rules table.
    Returns count of rules inserted/updated.

    Uses UPSERT: ON CONFLICT (rule_id) DO UPDATE — safe to re-run.
    Dry run: validates rule data without writing to DB.
    """
    print(f"\n{'='*60}")
    print(f"  NEUM LEX COUNSEL — Legal Rules Seeder")
    print(f"  ILRMF Rule Set v1.0 — {EXPECTED_RULE_COUNT} rules")
    print(f"  Mode: {'DRY RUN (no writes)' if dry_run else 'LIVE (writing to DB)'}")
    print(f"{'='*60}\n")

    # ── Validate rule data before any DB operations ───────────────
    valid_rule_types      = {"AGM", "AUDIT", "RETURN", "DIRECTOR", "TRANSFER",
                             "REGISTER", "ESCALATION", "CASCADE"}
    valid_severities      = {"GREEN", "YELLOW", "RED", "BLACK"}
    valid_revenue_tiers   = {"COMPLIANCE_PACKAGE", "STRUCTURED_REGULARIZATION",
                             "CORPORATE_RESCUE"}

    print("Validating rule definitions...")
    seen_ids = set()
    for i, rule in enumerate(ILRMF_RULES):
        issues = []
        if rule["rule_id"] in seen_ids:
            issues.append(f"duplicate rule_id")
        seen_ids.add(rule["rule_id"])
        if rule["rule_type"] not in valid_rule_types:
            issues.append(f"invalid rule_type: {rule['rule_type']!r}")
        if rule["default_severity"] not in valid_severities:
            issues.append(f"invalid severity: {rule['default_severity']!r}")
        if rule["revenue_tier"] not in valid_revenue_tiers:
            issues.append(f"invalid revenue_tier: {rule['revenue_tier']!r}")
        if not rule.get("statutory_basis"):
            issues.append("missing statutory_basis")
        if not rule.get("description"):
            issues.append("missing description")
        if rule["is_black_override"] and rule["default_severity"] != "BLACK":
            issues.append("is_black_override=True but severity != BLACK")
        if issues:
            print(f"  ✗ VALIDATION FAILED [{rule['rule_id']}]: {', '.join(issues)}")
            raise ValueError(f"Rule validation failed for {rule['rule_id']}")
        if verbose:
            print(
                f"  ✓ {rule['rule_id']:10s}  "
                f"{rule['default_severity']:7s}  "
                f"{rule['score_impact']:2d}pts  "
                f"{'BLACK-OVERRIDE' if rule['is_black_override'] else rule['revenue_tier']}"
            )

    actual_count = len(ILRMF_RULES)
    if actual_count != EXPECTED_RULE_COUNT:
        raise ValueError(
            f"Expected {EXPECTED_RULE_COUNT} rules, found {actual_count}. "
            "Update EXPECTED_RULE_COUNT if intentionally adding/removing rules."
        )
    print(f"\n  ✓ All {actual_count} rule definitions valid\n")

    if dry_run:
        # Show summary by module
        from collections import Counter
        module_counts = Counter(
            r["rule_id"].split("-")[0] for r in ILRMF_RULES
        )
        print("Module summary:")
        for module, count in sorted(module_counts.items()):
            print(f"  {module:6s}: {count} rules")
        black_overrides = [r["rule_id"] for r in ILRMF_RULES if r["is_black_override"]]
        print(f"\nBLACK override rules ({len(black_overrides)}): {', '.join(black_overrides)}")
        score_total = sum(r["score_impact"] for r in ILRMF_RULES)
        print(f"Total max score deduction if all triggered: {score_total} pts")
        print("\n✓ Dry run complete — no changes written to DB.")
        return 0

    # ── Connect to DB and upsert ──────────────────────────────────
    db_url = get_database_url()
    engine = create_async_engine(db_url, echo=False)

    async with engine.begin() as conn:
        inserted = 0
        updated = 0
        now = datetime.now(timezone.utc)

        print(f"Connected to database. Seeding {actual_count} rules...\n")

        for rule in ILRMF_RULES:
            # Check if rule already exists
            result = await conn.execute(
                sa.text("SELECT id, rule_version FROM legal_rules WHERE rule_id = :rule_id"),
                {"rule_id": rule["rule_id"]}
            )
            existing = result.fetchone()

            if existing:
                # Update existing rule
                await conn.execute(sa.text("""
                    UPDATE legal_rules SET
                        rule_name         = :rule_name,
                        rule_type         = CAST(:rule_type AS rule_type),
                        statutory_basis   = :statutory_basis,
                        description       = :description,
                        rule_condition    = CAST(:rule_condition AS jsonb),
                        default_severity  = CAST(:default_severity AS severity_level),
                        score_impact      = :score_impact,
                        revenue_tier      = CAST(:revenue_tier AS revenue_tier),
                        is_black_override = :is_black_override,
                        is_active         = TRUE,
                        updated_at        = :now
                    WHERE rule_id = :rule_id
                """), {
                    "rule_id":          rule["rule_id"],
                    "rule_name":        rule["rule_name"],
                    "rule_type":        rule["rule_type"],
                    "statutory_basis":  rule["statutory_basis"],
                    "description":      rule["description"],
                    "rule_condition":   json.dumps(rule["rule_condition"]),
                    "default_severity": rule["default_severity"],
                    "score_impact":     rule["score_impact"],
                    "revenue_tier":     rule["revenue_tier"],
                    "is_black_override": rule["is_black_override"],
                    "now":              now,
                })
                updated += 1
                status = "↺ updated"
            else:
                # Insert new rule
                await conn.execute(sa.text("""
                    INSERT INTO legal_rules (
                        id, rule_id, rule_name, rule_type,
                        statutory_basis, description, rule_condition,
                        default_severity, score_impact, revenue_tier,
                        is_black_override, rule_version, is_active,
                        created_at, updated_at
                    ) VALUES (
                        uuid_generate_v4(),
                        :rule_id, :rule_name, CAST(:rule_type AS rule_type),
                        :statutory_basis, :description,
                        CAST(:rule_condition AS jsonb),
                        CAST(:default_severity AS severity_level),
                        :score_impact,
                        CAST(:revenue_tier AS revenue_tier),
                        :is_black_override, '1.0', TRUE,
                        :now, :now
                    )
                """), {
                    "rule_id":          rule["rule_id"],
                    "rule_name":        rule["rule_name"],
                    "rule_type":        rule["rule_type"],
                    "statutory_basis":  rule["statutory_basis"],
                    "description":      rule["description"],
                    "rule_condition":   json.dumps(rule["rule_condition"]),
                    "default_severity": rule["default_severity"],
                    "score_impact":     rule["score_impact"],
                    "revenue_tier":     rule["revenue_tier"],
                    "is_black_override": rule["is_black_override"],
                    "now":              now,
                })
                inserted += 1
                status = "✓ inserted"

            if verbose:
                print(
                    f"  {status}  {rule['rule_id']:10s}  "
                    f"{rule['default_severity']:7s}  {rule['score_impact']:2d}pts  "
                    f"{rule['rule_name'][:50]}"
                )

        # ── Verify final count ────────────────────────────────────
        count_result = await conn.execute(
            sa.text("SELECT COUNT(*) FROM legal_rules WHERE is_active = TRUE")
        )
        db_count = count_result.scalar()

    await engine.dispose()

    print(f"\n{'='*60}")
    print(f"  Seeding complete!")
    print(f"  Inserted: {inserted} new rules")
    print(f"  Updated:  {updated} existing rules")
    print(f"  DB total active rules: {db_count}")

    if db_count < EXPECTED_RULE_COUNT:
        print(
            f"\n  ⚠ WARNING: DB has {db_count} active rules, "
            f"expected {EXPECTED_RULE_COUNT}."
        )
    else:
        print(f"\n  ✓ AI Constitution Article 1 satisfied: all {db_count} rules active.")
    print(f"{'='*60}\n")

    return inserted + updated


def main():
    parser = argparse.ArgumentParser(
        description="Seed ILRMF legal rules into NLC database.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Validate rules without writing to database."
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Print each rule as it is inserted/updated."
    )
    args = parser.parse_args()

    try:
        count = asyncio.run(seed_rules(dry_run=args.dry_run, verbose=args.verbose))
        sys.exit(0)
    except RuntimeError as e:
        print(f"\n✗ Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Seeding failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    main()
