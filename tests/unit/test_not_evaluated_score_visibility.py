from types import SimpleNamespace
from uuid import uuid4

from app.api.companies import _company_to_response


def _company(score, band):
    return SimpleNamespace(
        id=uuid4(),
        company_name="NLC Test Company",
        registration_number="TEST-001",
        incorporation_date=None,
        current_compliance_score=score,
        current_risk_band=band,
        last_evaluated_at=None,
        directors=[],
        compliance_flags=[],
        financial_year_end=None,
    )


def test_not_evaluated_company_does_not_expose_placeholder_score():
    response = _company_to_response(_company(100, "NOT_EVALUATED"))

    assert response.band == "NOT_EVALUATED"
    assert response.compliance_score is None


def test_evaluated_company_retains_numeric_score():
    response = _company_to_response(_company(88, "GREEN"))

    assert response.band == "GREEN"
    assert response.compliance_score == 88
