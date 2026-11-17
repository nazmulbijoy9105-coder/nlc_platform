from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CATALOG_PATH = ROOT / "docs" / "legal" / "85_rule_source_observation_catalog.json"
MANIFEST_PATH = ROOT / "docs" / "legal" / "85_rule_provenance_manifest.json"


def test_source_observation_catalog_is_pinned_and_covers_canonical_inventory() -> None:
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    assert catalog["schema_version"] == "1.0.0"
    assert catalog["observation_status"] == (
        "SOURCE_PRESENCE_ONLY_NOT_IDENTITY_OR_LEGAL_PROVENANCE"
    )
    assert catalog["repository_commit"] == manifest["canonical_id_inventory"][
        "source_revision"
    ]
    assert len(catalog["rules"]) == 85
    assert [item["historical_rule_id"] for item in catalog["rules"]] == [
        item["rule_id"] for item in manifest["rules"]
    ]

    artifacts = {item["key"]: item for item in catalog["source_artifacts"]}
    assert set(artifacts) == {
        "statutory_registry",
        "seed_catalogue",
        "runtime_engine",
        "evidence_contract",
        "applicability_contract",
        "legal_reconciliation",
        "rescue_registry",
    }
    for artifact in artifacts.values():
        assert len(artifact["blob_sha"]) == 40
        assert artifact["path"]
        assert artifact["observed_rule_ids"]

    for key in (
        "statutory_registry",
        "seed_catalogue",
        "runtime_engine",
        "legal_reconciliation",
        "rescue_registry",
    ):
        assert len(artifacts[key]["observed_rule_ids"]) == 85

    for rule in catalog["rules"]:
        observed = {item["artifact_key"] for item in rule["observations"]}
        assert {
            "statutory_registry",
            "seed_catalogue",
            "runtime_engine",
            "legal_reconciliation",
            "rescue_registry",
        } <= observed


def test_source_observations_do_not_resolve_known_inc001_collision() -> None:
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    inc001 = next(
        item for item in catalog["rules"] if item["historical_rule_id"] == "INC-001"
    )

    assert len(inc001["observations"]) >= 5
    assert "SOURCE_PRESENCE_ONLY" in catalog["observation_status"]
    assert "INC-001" in catalog["limitations"][1]
    assert "No canonical UUID" in catalog["limitations"][3]
