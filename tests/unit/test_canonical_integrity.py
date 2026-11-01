"""E1 gate: engine, canonical registry, rescue registry and DB seed carry identical rule IDs."""
import re
from collections import Counter
from pathlib import Path

from canonical_architecture.statutory_rescue import STATUTORY_RESCUE_REGISTRY
from canonical_architecture.statutory_rules import STATUTORY_RULE_REGISTRY

ROOT = Path(__file__).resolve().parents[2]
EXPECTED = 75
EXPECTED = 85


def _engine_ids():
    src = (ROOT / "app" / "rule_engine" / "engine.py").read_text(encoding="utf-8")
    return set(re.findall(r'rule_id="([A-Z]+-\d{3})"', src))


def _seed_rows():
    from scripts.seed_rules import ILRMF_RULES
    return [r["rule_id"] for r in ILRMF_RULES]


def test_counts():
    assert len(_engine_ids()) == EXPECTED
    assert len(STATUTORY_RULE_REGISTRY) == EXPECTED
    assert len(STATUTORY_RESCUE_REGISTRY) == EXPECTED


def test_engine_registry_rescue_sets_equal():
    e = _engine_ids()
    r = set(STATUTORY_RULE_REGISTRY)
    c = set(STATUTORY_RESCUE_REGISTRY)
    assert e == r, {"engine_only": sorted(e - r), "registry_only": sorted(r - e)}
    assert e == c, {"engine_only": sorted(e - c), "rescue_only": sorted(c - e)}


def test_seed_matches_engine_and_has_no_duplicates():
    rows = _seed_rows()
    dupes = [k for k, n in Counter(rows).items() if n > 1]
    assert not dupes, dupes
    s, e = set(rows), _engine_ids()
    assert s == e, {"seed_only": sorted(s - e), "engine_only": sorted(e - s)}


def test_inner_ids_match_keys():
    # StatutoryRule / RescueDef are frozen dataclasses — use attributes, not .get()
    bad_rules = [
        k for k, v in STATUTORY_RULE_REGISTRY.items()
        if getattr(v, "rule_id", None) != k
    ]
    assert not bad_rules, sorted(bad_rules)
    bad_rescue = [
        k for k, v in STATUTORY_RESCUE_REGISTRY.items()
        if getattr(v, "triggered_by", None) != k
    ]
    assert not bad_rescue, sorted(bad_rescue)
