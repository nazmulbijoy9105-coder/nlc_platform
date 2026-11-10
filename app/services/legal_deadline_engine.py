"""Deterministic primitives for source-approved statutory deadline rules.

This module intentionally contains no Bangladesh statutory rules, dates,
holiday calendar, or default legal conventions. Each rule must supply its
own reviewed source/version, effective interval, trigger and computation
convention. Customer-facing integration remains behind the calendar release
gate until a complete approved event manifest exists.
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal


Adjustment = Literal["NONE", "FOLLOWING", "PRECEDING"]
Unit = Literal["DAYS", "CLEAR_DAYS", "MONTHS", "YEARS"]


@dataclass(frozen=True, slots=True)
class DeadlineRule:
    rule_id: str
    source_citation: str
    source_version: str
    effective_from: date
    effective_to: date | None
    offset: int
    unit: Unit
    adjustment: Adjustment = "NONE"
    exclude_trigger_day: bool = False
    approved: bool = False

    def __post_init__(self) -> None:
        if not self.rule_id.strip():
            raise ValueError("rule_id is required")
        if not self.source_citation.strip() or not self.source_version.strip():
            raise ValueError("exact legal source and source version are required")
        if self.offset < 0:
            raise ValueError("offset cannot be negative")
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValueError("effective_to cannot precede effective_from")


def _add_months(value: date, months: int) -> date:
    """Add calendar months, clamping to the last day of the target month."""
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _add_years(value: date, years: int) -> date:
    """Add calendar years, clamping leap-day triggers to 28 February."""
    try:
        return value.replace(year=value.year + years)
    except ValueError:
        return value.replace(year=value.year + years, day=28)


def _adjust_business_day(
    value: date,
    adjustment: Adjustment,
    holidays: frozenset[date],
) -> date:
    if adjustment == "NONE":
        return value
    step = 1 if adjustment == "FOLLOWING" else -1
    while value.weekday() >= 5 or value in holidays:
        value += timedelta(days=step)
    return value


def calculate_deadline(
    rule: DeadlineRule,
    *,
    trigger_date: date,
    applicable: bool,
    trigger_evidence_verified: bool,
    holidays: frozenset[date] = frozenset(),
) -> date | None:
    """Calculate only a fully specified, approved and evidenced rule.

    None means no deadline may be emitted; it does not mean no obligation
    exists. Callers must preserve UNKNOWN/DISPUTED/NOT_APPLICABLE separately.
    """
    if not rule.approved or not applicable or not trigger_evidence_verified:
        return None
    if trigger_date < rule.effective_from:
        return None
    if rule.effective_to is not None and trigger_date > rule.effective_to:
        return None

    if rule.unit == "CLEAR_DAYS":
        # Clear-day counting excludes the trigger day by definition; the due
        # date follows the final clear day. Do not apply exclude_trigger_day twice.
        due = trigger_date + timedelta(days=rule.offset + 1)
    else:
        base = trigger_date + timedelta(days=1) if rule.exclude_trigger_day else trigger_date

    if rule.unit == "CLEAR_DAYS":
        pass  # due was computed above using the clear-day convention.
    elif rule.unit == "DAYS":
        due = base + timedelta(days=rule.offset)
    elif rule.unit == "MONTHS":
        due = _add_months(base, rule.offset)
    elif rule.unit == "YEARS":
        due = _add_years(base, rule.offset)
    else:  # pragma: no cover - Literal protects typed callers; runtime guard remains.
        raise ValueError(f"Unsupported deadline unit: {rule.unit}")

    return _adjust_business_day(due, rule.adjustment, holidays)
