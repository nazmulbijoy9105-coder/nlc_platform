"""Rescue authorization is independent of score publication and counsel allowlisting."""

import ast
from pathlib import Path

import pytest
from canonical_architecture.rjsc_scope import RJSC_OUT_OF_SCOPE_RULE_IDS
from fastapi import HTTPException

import app.rule_engine.engine as engine_module
from app.api.rescue import _require_commercial_engagement_release


def test_commercial_engagement_is_withheld_while_product_score_release_is_closed(monkeypatch):
    monkeypatch.setattr(engine_module, "legal_score_is_released", lambda: False)
    with pytest.raises(HTTPException) as exc:
        _require_commercial_engagement_release()
    assert exc.value.status_code == 503


def test_commercial_engagement_proceeds_when_product_score_release_is_open(monkeypatch):
    monkeypatch.setattr(engine_module, "legal_score_is_released", lambda: True)
    assert _require_commercial_engagement_release() is None


def test_only_commercial_engagement_endpoint_is_score_release_gated():
    source = (Path(__file__).resolve().parents[2] / "app/api/rescue.py").read_text()
    tree = ast.parse(source)
    gated_functions = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef))
        and node.name != "_require_commercial_engagement_release"
        and any(
            isinstance(child, ast.Call)
            and isinstance(child.func, ast.Name)
            and child.func.id == "_require_commercial_engagement_release"
            for child in ast.walk(node)
        )
    }
    assert gated_functions == {"create_engagement_from_rescue"}
    assert "_require_legal_release" not in source



def test_rescue_service_requires_released_rule_findings_and_rule_linked_steps(monkeypatch):
    from types import SimpleNamespace

    from app.services.rescue_service import validate_rescue_engine_output

    monkeypatch.setattr(engine_module, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(engine_module, "PRODUCT_SCORING_RULE_IDS", frozenset({"AGM-001"}))
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
    monkeypatch.setattr(engine_module, "PRODUCT_SCORING_RULE_IDS", frozenset({"AGM-001"}))
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
    monkeypatch.setattr(engine_module, "PRODUCT_SCORING_RULE_IDS", frozenset({"AGM-001"}))
    flag = SimpleNamespace(
        rule_id="AGM-001",
        resolved=False,
        conditional_applies=True,
        state="NON_COMPLIANT",
        eval_state="VIOLATION",
        score_impact=5,
    )
    with pytest.raises(ValueError, match="RED or BLACK"):
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
    monkeypatch.setattr(engine_module, "PRODUCT_SCORING_RULE_IDS", frozenset({"AGM-001"}))
    output = SimpleNamespace(
        company_id="company-A",
        score_breakdown=SimpleNamespace(risk_band="RED", final_score=40),
        flags=[],
        rescue_sequence=[{"title": "Remediate", "related_rules": ["AGM-001"]}],
    )
    with pytest.raises(PermissionError):
        validate_rescue_engine_output(output, expected_company_id="company-B")



def test_rescue_service_allows_absent_engine_company_id_when_no_mismatch_can_be_established(monkeypatch):
    from types import SimpleNamespace

    from app.services.rescue_service import validate_rescue_engine_output

    monkeypatch.setattr(engine_module, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(engine_module, "PRODUCT_SCORING_RULE_IDS", frozenset({"AGM-001"}))
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
        score_breakdown=SimpleNamespace(risk_band="RED", final_score=40),
        flags=[flag],
        rescue_sequence=[{"title": "Remediate", "related_rules": ["AGM-001"]}],
    )
    assert validate_rescue_engine_output(
        output, expected_company_id="company-1"
    ) == frozenset({"AGM-001"})


def test_rescue_service_rejects_ambiguous_duplicate_findings(monkeypatch):
    from types import SimpleNamespace

    from app.services.rescue_service import validate_rescue_engine_output

    monkeypatch.setattr(engine_module, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(engine_module, "PRODUCT_SCORING_RULE_IDS", frozenset({"AGM-001"}))
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



def test_rescue_service_rejects_finding_from_unreleased_rule_id(monkeypatch):
    from types import SimpleNamespace

    from app.services.rescue_service import validate_rescue_engine_output

    monkeypatch.setattr(engine_module, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(engine_module, "PRODUCT_SCORING_RULE_IDS", frozenset({"AGM-002"}))
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
        rescue_sequence=[{"title": "Remediate", "related_rules": ["AGM-001"]}],
    )
    with pytest.raises(PermissionError, match="released"):
        validate_rescue_engine_output(output, expected_company_id="company-1")



@pytest.mark.parametrize("rule_id", sorted(RJSC_OUT_OF_SCOPE_RULE_IDS))
def test_rescue_service_rejects_out_of_scope_rule_even_if_product_allowlisted(monkeypatch, rule_id):
    from types import SimpleNamespace

    from app.services.rescue_service import validate_rescue_engine_output

    monkeypatch.setattr(engine_module, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(
        engine_module, "PRODUCT_SCORING_RULE_IDS", frozenset({"AGM-001", rule_id})
    )
    tax_flag = SimpleNamespace(
        rule_id=rule_id,
        resolved=False,
        conditional_applies=True,
        state="NON_COMPLIANT",
        eval_state="VIOLATION",
        severity="BLACK",
        score_impact=100,
    )
    output = SimpleNamespace(
        company_id="company-1",
        score_breakdown=SimpleNamespace(risk_band="BLACK", final_score=0),
        flags=[tax_flag],
        rescue_sequence=[{"title": "Out-of-scope remediation", "related_rules": [rule_id]}],
    )
    with pytest.raises(PermissionError, match="out-of-scope"):
        validate_rescue_engine_output(output)



def test_rescue_service_accepts_unverified_rule_when_score_is_unreleased(monkeypatch):
    from types import SimpleNamespace

    from app.services.rescue_service import validate_rescue_engine_output

    monkeypatch.setattr(engine_module, "LEGAL_SCORE_RELEASED", False)
    monkeypatch.setattr(engine_module, "PRODUCT_SCORING_RULE_IDS", frozenset({"AGM-001"}))
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
        score_breakdown=SimpleNamespace(risk_band="NOT_EVALUATED", final_score=None),
        flags=[flag],
        rescue_sequence=[{"title": "Authorized action", "related_rules": ["AGM-001"]}],
    )
    assert validate_rescue_engine_output(output, expected_company_id="company-1") == frozenset({"AGM-001"})
