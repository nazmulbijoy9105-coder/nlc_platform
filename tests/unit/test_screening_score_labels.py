"""All score-bearing company API contracts identify outputs as screening only."""

from app.api.companies import (
    CompanyResponse,
    ComplianceSummaryResponse,
    FlagResponse,
    ScoreHistoryEntry,
)


def test_company_score_api_contracts_are_screening_only():
    for schema in (CompanyResponse, ComplianceSummaryResponse, FlagResponse, ScoreHistoryEntry):
        assert schema.model_fields["screening_only"].default is True
        assert schema.model_fields["legal_advice"].default is False
        assert "not legal advice" in schema.model_fields["disclaimer"].default.lower()


def test_compliance_score_contract_names_the_output_as_screening():
    assert ComplianceSummaryResponse.model_fields["score_label"].default == "Screening score"
    assert (
        ComplianceSummaryResponse.model_fields["release_scope"].default
        == "SCREENED_PRIVATE_BETA"
    )
