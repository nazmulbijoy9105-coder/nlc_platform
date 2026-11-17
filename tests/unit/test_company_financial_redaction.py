from datetime import date
from types import SimpleNamespace
import uuid

from app.api.companies import _company_to_response
from app.models.enums import RevenueTier


def _valid_evaluation_run(company, *, score, risk_band, calculated_at):
    from app.compliance.evaluation_integrity import calculate_evaluation_score_hash
    from app.compliance.rule_outcome_ledger import hash_rule_outcomes_snapshot
    from app.rule_engine.engine import RULE_ENGINE_VERSION, SCORING_SPEC_VERSION

    outcomes = [{
        "rule_id": "AGM-001",
        "assessment_source": "NO_FINDING_EMITTED_NOT_PROOF_OF_COMPLIANCE",
        "findings": [],
    }]
    flags_snapshot = []
    fact_provenance_snapshot = []
    score_breakdown_snapshot = {
        "scoring_spec_version": SCORING_SPEC_VERSION,
        "score_reconciles": True,
        "final_score": score,
    }
    rule_outcomes_hash = hash_rule_outcomes_snapshot(outcomes)
    score_hash = calculate_evaluation_score_hash(
        previous_hash=None,
        company_id=company.id,
        score=score,
        risk_band=risk_band,
        calculated_at=calculated_at,
        engine_version=RULE_ENGINE_VERSION,
        trigger_source="TEST",
        flags_snapshot=flags_snapshot,
        fact_provenance_snapshot=fact_provenance_snapshot,
        score_breakdown_snapshot=score_breakdown_snapshot,
        rule_outcomes_hash=rule_outcomes_hash,
        rule_outcomes_snapshot=outcomes,
    )
    return SimpleNamespace(
        company_id=company.id,
        evaluation_status="COMPLETED",
        score=score,
        risk_band=risk_band,
        calculated_at=calculated_at,
        engine_version=RULE_ENGINE_VERSION,
        trigger_source="TEST",
        previous_hash=None,
        score_hash=score_hash,
        flags_snapshot=flags_snapshot,
        fact_provenance_snapshot=fact_provenance_snapshot,
        score_breakdown_snapshot=score_breakdown_snapshot,
        rule_outcomes_snapshot=outcomes,
        rule_outcomes_hash=rule_outcomes_hash,
        rule_catalogue_count=1,
    )


def _company():
    return SimpleNamespace(
        id=uuid.uuid4(),
        company_name="Financial Privacy Test Ltd",
        registration_number="C-PRIV-001",
        incorporation_date=date(2020, 1, 1),
        current_risk_band=None,
        current_compliance_score=None,
        financial_year_end=date(2025, 12, 31),
        registered_address="Dhaka",
        revenue_tier=RevenueTier.STRUCTURED_REGULARIZATION,
        is_fdi_registered=False,
        is_dormant=False,
        created_at=None,
        compliance_flags=[],
        directors=[],
        is_manufacturing=False,
        tax_return_filed_for_current_fy=True,
        advance_tax_q1_paid=True,
        advance_tax_q2_paid=False,
        advance_tax_q3_paid=True,
        advance_tax_q4_paid=False,
        penalty_notices_received=2,
        penalty_notices_resolved=1,
    )


def test_company_response_redacts_financial_fields_without_permission():
    response = _company_to_response(_company(), can_view_financials=False)

    assert response.revenue_tier is None
    assert response.tax_return_filed_for_current_fy is None
    assert response.advance_tax_q1_paid is None
    assert response.advance_tax_q2_paid is None
    assert response.advance_tax_q3_paid is None
    assert response.advance_tax_q4_paid is None
    assert response.penalty_notices_received is None
    assert response.penalty_notices_resolved is None
    assert response.registered_address == "Dhaka"
    assert response.company_type is None


def test_company_response_includes_financial_fields_with_permission():
    response = _company_to_response(_company(), can_view_financials=True)

    assert response.revenue_tier == RevenueTier.STRUCTURED_REGULARIZATION.value
    assert response.tax_return_filed_for_current_fy is True
    assert response.advance_tax_q1_paid is True
    assert response.penalty_notices_received == 2


def test_company_response_withholds_cached_black_band_when_latest_run_is_pending(monkeypatch):
    from datetime import datetime, timezone

    from app.api import companies as companies_api
    from app.models.enums import RiskBand
    from app.rule_engine.engine import RULE_ENGINE_VERSION, SCORING_SPEC_VERSION

    monkeypatch.setattr(companies_api, "_legal_score_is_released", lambda: True)
    company = _company()
    now = datetime.now(timezone.utc)
    company.current_risk_band = RiskBand.BLACK
    company.current_compliance_score = 10
    company.last_evaluated_at = now
    company.updated_at = now
    pending_run = SimpleNamespace(
        evaluation_status="PENDING",
        score=None,
        risk_band=RiskBand.NOT_EVALUATED,
        calculated_at=now,
    )

    response = _company_to_response(company, evaluation_run=pending_run)

    assert response.band == "NOT_EVALUATED"
    assert response.compliance_score is None
    assert response.evaluation_status == "PENDING"
    assert response.black_flags == 0


def test_company_response_marks_cached_score_stale_after_profile_change(monkeypatch):
    from datetime import datetime, timedelta, timezone

    from app.api import companies as companies_api
    from app.models.enums import RiskBand

    monkeypatch.setattr(companies_api, "_legal_score_is_released", lambda: True)
    company = _company()
    evaluated_at = datetime.now(timezone.utc)
    company.current_risk_band = RiskBand.RED
    company.current_compliance_score = 20
    company.last_evaluated_at = evaluated_at
    company.updated_at = evaluated_at + timedelta(seconds=1)
    completed_run = _valid_evaluation_run(
        company, score=20, risk_band=RiskBand.RED, calculated_at=evaluated_at
    )

    response = _company_to_response(company, evaluation_run=completed_run)

    assert response.band == "NOT_EVALUATED"
    assert response.compliance_score is None
    assert response.evaluation_status == "STALE"


def test_company_response_releases_only_matching_completed_evaluation(monkeypatch):
    from datetime import datetime, timezone

    from app.api import companies as companies_api
    from app.models.enums import RiskBand

    monkeypatch.setattr(companies_api, "_legal_score_is_released", lambda: True)
    company = _company()
    now = datetime.now(timezone.utc)
    company.current_risk_band = RiskBand.GREEN
    company.current_compliance_score = 85
    company.last_evaluated_at = now
    company.updated_at = now
    completed_run = _valid_evaluation_run(
        company, score=85, risk_band=RiskBand.GREEN, calculated_at=now
    )

    response = _company_to_response(company, evaluation_run=completed_run)

    assert response.band == "GREEN"
    assert response.compliance_score == 85
    assert response.evaluation_status == "EVALUATED"
