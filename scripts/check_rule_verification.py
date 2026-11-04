#!/usr/bin/env python3
"""CI guard for engine/seed rule inventory and verification metadata.

This enforces static inventory parity. It does NOT claim to perform a historical
approval-regression comparison: that requires a trusted prior-state baseline.
"""
import ast
import re
import sys
from pathlib import Path


def _engine_rule_ids(source: str) -> set[str]:
    tree = ast.parse(source)
    ids: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.keyword) and node.arg == "rule_id" and isinstance(node.value, ast.Constant):
            value = node.value.value
            if isinstance(value, str) and re.fullmatch(r"[A-Z]{2,12}-\d{3}", value):
                ids.add(value)
        # BSEC candidate rules are tuple-declared rather than ComplianceFlag keywords.
        if isinstance(node, ast.Tuple) and node.elts and isinstance(node.elts[0], ast.Constant):
            value = node.elts[0].value
            if isinstance(value, str) and re.fullmatch(r"[A-Z]{2,12}-\d{3}", value):
                ids.add(value)
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "rule_id" and isinstance(node.value, ast.Constant):
                    value = node.value.value
                    if isinstance(value, str) and re.fullmatch(r"[A-Z]{2,12}-\d{3}", value):
                        ids.add(value)
    return ids


def _seed_rule_ids(source: str) -> set[str]:
    tree = ast.parse(source)
    ids: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if (isinstance(key, ast.Constant) and key.value == "rule_id"
                        and isinstance(value, ast.Constant) and isinstance(value.value, str)):
                    ids.add(value.value)
    return ids


def main() -> int:
    engine_path = Path("app/rule_engine/engine.py")
    seed_path = Path("scripts/seed_rules.py")
    if not engine_path.exists() or not seed_path.exists():
        print("FAIL: engine or seed file missing")
        return 1

    engine = _engine_rule_ids(engine_path.read_text(encoding="utf-8"))
    seed = _seed_rule_ids(seed_path.read_text(encoding="utf-8"))
    print("Rule Verification Status Check")
    print("=" * 50)
    print(f"ENGINE (AST): {len(engine)} rules")
    print(f"SEED   (AST): {len(seed)} rules")
    if engine != seed:
        print(f"ENGINE missing from SEED: {sorted(engine - seed)}")
        print(f"SEED missing from ENGINE: {sorted(seed - engine)}")
        return 1

    print(f"PASS: exact engine/seed inventory parity ({len(engine)}/{len(seed)})")
    print("NOT CHECKED: VERIFIED-to-PENDING regression comparison has no trusted prior-state baseline")
    return 0


if __name__ == "__main__":
    sys.exit(main())
