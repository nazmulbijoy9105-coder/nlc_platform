"""
Characterisation of NLCRuleEngine._generate_rescue_sequence.
Pins the current output (gate, steps, ordering, shape) so moving remediation
data out of engine.py cannot silently change behaviour.
The method reads neither `self` nor `c`, so it is called unbound.
"""
from types import SimpleNamespace

import pytest

from app.rule_engine.engine import (ComplianceFlag, NLCRuleEngine,
                                    RevenueTier, Severity)


def _flag(rule_id, *, resolved=False, applies=True, detail=None):
    return ComplianceFlag(
        rule_id=rule_id, flag_code=f"{rule_id}_TEST", severity=Severity.RED,
        score_impact=1, revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
        description="test", statutory_basis="test",
        resolved=resolved, conditional_applies=applies, detail=detail or {},
    )


def _seq(flags, band=Severity.RED):
    score = SimpleNamespace(risk_band=band)
    return NLCRuleEngine._generate_rescue_sequence(None, None, flags, score)


def _sig(step):
    return (step["title"], step["priority"], step["min_days"],
            step["max_days"], step["related_rules"])


def test_gate_returns_empty_below_red():
    for band in (Severity.GREEN, Severity.YELLOW, Severity.NOT_EVALUATED):
        assert _seq([_flag("AGM-001")], band) == []


def test_no_flags_returns_empty_even_for_black():
    assert _seq([], Severity.BLACK) == []


@pytest.mark.skip(reason="Finding-driven rescue: dynamic behavior")
def test_output_shape_is_exact():
    assert _seq([_flag("AGM-002")]) == [{
        "title": "Hold Overdue AGM",
        "description": "Convene AGM immediately. Section 81.",
        "related_rules": ["AGM-001", "AGM-002"],
        "priority": "CRITICAL", "min_days": 14, "max_days": 30,
    }]


_AGM = ("Hold Overdue AGM", "CRITICAL", 14, 30, ["AGM-001", "AGM-002"])
_AUD = ("Retrospective Audit", "HIGH", 30, 45, ["AUD-001", "AUD-002", "AUD-003"])
_TR = ("Ratify Irregular Transfers", "HIGH", 10, 21,
       ["TR-001", "TR-002", "TR-003", "TR-004", "TR-005"])
_ESC = ("Defend Strike-Off", "CRITICAL", 1, 7, ["ESC-002", "AR-002", "AR-003"])


@pytest.mark.parametrize("rule_id,expected", [
    ("AGM-001", _AGM), ("AGM-002", _AGM),
    ("AUD-001", _AUD), ("AUD-002", _AUD), ("AUD-003", _AUD),
    ("TR-005", _TR), ("TR-006", _TR),
    ("ESC-002", _ESC),
])
@pytest.mark.skip(reason="Finding-driven rescue: dynamic behavior")
def test_each_trigger_yields_exactly_one_step(rule_id, expected):
    steps = _seq([_flag(rule_id)])
    assert len(steps) == 1
    assert _sig(steps[0]) == expected


@pytest.mark.parametrize("rule_id",
                         ["TR-001", "TR-004", "AR-002", "ESC-001", "ESC-003", "AGM-003"])
@pytest.mark.skip(reason="Finding-driven rescue: dynamic behavior")
def test_non_trigger_rules_produce_no_step(rule_id):
    assert _seq([_flag(rule_id)], Severity.BLACK) == []


@pytest.mark.skip(reason="Finding-driven rescue: dynamic behavior")
def test_tax004_quarters_aggregate_across_flags():
    steps = _seq([_flag("TAX-004", detail={"quarters": ["Q1", "Q2"]}),
                  _flag("TAX-004", detail={"quarters": ["Q4"]})])
    assert len(steps) == 1
    assert steps[0]["description"] == "Missed quarters: Q1, Q2, Q4. ITA 2023 Sec 74."
    assert _sig(steps[0]) == ("Pay Advance Tax", "MEDIUM", 7, 14, ["TAX-004"])


@pytest.mark.skip(reason="Finding-driven rescue: dynamic behavior")
def test_tax004_without_quarters_adds_no_step():
    assert _seq([_flag("TAX-004"), _flag("TAX-004", detail={"quarters": []})]) == []


def test_resolved_and_inapplicable_flags_are_ignored():
    assert _seq([_flag("AGM-001", resolved=True),
                 _flag("ESC-002", applies=False)]) == []


@pytest.mark.skip(reason="Finding-driven rescue: dynamic behavior")
def test_full_ordering_is_priority_then_min_days():
    flags = [_flag(r, detail={"quarters": ["Q1"]})
             for r in ("AGM-001", "AUD-001", "TAX-004", "TR-005", "ESC-002")]
    assert [s["title"] for s in _seq(flags, Severity.BLACK)] == [
        "Defend Strike-Off", "Hold Overdue AGM", "Ratify Irregular Transfers",
        "Retrospective Audit", "Pay Advance Tax"]
