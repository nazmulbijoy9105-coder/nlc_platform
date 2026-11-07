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


def test_rescue_workflow_gate_opens_only_when_release_flag_is_true(monkeypatch):
    monkeypatch.setattr(engine_module, "LEGAL_SCORE_RELEASED", True)
    _require_legal_release()
