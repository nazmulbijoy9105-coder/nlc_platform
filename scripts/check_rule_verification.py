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

    # The approval register is a release control, not merely documentation.
    approval_path = Path("docs/legal/legal_approval_register.yaml")
    if not approval_path.exists():
        print("FAIL: legal approval register missing")
        return 1
    approval = approval_path.read_text(encoding="utf-8")
    approval_ids = set(re.findall(
        r"^\s*- rule_id:\s*([A-Z]{2,12}-\d{3})\s*$", approval, re.MULTILINE
    ))
    review_required = len(re.findall(
        r"^\s+status:\s*REVIEW_REQUIRED\s*$", approval, re.MULTILINE
    ))
    score_ineligible = len(re.findall(
        r"^\s+score_eligible:\s*false\s*$", approval, re.MULTILINE
    ))
    if "approval_policy: fail_closed" not in approval or "approved_rule_ids: []" not in approval:
        print("FAIL: approval register is not explicitly fail-closed with zero approved IDs")
        return 1
    if approval_ids != seed:
        print(f"FAIL: approval register inventory mismatch; missing={sorted(seed - approval_ids)} extra={sorted(approval_ids - seed)}")
        return 1
    if review_required != len(seed) or score_ineligible != len(seed):
        print(f"FAIL: expected every rule REVIEW_REQUIRED and score_eligible=false; got {review_required}/{len(seed)} and {score_ineligible}/{len(seed)}")
        return 1

    engine_source = engine_path.read_text(encoding="utf-8")
    seed_source = seed_path.read_text(encoding="utf-8")
    if re.search(r"UPDATE\s+legal_rules", seed_source, re.IGNORECASE):
        print("FAIL: seed_rules.py must not update existing legal_rules outside the audited version workflow")
        return 1
    if '"NOT_EVALUATED"' not in seed_source:
        print("FAIL: seed_rules.py must accept NOT_EVALUATED severity")
        return 1

    if not re.search(r"^LEGAL_SCORE_RELEASED:\s*bool\s*=\s*False\s*$", engine_source, re.MULTILINE):
        print("FAIL: legal score release flag is not explicitly disabled")
        return 1
    if not re.search(r"^VERIFIED_RULE_IDS:\s*frozenset\[str\]\s*=\s*frozenset\(\)\s*$", engine_source, re.MULTILINE):
        print("FAIL: verified rule allowlist must remain empty until counsel approval")
        return 1

    print(f"PASS: all {len(seed)} rules remain REVIEW_REQUIRED and score-ineligible")
    print("PASS: statutory scoring release flag is disabled and verified allowlist is empty")
    return 0


if __name__ == "__main__":
    sys.exit(main())
