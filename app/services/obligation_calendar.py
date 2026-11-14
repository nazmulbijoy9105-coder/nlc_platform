"""Deterministic corporate-calendar planning primitives.

This module creates reminders, not statutory findings. A generated item never
means that a filing was missed; proof of the event, applicability and legal
exceptions belongs to the evaluation/evidence layer.

Legal anchors:
- Companies Act 1994 (Bangladesh), s.81: AGM in each English calendar year
  and no more than 15 months between successive AGMs; first-AGM period is
  separately handled by the Act.
- Companies Act 1994, s.96: at least one Board meeting every three months
  and at least four in each year.
- Companies Act 1994, s.183: financial statements are presented at the AGM.
- Companies Act 1994, s.210(1), (6): auditor appointment at AGM; first auditor
  appointed by Board within one month of registration.
- BSEC Corporate Governance Code 2018, Conditions 5(4)(a) and 5(5)(e)-(g):
  listed-issuer Audit Committee has at least four meetings in a financial year
  and reviews annual, quarterly and half-yearly statements. The Code's scope
  and amendments must be independently verified for the relevant issuer/date.
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Iterable


class Applicability(StrEnum):
    APPLICABLE = "APPLICABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNKNOWN = "UNKNOWN"


class DueKind(StrEnum):
    STATUTORY_DEADLINE = "STATUTORY_DEADLINE"
    INTERNAL_PLANNING_TARGET = "INTERNAL_PLANNING_TARGET"
    REVIEW_WINDOW = "REVIEW_WINDOW"


@dataclass(frozen=True)
class CalendarObligation:
    obligation_id: str
    title: str
    due_date: date | None
    applicability: Applicability
    due_kind: DueKind
    statutory_basis: str
    reason: str
    requires_documentary_evidence: bool = True


def add_calendar_months(value: date, months: int) -> date:
    """Add calendar months, clamping to the final day of the target month."""
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _quarterly_dates(start: date, end: date) -> tuple[date, ...]:
    dates: list[date] = []
    cursor = add_calendar_months(start, 3)
    while cursor <= end:
        dates.append(cursor)
        cursor = add_calendar_months(cursor, 3)
    if not dates or dates[-1] < end:
        dates.append(end)
    return tuple(dates[:4])


def build_private_company_calendar(
    *,
    as_of: date,
    company_type: str | None,
    company_type_verified: bool,
    incorporation_date: date | None,
    agm_dates: Iterable[date] | None,
    agm_history_verified: bool,
    board_meeting_dates: Iterable[date] | None,
    board_history_verified: bool,
    financial_year_start: date | None = None,
    financial_year_end: date | None = None,
    first_auditor_appointed: bool | None = None,
    first_auditor_status_verified: bool = False,
    bsec_listed: bool | None = None,
    bsec_listing_verified: bool = False,
    is_subsidiary_of_listed_issuer: bool | None = None,
    subsidiary_scope_verified: bool = False,
) -> tuple[CalendarObligation, ...]:
    """Return a stable, sorted set of obligations for one company snapshot.

    A missing/unverified fact produces UNKNOWN, not an inferred breach.
    BSEC items are never included in the ordinary private-company pack merely
    because the entity has a public-company parent; subsidiary scope is a
    separate verified input and requires counsel confirmation.
    """
    kind = (company_type or "").upper()
    company_known = company_type_verified and bool(kind)
    is_private = company_known and kind in {"PRIVATE_LIMITED", "PRIVATE_COMPANY"}
    is_other = company_known and not is_private
    items: list[CalendarObligation] = []

    if not company_known:
        items.append(CalendarObligation(
            "AGM-81", "Annual general meeting", None, Applicability.UNKNOWN,
            DueKind.STATUTORY_DEADLINE, "Companies Act 1994, s.81(1)",
            "Verified legal form is required before calculating company-specific obligations.",
        ))
    elif incorporation_date is None:
        items.append(CalendarObligation(
            "AGM-81", "Annual general meeting", None, Applicability.UNKNOWN,
            DueKind.STATUTORY_DEADLINE, "Companies Act 1994, s.81(1)",
            "Incorporation date is missing; no AGM due date can be calculated.",
        ))
    elif not agm_history_verified or agm_dates is None:
        items.append(CalendarObligation(
            "AGM-81", "Annual general meeting", None, Applicability.APPLICABLE,
            DueKind.STATUTORY_DEADLINE, "Companies Act 1994, s.81(1)",
            "AGM obligation applies, but verified AGM history is required to calculate the next due date.",
        ))
    else:
        history = sorted(set(agm_dates))
        if not history:
            due = add_calendar_months(incorporation_date, 18)
            reason = "First AGM period: 18 calendar months from registration; verify any statutory extension."
        else:
            last_agm = history[-1]
            annual_boundary = date(as_of.year, 12, 31)
            if last_agm.year >= as_of.year:
                annual_boundary = date(as_of.year + 1, 12, 31)
            due = min(add_calendar_months(last_agm, 15), annual_boundary)
            reason = "Next AGM planning date is the earlier of the 15-month interval and the next applicable calendar-year boundary."
        items.append(CalendarObligation(
            "AGM-81", "Annual general meeting", due, Applicability.APPLICABLE,
            DueKind.STATUTORY_DEADLINE, "Companies Act 1994, s.81(1)", reason,
        ))
        items.append(CalendarObligation(
            "ACC-183", "Present annual financial statements at AGM", due,
            Applicability.APPLICABLE, DueKind.STATUTORY_DEADLINE,
            "Companies Act 1994, s.183(1)",
            "Presentation is linked to the AGM; accounts period and any Registrar extension require separate verification.",
        ))
        items.append(CalendarObligation(
            "AUD-210-AGM", "Auditor appointment/reappointment at AGM", due,
            Applicability.APPLICABLE, DueKind.STATUTORY_DEADLINE,
            "Companies Act 1994, s.210(1)",
            "Appointment and statutory exceptions must be checked against the AGM record.",
        ))

    if incorporation_date is not None:
        first_auditor_due = add_calendar_months(incorporation_date, 1)
        if first_auditor_status_verified and first_auditor_appointed is True:
            audit_state = Applicability.NOT_APPLICABLE
            audit_reason = "Verified first-auditor appointment is recorded."
        elif first_auditor_status_verified and first_auditor_appointed is False:
            audit_state = Applicability.APPLICABLE
            audit_reason = "Verified absence is recorded; counsel must assess the legal consequence."
        else:
            audit_state = Applicability.UNKNOWN
            audit_reason = "First-auditor appointment status is not verified."
        items.append(CalendarObligation(
            "AUD-210-6", "First auditor appointment review", first_auditor_due,
            audit_state, DueKind.STATUTORY_DEADLINE,
            "Companies Act 1994, s.210(6)", audit_reason,
        ))

    if not board_history_verified or board_meeting_dates is None:
        items.append(CalendarObligation(
            "BOD-96", "Board meeting cycle", None, Applicability.APPLICABLE,
            DueKind.STATUTORY_DEADLINE, "Companies Act 1994, s.96",
            "At least one meeting every three months and four per year; complete verified meeting history is required to calculate the next cycle.",
        ))
    else:
        meetings = sorted(set(board_meeting_dates))
        if meetings:
            due = add_calendar_months(meetings[-1], 3)
            items.append(CalendarObligation(
                "BOD-96", "Next Board meeting cycle", due,
                Applicability.APPLICABLE, DueKind.STATUTORY_DEADLINE,
                "Companies Act 1994, s.96",
                "Next rolling three-month checkpoint; four-meetings-per-year count must also be tested against the complete annual ledger.",
            ))
        else:
            items.append(CalendarObligation(
                "BOD-96", "Board meeting cycle", None, Applicability.UNKNOWN,
                DueKind.STATUTORY_DEADLINE, "Companies Act 1994, s.96",
                "No verified Board meeting dates were supplied.",
            ))

    # Listed-issuer Code obligations are not private-company defaults.
    if bsec_listed is True and bsec_listing_verified:
        code_applies = Applicability.APPLICABLE
    elif bsec_listed is False and bsec_listing_verified:
        code_applies = Applicability.NOT_APPLICABLE
    elif is_private and bsec_listed is None:
        code_applies = Applicability.NOT_APPLICABLE
    else:
        code_applies = Applicability.UNKNOWN

    subsidiary_applies = (
        is_subsidiary_of_listed_issuer is True and subsidiary_scope_verified
    )
    if code_applies == Applicability.APPLICABLE or subsidiary_applies:
        if financial_year_start is None or financial_year_end is None:
            items.append(CalendarObligation(
                "BSEC-AC-5(4)", "Audit Committee four-meeting annual cycle",
                None, Applicability.UNKNOWN, DueKind.INTERNAL_PLANNING_TARGET,
                "BSEC Corporate Governance Code 2018, Condition 5(4)(a)",
                "Verified financial-year boundaries are required; this is a listed-issuer Code obligation, not an ordinary private-company duty.",
            ))
        else:
            for index, due in enumerate(_quarterly_dates(financial_year_start, financial_year_end), 1):
                items.append(CalendarObligation(
                    f"BSEC-AC-5(4)-Q{index}", f"Audit Committee meeting cycle {index}",
                    due, Applicability.APPLICABLE, DueKind.INTERNAL_PLANNING_TARGET,
                    "BSEC Corporate Governance Code 2018, Condition 5(4)(a)",
                    "Quarterly planning target used to schedule at least four meetings in the financial year; the Code sets an annual minimum, not these exact quarter-end dates.",
                ))
        if financial_year_start and financial_year_end:
            items.extend((
                CalendarObligation(
                    "BSEC-AC-5(5)(g)-Q", "Audit Committee quarterly financial-statement review",
                    None, Applicability.APPLICABLE, DueKind.REVIEW_WINDOW,
                    "BSEC Corporate Governance Code 2018, Condition 5(5)(g)",
                    "Review quarterly statements with management before Board approval; due date depends on the issuer's reporting and Board timetable.",
                ),
                CalendarObligation(
                    "BSEC-AC-5(5)(g)-H", "Audit Committee half-yearly financial-statement review",
                    None, Applicability.APPLICABLE, DueKind.REVIEW_WINDOW,
                    "BSEC Corporate Governance Code 2018, Condition 5(5)(g)",
                    "Review half-yearly statements with management before Board approval; no filing deadline is inferred here.",
                ),
            ))
    elif code_applies == Applicability.UNKNOWN:
        items.append(CalendarObligation(
            "BSEC-SCOPE", "BSEC Code applicability review", None,
            Applicability.UNKNOWN, DueKind.REVIEW_WINDOW,
            "BSEC Corporate Governance Code 2018, Conditions 1, 2 and 5",
            "Listing and any listed-parent subsidiary relationship require source-backed verification; no Code deadline is generated while scope is unknown.",
        ))

    return tuple(sorted(items, key=lambda item: (
        item.due_date or date.max, item.obligation_id
    )))
