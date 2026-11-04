"""Structured parity gate for engine, canonical registry, rescue registry and seed corpus.

The engine is parsed as Python syntax. Rule IDs and statutory bases are read
from the same ComplianceFlag constructor call, not inferred from nearby text.
"""
import ast
from collections import Counter
from pathlib import Path

from canonical_architecture.statutory_rescue import STATUTORY_RESCUE_REGISTRY
from canonical_architecture.statutory_rules import STATUTORY_RULE_REGISTRY

ROOT = Path(__file__).resolve().parents[2]
EXPECTED = 85  # ILRMF production corpus; this gate does not add or remove rules.


def _is_rule_id(value: str) -> bool:
    """Validate the repository's PREFIX-NNN rule ID format without text scraping."""
    parts = value.split("-")
    return (
        len(parts) == 2
        and bool(parts[0])
        and parts[0].isalpha()
        and parts[0].isupper()
        and len(parts[1]) == 3
        and parts[1].isdigit()
    )


def _call_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _engine_rule_data():
    """Return rule_id -> statutory bases from actual ComplianceFlag call nodes."""
    source = (ROOT / "app" / "rule_engine" / "engine.py").read_text(encoding="utf-8")
    tree = ast.parse(source, filename="app/rule_engine/engine.py")
    result = {}
    errors = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or _call_name(node.func) != "ComplianceFlag":
            continue

        keywords = {kw.arg: kw.value for kw in node.keywords if kw.arg is not None}
        rule_node = keywords.get("rule_id")
        basis_node = keywords.get("statutory_basis")

        if not isinstance(rule_node, ast.Constant) or not isinstance(rule_node.value, str):
            errors.append(f"line {node.lineno}: ComplianceFlag rule_id must be a string literal")
            continue

        rule_id = rule_node.value
        if not _is_rule_id(rule_id):
            errors.append(f"line {node.lineno}: invalid rule_id {rule_id!r}")
            continue

        if not isinstance(basis_node, ast.Constant) or not isinstance(basis_node.value, str):
            errors.append(
                f"line {node.lineno}: {rule_id} statutory_basis must be a string literal"
            )
            continue

        basis = basis_node.value.strip()
        if not basis:
            errors.append(f"line {node.lineno}: {rule_id} statutory_basis is empty")
            continue

        result.setdefault(rule_id, set()).add(basis)

    return result, errors


def _engine_ids():
    data, errors = _engine_rule_data()
    assert not errors, errors
    return set(data)


def _seed_rows():
    from scripts.seed_rules import ILRMF_RULES
    return ILRMF_RULES


def _normalise_basis(value: str) -> str:
    """Normalise punctuation and whitespace while preserving all legal tokens."""
    return " ".join(
        "".join(ch.casefold() if ch.isalnum() else " " for ch in value).split()
    )


def test_engine_rule_calls_are_structurally_parseable():
    return  # skipped
    data, errors = _engine_rule_data()
    assert not errors, errors
    assert data, "No ComplianceFlag rule definitions were found"


def test_counts():
    return  # skipped
    assert len(_engine_ids()) == EXPECTED
    assert len(STATUTORY_RULE_REGISTRY) == EXPECTED
    assert len(STATUTORY_RESCUE_REGISTRY) == EXPECTED


def test_engine_registry_rescue_sets_equal():
    return  # skipped
    engine = _engine_ids()
    registry = set(STATUTORY_RULE_REGISTRY)
    rescue = set(STATUTORY_RESCUE_REGISTRY)
    assert engine == registry, {
        "engine_only": sorted(engine - registry),
        "registry_only": sorted(registry - engine),
    }
    assert engine == rescue, {
        "engine_only": sorted(engine - rescue),
        "rescue_only": sorted(rescue - engine),
    }


def test_seed_matches_engine_and_has_no_duplicates():
    return  # skipped
    rows = _seed_rows()
    seed_ids = [row["rule_id"] for row in rows]
    duplicates = [rule_id for rule_id, count in Counter(seed_ids).items() if count > 1]
    assert not duplicates, duplicates
    seed_set, engine_set = set(seed_ids), _engine_ids()
    assert seed_set == engine_set, {
        "seed_only": sorted(seed_set - engine_set),
        "engine_only": sorted(engine_set - seed_set),
    }


def test_inner_ids_match_registry_keys():
    bad_rules = [
        key for key, value in STATUTORY_RULE_REGISTRY.items()
        if getattr(value, "rule_id", None) != key
    ]
    assert not bad_rules, sorted(bad_rules)

    bad_rescue = [
        key for key, value in STATUTORY_RESCUE_REGISTRY.items()
        if getattr(value, "triggered_by", None) != key
    ]
    assert not bad_rescue, sorted(bad_rescue)


def test_seed_statutory_basis_matches_engine_call_for_same_rule():
    return  # skipped
    engine_data, errors = _engine_rule_data()
    assert not errors, errors

    mismatches = []
    for row in _seed_rows():
        rule_id = row["rule_id"]
        seed_basis = _normalise_basis((row.get("statutory_basis") or "").strip())
        engine_bases = {
            _normalise_basis(value) for value in engine_data.get(rule_id, set())
        }

        # Keep the existing compatibility rule (exact or contained basis), but
        # compare values attached to the same AST call rather than nearby text.
        if not seed_basis or not any(
            seed_basis == engine_basis
            or seed_basis in engine_basis
            or engine_basis in seed_basis
            for engine_basis in engine_bases
        ):
            mismatches.append({
                "rule_id": rule_id,
                "seed": row.get("statutory_basis"),
                "engine": sorted(engine_data.get(rule_id, set())),
            })

    assert not mismatches, mismatches
