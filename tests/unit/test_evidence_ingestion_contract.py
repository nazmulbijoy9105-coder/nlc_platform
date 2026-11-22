import hashlib
import json

import pytest

from scripts.ingest_finding_evidence import validate_manifest


def _row(**overrides):
    fact_value = {"value": True}
    fact_canonical = json.dumps(
        {"value": fact_value["value"]},
        sort_keys=True,
        separators=(",", ":"),
    )
    evidence_canonical = '{"binding_id":"fixture"}'
    row = {
        "binding_id": "00000000-0000-0000-0000-000000000001",
        "company_id": "00000000-0000-0000-0000-000000000002",
        "company_fact_id": "00000000-0000-0000-0000-000000000003",
        "evidence_role": "PRIMARY",
        "fact_key": "certificate_obtained",
        "fact_value_snapshot": fact_value,
        "fact_value_canonical": fact_canonical,
        "evidence_canonical": evidence_canonical,
        "fact_value_hash": hashlib.sha256(
            json.dumps(
                {"value": {"value": True}},
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest(),
        "evidence_hash": hashlib.sha256(
            evidence_canonical.encode("utf-8")
        ).hexdigest(),
        "trust_level": "USER_ASSERTED",
        "verification_status": "UNVERIFIED",
        "observed_on": "2026-11-22",
        "asserted_by": "00000000-0000-0000-0000-000000000004",
    }
    row.update(overrides)
    return row


def test_evidence_ingestion_accepts_valid_unverified_user_assertion():
    assert validate_manifest([_row()]) == [_row()]


def test_evidence_ingestion_rejects_hash_mismatch():
    with pytest.raises(ValueError, match="fact_value_hash mismatch"):
        validate_manifest([_row(fact_value_hash="0" * 64)])


def test_evidence_ingestion_rejects_verified_without_document():
    with pytest.raises(ValueError, match="cannot be VERIFIED"):
        validate_manifest([
            _row(
                verification_status="VERIFIED",
            )
        ])
