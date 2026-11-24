"""Fail-closed registry-integrity gate for rescue authorization.

The production statutory registry is the only source of valid rule ids:
scope parity must hold exactly and every rule id referenced for
authorization must be a valid production id. A paused release switch is a
distinct condition and keeps confirmed-step authorization per the approved
contract (see test_rescue_sequence_parity.py).
"""

from types import SimpleNamespace

import app.rule_engine.engine as engine_module
from app.rule_engine.engine import (
    ComplianceFlag,
    NLCRuleEngine,
    RevenueTier,
    RuleState,
    Severity,
)


def _flag(rule_id):
    return ComplianceFlag(
        rule_id=rule_id,
        flag_code=f"{rule_id}_TEST",
        severity=Severity.RED,
        score_impact=1,
        revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
        description="test",
        statutory_basis="test",
        state=RuleState.NON_COMPLIANT,
        resolved=False,
        conditional_applies=True,
        detail={},
    )


def _steps(*rule_ids):
    return [{
        "title": "step",
        "description": "step",
        "related_rules": list(rule_ids),
        "priority": "HIGH",
        "rescue_id": "R-TEST",
    }]


def _dispositions(flags, steps):
    score = SimpleNamespace(risk_band=Severity.RED)
    return NLCRuleEngine._build_rescue_dispositions(flags, score, steps)


def _break_scope_parity(monkeypatch):
    def _raise(canonical_rule_ids):
        raise RuntimeError("RJSC scope identity parity failure (test)")

    monkeypatch.setattr(engine_module, "assert_rjsc_scope_parity", _raise)


def test_registry_parity_failure_blocks_confirmed_step_action(monkeypatch):
    _break_scope_parity(monkeypatch)
    finding = _flag("AGM-001")

    result = _dispositions([finding], _steps("AGM-001"))

    assert result[0]["disposition"] == "BLOCKED"
    assert result[0]["reason"] == "REGISTRY_INTEGRITY_FAILURE"


def test_paused_release_keeps_confirmed_step_authorized_when_registry_holds(
    monkeypatch,
):
    monkeypatch.setattr(engine_module, "LEGAL_SCORE_RELEASED", False)
    finding = _flag("AGM-001")

    result = _dispositions([finding], _steps("AGM-001"))

    assert result[0]["disposition"] == "ACTION_REQUIRED"
    assert result[0]["reason"] == "CONFIRMED_RESCUE_STEP"


def test_step_referencing_unknown_rule_id_blocks_authorization():
    finding = _flag("AGM-001")

    result = _dispositions([finding], _steps("AGM-001", "NOT-IN-REGISTRY"))

    assert result[0]["disposition"] == "BLOCKED"
    assert result[0]["reason"] == "REGISTRY_INTEGRITY_FAILURE"
