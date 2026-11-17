"""Build deterministic, non-authorising finding/evidence binding snapshots.

This module is pure: it performs no database writes and never changes a
compliance outcome. ATTRIBUTED is deliberately not assigned automatically.
"""
from __future__ import annotations

import re
import uuid
from collections import defaultdict
from datetime import date, datetime
from typing import Any, Mapping, Sequence

from app.rule_engine.canonical_identity import RuleResolution, canonical_definition_hash


_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _stable_hash(value: Mapping[str, Any]) -> str:
    return canonical_definition_hash(value)


def _normalise_fact(
    fact: Mapping[str, Any], *, company_id: str, evidence_role: str
) -> dict[str, Any]:
    fact_id = str(fact.get("fact_id") or fact.get("id") or "")
    fact_key = str(fact.get("fact_key") or "")
    if not fact_id or not fact_key:
        raise ValueError("Every finding evidence item requires fact_id and fact_key")
    value_hash = _stable_hash({"value": fact.get("fact_value", fact.get("value"))})
    trust = str(fact.get("trust_level") or "USER_ASSERTED").upper()
    verification = str(fact.get("verification_status") or "UNVERIFIED").upper()
    if trust not in {"USER_ASSERTED", "AUTHORIZED_DOCUMENT_BACKED"}:
        raise ValueError("Unsupported evidence trust level")
    if verification not in {"UNVERIFIED", "VERIFIED", "REJECTED", "SUPERSEDED"}:
        raise ValueError("Unsupported evidence verification status")
    document_hash = fact.get("document_sha256")
    if document_hash is not None:
        document_hash = str(document_hash).lower()
        if not _SHA256.fullmatch(document_hash):
            raise ValueError("document_sha256 must be a lowercase SHA-256 digest")
    if trust == "AUTHORIZED_DOCUMENT_BACKED" and (
        not fact.get("document_id")
        or not fact.get("authorized_uploader_id")
        or not fact.get("uploaded_at")
        or not fact.get("source_reference")
    ):
        raise ValueError("Document-backed evidence requires document, uploader, upload time and source reference")
    if verification == "VERIFIED" and (
        not fact.get("verified_by") or not fact.get("verified_at")
        or trust != "AUTHORIZED_DOCUMENT_BACKED"
    ):
        raise ValueError("Verified evidence requires a verified document-backed source and verifier")
    snapshot = {
        "company_id": company_id,
        "company_fact_id": fact_id,
        "evidence_role": evidence_role,
        "fact_key": fact_key,
        "fact_value_snapshot": fact.get("fact_value", fact.get("value")),
        "fact_value_hash": value_hash,
        "trust_level": trust,
        "verification_status": verification,
        "observed_on": str(fact.get("observed_on") or ""),
        "source_reference": fact.get("source_reference"),
        "document_id": str(fact["document_id"]) if fact.get("document_id") else None,
        "document_sha256": document_hash,
        "asserted_by": str(fact.get("asserted_by") or ""),
        "authorized_uploader_id": str(fact["authorized_uploader_id"]) if fact.get("authorized_uploader_id") else None,
        "uploaded_at": str(fact["uploaded_at"]) if fact.get("uploaded_at") else None,
        "verified_by": str(fact["verified_by"]) if fact.get("verified_by") else None,
        "verified_at": str(fact["verified_at"]) if fact.get("verified_at") else None,
    }
    if not snapshot["asserted_by"] or not snapshot["observed_on"]:
        raise ValueError("Evidence requires asserted_by and observed_on")
    snapshot["evidence_hash"] = _stable_hash(snapshot)
    return snapshot


def _evidence_status(
    evidence: Sequence[Mapping[str, Any]], required_fact_keys: Sequence[str]
) -> str:
    if not evidence:
        return "MISSING"
    # Without an evaluator-declared required-fact set, completeness cannot be asserted.
    if not required_fact_keys:
        return "PARTIAL"
    if any(item["verification_status"] in {"REJECTED", "SUPERSEDED"} for item in evidence):
        return "INVALID"
    values_by_key: dict[str, set[str]] = defaultdict(set)
    for item in evidence:
        values_by_key[item["fact_key"]].add(item["fact_value_hash"])
    if any(len(values) > 1 for values in values_by_key.values()):
        return "CONFLICT"
    present = set(values_by_key)
    required = {str(key) for key in required_fact_keys}
    if required - present:
        return "PARTIAL"
    if any(
        item["verification_status"] != "VERIFIED"
        or item["trust_level"] != "AUTHORIZED_DOCUMENT_BACKED"
        for item in evidence
    ):
        return "UNVERIFIED"
    return "COMPLETE"


