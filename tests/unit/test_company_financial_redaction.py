from datetime import date
from types import SimpleNamespace
import uuid

from app.api.companies import _company_to_response
from app.models.enums import RevenueTier


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
        revenue_tier=RevenueTier.MEDIUM,
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

    assert response.revenue_tier == RevenueTier.MEDIUM.value
    assert response.tax_return_filed_for_current_fy is True
    assert response.advance_tax_q1_paid is True
    assert response.penalty_notices_received == 2
