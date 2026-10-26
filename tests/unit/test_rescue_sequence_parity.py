"""Contract tests for finding-driven statutory rescue sequencing."""

from types import SimpleNamespace

import pytest

from app.rule_engine.engine import (
    ComplianceFlag,
    NLCRuleEngine,
    RevenueTier,
    RuleState,
    Severity,
)


def _flag(
    rule_id,
    *,
    severity=Severity.RED,
    state=RuleState.NON_COMPLIANT,
    resolved=False,
    applies=True,
    detail=None,
):
    return ComplianceFlag(
        rule_id=rule_id,
        flag_code=f"{rule_id}_TEST",
        severity=severity,
        score_impact=1,
        revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
        description="test",
        statutory_basis="test",
        state=state,
        resolved=resolved,
        conditional_applies=applies,
        detail=detail or {},
    )


def _seq(flags, band=Severity.RED):
    score = SimpleNamespace(risk_band=band)
    return NLCRuleEngine._generate_rescue_sequence(None, None, flags, score)


def test_gate_returns_empty_below_red():
    for band in (Severity.GREEN, Severity.YELLOW, Severity.NOT_EVALUATED):
        assert _seq([_flag("AGM-001")], band) == []


def test_no_flags_returns_empty_even_for_black():
    assert _seq([], Severity.BLACK) == []


def test_output_shape_and_metadata_come_from_canonical_registry():
    from canonical_architecture.statutory_rescue import STATUTORY_RESCUE_REGISTRY

    rescue = STATUTORY_RESCUE_REGISTRY["AGM-002"]
    steps = _seq([_flag("AGM-002")])

    assert len(steps) == 1
    step = steps[0]
    assert set(step) == {
        "title", "description", "related_rules", "priority",
        "min_days", "max_days", "rescue_id", "authority",
        "closure_condition", "statutory_basis", "complexity",
        "estimated_days_min", "estimated_days_max",
    }
    assert step["title"] == rescue.get("objective")
    assert step["rescue_id"] == rescue.get("rescue_id")
    assert step["authority"] == rescue.get("authority")
    assert step["closure_condition"] == rescue.get("closure_condition")
    assert step["related_rules"] == ["AGM-002"]
    assert step["priority"] == "HIGH"


@pytest.mark.parametrize(
    "rule_id",
    ["AGM-001", "AGM-002", "AUD-001", "AUD-002", "AUD-003",
     "TR-005", "TR-006", "ESC-002", "TR-001", "TR-004",
     "AR-002", "ESC-001", "ESC-003", "AGM-003"],
)
def test_registered_actionable_finding_yields_one_step(rule_id):
    steps = _seq([_flag(rule_id)])
    assert len(steps) == 1
    assert steps[0]["related_rules"] == [rule_id]


@pytest.mark.parametrize(
    "finding",
    [
        _flag("AGM-001", resolved=True),
        _flag("AGM-001", applies=False),
        _flag("AGM-001", state=RuleState.UNKNOWN),
        _flag("AGM-001", state=RuleState.COMPLIANT),
        _flag("AGM-001", severity=Severity.YELLOW),
    ],
)
def test_inactive_or_non_actionable_findings_produce_no_step(finding):
    assert _seq([finding]) == []


def test_tax004_quarters_aggregate_and_deduplicate_across_flags():
    steps = _seq([
        _flag("TAX-004", detail={"quarters": ["Q1", "Q2"]}),
        _flag("TAX-004", detail={"quarters": ["Q2", "Q4"]}),
    ])

    assert len(steps) == 1
    assert steps[0]["related_rules"] == ["TAX-004"]
    assert "Missed quarters: Q1, Q2, Q4." in steps[0]["description"]


def test_tax004_without_established_quarters_adds_no_step():
    assert _seq([
        _flag("TAX-004"),
        _flag("TAX-004", detail={"quarters": []}),
    ]) == []


def test_tax004_ignores_quarters_from_resolved_or_inapplicable_flags():
    steps = _seq([
        _flag("TAX-004", detail={"quarters": ["Q1"]}),
        _flag("TAX-004", resolved=True, detail={"quarters": ["Q2"]}),
        _flag("TAX-004", applies=False, detail={"quarters": ["Q3"]}),
    ])

    assert len(steps) == 1
    assert "Missed quarters: Q1." in steps[0]["description"]
    assert "Q2" not in steps[0]["description"]
    assert "Q3" not in steps[0]["description"]


def test_resolved_and_inapplicable_flags_are_ignored():
    assert _seq([
        _flag("AGM-001", resolved=True),
        _flag("ESC-002", applies=False),
    ]) == []


def test_black_findings_sort_before_red_findings():
    steps = _seq([
        _flag("AGM-001"),
        _flag("ESC-002", severity=Severity.BLACK),
        _flag("AUD-001"),
    ], Severity.BLACK)

    assert [step["related_rules"] for step in steps] == [
        ["ESC-002"], ["AGM-001"], ["AUD-001"]
    ]
    assert steps[0]["priority"] == "CRITICAL"
    assert all(step["priority"] == "HIGH" for step in steps[1:])


def test_missing_mapping_for_actionable_finding_is_explicit():
    with pytest.raises(ValueError, match="Missing statutory rescue mapping"):
        _seq([_flag("NO-SUCH-RULE")])
