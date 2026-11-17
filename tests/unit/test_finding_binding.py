from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.rule_engine.canonical_identity import RuleResolution
from app.rule_engine.finding_binding import (
    build_finding_binding_snapshot,
    persist_finding_binding,
)


def _resolution(status="RESOLVED"):
    return RuleResolution(
        status=status,
        source_namespace="engine-build:abc",
        historical_rule_id="AGM-001",
        effective_date=date(2026, 1, 1),
        canonical_rule_id="00000000-0000-0000-0000-000000000001" if status == "RESOLVED" else None,
        alias_id="00000000-0000-0000-0000-000000000002" if status == "RESOLVED" else None,
        revision_id="00000000-0000-0000-0000-000000000003" if status == "RESOLVED" else None,
        revision_number=1 if status == "RESOLVED" else None,
        approval_state="REVIEW_REQUIRED",
        definition_hash="a" * 64 if status == "RESOLVED" else None,
        evaluator_name="agm_evaluator" if status == "RESOLVED" else None,
        evaluator_version="2.1.0" if status == "RESOLVED" else None,
        evaluator_artifact_hash="b" * 64 if status == "RESOLVED" else None,
    )


def _fact(**overrides):
    row = {
        "fact_id": "00000000-0000-0000-0000-000000000101",
        "fact_key": "agm_held",
        "fact_value": False,
        "trust_level": "AUTHORIZED_DOCUMENT_BACKED",
        "verification_status": "VERIFIED",
        "observed_on": "2025-12-31",
        "source_reference": "document:doc-1",
        "document_id": "00000000-0000-0000-0000-000000000201",
        "document_sha256": "c" * 64,
        "asserted_by": "00000000-0000-0000-0000-000000000301",
        "authorized_uploader_id": "00000000-0000-0000-0000-000000000301",
        "uploaded_at": "2025-12-30T10:00:00+00:00",
        "verified_by": "00000000-0000-0000-0000-000000000302",
        "verified_at": "2025-12-31T10:00:00+00:00",
    }
    row.update(overrides)
    return row


def _build(resolution=None, facts=None, **overrides):
    args = {
        "company_id": "00000000-0000-0000-0000-000000000401",
        "compliance_flag_id": "00000000-0000-0000-0000-000000000402",
        "evaluation_run_id": "00000000-0000-0000-0000-000000000403",
        "source_namespace": "engine-build:abc",
        "historical_rule_id": "AGM-001",
        "jurisdiction": "BD",
        "effective_date": date(2026, 1, 1),
        "resolution": resolution or _resolution(),
        "finding_snapshot": {"evaluation_state": "NOT_COMPLIANT", "score_impact": 0},
        "evidence_facts": facts if facts is not None else [_fact()],
    }
    args.update(overrides)
    return build_finding_binding_snapshot(**args)


def test_binding_captures_exact_canonical_alias_revision_and_evaluator():
    result = _build()
    binding = result["binding"]
    assert binding["canonical_rule_id"] == "00000000-0000-0000-0000-000000000001"
    assert binding["alias_id"] == "00000000-0000-0000-0000-000000000002"
    assert binding["revision_id"] == "00000000-0000-0000-0000-000000000003"
    assert binding["evaluator_artifact_hash"] == "b" * 64
    assert binding["jurisdiction"] == "BD"
    assert binding["finding_snapshot"]["evaluation_state"] == "NOT_COMPLIANT"
    assert result["evidence"][0]["fact_value_snapshot"] is False
    assert binding["resolution_status"] == "RESOLVED"


def test_identity_resolution_does_not_imply_legal_approval_or_attribution():
    binding = _build(required_fact_keys=["agm_held"])["binding"]
    assert binding["attribution_status"] == "CURRENT_EVALUATION"
    assert binding["evidence_status"] == "COMPLETE"
    assert _resolution().approval_state == "REVIEW_REQUIRED"


