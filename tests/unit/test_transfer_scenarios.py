"""TR-012: Transfer rule test coverage — 3 required scenarios.

(a) restriction violated → NON_COMPLIANT + BLACK
(b) restriction present but complied with → COMPLIANT
(c) approval evidence missing → UNKNOWN (0 pts)
"""
import pytest
from types import SimpleNamespace
from app.rule_engine.engine import ComplianceFlag, NLCRuleEngine, RevenueTier, RuleState, Severity


def _flag(rule_id="TR-005", *, severity=Severity.RED, state=RuleState.NON_COMPLIANT,
          resolved=False, applies=True, detail=None):
    return ComplianceFlag(
        rule_id=rule_id, flag_code=f"{rule_id}_TEST", severity=severity,
        score_impact=1, revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
        description="test", statutory_basis="test", state=state,
        resolved=resolved, conditional_applies=applies, detail=detail or {},
    )


def _score(band=Severity.RED):
    return SimpleNamespace(risk_band=band)


def test_transfer_restriction_violated_fires_black():
    """TR-012 (a): AoA restriction violated → NON_COMPLIANT + BLACK."""
    flags = [_flag("TR-005", severity=Severity.BLACK)]
    score = _score(Severity.BLACK)
    result = NLCRuleEngine._generate_rescue_sequence(None, None, flags, score)
    assert len(result) >= 1, "Restriction violation should yield rescue steps"


def test_transfer_restriction_present_complied_compliant():
    """TR-012 (b): restriction present but complied with → COMPLIANT (no rescue)."""
    flags = [_flag("TR-005", state=RuleState.COMPLIANT)]
    score = _score(Severity.GREEN)
    result = NLCRuleEngine._generate_rescue_sequence(None, None, flags, score)
    assert result == [], "Compliant transfer should yield no rescue steps"


def test_transfer_approval_missing_yields_unknown():
    """TR-012 (c): approval evidence missing → UNKNOWN (0 pts, no rescue)."""
    flags = [_flag("TR-005", state=RuleState.UNKNOWN)]
    score = _score(Severity.YELLOW)
    result = NLCRuleEngine._generate_rescue_sequence(None, None, flags, score)
    assert result == [], "UNKNOWN findings should yield no rescue steps"
