from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE_AUDIT = ROOT / "tools" / "audit_rule_source_reconciliation.py"
CONTRACT_BUILDER = ROOT / "tools" / "build_rule_fact_evidence_contracts.py"


def test_85_rule_fact_evidence_contracts_are_complete_and_fail_closed(tmp_path: Path) -> None:
    source_report = tmp_path / "source_reconciliation.json"
    contract_report = tmp_path / "fact_evidence_contracts.json"

    subprocess.run(
        [sys.executable, str(SOURCE_AUDIT), "--output", str(source_report)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        [
            sys.executable,
            str(CONTRACT_BUILDER),
            "--input",
            str(source_report),
            "--output",
            str(contract_report),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    source = json.loads(source_report.read_text(encoding="utf-8"))
    report = json.loads(contract_report.read_text(encoding="utf-8"))
    source_by_id = {rule["historical_rule_id"]: rule for rule in source["rules"]}
    contract_by_id = {rule["historical_rule_id"]: rule for rule in report["rules"]}
    for rule_id, source_rule in source_by_id.items():
        declared_inputs = {
            condition.strip("'\\\"")
            for condition in source_rule["applicability_contract"]["required_conditions"]
        }
        contract_fact_keys = {
            fact["fact_key"] for fact in contract_by_id[rule_id]["facts"]
        }
        assert declared_inputs <= contract_fact_keys, (
            f"{rule_id} omits applicability-required facts: "
            f"{sorted(declared_inputs - contract_fact_keys)}"
        )

    assert report["baseline_commit"] == "cefe6f169cd283d2e61071a3b7438657da04321e"
    assert report["report_type"] == "FAIL_CLOSED_FACT_EVIDENCE_CONTRACT_DRAFTS_NOT_APPROVED"
    assert report["rule_count"] == 85
    assert report["contract_status"] == "DRAFT_INCOMPLETE"

    ids = [rule["historical_rule_id"] for rule in report["rules"]]
    assert ids == sorted(set(ids))
    for rule in report["rules"]:
        assert rule["contract_status"] == "DRAFT_INCOMPLETE"
        assert rule["legal_review_status"] == "REVIEW_REQUIRED"
        assert rule["product_decision_status"] == "NOT_REVIEWED"
        assert all(fact["data_type"] == "UNSPECIFIED" for fact in rule["facts"])
        assert all(fact["mapping_status"] == "REQUIRES_DOMAIN_MAPPING" for fact in rule["facts"])
        assert all(item["issuer"] == "UNSPECIFIED" for item in rule["evidence_items"])
        assert all(item["verification_method"] == "UNSPECIFIED" for item in rule["evidence_items"])
        assert all(item["fact_keys_supported"] == [] for item in rule["evidence_items"])

    source_rules_by_id = {
        rule["historical_rule_id"]: rule
        for rule in json.loads(source_report.read_text(encoding="utf-8"))["rules"]
    }
    for rule in report["rules"]:
        actual_fact_keys = {fact["fact_key"] for fact in rule["facts"]}
        required_applicability_facts = {
            condition[1:-1]
            if len(condition) >= 2
            and condition[0] == condition[-1]
            and condition[0] in {"'", '"'}
            else condition
            for condition in source_rules_by_id[rule["historical_rule_id"]][
                "applicability_contract"
            ]["required_conditions"]
        }
        assert required_applicability_facts <= actual_fact_keys, (
            f"{rule['historical_rule_id']} missing applicability facts: "
            f"{sorted(required_applicability_facts - actual_fact_keys)}"
        )

    agm005 = next(rule for rule in report["rules"] if rule["historical_rule_id"] == "AGM-005")
    source_rules = json.loads(source_report.read_text(encoding="utf-8"))["rules"]
    agm005_source = next(
        rule for rule in source_rules if rule["historical_rule_id"] == "AGM-005"
    )
    agm005_fact_keys = {fact["fact_key"] for fact in agm005["facts"]}

    expected_agm005_facts = {
        "agm_held",
        "member_count",
        "members_present_at_agm",
        "quorum_required",
        "agm_quorum_evidence_ref",
    }
    assert expected_agm005_facts <= agm005_fact_keys, (
        "AGM-005 is missing required quorum facts: "
        f"{sorted(expected_agm005_facts - agm005_fact_keys)}"
    )

    seed_fact_keys = {
        fact[1:-1]
        if len(fact) >= 2 and fact[0] == fact[-1] and fact[0] in {"'", '"'}
        else fact
        for fact in agm005_source["seed_fact_inputs"]
    }
    assert seed_fact_keys <= agm005_fact_keys, (
        "AGM-005 dropped original seed facts: "
        f"{sorted(seed_fact_keys - agm005_fact_keys)}"
    )
    assert any(
        fact["fact_key"] == "member_count"
        and "not more than six members" in fact["source_expression"]
        and fact["data_type"] == "UNSPECIFIED"
        and fact["evidence_links"] == []
        and fact["mapping_status"] == "REQUIRES_DOMAIN_MAPPING"
        for fact in agm005["facts"]
    )
    assert "member_count" in {fact["fact_key"] for fact in agm005["facts"]}
    member_count = next(
        fact for fact in agm005["facts"] if fact["fact_key"] == "member_count"
    )
    assert member_count["source_expression"] == "statutory_registry.requirement"
    assert "not more than six members" in member_count["source_evidence"]
    assert member_count["data_type"] == "UNSPECIFIED"
    assert member_count["mapping_status"] == "REQUIRES_DOMAIN_MAPPING"
    assert member_count["evidence_links"] == []
    assert "agm_quorum_evidence_ref" in {fact["fact_key"] for fact in agm005["facts"]}
    assert "REQUIRES_DOMAIN_MAPPING" in {
        condition["mapping_status"] for condition in agm005["applicability_conditions"]
    }

    inc001 = next(rule for rule in report["rules"] if rule["historical_rule_id"] == "INC-001")
    assert inc001["identity_resolution"] == "AMBIGUOUS_KNOWN_PRODUCTION_SEED_COLLISION"
    assert inc001["contract_status"] == "DRAFT_INCOMPLETE"


def test_builder_rejects_non_pinned_or_incomplete_source_report(tmp_path: Path) -> None:
    source_report = tmp_path / "bad_source.json"
    output = tmp_path / "out.json"
    source_report.write_text(
        json.dumps(
            {
                "baseline_commit": "wrong",
                "report_type": "AST_SOURCE_DEFINITION_RECONCILIATION_NOT_LEGAL_APPROVAL",
                "rules": [],
            }
        ),
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            sys.executable,
            str(CONTRACT_BUILDER),
            "--input",
            str(source_report),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "unexpected AST audit baseline" in result.stderr
