"""INC-002 registry and counsel-gate tests."""
from scripts.seed_rules import EXPECTED_RULE_COUNT, ILRMF_RULES
from app.rule_engine.engine import PRODUCT_SCORING_RULE_IDS, SCORE_DEDUCTION_RULE_IDS, VERIFIED_RULE_IDS, _counsel_score_basis_is_verified


def test_seed_registry_has_86_unique_rules_and_inc002():
    ids = [r["rule_id"] for r in ILRMF_RULES]
    assert EXPECTED_RULE_COUNT == 86
    assert len(ids) == 86
    assert len(set(ids)) == 86
    assert "INC-002" in ids


def test_inc002_is_in_product_registries_not_counsel_verified():
    assert len(PRODUCT_SCORING_RULE_IDS) == 86
    assert len(SCORE_DEDUCTION_RULE_IDS) == 86
    assert "INC-002" in PRODUCT_SCORING_RULE_IDS
    assert "INC-002" in SCORE_DEDUCTION_RULE_IDS
    assert "INC-002" not in VERIFIED_RULE_IDS


def test_registry_addition_does_not_bypass_counsel_gate():
    assert not _counsel_score_basis_is_verified()
