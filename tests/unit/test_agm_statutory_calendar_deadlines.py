from datetime import date, timedelta

from app.rule_engine.engine import RuleState, Severity


def _evaluate_first_agm(rule_engine, build_profile, incorporation_date, as_of, agm_count=0):
    profile = build_profile(
        incorporation_date=incorporation_date,
        agm_count=agm_count,
        agm_history_verified=True,
        agm_history_evidence_ref="AGM-HISTORY-TEST",
        last_agm_date=None,
        agm_held_this_cycle=False,
    )
    output = rule_engine.evaluate(profile, today=as_of)
    return [flag for flag in output.flags if flag.rule_id == "AGM-001"]


def test_agm001_exact_deadline_is_not_overdue(rule_engine, build_profile):
    incorporation_date = date(2024, 1, 31)
    deadline = date(2025, 7, 31)

    flags = _evaluate_first_agm(
        rule_engine, build_profile, incorporation_date, deadline
    )

    assert flags == []


def test_agm001_becomes_overdue_the_day_after_deadline(rule_engine, build_profile):
    incorporation_date = date(2024, 1, 31)
    deadline = date(2025, 7, 31)

    flags = _evaluate_first_agm(
        rule_engine, build_profile, incorporation_date, deadline + timedelta(days=1)
    )

    assert len(flags) == 1
    assert flags[0].flag_code == "FIRST_AGM_DEFAULT"
    assert flags[0].detail["deadline"] == deadline.isoformat()
    assert flags[0].detail["delay_days"] == 1
    assert flags[0].severity == Severity.RED


def test_agm001_august_31_deadline_clamps_to_february_28(rule_engine, build_profile):
    incorporation_date = date(2023, 8, 31)
    deadline = date(2025, 2, 28)

    flags = _evaluate_first_agm(
        rule_engine, build_profile, incorporation_date, deadline + timedelta(days=1)
    )

    assert len(flags) == 1
    assert flags[0].detail["deadline"] == deadline.isoformat()


def test_agm001_august_31_deadline_clamps_to_february_29_in_leap_year(
    rule_engine, build_profile
):
    incorporation_date = date(2022, 8, 31)
    deadline = date(2024, 2, 29)

    flags = _evaluate_first_agm(
        rule_engine, build_profile, incorporation_date, deadline + timedelta(days=1)
    )

    assert len(flags) == 1
    assert flags[0].detail["deadline"] == deadline.isoformat()


def test_agm001_february_29_incorporation_adds_eighteen_calendar_months(
    rule_engine, build_profile
):
    incorporation_date = date(2024, 2, 29)
    deadline = date(2025, 8, 29)

    flags = _evaluate_first_agm(
        rule_engine, build_profile, incorporation_date, deadline + timedelta(days=1)
    )

    assert len(flags) == 1
    assert flags[0].detail["deadline"] == deadline.isoformat()


def test_agm001_delay_of_365_days_remains_red(rule_engine, build_profile):
    incorporation_date = date(2024, 1, 31)
    deadline = date(2025, 7, 31)

    flags = _evaluate_first_agm(
        rule_engine,
        build_profile,
        incorporation_date,
        deadline + timedelta(days=365),
    )

    assert len(flags) == 1
    assert flags[0].detail["delay_days"] == 365
    assert flags[0].severity == Severity.RED


def test_agm001_delay_of_366_days_is_black(rule_engine, build_profile):
    incorporation_date = date(2024, 1, 31)
    deadline = date(2025, 7, 31)

    flags = _evaluate_first_agm(
        rule_engine,
        build_profile,
        incorporation_date,
        deadline + timedelta(days=366),
    )

    assert len(flags) == 1
    assert flags[0].detail["delay_days"] == 366
    assert flags[0].severity == Severity.BLACK


def test_agm001_only_applies_when_verified_agm_count_is_zero(
    rule_engine, build_profile
):
    incorporation_date = date(2024, 1, 31)
    as_of = date(2026, 8, 1)

    no_agm_flags = _evaluate_first_agm(
        rule_engine, build_profile, incorporation_date, as_of, agm_count=0
    )
    subsequent_agm_flags = _evaluate_first_agm(
        rule_engine, build_profile, incorporation_date, as_of, agm_count=1
    )
    unknown_count_flags = _evaluate_first_agm(
        rule_engine, build_profile, incorporation_date, as_of, agm_count=None
    )

    assert len(no_agm_flags) == 1
    assert no_agm_flags[0].flag_code == "FIRST_AGM_DEFAULT"
    assert subsequent_agm_flags == []
    assert len(unknown_count_flags) == 1
    assert unknown_count_flags[0].state == RuleState.UNKNOWN
    assert unknown_count_flags[0].score_impact == 0