def build_finding_binding_snapshot(
    *,
    company_id: str,
    compliance_flag_id: str,
    evaluation_run_id: str | None,
    source_namespace: str,
    historical_rule_id: str,
    jurisdiction: str,
    effective_date: date,
    resolution: RuleResolution,
    finding_snapshot: Mapping[str, Any],
    evidence_facts: Sequence[Mapping[str, Any]],
    required_fact_keys: Sequence[str] = (),
    evidence_roles: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Return DB-ready immutable binding/evidence rows and deterministic hashes.

    Resolution is only identity/version selection. The output never authorises
    legal approval, historical attribution, compliance, or score release.
    """
    if not company_id or not compliance_flag_id or not evaluation_run_id or not source_namespace or not historical_rule_id or not jurisdiction:
        raise ValueError("Company, finding, jurisdiction and namespaced rule identity are required")
    if not isinstance(effective_date, date) or isinstance(effective_date, datetime):
        raise ValueError("effective_date must be a date without a time component")
    if resolution.effective_date != effective_date:
        raise ValueError("Resolution date must equal the finding's legal effective date")
    if (
        resolution.source_namespace != source_namespace
        or resolution.historical_rule_id != historical_rule_id
    ):
        raise ValueError("Resolution key must exactly match the finding's namespaced legacy identity")

    evidence_roles = evidence_roles or {}
    evidence_rows = [
        _normalise_fact(
            fact,
            company_id=company_id,
            evidence_role=evidence_roles.get(str(fact.get("fact_id") or fact.get("id")), "RULE_INPUT"),
        )
        for fact in evidence_facts
    ]
    evidence_rows.sort(key=lambda item: (item["fact_key"], item["company_fact_id"]))
    evidence_status = _evidence_status(evidence_rows, required_fact_keys)
    evidence_manifest_hash = _stable_hash({"evidence": evidence_rows})
    finding_hash = _stable_hash({"finding": finding_snapshot})

    resolved = resolution.status == "RESOLVED"
    if resolution.evaluator_artifact_hash and not _SHA256.fullmatch(resolution.evaluator_artifact_hash):
        raise ValueError("Evaluator artifact hash must be a lowercase SHA-256 digest")
    if resolved and not (
        resolution.canonical_rule_id and resolution.alias_id and resolution.revision_id
        and resolution.revision_number and _SHA256.fullmatch(resolution.definition_hash or "")
    ):
        raise ValueError("Resolved identity lacks canonical alias/revision/hash metadata")
    if not resolved and resolution.revision_id:
        raise ValueError("Unresolved identity cannot carry a selected revision")

    binding = {
        "company_id": company_id,
        "compliance_flag_id": compliance_flag_id,
        "evaluation_run_id": evaluation_run_id,
        "source_namespace": source_namespace,
        "historical_rule_id": historical_rule_id,
        "jurisdiction": jurisdiction,
        "resolution_status": resolution.status,
        "attribution_status": "CURRENT_EVALUATION",
        "canonical_rule_id": resolution.canonical_rule_id if resolved else None,
        "alias_id": resolution.alias_id if resolved else None,
        "revision_id": resolution.revision_id if resolved else None,
        "effective_date": effective_date,
        "revision_number": resolution.revision_number if resolved else None,
        "definition_hash": resolution.definition_hash if resolved else None,
        "evaluator_name": resolution.evaluator_name if resolved else None,
        "evaluator_version": resolution.evaluator_version if resolved else None,
        "evaluator_artifact_hash": resolution.evaluator_artifact_hash if resolved else None,
        "evidence_status": evidence_status,
        "evidence_manifest_hash": evidence_manifest_hash,
        "finding_snapshot": dict(finding_snapshot),
        "finding_snapshot_hash": finding_hash,
    }
    return {"binding": binding, "evidence": evidence_rows}


async def persist_finding_binding(session: Any, snapshot: Mapping[str, Any]):
    """Append binding and evidence rows in the caller's transaction; never commit.

    The caller must use the normal authenticated tenant-scoped AsyncSession.
    Database RLS and insert guards are authoritative. Historical attribution
    cannot be set through this write path.
    """
    from app.models.finding_evidence import (
        ComplianceFindingBinding,
        ComplianceFindingEvidence,
    )

    binding_values = dict(snapshot.get("binding") or {})
    evidence_values = list(snapshot.get("evidence") or [])
    if binding_values.get("attribution_status") != "CURRENT_EVALUATION":
        raise ValueError("This write path only records current evaluations; historical attribution requires separate review")
    if not binding_values.get("company_id") or not binding_values.get("compliance_flag_id"):
        raise ValueError("Finding binding requires a tenant and compliance flag")
    def _uuid_fields(values: dict[str, Any], fields: Sequence[str]) -> None:
        for field in fields:
            value = values.get(field)
            if value is not None and not isinstance(value, uuid.UUID):
                values[field] = uuid.UUID(str(value))

    def _date_value(value: Any, field: str) -> date:
        if isinstance(value, datetime):
            raise ValueError(f"{field} must be a date, not a datetime")
        if isinstance(value, date):
            return value
        try:
            return date.fromisoformat(str(value))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field} must be an ISO-8601 date") from exc

    def _datetime_value(value: Any, field: str) -> datetime | None:
        if value is None:
            return None
        parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError(f"{field} must include a timezone offset")
        return parsed

    binding_values.setdefault("id", uuid.uuid4())
    _uuid_fields(binding_values, ("id", "company_id", "compliance_flag_id", "evaluation_run_id",
                                  "attribution_reviewed_by", "canonical_rule_id", "alias_id", "revision_id"))
    binding_values["effective_date"] = _date_value(binding_values.get("effective_date"), "effective_date")
    binding = ComplianceFindingBinding(**binding_values)
    session.add(binding)
    await session.flush()
    rows = []
    for evidence in evidence_values:
        values = dict(evidence)
        _uuid_fields(values, ("company_id", "company_fact_id", "document_id", "asserted_by",
                              "authorized_uploader_id", "verified_by"))
        values["observed_on"] = _date_value(values.get("observed_on"), "observed_on")
        for field in ("uploaded_at", "verified_at"):
            values[field] = _datetime_value(values.get(field), field)
        rows.append(ComplianceFindingEvidence(binding_id=binding.id, **values))
    if rows:
        session.add_all(rows)
        await session.flush()
    return binding
