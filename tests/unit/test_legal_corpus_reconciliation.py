"""Regression tests for seed uniqueness and statutory rule identity collisions."""
import ast
from collections import Counter
from pathlib import Path

from scripts.seed_rules import EXPECTED_RULE_COUNT, ILRMF_RULES

ROOT = Path(__file__).resolve().parents[2]


def test_seed_rule_ids_are_unique_and_match_expected_count():
    ids = [row["rule_id"] for row in ILRMF_RULES]
    duplicates = sorted(rule_id for rule_id, count in Counter(ids).items() if count > 1)
    assert not duplicates, f"duplicate seed rule IDs: {duplicates}"
    assert len(ids) == EXPECTED_RULE_COUNT == 85


def test_seed_agm_rules_use_single_evidence_gated_definition():
    by_id = {row["rule_id"]: row for row in ILRMF_RULES}
    for rule_id in ("AGM-001", "AGM-002", "AGM-003", "AGM-004", "AGM-005"):
        assert rule_id in by_id
    assert "calendar-month" in by_id["AGM-001"]["description"]
    assert "short_notice_consent_verified" in by_id["AGM-003"]["rule_condition"]["trigger"]
    assert "verified_quorum_required" in by_id["AGM-005"]["rule_condition"]["trigger"]


def test_canonical_registry_has_no_duplicate_dictionary_keys():
    source = (ROOT / "canonical_architecture" / "statutory_rules.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    duplicates = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        keys = [key.value for key in node.keys if isinstance(key, ast.Constant) and isinstance(key.value, str)]
        duplicates.extend(sorted(key for key, count in Counter(keys).items() if count > 1))
    assert not duplicates, f"duplicate literal dictionary keys: {duplicates}"


def test_aud001_has_one_authoritative_requirement_key():
    source = (ROOT / "canonical_architecture" / "statutory_rules.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    target = None
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            keys = [key.value for key in node.keys if isinstance(key, ast.Constant) and isinstance(key.value, str)]
            if "AUD-001" in keys:
                target = node
                break
    assert target is not None
    requirements = [
        key.value for key in target.keys
        if isinstance(key, ast.Constant) and key.value == "requirement"
    ]
    assert len(requirements) == 1


def test_capital_reduction_and_charge_satisfaction_have_distinct_statutory_identity():
    source = (ROOT / "canonical_architecture" / "statutory_rules.py").read_text(encoding="utf-8")
    assert '"CAP-003": {' in source
    assert '"law": "Section 59, Companies Act 1994 (Bangladesh)"' in source
    assert '"CHG-001": {' in source
    assert '"law": "Section 87(2), Companies Act 1994 (Bangladesh)"' in source