def test_unresolved_legacy_identifier_is_preserved_without_canonical_assignment():
    binding = _build(resolution=_resolution("UNRESOLVED"))["binding"]
    assert binding["historical_rule_id"] == "AGM-001"
    assert binding["canonical_rule_id"] is None
    assert binding["revision_id"] is None
    assert binding["resolution_status"] == "UNRESOLVED"


def test_missing_required_fact_is_partial_not_complete():
    binding = _build(required_fact_keys=["agm_held", "auditor_appointed"])["binding"]
    assert binding["evidence_status"] == "PARTIAL"


def test_user_asserted_evidence_is_not_marked_complete():
    fact = _fact(
        trust_level="USER_ASSERTED",
        verification_status="UNVERIFIED",
        source_reference=None,
        document_id=None,
        document_sha256=None,
        authorized_uploader_id=None,
        uploaded_at=None,
        verified_by=None,
        verified_at=None,
    )
    assert _build(facts=[fact])["binding"]["evidence_status"] == "UNVERIFIED"


def test_conflicting_fact_values_are_detected():
    second = _fact(fact_id="fact-2", fact_value=True)
    assert _build(facts=[_fact(), second])["binding"]["evidence_status"] == "CONFLICT"


def test_rejected_evidence_is_invalid():
    fact = _fact(verification_status="REJECTED", verified_by=None, verified_at=None)
    assert _build(facts=[fact])["binding"]["evidence_status"] == "INVALID"


def test_resolution_key_mismatch_is_rejected():
    with pytest.raises(ValueError, match="exactly match"):
        _build(historical_rule_id="INC-002")


def test_resolution_date_mismatch_is_rejected():
    with pytest.raises(ValueError, match="effective date"):
        _build(effective_date=date(2025, 1, 1))


def test_resolved_identity_without_alias_metadata_is_rejected():
    incomplete = RuleResolution(
        status="RESOLVED",
        source_namespace="engine-build:abc",
        historical_rule_id="AGM-001",
        effective_date=date(2026, 1, 1),
        canonical_rule_id="canonical",
        revision_id="revision",
        revision_number=1,
        definition_hash="a" * 64,
    )
    with pytest.raises(ValueError, match="alias/revision/hash"):
        _build(resolution=incomplete)


def test_evidence_without_source_actor_is_rejected():
    with pytest.raises(ValueError, match="asserted_by"):
        _build(facts=[_fact(asserted_by="")])



def test_datetime_effective_date_is_rejected():
    with pytest.raises(ValueError, match="without a time"):
        _build(effective_date=datetime(2026, 1, 1, 12, 0))


@pytest.mark.asyncio
async def test_persistence_rejects_tampered_evidence_payload_before_insert():
    session = MagicMock()
    result = _build(required_fact_keys=["agm_held"])
    result["evidence"][0]["fact_value_snapshot"] = True
    with pytest.raises(ValueError, match="Evidence manifest digest"):
        await persist_finding_binding(session, result)
    assert not session.add.called


@pytest.mark.asyncio
async def test_persistence_rejects_tampered_finding_payload_before_insert():
    session = MagicMock()
    result = _build(required_fact_keys=["agm_held"])
    result["binding"]["finding_snapshot"]["evaluation_state"] = "COMPLIANT"
    with pytest.raises(ValueError, match="Finding snapshot digest"):
        await persist_finding_binding(session, result)
    assert not session.add.called


@pytest.mark.asyncio
async def test_persistence_flushes_in_caller_transaction_without_commit():
    session = MagicMock()
    session.flush = AsyncMock()
    session.add = MagicMock()
    session.add_all = MagicMock()
    result = _build(required_fact_keys=["agm_held"])

    binding = await persist_finding_binding(session, result)

    assert binding.id is not None
    assert session.add.call_count == 1
    assert session.add_all.call_count == 1
    assert session.flush.await_count == 2
    assert not session.commit.called


def test_persistence_rejects_historical_attribution_shortcut():
    session = MagicMock()
    result = _build(required_fact_keys=["agm_held"])
    result["binding"]["attribution_status"] = "ATTRIBUTED"

    with pytest.raises(ValueError, match="historical attribution"):
        import asyncio
        asyncio.run(persist_finding_binding(session, result))
