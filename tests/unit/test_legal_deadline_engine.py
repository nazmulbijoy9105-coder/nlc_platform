from datetime import date

import pytest

from app.services.legal_deadline_engine import DeadlineRule, calculate_deadline


def rule(**overrides):
    values = {
        "rule_id": "TEST-001",
        "source_citation": "Test instrument, section 1 (fixture only)",
        "source_version": "fixture-2026-01",
        "effective_from": date(2020, 1, 1),
        "effective_to": None,
        "offset": 10,
        "unit": "DAYS",
        "adjustment": "NONE",
        "exclude_trigger_day": False,
        "approved": True,
    }
    values.update(overrides)
    return DeadlineRule(**values)


def test_unapproved_or_unproven_rule_never_emits_a_deadline():
    candidate = rule(approved=False)
    assert calculate_deadline(
        candidate,
        trigger_date=date(2026, 1, 1),
        applicable=True,
        trigger_evidence_verified=True,
    ) is None
    assert calculate_deadline(
        rule(),
        trigger_date=date(2026, 1, 1),
        applicable=True,
        trigger_evidence_verified=False,
    ) is None
    assert calculate_deadline(
        rule(),
        trigger_date=date(2026, 1, 1),
        applicable=False,
        trigger_evidence_verified=True,
    ) is None


def test_days_and_clear_days_are_explicitly_different():
    trigger = date(2026, 1, 1)
    assert calculate_deadline(
        rule(unit="DAYS", offset=10),
        trigger_date=trigger,
        applicable=True,
        trigger_evidence_verified=True,
    ) == date(2026, 1, 11)
    assert calculate_deadline(
        rule(unit="CLEAR_DAYS", offset=10),
        trigger_date=trigger,
        applicable=True,
        trigger_evidence_verified=True,
    ) == date(2026, 1, 12)


def test_calendar_month_clamps_end_of_month():
    assert calculate_deadline(
        rule(unit="MONTHS", offset=1),
        trigger_date=date(2026, 1, 31),
        applicable=True,
        trigger_evidence_verified=True,
    ) == date(2026, 2, 28)


def test_leap_day_year_clamps_to_february_28():
    assert calculate_deadline(
        rule(unit="YEARS", offset=1),
        trigger_date=date(2024, 2, 29),
        applicable=True,
        trigger_evidence_verified=True,
    ) == date(2025, 2, 28)


def test_explicit_holiday_and_weekend_adjustment():
    assert calculate_deadline(
        rule(offset=0, adjustment="FOLLOWING"),
        trigger_date=date(2026, 1, 2),  # Friday
        applicable=True,
        trigger_evidence_verified=True,
        holidays=frozenset({date(2026, 1, 5)}),
    ) == date(2026, 1, 6)


def test_rule_effective_interval_is_enforced():
    candidate = rule(effective_to=date(2025, 12, 31))
    assert calculate_deadline(
        candidate,
        trigger_date=date(2026, 1, 1),
        applicable=True,
        trigger_evidence_verified=True,
    ) is None


@pytest.mark.parametrize(
    "overrides",
    [
        {"source_citation": ""},
        {"source_version": ""},
        {"offset": -1},
        {"effective_from": date(2026, 1, 1), "effective_to": date(2025, 12, 31)},
    ],
)
def test_incomplete_or_invalid_rule_definition_is_rejected(overrides):
    with pytest.raises(ValueError):
        rule(**overrides)
