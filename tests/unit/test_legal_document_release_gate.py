import pytest
from fastapi import HTTPException

from app.api.documents import _require_document_legal_release
from app.models.enums import DocumentType


def test_unvalidated_ai_rescue_due_diligence_and_notice_cannot_be_released(monkeypatch):
    import app.rule_engine.engine as engine

    monkeypatch.setattr(engine, "LEGAL_SCORE_RELEASED", False)
    for document_type in (
        DocumentType.RESCUE_PLAN,
        DocumentType.DUE_DILIGENCE,
        DocumentType.STATUTORY_NOTICE,
    ):
        with pytest.raises(HTTPException) as exc:
            _require_document_legal_release(document_type)
        assert exc.value.status_code == 503


def test_non_scoring_corporate_document_types_remain_subject_to_human_approval(monkeypatch):
    import app.rule_engine.engine as engine

    monkeypatch.setattr(engine, "LEGAL_SCORE_RELEASED", False)
    for document_type in (
        DocumentType.AGM_MINUTES,
        DocumentType.BOARD_RESOLUTION,
        DocumentType.ANNUAL_RETURN,
    ):
        _require_document_legal_release(document_type)
