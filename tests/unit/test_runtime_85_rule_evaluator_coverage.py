"""Exercise every registered rule through the real NLCRuleEngine.evaluate path.

The seed/registry parser proves only that rule IDs are declared. This test
requires each of the 85 IDs to be emitted by at least one deterministic
CompanyProfile scenario, and reports the profile responsible for each ID.
"""
from __future__ import annotations

import pytest

from app.rule_engine.engine import NLCRuleEngine
from scripts.seed_rules import ILRMF_RULES
from tools.engine_introspection import profiles, today


pytestmark = [pytest.mark.unit, pytest.mark.rule]


def test_all_85_rules_are_emitted_by_runtime_evaluator() -> None:
    expected = {rule["rule_id"] for rule in ILRMF_RULES}
    emitted_by: dict[str, set[str]] = {}

    for profile_name, profile in profiles.items():
        output = NLCRuleEngine(today=today).evaluate(profile, today=today)
        for flag in output.flags:
            emitted_by.setdefault(flag.rule_id, set()).add(profile_name)

    emitted = set(emitted_by)
    missing = sorted(expected - emitted)
    unexpected = sorted(emitted - expected)

    assert not unexpected, f"Runtime emitted IDs outside the 85-rule catalogue: {unexpected}"
    assert not missing, (
        "The runtime evaluator has no emitted finding for these registered IDs: "
        + ", ".join(missing)
        + ". Add a deterministic, rule-specific CompanyProfile scenario; do not "
        "satisfy this test with AST parsing, registry membership, or mocked flags."
    )
    assert len(emitted_by) == 85
    assert all(emitted_by[rule_id] for rule_id in expected)
