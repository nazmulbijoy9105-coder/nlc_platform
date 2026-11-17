from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs" / "legal" / "85_rule_provenance_manifest.json"
CATALOG = ROOT / "docs" / "legal" / "bd_statutory_source_chain.json"
BUILDER = ROOT / "tools" / "build_bd_statutory_source_chain.py"


def test_85_rule_source_chain_dossiers_are_fail_closed() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    expected = [rule["rule_id"] for rule in manifest["rules"]]
    actual = [rule["rule_id"] for rule in catalog["rules"]]

    assert catalog["canonical_rule_count"] == 85
    assert actual == expected == sorted(set(actual))
    assert catalog["jurisdiction"] == "BD"
    assert catalog["source_policy"]["primary_language"] == "BANGLA"

    for rule in catalog["rules"]:
        assert rule["source_chain_status"] == "UNRESOLVED"
        assert rule["legal_proposition"] is None
        assert rule["instrument_refs"] == []
        assert rule["amendment_events"] == []
        assert rule["operative_periods"] == []
        assert rule["legal_review_status"] == "REVIEW_REQUIRED"
        assert rule["source_review_status"] == "NOT_STARTED"


def test_builder_reproduces_committed_catalog(tmp_path: Path) -> None:
    output = tmp_path / "source_chain.json"
    subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--manifest",
            str(MANIFEST),
            "--output",
            str(output),
            "--snapshot-date",
            "2026-11-18",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    generated = json.loads(output.read_text(encoding="utf-8"))
    committed = json.loads(CATALOG.read_text(encoding="utf-8"))
    assert generated == committed


def test_builder_rejects_non_bd_manifest(tmp_path: Path) -> None:
    bad_manifest = tmp_path / "bad.json"
    output = tmp_path / "output.json"
    bad_manifest.write_text(
        json.dumps({"jurisdiction": "UK", "rules": []}),
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            sys.executable,
            str(BUILDER),
            "--manifest",
            str(bad_manifest),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "jurisdiction must be BD" in result.stderr
