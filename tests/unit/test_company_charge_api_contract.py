from pydantic import ValidationError
import pytest

from app.api.companies import CompanyChargeCreateRequest, CompanyChargeVerificationRequest


def test_charge_creation_rejects_client_supplied_verification_metadata():
    with pytest.raises(ValidationError):
        CompanyChargeCreateRequest.model_validate({
            "creation_date": "2025-01-10",
            "charge_type": "MORTGAGE",
            "amount_bdt": "100000.00",
            "charge_holder": "Example Bank",
            "creation_date_verified": True,
            "creation_date_evidence_ref": "client-asserted",
        })


def test_charge_verification_rejects_client_supplied_reviewer_identity():
    with pytest.raises(ValidationError):
        CompanyChargeVerificationRequest.model_validate({
            "creation_date_verified": True,
            "creation_date_evidence_ref": "doc://verified-charge",
            "creation_date_verified_by": "00000000-0000-0000-0000-000000000001",
        })


def test_charge_verification_requires_non_null_boolean_when_flag_is_supplied():
    with pytest.raises(ValidationError):
        CompanyChargeVerificationRequest.model_validate({
            "creation_date_verified": None,
        })
