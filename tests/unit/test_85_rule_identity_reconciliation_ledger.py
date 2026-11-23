"""Integrity tests for the 85-row source/production reconciliation ledger."""
import json
from pathlib import Path

from scripts.seed_rules import ILRMF_RULES

ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / "docs" / "legal" / "85_rule_identity_definition_reconciliation_2026-11-23.json"


def _stable(value):
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


def test_reconciliation_ledger_covers_exactly_the_85_current_engine_ids():
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    expected = {rule["rule_id"] for rule in ILRMF_RULES}
    rows = ledger["rules"]
    actual = [row["rule_id"] for row in rows]

    assert len(rows) == 85
    assert len(set(actual)) == 85
    assert set(actual) == expected
    assert ledger["summary"]["rows"] == 85
    assert ledger["sources"]["current_main_commit"] == "7fa78ce19d501f2991aed7d25d7572d6a4996cd5"


def test_ledger_preserves_each_source_and_production_definition_without_auto_resolution():
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    seed = {rule["rule_id"]: rule for rule in ILRMF_RULES}

    for row in ledger["rules"]:
        rule_id = row["rule_id"]
        assert _stable(row["canonical_source_definition"]) == _stable(seed[rule_id])
        assert row["production_legal_rules_definition"]["rule_id"] == rule_id
        assert row["identity_resolution"] == "UNRESOLVED_PENDING_INDIVIDUAL_REVIEW"
        assert row["historical_finding_attribution"] == "UNATTRIBUTED_PENDING_RECORD_LEVEL_REVIEW"
        assert row["legal_revision"] == "NOT_CREATED_SOURCE_AND_EFFECTIVE_DATE_REVIEW_REQUIRED"


def test_inc001_and_inc002_are_separately_preserved_as_legacy_identity_cases():
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    inc001 = next(row for row in ledger["rules"] if row["rule_id"] == "INC-001")
    legacy = ledger["additional_legacy_identities"]

    assert "INC-001" in inc001["definition_differences"]
    assert len(legacy) == 1
    assert legacy[0]["rule_id"] == "INC-002"
    assert legacy[0]["identity_resolution"] == "QUARANTINED_LEGACY_IDENTITY_REQUIRES_RECORD_LEVEL_REVIEW"
    assert "INC-002" not in {rule["rule_id"] for rule in ILRMF_RULES}
