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


def test_clear_days_always_excludes_trigger_day_once():
    assert calculate_deadline(
        rule(unit="CLEAR_DAYS", offset=10, exclude_trigger_day=True),
        trigger_date=date(2026, 1, 1),
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
        {"unit": "FORTNIGHTS"},
        {"adjustment": "AUTOMATIC"},
        {"effective_from": date(2026, 1, 1), "effective_to": date(2025, 12, 31)},
    ],
)
def test_incomplete_or_invalid_rule_definition_is_rejected(overrides):
    with pytest.raises(ValueError):
        rule(**overrides)



def test_approved_penalty_respects_grace_cap_and_effective_dates():
    from decimal import Decimal

    from app.services.legal_deadline_engine import (
        PenaltyRule,
        calculate_approved_penalty,
    )

    candidate = PenaltyRule(
        rule_id="PEN-TEST-01",
        source_citation="Fixture-only statute section",
        source_version="fixture-v1",
        effective_from=date(2025, 1, 1),
        effective_to=date(2026, 12, 31),
        liable_person="company",
        fixed_amount=Decimal("100"),
        per_day_amount=Decimal("10"),
        grace_days=5,
        cap_amount=Decimal("250"),
        approved=True,
    )
    assert calculate_approved_penalty(
        candidate,
        days_overdue=4,
        as_of=date(2026, 1, 1),
        applicable=True,
        trigger_evidence_verified=True,
    ) == Decimal("100.00")
    assert calculate_approved_penalty(
        candidate,
        days_overdue=30,
        as_of=date(2026, 1, 1),
        applicable=True,
        trigger_evidence_verified=True,
    ) == Decimal("250.00")


def test_penalty_fails_closed_without_approval_applicability_or_evidence():
    from dataclasses import replace
    from decimal import Decimal

    from app.services.legal_deadline_engine import (
        PenaltyRule,
        calculate_approved_penalty,
    )

    candidate = PenaltyRule(
        rule_id="PEN-TEST-02",
        source_citation="Fixture-only statute section",
        source_version="fixture-v1",
        effective_from=date(2025, 1, 1),
        effective_to=None,
        liable_person="director",
        fixed_amount=Decimal("50"),
        approved=False,
    )
    args = dict(
        days_overdue=10,
        as_of=date(2026, 1, 1),
        applicable=True,
        trigger_evidence_verified=True,
    )
    assert calculate_approved_penalty(candidate, **args) is None
    approved = replace(candidate, approved=True)
    assert calculate_approved_penalty(
        approved, **{**args, "applicable": False}
    ) is None
    assert calculate_approved_penalty(
        approved, **{**args, "trigger_evidence_verified": False}
    ) is None
