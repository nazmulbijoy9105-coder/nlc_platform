"""Fail-closed structural tests for the Bangladesh 85-rule provenance manifest."""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "docs" / "legal" / "85_rule_provenance_manifest.json"
SCHEMA_PATH = ROOT / "docs" / "legal" / "85_rule_provenance_manifest.schema.json"


def _manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_manifest_contains_exactly_85_unique_canonical_rule_ids() -> None:
    manifest = _manifest()
    rules = manifest["rules"]
    ids = [item["rule_id"] for item in rules]

    assert manifest["canonical_rule_count"] == 85
    assert len(ids) == 85
    assert len(set(ids)) == 85
    assert ids == sorted(ids)


def test_manifest_is_fail_closed_and_does_not_invent_legal_approval() -> None:
    manifest = _manifest()

    assert manifest["jurisdiction"] == "BD"
    assert manifest["status_policy"] == "FAIL_CLOSED"
    assert manifest["canonical_id_inventory"]["source_revision"] == (
        "cefe6f169cd283d2e61071a3b7438657da04321e"
    )
    assert manifest["canonical_id_inventory"]["source_revision_status"] == (
        "PINNED"
    )

    for rule in manifest["rules"]:
        assert rule["jurisdiction"] == "BD"
        assert rule["record_status"] == "UNRESOLVED"
        assert rule["identity"]["source_namespace"] is None
        assert rule["identity"]["canonical_rule_uuid"] is None
        assert rule["operative_effective_date"]["from"] is None
        assert rule["operative_effective_date"]["status"] == "UNRESOLVED"
        assert rule["legal_review"]["status"] == "REVIEW_REQUIRED"
        assert rule["legal_review"]["reviewed_payload_sha256"] is None
        assert rule["product_decision"]["status"] == "NOT_REVIEWED"


def test_legacy_inc002_is_quarantined_and_inc001_collision_is_not_resolved() -> None:
    manifest = _manifest()

    inc002 = [
        item for item in manifest["legacy_candidates"]
        if item["historical_rule_id"] == "INC-002"
    ]
    assert len(inc002) == 1
    assert inc002[0]["disposition"] == "QUARANTINED_PENDING_IDENTITY_REVIEW"
    assert inc002[0]["canonical_rule_uuid"] is None

    inc001 = [
        item for item in manifest["known_identity_conflicts"]
        if item["historical_rule_id"] == "INC-001"
    ]
    assert len(inc001) == 1
    assert inc001[0]["status"] == (
        "AMBIGUOUS_PENDING_SOURCE_NAMESPACE_RECONCILIATION"
    )
    assert "merge_definitions" in inc001[0]["prohibited_actions"]


def test_manifest_schema_and_manifest_use_json_documents() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    manifest = _manifest()

    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$defs"]["rule"]["additionalProperties"] is False
    assert len(manifest["rules"]) == 85
