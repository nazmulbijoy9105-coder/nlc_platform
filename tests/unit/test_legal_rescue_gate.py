"""Rescue workflow must stay blocked while legal scoring is unreleased."""

import pytest
from fastapi import HTTPException

import app.rule_engine.engine as engine_module
from app.api.rescue import _require_legal_release


def test_rescue_workflow_is_blocked_without_independent_legal_release(monkeypatch):
    monkeypatch.setattr(engine_module, "LEGAL_SCORE_RELEASED", False)
    with pytest.raises(HTTPException) as exc:
        _require_legal_release()
    assert exc.value.status_code == 503
    assert "independent counsel approval" in exc.value.detail


def test_rescue_workflow_gate_opens_only_when_release_flag_and_verified_rules_exist(monkeypatch):
    monkeypatch.setattr(engine_module, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(engine_module, "VERIFIED_RULE_IDS", frozenset({"AGM-001"}))
    _require_legal_release()


def test_rescue_service_requires_released_rule_findings_and_rule_linked_steps(monkeypatch):
    from types import SimpleNamespace

    from app.services.rescue_service import validate_rescue_engine_output

    monkeypatch.setattr(engine_module, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(engine_module, "VERIFIED_RULE_IDS", frozenset({"AGM-001"}))
    flag = SimpleNamespace(
        rule_id="AGM-001",
        resolved=False,
        conditional_applies=True,
        state="NON_COMPLIANT",
        eval_state="VIOLATION",
        severity="RED",
        score_impact=5,
    )
    output = SimpleNamespace(
        company_id="company-1",
        score_breakdown=SimpleNamespace(risk_band="RED", final_score=40),
        flags=[flag],
        rescue_sequence=[{"title": "Remediate AGM", "related_rules": ["AGM-001"]}],
    )
    assert validate_rescue_engine_output(output) == frozenset({"AGM-001"})


def test_rescue_service_rejects_unknown_or_unapproved_rule_links(monkeypatch):
    from types import SimpleNamespace

    from app.services.rescue_service import validate_rescue_engine_output

    monkeypatch.setattr(engine_module, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(engine_module, "VERIFIED_RULE_IDS", frozenset({"AGM-001"}))
    unknown_flag = SimpleNamespace(
        rule_id="AGM-001",
        resolved=False,
        conditional_applies=True,
        state="UNKNOWN",
        eval_state="UNKNOWN",
        score_impact=0,
    )
    output = SimpleNamespace(
        company_id="company-1",
        score_breakdown=SimpleNamespace(risk_band="BLACK", final_score=10),
        flags=[unknown_flag],
        rescue_sequence=[{"title": "Remediate", "related_rules": ["AGM-001"]}],
    )
    with pytest.raises(PermissionError):
        validate_rescue_engine_output(output)


def test_rescue_service_rejects_unlinked_steps_and_non_red_black_risk(monkeypatch):
    from types import SimpleNamespace

    from app.services.rescue_service import validate_rescue_engine_output

    monkeypatch.setattr(engine_module, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(engine_module, "VERIFIED_RULE_IDS", frozenset({"AGM-001"}))
    flag = SimpleNamespace(
        rule_id="AGM-001",
        resolved=False,
        conditional_applies=True,
        state="NON_COMPLIANT",
        eval_state="VIOLATION",
        score_impact=5,
    )
    with pytest.raises(ValueError):
        validate_rescue_engine_output(SimpleNamespace(
            company_id="company-1",
            score_breakdown=SimpleNamespace(risk_band="YELLOW", final_score=80),
            flags=[flag],
            rescue_sequence=[{"title": "Remediate", "related_rules": ["AGM-001"]}],
        ))
    with pytest.raises(ValueError):
        validate_rescue_engine_output(SimpleNamespace(
            company_id="company-1",
            score_breakdown=SimpleNamespace(risk_band="RED", final_score=40),
            flags=[flag],
            rescue_sequence=[{"title": "Unlinked remediation"}],
        ))


def test_rescue_service_rejects_cross_tenant_engine_output(monkeypatch):
    from types import SimpleNamespace

    from app.services.rescue_service import validate_rescue_engine_output

    monkeypatch.setattr(engine_module, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(engine_module, "VERIFIED_RULE_IDS", frozenset({"AGM-001"}))
    output = SimpleNamespace(
        company_id="company-A",
        score_breakdown=SimpleNamespace(risk_band="RED", final_score=40),
        flags=[],
        rescue_sequence=[{"title": "Remediate", "related_rules": ["AGM-001"]}],
    )
    with pytest.raises(PermissionError):
        validate_rescue_engine_output(output, expected_company_id="company-B")



def test_rescue_service_rejects_missing_tenant_identity(monkeypatch):
    from types import SimpleNamespace

    from app.services.rescue_service import validate_rescue_engine_output

    monkeypatch.setattr(engine_module, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(engine_module, "VERIFIED_RULE_IDS", frozenset({"AGM-001"}))
    output = SimpleNamespace(
        score_breakdown=SimpleNamespace(risk_band="RED", final_score=40),
        flags=[],
        rescue_sequence=[{"title": "Remediate", "related_rules": ["AGM-001"]}],
    )
    with pytest.raises(PermissionError, match="tenant/company identity"):
        validate_rescue_engine_output(output)


def test_rescue_service_rejects_ambiguous_duplicate_findings(monkeypatch):
    from types import SimpleNamespace

    from app.services.rescue_service import validate_rescue_engine_output

    monkeypatch.setattr(engine_module, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(engine_module, "VERIFIED_RULE_IDS", frozenset({"AGM-001"}))
    flag = SimpleNamespace(
        rule_id="AGM-001",
        resolved=False,
        conditional_applies=True,
        state="NON_COMPLIANT",
        eval_state="VIOLATION",
        severity="RED",
        score_impact=5,
    )
    output = SimpleNamespace(
        company_id="company-1",
        score_breakdown=SimpleNamespace(risk_band="RED", final_score=40),
        flags=[flag, flag],
        rescue_sequence=[{"title": "Remediate", "related_rules": ["AGM-001"]}],
    )
    with pytest.raises(PermissionError, match="unique"):
        validate_rescue_engine_output(output, expected_company_id="company-1")
