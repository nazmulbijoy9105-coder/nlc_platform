"""Production lifecycle tests for mutable rule-engine instances."""
from app.core import dependencies


def test_get_rule_engine_returns_a_fresh_instance_for_each_evaluation(monkeypatch):
    class FakeRuleEngine:
        pass

    monkeypatch.setattr("app.rule_engine.NLCRuleEngine", FakeRuleEngine)

    first = dependencies.get_rule_engine()
    second = dependencies.get_rule_engine()

    assert isinstance(first, FakeRuleEngine)
    assert isinstance(second, FakeRuleEngine)
    assert first is not second
