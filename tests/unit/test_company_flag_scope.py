from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.api.companies import _filter_rjsc_active_flags, _flag_to_response
from canonical_architecture.rjsc_scope import RJSC_OUT_OF_SCOPE_RULE_IDS


@pytest.mark.parametrize("rule_id", sorted(RJSC_OUT_OF_SCOPE_RULE_IDS))
def test_out_of_scope_active_flag_is_never_returned_by_rjsc_flags_api(rule_id):
    flag = SimpleNamespace(
        rule_id=rule_id,
        detail={},
        flag_status="ACTIVE",
        evaluation_state="VIOLATION",
    )
    assert _filter_rjsc_active_flags([flag], set()) == []


def test_unclassified_active_flag_is_never_returned_by_rjsc_flags_api():
    flag = SimpleNamespace(
        rule_id="UNKNOWN-999",
        detail={},
        flag_status="ACTIVE",
        evaluation_state="VIOLATION",
    )
    assert _filter_rjsc_active_flags([flag], set()) == []


def test_in_scope_identity_conflict_is_suppressed_from_active_flags_api():
    flag = SimpleNamespace(
        rule_id="AGM-001",
        detail={"rule_catalogue_binding": "STATUTORY_BASIS_MISMATCH"},
        flag_status="ACTIVE",
        evaluation_state="VIOLATION",
    )
    assert _filter_rjsc_active_flags([flag], set()) == []
    assert _filter_rjsc_active_flags([flag], {"AGM-001"}) == []


@pytest.mark.parametrize("rule_id", sorted(RJSC_OUT_OF_SCOPE_RULE_IDS))
def test_out_of_scope_flag_cannot_be_serialized_as_score_eligible(monkeypatch, rule_id):
    import app.api.companies as companies

    monkeypatch.setattr(companies, "_legal_score_is_released", lambda: True)
    monkeypatch.setattr(companies, "SCORE_DEDUCTION_RULE_IDS", frozenset({rule_id}))
    monkeypatch.setattr(companies, "VERIFIED_RULE_IDS", frozenset({rule_id}))
    monkeypatch.setattr(companies, "AUTHORIZED_BLACK_OVERRIDE_RULE_IDS", frozenset())
    flag = SimpleNamespace(
        id=uuid4(),
        rule_id=rule_id,
        evaluation_state="VIOLATION",
        flag_status="ACTIVE",
        detail={},
        severity="BLACK",
        score_impact=100,
        description="External tax finding",
        flag_code="TAX-001_TEST",
        is_black_override=True,
        triggered_date=datetime(2026, 11, 24, tzinfo=timezone.utc),
        resolved_date=None,
        resolution_notes=None,
    )
    response = _flag_to_response(flag)
    assert response.score_impact == 0
    assert response.severity == "NOT_EVALUATED"
    assert response.legal_review_status != "LEGALLY_VERIFIED"
    assert response.is_black_override is False



def test_company_summary_counts_only_active_rjsc_flags(monkeypatch):
    import app.api.companies as companies

    monkeypatch.setattr(companies, "_evaluation_run_is_current", lambda company, run: True)
    monkeypatch.setattr(companies, "_company_evaluation_status", lambda company, run: "EVALUATED")
    company = SimpleNamespace(
        id=uuid4(),
        company_name="Scope Test Ltd",
        registration_number="RJSC-TEST-001",
        incorporation_date=datetime(2020, 1, 1).date(),
        current_compliance_score=90,
        current_risk_band="RED",
        directors=[],
        compliance_flags=[
            SimpleNamespace(
                rule_id="AGM-001",
                flag_status="ACTIVE",
                severity="RED",
                detail={},
            ),
            SimpleNamespace(
                rule_id="TAX-001",
                flag_status="ACTIVE",
                severity="BLACK",
                detail={},
            ),
        ],
    )

    response = companies._company_to_response(company, evaluation_run=object())

    assert response.violation_count == 1
    assert response.active_flags == 1
    assert response.red_flags == 1
    assert response.black_flags == 0
    assert response.yellow_flags == 0
