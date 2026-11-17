from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools" / "audit_rule_source_reconciliation.py"


def test_ast_rule_source_reconciliation_is_complete_and_fail_closed(tmp_path: Path) -> None:
    output = tmp_path / "rule_source_reconciliation.json"
    subprocess.run(
        [sys.executable, str(SCRIPT), "--output", str(output)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    report = json.loads(output.read_text(encoding="utf-8"))

    assert report["baseline_commit"] == "cefe6f169cd283d2e61071a3b7438657da04321e"
    assert report["report_type"] == "AST_SOURCE_DEFINITION_RECONCILIATION_NOT_LEGAL_APPROVAL"
    assert report["rule_count"] == 85
    assert len(report["rules"]) == 85

    ids = [rule["historical_rule_id"] for rule in report["rules"]]
    assert ids == sorted(set(ids))
    for rule in report["rules"]:
        assert rule["identity_resolution"] in {
            "UNRESOLVED",
            "AMBIGUOUS_KNOWN_PRODUCTION_SEED_COLLISION",
        }
        assert rule["historical_origin"] == "NOT_ESTABLISHED"
        assert rule["legal_review_status"] == "REVIEW_REQUIRED"
        assert rule["product_decision_status"] == "NOT_REVIEWED"
        assert rule["evidence_contract"]["status"] in {"MAPPED", "MISSING"}
        assert rule["applicability_contract"]["status"] in {"MAPPED", "MISSING"}
        assert isinstance(rule["seed_fact_inputs"], list)
        assert isinstance(rule["fact_evidence_gaps"], list)
        assert all(
            len(candidate["definition_sha256"]) == 64
            and len(candidate["blob_sha"]) == 40
            for candidate in rule["source_candidates"]
        )

    inc001 = next(rule for rule in report["rules"] if rule["historical_rule_id"] == "INC-001")
    assert inc001["identity_resolution"] == "AMBIGUOUS_KNOWN_PRODUCTION_SEED_COLLISION"
    assert "statutory_registry" in {
        candidate["artifact"] for candidate in inc001["source_candidates"]
    }
    assert inc001["evidence_contract"]["status"] in {"MAPPED", "MISSING"}
    assert inc001["applicability_contract"]["status"] in {"MAPPED", "MISSING"}

    assert all(
        rule["seed_vs_statutory_basis"] != "EXACT_TEXT_MATCH"
        or "statutory_registry" in {candidate["artifact"] for candidate in rule["source_candidates"]}
        for rule in report["rules"]
    )
