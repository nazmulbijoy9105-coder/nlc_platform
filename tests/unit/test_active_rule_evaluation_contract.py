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
    assert LEGAL_SCORE_RELEASED is True
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
