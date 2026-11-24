"""Evaluation results expose rescue workflows independently of score release."""

import ast
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from canonical_architecture.statutory_rules import STATUTORY_RULE_REGISTRY

from app.rule_engine import CompanyProfile
from app.services.compliance_service import ComplianceService, RescueWorkflowOutcome


def _catalogue_rows():
    return [
        SimpleNamespace(
            rule_id=rule_id, statutory_basis=rule.law, is_active=True,
            rule_version="test-v1", verification_status="UNVERIFIED",
        )
        for rule_id, rule in STATUTORY_RULE_REGISTRY.items()
    ]


@pytest.fixture
def evaluation(monkeypatch):
    company_id = uuid4()
    db = MagicMock()
    facts_result = MagicMock()
    facts_result.scalars.return_value.all.return_value = []
    catalogue_result = MagicMock()
    catalogue_result.scalars.return_value.all.return_value = _catalogue_rows()
    db.execute = AsyncMock(side_effect=[MagicMock(), facts_result, catalogue_result])
    build_profile = AsyncMock(return_value={
        "company_id": str(company_id), "company_name": "Rescue Company",
    })

    class FakeCompanyService:
        def __init__(self, session):
            assert session is db
            self.build_company_profile = build_profile

    monkeypatch.setattr("app.services.company_service.CompanyService", FakeCompanyService)
    breakdown = SimpleNamespace(
        risk_band="GREEN", final_score=100, raw_total=100, category_deductions={},
        exposure_band="LOW", coverage={}, active_flag_count=0, black_flag_count=0,
        red_flag_count=0, yellow_flag_count=0, override_applied=False, override_reason=None,
        **{f"{category}_score": 0 for category in (
            "agm", "audit", "return", "director", "shareholding", "capital", "office",
            "register", "tax", "bankruptcy", "labour", "bsec", "fx", "escalation",
        )},
    )
    sequence = [{"title": "Remediate AGM", "related_rules": ["AGM-001"]}]
    output = SimpleNamespace(
        flags=[], rescue_sequence=sequence, score_breakdown=breakdown,
        engine_version="test-engine", ilrmf_version="test-ilrmf",
    )
    engine = SimpleNamespace(evaluate=MagicMock(return_value=output))
    run = SimpleNamespace(
        id=uuid4(), score_hash="h", evaluation_status="COMPLETED",
        calculated_at=datetime.now(UTC),
    )
    persist = AsyncMock(return_value=(run, RescueWorkflowOutcome("PLAN_CREATED")))
    monkeypatch.setattr(ComplianceService, "_persist_evaluation", persist)
    return SimpleNamespace(
        service=ComplianceService(db), company_id=company_id, engine=engine,
        persist=persist, run=run, sequence=sequence, build_profile=build_profile,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("outcome", [
    RescueWorkflowOutcome("PLAN_CREATED"),
    RescueWorkflowOutcome("NOT_ENTITLED"),
    RescueWorkflowOutcome("BLOCKED_CATALOGUE_CONFLICTS", "note"),
    RescueWorkflowOutcome("NOT_APPLICABLE"),
])
async def test_closed_score_release_exposes_rescue_workflow(evaluation, monkeypatch, outcome):
    monkeypatch.setattr("app.rule_engine.engine.LEGAL_SCORE_RELEASED", False)
    evaluation.persist.return_value = (evaluation.run, outcome)

    result = await evaluation.service.evaluate_company(
        evaluation.company_id, rule_engine=evaluation.engine,
    )

    assert result["score"] is None
    assert result["rescue_required"] is False
    assert result["rescue_sequence"] == evaluation.sequence
    assert result["rescue_workflow_status"] == outcome.status
    assert result["rescue_workflow_note"] == outcome.note
    evaluation.build_profile.assert_awaited_once_with(evaluation.company_id, refresh=True)
    evaluation.engine.evaluate.assert_called_once()
    assert isinstance(evaluation.engine.evaluate.call_args.args[0], CompanyProfile)
    evaluation.persist.assert_awaited_once()


@pytest.mark.asyncio
async def test_open_score_release_also_exposes_rescue_sequence(evaluation, monkeypatch):
    monkeypatch.setattr("app.rule_engine.engine.LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(
        "app.rule_engine.engine.PRODUCT_SCORING_RULE_IDS", frozenset({"AGM-001"}),
    )

    result = await evaluation.service.evaluate_company(
        evaluation.company_id, rule_engine=evaluation.engine,
    )

    assert result["legal_evaluation_status"] == "RELEASED"
    assert result["score"] == 100
    assert result["rescue_sequence"] == evaluation.sequence
    assert result["rescue_workflow_status"] == "PLAN_CREATED"
    assert result["rescue_workflow_note"] is None


def test_persisted_rescue_outcome_and_public_sequence_contract():
    source = Path(__file__).resolve().parents[2] / "app/services/compliance_service.py"
    tree = ast.parse(source.read_text())
    service = next(node for node in tree.body if isinstance(node, ast.ClassDef)
                   and node.name == "ComplianceService")
    methods = {node.name: node for node in service.body
               if isinstance(node, ast.AsyncFunctionDef)}
    persist = methods["_persist_evaluation"]
    assert isinstance(persist.body[-1], ast.Return)
    assert isinstance(persist.body[-1].value, ast.Tuple)
    assert [ast.unparse(item) for item in persist.body[-1].value.elts] == [
        "evaluation_run", "rescue_workflow",
    ]
    assignments = [node for node in ast.walk(persist) if isinstance(node, ast.Assign)]
    assert any(
        any(isinstance(target, ast.Name) and target.id == "rescue_workflow"
            for target in node.targets)
        and isinstance(node.value, ast.Await)
        and isinstance(node.value.value, ast.Call)
        and isinstance(node.value.value.func, ast.Attribute)
        and isinstance(node.value.value.func.value, ast.Name)
        and node.value.value.func.value.id == "self"
        and node.value.value.func.attr == "_start_rescue_workflow"
        for node in assignments
    )
    assert any(
        any(isinstance(target, ast.Subscript)
            and isinstance(target.value, ast.Name) and target.value.id == "company_svc_update"
            and isinstance(target.slice, ast.Constant)
            and target.slice.value == "rescue_generation_error" for target in node.targets)
        and isinstance(node.value, ast.Attribute)
        and isinstance(node.value.value, ast.Name)
        and node.value.value.id == "rescue_workflow" and node.value.attr == "note"
        for node in assignments
    )
    returned_dicts = [node.value for node in ast.walk(methods["evaluate_company"])
                      if isinstance(node, ast.Return) and isinstance(node.value, ast.Dict)]
    assert any(
        isinstance(key, ast.Constant) and key.value == "rescue_sequence"
        and ast.unparse(value) == "list(output.rescue_sequence or [])"
        for returned in returned_dicts
        for key, value in zip(returned.keys, returned.values, strict=True)
    )
