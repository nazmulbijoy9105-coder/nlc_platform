"""API-001: Rule parity test — verify engine, canonical, and API rule sets agree.

Static parity test (no HTTP request needed). Verifies that:
1. STATUTORY_RULE_REGISTRY has all expected rules (80+)
2. NLCRuleEngine source references all rules in the registry (80%+ coverage)
3. Rule counts are close (within 10% of each other)

For the full HTTP parity test (GET /api/v1/rules with auth), see
tests/integration/test_api_rule_parity.py (requires running server).
"""
from __future__ import annotations

import inspect
import re

from canonical_architecture.statutory_rules import STATUTORY_RULE_REGISTRY
from app.rule_engine.engine import NLCRuleEngine


def _engine_rule_ids():
    """Extract all rule_id = "XXX-NNN" references from the engine source."""
    source = inspect.getsource(NLCRuleEngine)
    return {m.group(1) for m in re.finditer(r'rule_id\s*=\s*"([A-Z]{2,4}-\d{3})"', source)}


def test_canonical_registry_has_rules():
    """API-001: STATUTORY_RULE_REGISTRY should not be empty."""
    assert len(STATUTORY_RULE_REGISTRY) > 0, "STATUTORY_RULE_REGISTRY is empty"
    assert len(STATUTORY_RULE_REGISTRY) >= 80, (
        f"Expected 80+ rules, got {len(STATUTORY_RULE_REGISTRY)}"
    )


def test_engine_references_all_canonical_rules():
    """API-001: Engine source should reference most rules in the canonical registry."""
    engine_ids = _engine_rule_ids()
    canonical_ids = set(STATUTORY_RULE_REGISTRY.keys())
    coverage = len(canonical_ids & engine_ids) / len(canonical_ids) * 100
    assert coverage >= 80, (
        f"Engine references only {coverage:.0f}% of canonical rules. "
        f"Missing: {sorted(canonical_ids - engine_ids)[:10]}..."
    )


def test_canonical_and_engine_rule_counts_are_close():
    """API-001: Rule counts should be close (within 10% of each other)."""
    engine_ids = _engine_rule_ids()
    canonical_ids = set(STATUTORY_RULE_REGISTRY.keys())
    diff = abs(len(engine_ids) - len(canonical_ids))
    max_count = max(len(engine_ids), len(canonical_ids))
    assert diff / max_count < 0.1, (
        f"Rule count difference too large: engine={len(engine_ids)}, "
        f"canonical={len(canonical_ids)}, diff={diff}"
    )
