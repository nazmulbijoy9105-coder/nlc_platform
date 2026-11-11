#!/usr/bin/env python3
"""CI parity and release-policy guard for the owner-attested ILRMF catalogue.

Catalogue activation, product scoring eligibility and company-specific evaluation
are distinct: all 85 IDs are active; 82 are score-bearing; 3 are informational.
Unknown or unverified company facts remain non-scoring at runtime.
"""
import ast
import re
import sys
from pathlib import Path

INFO_ONLY = {"AR-001", "SH-002", "ESC-003"}
RULE_RE = re.compile(r"^[A-Z]{2,12}-\d{3}$")


def engine_ids(source: str) -> set[str]:
    tree = ast.parse(source)
    result = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.keyword) and node.arg == "rule_id" and isinstance(node.value, ast.Constant):
            value = node.value.value
            if isinstance(value, str) and RULE_RE.fullmatch(value):
                result.add(value)
        if isinstance(node, ast.Tuple) and node.elts and isinstance(node.elts[0], ast.Constant):
            value = node.elts[0].value
            if isinstance(value, str) and RULE_RE.fullmatch(value):
                result.add(value)
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "rule_id" and isinstance(node.value, ast.Constant):
                    value = node.value.value
                    if isinstance(value, str) and RULE_RE.fullmatch(value):
                        result.add(value)
    return result


def literal_set(source: str, name: str) -> set[str]:
    match = re.search(rf"^{name}:\s*frozenset\[str\]\s*=\s*frozenset\(\{{([\s\S]*?)\}}\)", source, re.M)
    if not match:
        raise ValueError(f"{name} must be an explicit frozenset literal")
    return set(re.findall(r'"([A-Z]{2,12}-\d{3})"', match.group(1)))


def main() -> int:
    engine_path = Path("app/rule_engine/engine.py")
    seed_path = Path("scripts/seed_rules.py")
    register_path = Path("docs/legal/legal_approval_register.yaml")
    for path in (engine_path, seed_path, register_path):
        if not path.exists():
            print(f"FAIL: required release file missing: {path}")
            return 1

    engine_source = engine_path.read_text(encoding="utf-8")
    seed_source = seed_path.read_text(encoding="utf-8")
    register = register_path.read_text(encoding="utf-8")
    engine = engine_ids(engine_source)
    seed = set(re.findall(r'"rule_id":\s*"([A-Z]{2,12}-\d{3})"', seed_source))
    verified = literal_set(engine_source, "VERIFIED_RULE_IDS")
    scoring = literal_set(engine_source, "PRODUCT_SCORING_RULE_IDS")
    register_ids = set(re.findall(r"^\s*- rule_id:\s*([A-Z]{2,12}-\d{3})\s*$", register, re.M))
    verified_header = register.split("rules:", 1)[0]
    approved = set(re.findall(r"^\s*- ([A-Z]{2,12}-\d{3})\s*$", verified_header, re.M))
    statuses = re.findall(r"^\s+status:\s*([A-Z_]+)\s*$", register, re.M)
    eligibility = re.findall(r"^\s+score_eligible:\s*(true|false)\s*$", register, re.M)

    failures = []
    if len(engine) != 85 or engine != seed:
        failures.append(f"engine/seed mismatch: engine={len(engine)}, seed={len(seed)}")
    if verified != seed or approved != seed or register_ids != seed:
        failures.append(f"verification register mismatch: verified={len(verified)}, approved={len(approved)}, rows={len(register_ids)}, seed={len(seed)}")
    if len(statuses) != 85 or set(statuses) != {"VERIFIED"}:
        failures.append(f"expected 85 VERIFIED register rows; found {len(statuses)}")
    if len(eligibility) != 85:
        failures.append(f"expected 85 score_eligible values; found {len(eligibility)}")
    else:
        eligible_by_id = {}
        row_matches = re.findall(
            r"^  - rule_id: ([A-Z]{2,12}-\d{3})\n    status: VERIFIED\n    score_eligible: (true|false)$",
            register, re.M
        )
        eligible_by_id = {rid: value == "true" for rid, value in row_matches}
        expected = {rid: rid not in INFO_ONLY for rid in seed}
        if eligible_by_id != expected:
            failures.append("score_eligible must be true for the 82 score-bearing IDs and false only for AR-001, SH-002, ESC-003")
    if scoring != seed - INFO_ONLY or len(scoring) != 82:
        failures.append(f"product scoring allowlist mismatch: {len(scoring)}")
    if not re.search(r"^LEGAL_SCORE_RELEASED:\s*bool\s*=\s*True$", engine_source, re.M):
        failures.append("LEGAL_SCORE_RELEASED is not True")
    if "approval_policy: owner_attested" not in verified_header:
        failures.append("register must declare owner_attested policy")
    if "UPDATE legal_rules SET is_active = TRUE" not in seed_source:
        failures.append("seeder does not reactivate existing canonical rule rows")
    if "TRUE, :now, :now" not in seed_source:
        failures.append("seeder must insert missing catalogue rows active")

    if failures:
        for failure in failures:
            print("FAIL:", failure)
        return 1

    print("PASS: 85/85 engine, seed and owner-attested verification IDs match")
    print("PASS: all 85 catalogue entries seed active; 82 scoring + 3 informational")
    print("PASS: product scoring release enabled; company-specific UNKNOWN facts remain guarded by the engine")
    return 0


if __name__ == "__main__":
    sys.exit(main())
