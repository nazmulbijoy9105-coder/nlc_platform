"""Catch silent duplicate declarations before Python dict construction hides them."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _assignment(tree, name):
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            return node.value
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == name
        ):
            return node.value
    raise AssertionError(f"missing assignment: {name}")


def test_statutory_rule_source_has_no_duplicate_literal_identity_declarations():
    path = ROOT / "canonical_architecture" / "statutory_rules.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    rules = _assignment(tree, "_RULES")
    assert isinstance(rules, (ast.Tuple, ast.List))
    ids = []
    for item in rules.elts:
        if not (isinstance(item, ast.Call) and item.args and isinstance(item.args[0], ast.Constant)):
            continue
        if isinstance(item.args[0].value, str):
            ids.append(item.args[0].value)
    assert len(ids) == len(set(ids)), {"duplicate_ids": sorted({x for x in ids if ids.count(x) > 1})}

    legacy = _assignment(tree, "_LEGACY_RULE_DICTS")
    assert isinstance(legacy, ast.Dict)
    keys = [key.value for key in legacy.keys if isinstance(key, ast.Constant) and isinstance(key.value, str)]
    assert len(keys) == len(set(keys)), {"duplicate_legacy_ids": sorted({x for x in keys if keys.count(x) > 1})}


def test_rule_identity_manifest_is_exact_across_canonical_seed_and_rescue():
    from canonical_architecture.statutory_rules import STATUTORY_RULE_REGISTRY
    from canonical_architecture.statutory_rescue import STATUTORY_RESCUE_REGISTRY
    from scripts.seed_rules import ILRMF_RULES

    seed_ids = [row["rule_id"] for row in ILRMF_RULES]
    canonical_ids = set(STATUTORY_RULE_REGISTRY)
    rescue_ids = set(STATUTORY_RESCUE_REGISTRY)
    assert len(seed_ids) == len(set(seed_ids))
    assert len(canonical_ids) == 85
    assert set(seed_ids) == canonical_ids
    assert not ({"INC-002"} & canonical_ids)
    assert rescue_ids <= canonical_ids
    assert all(rule.rule_id == key for key, rule in STATUTORY_RULE_REGISTRY.items())
    assert all(rule.triggered_by == key for key, rule in STATUTORY_RESCUE_REGISTRY.items())
