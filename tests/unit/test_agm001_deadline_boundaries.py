"""Deterministic boundary tests for AGM-001 (Companies Act 1994 s.81(1), first proviso).

Draft statutory reading remains pending counsel approval. These tests verify the
engine's configured 18-calendar-month calculation, including end-of-month
clamping, and do not certify that interpretation as legally approved.
"""
from datetime import date, timedelta

import pytest


def _first_agm_default(output):
    return [
        flag for flag in output.flags
        if flag.rule_id == "AGM-001" and flag.flag_code == "FIRST_AGM_DEFAULT"
    ]


def _evaluate(rule_engine, build_profile, incorporation, today, **overrides):
    profile = build_profile(
        incorporation_date=incorporation,
        agm_count=0,
        last_agm_date=None,
        agm_held_this_cycle=False,
        **overrides,
    )
    return rule_engine.evaluate(profile, today=today)


# (incorporation, expected deadline)
DEADLINES = [
    (date(2024, 1, 31), date(2025, 7, 31)),    # ordinary
    (date(2023, 8, 31), date(2025, 2, 28)),    # clamp to 28 Feb (non-leap)
    (date(2022, 8, 31), date(2024, 2, 29)),    # clamp to 29 Feb (leap)
    (date(2024, 2, 29), date(2025, 8, 29)),    # incorporated on leap day
    (date(2024, 12, 31), date(2026, 6, 30)),   # clamp to 30 Jun
]


@pytest.mark.parametrize("incorporation,deadline", DEADLINES)
def test_no_default_on_deadline_day(rule_engine, build_profile, incorporation, deadline):
    output = _evaluate(rule_engine, build_profile, incorporation, deadline)
    assert _first_agm_default(output) == []


@pytest.mark.parametrize("incorporation,deadline", DEADLINES)
def test_default_starts_day_after_deadline(rule_engine, build_profile, incorporation, deadline):
    output = _evaluate(
        rule_engine, build_profile, incorporation, deadline + timedelta(days=1)
    )
    flags = _first_agm_default(output)
    assert len(flags) == 1
    detail = flags[0].detail
    assert detail["deadline"] == deadline.isoformat()
    assert detail["delay_days"] == 1
    assert detail["deadline_basis"] == "18_CALENDAR_MONTHS_FROM_INCORPORATION"
    assert detail["statutory_period_months"] == 18


def test_calendar_rule_differs_from_legacy_548_day_rule_late(rule_engine, build_profile):
    # Inc 2024-12-31: calendar deadline 2026-06-30; legacy 548-day date 2026-07-02.
    # On 2026-07-01 the calendar rule has expired; the legacy rule had not.
    output = _evaluate(
        rule_engine, build_profile, date(2024, 12, 31), date(2026, 7, 1)
    )
    assert len(_first_agm_default(output)) == 1


def test_calendar_rule_differs_from_legacy_548_day_rule_early(rule_engine, build_profile):
    # Inc 2024-03-01: calendar deadline 2025-09-01; legacy 548-day trigger fired
    # on 2025-09-01. The calendar rule must NOT flag on 2025-09-01.
    output = _evaluate(
        rule_engine, build_profile, date(2024, 3, 1), date(2025, 9, 1)
    )
    assert _first_agm_default(output) == []


def test_black_threshold_is_365_vs_366_days_late(rule_engine, build_profile):
    incorporation, deadline = date(2020, 1, 15), date(2021, 7, 15)
    red = _first_agm_default(
        _evaluate(
            rule_engine, build_profile, incorporation, deadline + timedelta(days=365)
        )
    )
    black = _first_agm_default(
        _evaluate(
            rule_engine, build_profile, incorporation, deadline + timedelta(days=366)
        )
    )
    assert len(red) == len(black) == 1
    assert red[0].severity.value == "RED"
    assert black[0].severity.value == "BLACK"


def test_unverified_history_never_infers_default(rule_engine, build_profile):
    output = _evaluate(
        rule_engine, build_profile, date(2020, 1, 15), date(2026, 1, 15),
        agm_history_verified=False,
    )
    assert _first_agm_default(output) == []
    codes = [flag.flag_code for flag in output.flags if flag.rule_id == "AGM-001"]
    assert "AGM_HISTORY_REQUIRES_VERIFICATION" in codes


@pytest.mark.parametrize(
    "missing_field",
    [
        "agm_history_evidence_ref",
        "agm_history_verified_at",
        "agm_history_verified_by",
    ],
)
def test_incomplete_history_verification_never_infers_default(
    rule_engine, build_profile, missing_field
):
    output = _evaluate(
        rule_engine,
        build_profile,
        date(2020, 1, 15),
        date(2026, 1, 15),
        **{missing_field: None},
    )
    assert _first_agm_default(output) == []
    codes = [flag.flag_code for flag in output.flags if flag.rule_id == "AGM-001"]
    assert "AGM_HISTORY_REQUIRES_VERIFICATION" in codes


def test_missing_incorporation_date_is_unknown_not_default(rule_engine, build_profile):
    output = _evaluate(rule_engine, build_profile, None, date(2026, 1, 15))
    assert _first_agm_default(output) == []
    codes = [flag.flag_code for flag in output.flags if flag.rule_id == "AGM-001"]
    assert "INCORPORATION_DATE_UNKNOWN" in codes


def test_missing_agm_count_is_unknown_not_default(rule_engine, build_profile):
    profile = build_profile(
        incorporation_date=date(2020, 1, 15),
        agm_count=None,
        last_agm_date=None,
        agm_held_this_cycle=False,
    )
    output = rule_engine.evaluate(profile, today=date(2026, 1, 15))
    assert _first_agm_default(output) == []
    codes = [flag.flag_code for flag in output.flags if flag.rule_id == "AGM-001"]
    assert "AGM_COUNT_UNKNOWN" in codes


def test_first_agm_held_means_no_first_agm_default(rule_engine, build_profile):
    profile = build_profile(
        incorporation_date=date(2020, 1, 15),
        agm_count=1,
        last_agm_date=date(2021, 3, 1),
        agm_held_this_cycle=True,
    )
    output = rule_engine.evaluate(profile, today=date(2026, 1, 15))
    assert _first_agm_default(output) == []
