"""Regression contracts for active rule evaluation and legacy identity separation."""

from app.rule_engine.engine import (
    CORE_REGISTERS,
    REQUIRED_REGISTERS,
    LEGAL_SCORE_RELEASED,
    PRODUCT_SCORING_RULE_IDS,
)
from canonical_architecture.evidence_model import EVIDENCE_REGISTRY


ACTIVE_EVALUATION_RULE_IDS = {
    "DIR-001",
    "AGM-001",
    "BOD-001",
    "AUD-001",
    "DIR-006",
}


def test_requested_rules_remain_product_scoring_enabled():
    assert LEGAL_SCORE_RELEASED is False  # statutory scoring remains paused pending complete independent legal verification
    assert ACTIVE_EVALUATION_RULE_IDS <= PRODUCT_SCORING_RULE_IDS


def test_legacy_rule_ids_are_preserved():
    assert "INC-001" in EVIDENCE_REGISTRY
    assert "REG-002" in EVIDENCE_REGISTRY


def test_reg002_is_limited_to_internal_records():
    assert set(CORE_REGISTERS) == {"members", "charges", "minutes_agm"}
    assert "directors" not in REQUIRED_REGISTERS
    mapping = EVIDENCE_REGISTRY["REG-002"]
    assert mapping.source_section == "S34/S89/S174"
    assert "REGISTER_OF_MEMBERS_ENTRY" in mapping.primary_evidence
    assert "REGISTER_OF_CHARGES_ENTRY" in mapping.primary_evidence
    assert "AGM_MINUTES_SIGNED_BY_CHAIRMAN" in mapping.primary_evidence
    assert "FORM_XII_DIRECTOR_CHANGE" not in mapping.primary_evidence
    assert "RJSC_FILING_ACKNOWLEDGEMENT" not in mapping.primary_evidence


def test_dir001_owns_form_xii_rjsc_filing_evidence():
    mapping = EVIDENCE_REGISTRY["DIR-001"]
    assert mapping.source_section == "S115"
    assert "FORM_XII_DIRECTOR_CHANGE" in mapping.primary_evidence
    assert "RJSC_FILING_ACKNOWLEDGEMENT" in mapping.primary_evidence



def test_compliance_summary_contract_exposes_immutable_evaluation_identity():
    from app.api.companies import ComplianceSummaryResponse

    fields = ComplianceSummaryResponse.model_fields
    assert {
        "evaluation_run_id",
        "evaluation_hash",
        "evaluation_run_status",
        "evaluation_calculated_at",
        "engine_version",
        "ilrmf_version",
        "scoring_spec_version",
    } <= set(fields)

    response = ComplianceSummaryResponse(
        company_id="company-1",
        company_name="Example Ltd",
        current_score=82,
        pre_override_score=82,
        risk_band="GREEN",
        active_flags=0,
        black_flags=0,
        red_flags=0,
        yellow_flags=0,
        last_evaluated_at="2026-11-12T00:00:00+00:00",
        evaluation_triggered=True,
        evaluation_run_id="run-1",
        evaluation_hash="a" * 64,
        evaluation_run_status="COMPLETED",
        evaluation_calculated_at="2026-11-12T00:00:00+00:00",
        engine_version="2.2",
        ilrmf_version="2.2",
        scoring_spec_version="2.1",
    )
    payload = response.model_dump()
    assert payload["evaluation_run_id"] == "run-1"
    assert payload["evaluation_hash"] == "a" * 64
    assert payload["evaluation_run_status"] == "COMPLETED"



def test_latest_evaluation_run_lookup_is_company_scoped_and_ordered():
    import asyncio
    import uuid
    from types import SimpleNamespace

    from app.services.compliance_service import ComplianceService

    company_id = uuid.uuid4()
    expected = SimpleNamespace(id=uuid.uuid4(), company_id=company_id)

    class Result:
        def scalar_one_or_none(self):
            return expected

    class FakeSession:
        async def execute(self, statement):
            compiled = str(statement)
            assert "compliance_evaluation_runs.company_id" in compiled
            assert "ORDER BY compliance_evaluation_runs.calculated_at DESC" in compiled
            assert "LIMIT" in compiled
            return Result()

    actual = asyncio.run(ComplianceService(FakeSession()).get_latest_evaluation_run(company_id))
    assert actual is expected
