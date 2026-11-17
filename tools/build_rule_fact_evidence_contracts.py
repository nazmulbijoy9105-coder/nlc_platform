#!/usr/bin/env python3
"""Build fail-closed 85-rule fact/evidence contract drafts from AST audit output.

This is an inventory generator, not a semantic mapper. It never infers fact
types, evidence issuers, verification procedures, legal sufficiency, or approval.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

EXPECTED_BASELINE = "cefe6f169cd283d2e61071a3b7438657da04321e"
EXPECTED_REPORT_TYPE = "AST_SOURCE_DEFINITION_RECONCILIATION_NOT_LEGAL_APPROVAL"


def source_label(value: str) -> str:
    """Remove only the Python quoting added by ast.unparse for string literals."""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def build_contract(rule: dict[str, Any]) -> dict[str, Any]:
    facts = [
        {
            "fact_key": source_label(fact),
            "source_expression": source_label(fact),
            "data_type": "UNSPECIFIED",
            "collection_source": "UNSPECIFIED",
            "verification_method": "UNSPECIFIED",
            "temporal_basis": "UNSPECIFIED",
            "evidence_links": [],
            "mapping_status": "REQUIRES_DOMAIN_MAPPING",
        }
        for fact in rule["seed_fact_inputs"]
    ]
    applicability = [
        {
            "condition_expression": source_label(condition),
            "fact_key": None,
            "evaluation_semantics": "UNSPECIFIED",
            "exception_effect": "UNSPECIFIED",
            "mapping_status": "REQUIRES_DOMAIN_MAPPING",
        }
        for condition in rule["applicability_contract"]["required_conditions"]
    ]
    exceptions = [
        {
            "condition_expression": condition,
            "fact_key": None,
            "resulting_state": "NOT_APPLICABLE",
            "evaluation_semantics": "UNSPECIFIED",
            "mapping_status": "REQUIRES_DOMAIN_MAPPING",
        }
        for condition in rule["applicability_contract"]["exception_inputs"]
    ]

    evidence_contract = rule["evidence_contract"]
    evidence_items = []
    for polarity, key in (
        ("COMPLIANCE", "primary_evidence"),
        ("NON_COMPLIANCE", "non_compliance_evidence"),
    ):
        for evidence_type in evidence_contract[key]:
            evidence_items.append(
                {
                    "evidence_type": evidence_type,
                    "polarity": polarity,
                    "issuer": "UNSPECIFIED",
                    "authenticity_check": "UNSPECIFIED",
                    "verification_method": "UNSPECIFIED",
                    "validity_period": "UNSPECIFIED",
                    "source_section_label": evidence_contract["source_section_label"],
                    "evidentiary_standard": evidence_contract["evidentiary_standard"],
                    "fact_keys_supported": [],
                    "mapping_status": "REQUIRES_DOMAIN_AND_LEGAL_REVIEW",
                }
            )

    gaps = []
    if not facts:
        gaps.append("NO_SEED_FACT_INPUTS")
    if not applicability:
        gaps.append("NO_APPLICABILITY_CONDITIONS")
    if not exceptions:
        gaps.append("NO_EXPLICIT_EXCEPTION_INPUTS")
    if evidence_contract["status"] == "MISSING":
        gaps.append("NO_EVIDENCE_REGISTRY_MAPPING")
    if not evidence_items:
        gaps.append("NO_EVIDENCE_ITEMS")
    if facts and evidence_items:
        gaps.append("FACT_TO_EVIDENCE_LINKS_NOT_ESTABLISHED")
    if any(item["issuer"] == "UNSPECIFIED" for item in evidence_items):
        gaps.append("EVIDENCE_ISSUER_UNSPECIFIED")
    if any(item["verification_method"] == "UNSPECIFIED" for item in evidence_items):
        gaps.append("EVIDENCE_VERIFICATION_UNSPECIFIED")
    if rule["runtime_evaluator_status"] != "FOUND":
        gaps.append("RUNTIME_EVALUATOR_NOT_RESOLVED")

    return {
        "historical_rule_id": rule["historical_rule_id"],
        "identity_resolution": rule["identity_resolution"],
        "historical_origin": rule["historical_origin"],
        "facts": facts,
        "applicability_conditions": applicability,
        "exception_conditions": exceptions,
        "evidence_items": evidence_items,
        "evidence_policy": {
            "evidentiary_standard": evidence_contract["evidentiary_standard"],
            "source_section_label": evidence_contract["source_section_label"],
            "status": evidence_contract["status"],
        },
        "contract_status": "DRAFT_INCOMPLETE",
        "gaps": sorted(set(gaps)),
        "legal_review_status": "REVIEW_REQUIRED",
        "product_decision_status": "NOT_REVIEWED",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True, help="AST reconciliation JSON")
    parser.add_argument("--output", type=Path, required=True, help="Contract inventory JSON")
    args = parser.parse_args()

    source = json.loads(args.input.read_text(encoding="utf-8"))
    if source.get("baseline_commit") != EXPECTED_BASELINE:
        raise SystemExit("unexpected AST audit baseline")
    if source.get("report_type") != EXPECTED_REPORT_TYPE:
        raise SystemExit("unexpected AST audit report type")
    rules = source.get("rules")
    if not isinstance(rules, list) or len(rules) != 85:
        raise SystemExit("expected exactly 85 AST-audited rules")
    ids = [rule.get("historical_rule_id") for rule in rules]
    if len(set(ids)) != 85 or ids != sorted(ids):
        raise SystemExit("rule IDs must be unique and sorted")

    contracts = [build_contract(rule) for rule in rules]
    result = {
        "schema_version": "1.0.0",
        "baseline_commit": EXPECTED_BASELINE,
        "report_type": "FAIL_CLOSED_FACT_EVIDENCE_CONTRACT_DRAFTS_NOT_APPROVED",
        "jurisdiction": "BD",
        "rule_count": len(contracts),
        "contract_status": "DRAFT_INCOMPLETE",
        "rules": contracts,
        "limitations": [
            "Seed data-point names are preserved as source expressions; no database field or data type is inferred.",
            "Applicability conditions and exceptions are preserved as expressions; no executable semantics are inferred.",
            "Evidence labels are inventory identifiers, not proof that a document exists, is authentic, or is legally sufficient.",
            "No issuer, authenticity check, verification method, validity period, fact-to-evidence link, or evidence sufficiency rule is inferred.",
            "Every rule remains subject to independent Bangladesh counsel review and a separate product-owner decision.",
            "This artifact does not approve legal identity, statutory provenance, scoring, or release.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
