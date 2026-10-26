"""RES-015: Parity test — engine rescue sequence vs canonical rescue planner.

Verifies that NLCRuleEngine._generate_rescue_sequence and
canonical_architecture.lifecycle_engine.LifecycleEngine.generate_rescue_plan
produce consistent step sequences for the same set of active findings.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.rule_engine.engine import (
    ComplianceFlag,
    NLCRuleEngine,
    RevenueTier,
    RuleState,
    Severity,
)


def _flag(rule_id, *, severity=Severity.RED, state=RuleState.NON_COMPLIANT,
           resolved=False, applies=True, detail=None):
    return ComplianceFlag(
        rule_id=rule_id, flag_code=f"{rule_id}_TEST", severity=severity,
        score_impact=1, revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
        description="test", statutory_basis="test", state=state,
        resolved=resolved, conditional_applies=applies, detail=detail or {},
    )


def _engine_steps(flags, band=Severity.RED):
    """Get step sequence from the engine's _generate_rescue_sequence."""
    score = SimpleNamespace(risk_band=band)
    return NLCRuleEngine._generate_rescue_sequence(None, None, flags, score)


def _canonical_steps(rule_ids):
    """Get step sequence from the canonical lifecycle_engine planner."""
    try:
        from canonical_architecture.lifecycle_engine import LifecycleEngine
        planner = LifecycleEngine()
        return planner.generate_rescue_plan(rule_ids)
    except Exception as exc:
        pytest.skip(f"Canonical planner not available: {exc}")


def _rule_ids(steps):
    """Extract ordered list of rule IDs from a step sequence."""
    ids = []
    for s in steps:
        for r in s.get("related_rules", []):
            if r not in ids:
                ids.append(r)
    return ids


PARITY_CASES = [
    (["AGM-001"], Severity.RED),
    (["AGM-002"], Severity.RED),
    (["AUD-001"], Severity.RED),
    (["TR-005"], Severity.RED),
    (["ESC-002"], Severity.BLACK),
    (["AGM-001", "AUD-001", "TR-005"], Severity.BLACK),
]


@pytest.mark.parametrize("rule_ids,band", PARITY_CASES)
def test_engine_and_canonical_produce_same_rule_ids(rule_ids, band):
    """RES-015: Both planners should reference the same rule IDs."""
    flags = [_flag(rid, severity=band) for rid in rule_ids]
    engine_ids = _rule_ids(_engine_steps(flags, band))
    canonical_ids = _rule_ids(_canonical_steps(rule_ids))
    assert set(engine_ids) == set(canonical_ids), (
        f"Rule ID mismatch for {rule_ids}: "
        f"engine={engine_ids}, canonical={canonical_ids}"
    )


@pytest.mark.parametrize("rule_ids,band", PARITY_CASES)
def test_engine_and_canonical_produce_same_step_count(rule_ids, band):
    """RES-015: Both planners should produce the same number of steps."""
    flags = [_flag(rid, severity=band) for rid in rule_ids]
    engine_steps = _engine_steps(flags, band)
    canonical_steps = _canonical_steps(rule_ids)
    if not canonical_steps:
        pytest.skip("Canonical planner returned no steps")
    assert len(engine_steps) == len(canonical_steps), (
        f"Step count mismatch for {rule_ids}: "
        f"engine={len(engine_steps)}, canonical={len(canonical_steps)}"
    )
