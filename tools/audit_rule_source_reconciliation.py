#!/usr/bin/env python3
"""Build a read-only, AST-derived reconciliation inventory for historical rule IDs.

This reports source definitions and evaluator artifacts at a pinned repository
revision. It deliberately does not infer legal equivalence or canonical identity.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BASELINE = "cefe6f169cd283d2e61071a3b7438657da04321e"
SOURCES = {
    "seed_catalogue": ("scripts/seed_rules.py", "0e0c43cfa7287575e9d07d4bed05e007dc942ac8"),
    "statutory_registry": ("canonical_architecture/statutory_rules.py", "f811bb2242ba25867aedea3769444eda425e0e49"),
    "runtime_engine": ("app/rule_engine/engine.py", "52a2a5d76e31429da5144e61b6b92db30b9161c4"),
    "evidence_contract": ("canonical_architecture/evidence_model.py", "36d89852e32807344901c673541b7a26301569a6"),
    "applicability_contract": ("canonical_architecture/applicability_model.py", "7cf69b4157eaa55e2345ddad3554cda0e9001b04"),
    "legal_reconciliation": ("canonical_architecture/legal_reconciliation.py", "f4049349a64480a8cf332f3f9f00f5e8035d028c"),
    "rescue_registry": ("canonical_architecture/statutory_rescue.py", "95375dfdafab04c08a29c5a16d91491487876c2d"),
}


def digest(node: ast.AST) -> str:
    payload = ast.dump(node, annotate_fields=True, include_attributes=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def assignment(tree: ast.Module, name: str) -> ast.AST:
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(t, ast.Name) and t.id == name for t in targets):
                return node.value
    raise ValueError(f"assignment {name!r} not found")


def literal_string(node: ast.AST) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def keyed_dict(node: ast.AST, *, key_name: str | None = None) -> dict[str, ast.AST]:
    result: dict[str, ast.AST] = {}
    if isinstance(node, ast.Dict):
        for key, value in zip(node.keys, node.values):
            key_value = literal_string(key) if key is not None else None
            if key_value and key_value.replace("-", "").isalnum():
                result[key_value] = value
    elif isinstance(node, (ast.List, ast.Tuple)):
        for value in node.elts:
            if not isinstance(value, ast.Dict):
                continue
            for key, item in zip(value.keys, value.values):
                if literal_string(key) == key_name:
                    rule_id = literal_string(item)
                    if rule_id:
                        result[rule_id] = value
                    break
    return result


def read_tree(name: str) -> ast.Module:
    path, _ = SOURCES[name]
    return ast.parse((ROOT / path).read_text(encoding="utf-8"), filename=path)


def function_index(tree: ast.Module) -> dict[str, ast.AST]:
    return {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def tuple_items(node: ast.AST | None) -> list[str]:
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        return [ast.unparse(item) for item in node.elts]
    return []


def call_arguments(node: ast.AST | None) -> list[ast.AST]:
    return list(node.args) if isinstance(node, ast.Call) else []


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    trees = {name: read_tree(name) for name in SOURCES}
    seed = keyed_dict(assignment(trees["seed_catalogue"], "ILRMF_RULES"), key_name="rule_id")
    statutory = keyed_dict(assignment(trees["statutory_registry"], "_LEGACY_RULE_DICTS"))
    evidence = keyed_dict(assignment(trees["evidence_contract"], "EVIDENCE_REGISTRY"))
    applicability = keyed_dict(assignment(trees["applicability_contract"], "APPLICABILITY_REGISTRY"))
    reconciliation = keyed_dict(assignment(trees["legal_reconciliation"], "LEGAL_RECONCILIATION"))
    rescue: dict[str, ast.AST] = {}
    rescue_nodes = assignment(trees["rescue_registry"], "_RESCUES")
    if isinstance(rescue_nodes, (ast.Tuple, ast.List)):
        for item in rescue_nodes.elts:
            if isinstance(item, ast.Call) and len(item.args) >= 2:
                triggered_by = literal_string(item.args[1])
                if triggered_by:
                    rescue[triggered_by] = item
    engine_functions = function_index(trees["runtime_engine"])

    expected_ids = sorted(seed)
    if len(expected_ids) != 85 or len(set(expected_ids)) != 85:
        raise SystemExit(f"expected exactly 85 unique seed IDs; found {len(expected_ids)}")

    records: list[dict[str, Any]] = []
    for rule_id in expected_ids:
        seed_node = seed[rule_id]
        seed_fields = {
            literal_string(k): v
            for k, v in zip(seed_node.keys, seed_node.values)
            if literal_string(k)
        }
        condition = seed_fields.get("rule_condition")
        check_fn = None
        if isinstance(condition, ast.Dict):
            for key, value in zip(condition.keys, condition.values):
                if literal_string(key) == "check_fn":
                    check_fn = literal_string(value)
                    break
        evaluator = engine_functions.get(check_fn) if check_fn else None
        observed = {
            "seed_catalogue": seed_node,
            "statutory_registry": statutory.get(rule_id),
            "evidence_contract": evidence.get(rule_id),
            "applicability_contract": applicability.get(rule_id),
            "legal_reconciliation": reconciliation.get(rule_id),
            "rescue_registry": rescue.get(rule_id),
            "runtime_evaluator": evaluator,
        }
        candidates = []
        for key, node in observed.items():
            if node is None:
                continue
            source_key = "runtime_engine" if key == "runtime_evaluator" else key
            path, blob_sha = SOURCES[source_key]
            candidates.append({
                "artifact": source_key,
                "path": path,
                "blob_sha": blob_sha,
                "symbol": check_fn if key == "runtime_evaluator" else (
                    "ILRMF_RULES" if key == "seed_catalogue" else {
                        "statutory_registry": "_LEGACY_RULE_DICTS",
                        "evidence_contract": "EVIDENCE_REGISTRY",
                        "applicability_contract": "APPLICABILITY_REGISTRY",
                        "legal_reconciliation": "LEGAL_RECONCILIATION",
                        "rescue_registry": "RESCUE_REGISTRY",
                    }[key]
                ),
                "definition_sha256": digest(node),
            })
        seed_basis = literal_string(seed_fields.get("statutory_basis", ast.Constant(None)))
        seed_data_points: list[str] = []
        if isinstance(condition, ast.Dict):
            for key, value in zip(condition.keys, condition.values):
                if literal_string(key) == "data_points":
                    seed_data_points = tuple_items(value)
                    break
        evidence_args = call_arguments(evidence.get(rule_id))
        applicability_args = call_arguments(applicability.get(rule_id))
        evidence_contract = {
            "status": "MAPPED" if len(evidence_args) >= 5 else "MISSING",
            "primary_evidence": tuple_items(evidence_args[1]) if len(evidence_args) >= 2 else [],
            "non_compliance_evidence": tuple_items(evidence_args[2]) if len(evidence_args) >= 3 else [],
            "evidentiary_standard": literal_string(evidence_args[3]) if len(evidence_args) >= 4 else None,
            "source_section_label": literal_string(evidence_args[4]) if len(evidence_args) >= 5 else None,
        }
        applicability_contract = {
            "status": "MAPPED" if len(applicability_args) >= 5 else "MISSING",
            "company_types": tuple_items(applicability_args[1]) if len(applicability_args) >= 2 else [],
            "required_conditions": tuple_items(applicability_args[2]) if len(applicability_args) >= 3 else [],
            "exception_inputs": tuple_items(applicability_args[3]) if len(applicability_args) >= 4 else [],
        }
        statutory_node = statutory.get(rule_id)
        statutory_fields = {}
        if isinstance(statutory_node, ast.Dict):
            statutory_fields = {
                literal_string(k): v
                for k, v in zip(statutory_node.keys, statutory_node.values)
                if literal_string(k)
            }
        statutory_law = literal_string(statutory_fields.get("law", ast.Constant(None)))
        basis_comparison = (
            "NOT_COMPARABLE_MISSING_STATUTORY_DEFINITION"
            if statutory_node is None else
            "EXACT_TEXT_MATCH" if seed_basis == statutory_law else
            "TEXT_DIVERGENCE_REVIEW_REQUIRED"
        )
        records.append({
            "historical_rule_id": rule_id,
            "identity_resolution": (
                "AMBIGUOUS_KNOWN_PRODUCTION_SEED_COLLISION"
                if rule_id == "INC-001" else "UNRESOLVED"
            ),
            "historical_origin": "NOT_ESTABLISHED",
            "seed_check_function": check_fn,
            "runtime_evaluator_status": "FOUND" if evaluator is not None else "NOT_FOUND_OR_NOT_MODULE_LEVEL",
            "seed_fact_inputs": seed_data_points,
            "evidence_contract": evidence_contract,
            "applicability_contract": applicability_contract,
            "fact_evidence_gaps": [
                gap for gap, condition in (
                    ("SEED_DATA_POINTS_MISSING", not seed_data_points),
                    ("EVIDENCE_MAPPING_MISSING", evidence_contract["status"] == "MISSING"),
                    ("APPLICABILITY_MAPPING_MISSING", applicability_contract["status"] == "MISSING"),
                    ("RUNTIME_EVALUATOR_NOT_FOUND", evaluator is None),
                ) if condition
            ],
            "seed_vs_statutory_basis": basis_comparison,
            "source_candidates": candidates,
            "missing_artifacts": [key for key, node in observed.items() if node is None],
            "legal_review_status": "REVIEW_REQUIRED",
            "product_decision_status": "NOT_REVIEWED",
        })

    result = {
        "schema_version": "1.0.0",
        "baseline_commit": BASELINE,
        "report_type": "AST_SOURCE_DEFINITION_RECONCILIATION_NOT_LEGAL_APPROVAL",
        "rule_count": len(records),
        "source_artifacts": [
            {"key": key, "path": path, "blob_sha": sha}
            for key, (path, sha) in SOURCES.items()
        ],
        "rules": records,
        "limitations": [
            "The baseline commit and blob SHAs pin observed repository content, not the first historical introduction of a rule.",
            "AST presence and exact-text comparison do not establish that two definitions express the same legal obligation.",
            "A missing mapping is a missing artifact in this source, not proof that the fact or evidence is not collected elsewhere.",
            "No UUID, alias, operative date, instrument, amendment chain, company scope, legal approval, or scoring approval is inferred.",
            "INC-001 remains ambiguous because the seed/engine Section 23 proposition conflicts with the separately observed production Section 9 catalogue proposition.",
        ],
    }
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
