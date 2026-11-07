"""Statutory calendar must remain unavailable until legal approval is real."""

from app.services.compliance_calendar import (
    LEGAL_CALENDAR_RELEASED,
    VERIFIED_CALENDAR_EVENT_TYPES,
    VERIFIED_PENALTY_EVENT_TYPES,
    _generate_calendar,
    calculate_penalty,
)


def test_statutory_calendar_is_fail_closed():
    assert LEGAL_CALENDAR_RELEASED is False
    assert VERIFIED_CALENDAR_EVENT_TYPES == frozenset()
    assert _generate_calendar(None) == []


def test_unapproved_statutory_penalties_are_never_estimated():
    assert VERIFIED_PENALTY_EVENT_TYPES == frozenset()
    assert calculate_penalty("agm", 30) is None
    assert calculate_penalty("corporate_tax_return", 30) is None
    assert calculate_penalty("vat_return", 30) is None
    assert calculate_penalty("bsec_q1_report", 30) is None
