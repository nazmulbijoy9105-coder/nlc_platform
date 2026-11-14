"""INC-002 registry and product scoring gate tests."""
from scripts.seed_rules import EXPECTED_RULE_COUNT, ILRMF_RULES
from app.rule_engine.engine import PRODUCT_SCORING_RULE_IDS, SCORE_DEDUCTION_RULE_IDS, legal_score_is_released


def test_seed_registry_has_86_unique_rules_and_inc002():
    ids = [r["rule_id"] for r in ILRMF_RULES]
    assert EXPECTED_RULE_COUNT == 86
    assert len(ids) == 86
    assert len(set(ids)) == 86
    assert "INC-002" in ids


def test_inc002_is_in_both_product_scoring_registries():
    assert len(PRODUCT_SCORING_RULE_IDS) == 86
    assert len(SCORE_DEDUCTION_RULE_IDS) == 86
    assert "INC-002" in PRODUCT_SCORING_RULE_IDS
    assert "INC-002" in SCORE_DEDUCTION_RULE_IDS
    assert "INC-002" in SCORE_DEDUCTION_RULE_IDS


def test_registry_scoring_still_requires_product_release_switch(monkeypatch):
    import app.rule_engine.engine as engine_module
    monkeypatch.setattr(engine_module, "LEGAL_SCORE_RELEASED", False)
    assert legal_score_is_released() is False
    monkeypatch.setattr(engine_module, "LEGAL_SCORE_RELEASED", True)
    assert legal_score_is_released() is True
