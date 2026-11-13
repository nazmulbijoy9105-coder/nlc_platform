#!/usr/bin/env python3
"""CI guard for engine/seed rule inventory and verification metadata.

This enforces static inventory parity. It does NOT claim to perform a historical
approval-regression comparison: that requires a trusted prior-state baseline.
"""
import ast
import csv
import json
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



def _seed_rule_rows(source: str) -> list[dict]:
    """Return literal seed rule dictionaries for release-policy validation."""
    tree = ast.parse(source)
    rows: list[dict] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        try:
            value = ast.literal_eval(node)
        except (ValueError, TypeError, SyntaxError):
            continue
        if isinstance(value, dict) and isinstance(value.get("rule_id"), str):
            rows.append(value)
    return rows


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

    # Product approval and independent legal verification are separate registers.
    product_path = Path("docs/product/product_rule_approval_register.yaml")
    legal_path = Path("docs/legal/legal_approval_register.yaml")
    if not product_path.exists() or not legal_path.exists():
        print("FAIL: product-owner or independent-counsel approval register missing")
        return 1
    product_approval = product_path.read_text(encoding="utf-8")
    product_header = product_approval.split("rules:", 1)[0]
    product_row_ids = set(re.findall(
        r"^\s*- rule_id:\s*([A-Z]{2,12}-\d{3})\s*$", product_approval, re.MULTILINE
    ))
    approved_ids = set(re.findall(
        r"^\s+- ([A-Z]{2,12}-\d{3})\s*$", product_header, re.MULTILINE
    ))
    product_approved_count = len(re.findall(
        r"^\s+product_status:\s*PRODUCT_APPROVED\s*$", product_approval, re.MULTILINE
    ))
    active_count = len(re.findall(
        r"^\s+product_active:\s*true\s*$", product_approval, re.MULTILINE
    ))
    eligible_count = len(re.findall(
        r"^\s+score_eligible:\s*true\s*$", product_approval, re.MULTILINE
    ))
    ineligible_count = len(re.findall(
        r"^\s+score_eligible:\s*false\s*$", product_approval, re.MULTILINE
    ))
    if "approval_policy: owner_attested" not in product_header or "legal_effect: NONE" not in product_header:
        print("FAIL: product register must explicitly be owner-attested and have no legal effect")
        return 1
    if product_row_ids != seed or approved_ids != seed:
        print(f"FAIL: product approval inventory mismatch; rows_missing={sorted(seed-product_row_ids)} rows_extra={sorted(product_row_ids-seed)} approved_missing={sorted(seed-approved_ids)}")
        return 1
    if product_approved_count != len(seed) or active_count != len(seed) or eligible_count != len(seed) or ineligible_count != 0:
        print(f"FAIL: expected 85 product-approved/active/score-eligible rules and no inactive catalogue rules; got {product_approved_count}, {active_count}, {eligible_count}, {ineligible_count}")
        return 1

    legal_approval = legal_path.read_text(encoding="utf-8")
    legal_header = legal_approval.split("rules:", 1)[0]
    legal_row_ids = set(re.findall(
        r"^\s*- rule_id:\s*([A-Z]{2,12}-\d{3})\s*$", legal_approval, re.MULTILINE
    ))
    counsel_approved_ids = set(re.findall(
        r"^\s+- ([A-Z]{2,12}-\d{3})\s*$", legal_header, re.MULTILINE
    ))
    review_required_count = len(re.findall(
        r"^\s+status:\s*REVIEW_REQUIRED\s*$", legal_approval, re.MULTILINE
    ))
    if "approval_policy: independent_counsel_only" not in legal_header or counsel_approved_ids or legal_row_ids != seed or review_required_count != len(seed):
        print("FAIL: legal register must retain all 85 rules as REVIEW_REQUIRED with no counsel approvals")
        return 1

    # Fail closed at the data source too: an empty engine allowlist is not
    # sufficient if the seeder can write scored or BLACK-override rule rows.
    seed_rows = _seed_rule_rows(seed_path.read_text(encoding="utf-8"))
    if len(seed_rows) != len(seed):
        print(f"FAIL: expected {len(seed)} literal seed rows, found {len(seed_rows)}")
        return 1
    unsafe_seed_rows = [
        row.get("rule_id") for row in seed_rows
        if row.get("is_black_override") is not False
    ]
    if unsafe_seed_rows:
        print(f"FAIL: seed rows contain unapproved BLACK overrides: {unsafe_seed_rows}")
        return 1

    # Keep every maintained catalogue representation aligned with the
    # unapproved release state. The legacy db_rules.txt is intentionally
    # excluded because it is a historical production export, not a source.
    csv_path = Path("docs/legal/NLC_BD_COMPANIES_LAW_RULES_v1.0.csv")
    json_path = Path("docs/legal/NLC_BD_COMPANIES_LAW_RULES_v1.0.json")
    canonical_path = Path("canonical_architecture/statutory_rules.py")
    matrix_path = Path("docs/LEGAL_BASIS_MATRIX.md")
    for path in (csv_path, json_path, canonical_path, matrix_path):
        if not path.exists():
            print(f"FAIL: legal catalogue representation missing: {path}")
            return 1

    with csv_path.open(encoding="utf-8", newline="") as handle:
        csv_rows = list(csv.DictReader(handle))
    csv_ids = {row["rule_id"] for row in csv_rows}
    if len(csv_rows) != len(seed) or csv_ids != seed:
        print(f"FAIL: legal CSV inventory mismatch; rows={len(csv_rows)} missing={sorted(seed - csv_ids)} extra={sorted(csv_ids - seed)}")
        return 1
    unsafe_csv = [
        row["rule_id"] for row in csv_rows
        if row["engine_black_override"].lower() == "true"
    ]
    if unsafe_csv:
        print(f"FAIL: legal CSV contains BLACK overrides: {unsafe_csv}")
        return 1

    catalogue_json = json.loads(json_path.read_text(encoding="utf-8"))
    json_rows = catalogue_json.get("rules", [])
    json_ids = {row.get("rule_id") for row in json_rows}
    if catalogue_json.get("rule_count") != len(seed) or len(json_rows) != len(seed) or json_ids != seed:
        print(f"FAIL: legal JSON inventory mismatch; rows={len(json_rows)}")
        return 1
    unsafe_json = [
        row.get("rule_id") for row in json_rows
        if row.get("engine_black_override") is True
    ]
    if unsafe_json:
        print(f"FAIL: legal JSON contains BLACK overrides: {unsafe_json}")
        return 1

    canonical_source = canonical_path.read_text(encoding="utf-8")
    # UNKNOWN company facts remain non-findings even though product scoring is released.
    if re.search(r'"is_black_override":\s*True', canonical_source):
        print("FAIL: canonical statutory rule registry contains a BLACK override")
        return 1

    matrix_rows = [
        line for line in matrix_path.read_text(encoding="utf-8").splitlines()
        if re.match(r"^\| [A-Z]{2,5}-\d{3} \|", line)
    ]
    if len(matrix_rows) != len(seed):
        print(f"FAIL: LEGAL_BASIS_MATRIX inventory mismatch: {len(matrix_rows)}/{len(seed)}")
        return 1

    engine_source = engine_path.read_text(encoding="utf-8")
    seed_source = seed_path.read_text(encoding="utf-8")
    if "UPDATE legal_rules SET is_active = TRUE" not in seed_source:
        print("FAIL: seed_rules.py must activate existing canonical catalogue rows")
        return 1
    if "TRUE, :now, :now" not in seed_source:
        print("FAIL: seed_rules.py must insert new canonical rows as active")
        return 1

    expected_release_assignment = 'LEGAL_SCORE_RELEASED: bool = os.getenv("LEGAL_SCORE_RELEASED", "false").strip().lower() in {"true", "1", "yes", "on"}'
    if expected_release_assignment not in engine_source:
        print("FAIL: product release must use LEGAL_SCORE_RELEASED env var and default to false")
        return 1
    env_example = Path(".env.example").read_text(encoding="utf-8")
    if not re.search(r"^LEGAL_SCORE_RELEASED=false$", env_example, re.MULTILINE):
        print("FAIL: .env.example must keep product scoring disabled by default")
        return 1
    release_tree = ast.parse(engine_source)
    release_function = next(
        (node for node in ast.walk(release_tree)
         if isinstance(node, ast.FunctionDef) and node.name == "legal_score_is_released"),
        None,
    )
    release_function_source = (
        ast.get_source_segment(engine_source, release_function) or ""
        if release_function is not None else ""
    )
    if (
        "VERIFIED_RULE_IDS" in release_function_source
        or "issubset" in release_function_source
        or "PRODUCT_SCORING_RULE_IDS" not in release_function_source
    ):
        print("FAIL: product release function must depend on the product allowlist, not counsel verification")
        return 1

    verified_match = re.search(
        r"^VERIFIED_RULE_IDS:\s*frozenset\[str\]\s*=\s*frozenset\(\{([\s\S]*?)\}\)",
        engine_source, re.MULTILINE
    )
    verified_engine_ids = set(re.findall(r'"([A-Z]{2,12}-\d{3})"', verified_match.group(1))) if verified_match else set()
    if verified_engine_ids:
        print(f"FAIL: default VERIFIED_RULE_IDS must remain empty pending independent Bangladesh-counsel verification; found={sorted(verified_engine_ids)}")
        return 1

    engine_tree = ast.parse(engine_source)
    product_ids: set[str] = set()
    deduction_ids: set[str] = set()
    for node in ast.walk(engine_tree):
        if (isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and node.target.id == "PRODUCT_SCORING_RULE_IDS"):
            product_ids = set(ast.literal_eval(node.value.args[0]))
        if (isinstance(node, ast.AnnAssign)
                and isinstance(node.target, ast.Name)
                and node.target.id == "SCORE_DEDUCTION_RULE_IDS"):
            deduction_ids = set(ast.literal_eval(node.value.args[0]))
    non_deduction_ids: set[str] = set()
    if product_ids != seed:
        print(f"FAIL: product-active rule allowlist mismatch; count={len(product_ids)} missing={sorted(seed-product_ids)} extra={sorted(product_ids-seed)}")
        return 1
    if deduction_ids != seed:
        print(f"FAIL: score-deduction allowlist mismatch; count={len(deduction_ids)}")
        return 1

    if not re.search(r"^BLACK_OVERRIDE_RULES:\s*set\[str\]\s*=\s*set\(\)\s*$", engine_source, re.MULTILINE):
        print("FAIL: unapproved legal rule catalogue must not define BLACK overrides")
        return 1

    print(f"PASS: {len(seed)} catalogue rules match engine, seed and legal register")
    print(f"PASS: {len(product_ids)} rules are product-active and score-eligible; counsel-verified IDs remain separate: {len(verified_engine_ids)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
