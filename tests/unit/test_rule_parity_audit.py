"""Regression tests for strict canonical rule parity auditing."""
import importlib.util
import sys
import pytest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[2] / "tools" / "audit_rule_parity.py"
SPEC = importlib.util.spec_from_file_location("nlc_rule_parity_audit", SCRIPT)
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)



def test_engine_parser_includes_tuple_declared_rule_ids():
    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr(AUDIT.Path, "read_text", lambda self, **kwargs: """
def rules():
    candidates = (
        ("BSEC-001", "FLAG", None, "description"),
        ("BSEC-002", "FLAG2", None, "description"),
    )
    return candidates
""")
        assert AUDIT.get_engine_rules() == {"BSEC-001", "BSEC-002"}
    finally:
        monkeypatch.undo()


def test_static_mode_compares_engine_and_seed_without_live_sources(monkeypatch):
    monkeypatch.setattr(AUDIT, "get_engine_rules", lambda: {"AGM-001", "INC-001"})
    monkeypatch.setattr(AUDIT, "get_seed_rule_definitions", lambda: {"AGM-001": {"rule_id": "AGM-001"}, "INC-001": {"rule_id": "INC-001"}})
    monkeypatch.setattr(AUDIT, "get_db_rules", lambda: (_ for _ in ()).throw(AssertionError("DB must be skipped")))
    monkeypatch.setattr(AUDIT, "get_api_rules", lambda: (_ for _ in ()).throw(AssertionError("API must be skipped")))
    monkeypatch.setattr(sys, "argv", ["audit_rule_parity.py", "--no-db", "--no-api"])

    assert AUDIT.main() == 0


def test_unavailable_requested_live_api_fails_audit(monkeypatch):
    monkeypatch.setattr(AUDIT, "get_engine_rules", lambda: {"AGM-001"})
    monkeypatch.setattr(AUDIT, "get_seed_rule_definitions", lambda: {"AGM-001": {"rule_id": "AGM-001"}})
    monkeypatch.setattr(AUDIT, "get_api_rules", lambda: None)
    monkeypatch.setattr(sys, "argv", ["audit_rule_parity.py", "--no-db"])

    assert AUDIT.main() == 2


def test_engine_seed_rule_mismatch_fails_static_audit(monkeypatch):
    monkeypatch.setattr(AUDIT, "get_engine_rules", lambda: {"AGM-001", "INC-001"})
    monkeypatch.setattr(AUDIT, "get_seed_rules", lambda: {"AGM-001"})
    monkeypatch.setattr(sys, "argv", ["audit_rule_parity.py", "--no-db", "--no-api"])

    assert AUDIT.main() == 1


def test_seed_definition_parser_loads_full_canonical_records():
    definitions = AUDIT.get_seed_rule_definitions()

    assert len(definitions) == 85
    assert len(set(definitions)) == 85
    assert all(
        {"rule_id", "rule_name", "rule_type", "statutory_basis", "description",
         "rule_condition", "default_severity", "score_impact", "revenue_tier",
         "is_black_override"} <= set(definition)
        for definition in definitions.values()
    )


def test_database_metadata_comparison_checks_full_fields_and_legacy_row():
    seed = {
        "AGM-001": {
            "rule_id": "AGM-001",
            "rule_name": "AGM test",
            "rule_type": "DEADLINE",
            "statutory_basis": "Section 81",
            "description": "Test rule",
            "rule_condition": {"trigger": "due"},
            "default_severity": "NOT_EVALUATED",
            "score_impact": 0,
            "revenue_tier": "COMPLIANCE_PACKAGE",
            "is_black_override": False,
        }
    }
    inventory = {
        "AGM-001": {
            **seed["AGM-001"],
            "rule_version": "1.0",
            "is_active": True,
            "verification_status": "PENDING",
        },
        "INC-002": {
            "rule_id": "INC-002",
            "rule_name": "Legacy inactive",
            "rule_type": "DEADLINE",
            "statutory_basis": "Historical",
            "description": "Historical row",
            "rule_condition": None,
            "default_severity": "NOT_EVALUATED",
            "score_impact": 0,
            "revenue_tier": "COMPLIANCE_PACKAGE",
            "is_black_override": False,
            "rule_version": "legacy",
            "is_active": False,
            "verification_status": "PENDING",
        },
    }

    result = AUDIT.compare_database_metadata(seed, inventory)

    assert result["mismatches"] == []
    assert result["active_count"] == 1
    assert result["inactive_ids"] == ["INC-002"]
    assert result["seed_manifest_sha256"] == result["database_active_manifest_sha256"]


def test_database_metadata_comparison_detects_statutory_basis_drift():
    seed = {
        "AGM-001": {
            "rule_id": "AGM-001",
            "rule_name": "AGM test",
            "rule_type": "DEADLINE",
            "statutory_basis": "Section 81",
            "description": "Test rule",
            "rule_condition": None,
            "default_severity": "NOT_EVALUATED",
            "score_impact": 0,
            "revenue_tier": "COMPLIANCE_PACKAGE",
            "is_black_override": False,
        }
    }
    database = {
        "AGM-001": {
            **seed["AGM-001"],
            "statutory_basis": "Section 82",
            "is_active": True,
            "verification_status": "PENDING",
        },
        "INC-002": {
            "default_severity": "NOT_EVALUATED",
            "score_impact": 0,
            "is_black_override": False,
            "is_active": False,
        },
    }

    result = AUDIT.compare_database_metadata(seed, database)

    assert any(
        item["rule_id"] == "AGM-001" and item["field"] == "statutory_basis"
        for item in result["mismatches"]
    )


def test_manifest_hash_is_order_independent():
    assert AUDIT._sha256({"a": 1, "b": 2}) == AUDIT._sha256({"b": 2, "a": 1})
