"""Canonical integrity checks for immutable compliance evaluation runs.

A historical run without its original rule-outcome snapshot cannot be
reconstructed from the current catalogue and must never be treated as
fully reconciled or PDF-eligible.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from app.compliance.rule_outcome_ledger import hash_rule_outcomes_snapshot

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_UNMAPPED_SOURCE = "ENGINE_FINDING_WITHOUT_ACTIVE_CATALOGUE_RULE"


def calculate_evaluation_score_hash(
    *,
    previous_hash: str | None,
    company_id: Any,
    score: int | None,
    risk_band: Any,
    calculated_at: Any,
    engine_version: str,
    trigger_source: str,
    flags_snapshot: list[dict[str, Any]],
    fact_provenance_snapshot: list[dict[str, Any]],
    score_breakdown_snapshot: dict[str, Any] | None,
    rule_outcomes_hash: str,
    rule_outcomes_snapshot: list[dict[str, Any]],
) -> str:
    """Reproduce the exact canonical SHA-256 material persisted by the evaluator."""
    risk_band_value = getattr(risk_band, "value", risk_band)
    hash_material = json.dumps(
        {
            "previous_hash": previous_hash or "GENESIS",
            "company_id": str(company_id),
            "score": score,
            "risk_band": risk_band_value,
            "calculated_at": calculated_at.isoformat(),
            "engine_version": engine_version,
            "trigger_source": trigger_source,
            "flags_snapshot": flags_snapshot,
            "fact_provenance_snapshot": fact_provenance_snapshot,
            "score_breakdown_snapshot": score_breakdown_snapshot,
            "rule_outcomes_hash": rule_outcomes_hash,
            "rule_outcomes_snapshot": rule_outcomes_snapshot,
        },
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(hash_material.encode()).hexdigest()


def evaluation_run_integrity_problems(run: Any) -> list[str]:
    """Return stable problem codes; never infer or repair missing historical evidence."""
    problems: list[str] = []
    outcomes = getattr(run, "rule_outcomes_snapshot", None)
    outcomes_hash = getattr(run, "rule_outcomes_hash", None)

    if not isinstance(outcomes, list) or not outcomes:
        problems.append("RULE_OUTCOME_SNAPSHOT_MISSING")
        outcomes = []
    else:
        if any(
            not isinstance(item, dict)
            or not isinstance(item.get("rule_id"), str)
            or not item.get("rule_id")
            for item in outcomes
        ):
            problems.append("RULE_OUTCOME_SNAPSHOT_MALFORMED")
        else:
            rule_ids = [item["rule_id"] for item in outcomes]
            if len(rule_ids) != len(set(rule_ids)):
                problems.append("RULE_OUTCOME_IDS_DUPLICATED")

            catalogue_count = sum(
                1 for item in outcomes
                if item.get("assessment_source") != _UNMAPPED_SOURCE
            )
            if getattr(run, "rule_catalogue_count", None) != catalogue_count:
                problems.append("RULE_CATALOGUE_COUNT_MISMATCH")
            if any(
                item.get("assessment_source") == _UNMAPPED_SOURCE
                for item in outcomes
            ):
                problems.append("UNMAPPED_RULE_OUTCOME_PRESENT")
            allowed_sources = {
                "ENGINE_FINDING",
                "NO_FINDING_EMITTED_NOT_PROOF_OF_COMPLIANCE",
                _UNMAPPED_SOURCE,
            }
            if any(item.get("assessment_source") not in allowed_sources for item in outcomes):
                problems.append("RULE_OUTCOME_SOURCE_UNRECOGNIZED")
            if any(not isinstance(item.get("findings"), list) for item in outcomes):
                problems.append("RULE_OUTCOME_FINDINGS_MALFORMED")

    outcomes_hash_valid = isinstance(outcomes_hash, str) and bool(
        _SHA256_RE.fullmatch(outcomes_hash)
    )
    if not outcomes_hash_valid:
        problems.append(
            "RULE_OUTCOME_HASH_MISSING"
            if not outcomes_hash
            else "RULE_OUTCOME_HASH_MALFORMED"
        )
    elif outcomes and hash_rule_outcomes_snapshot(outcomes) != outcomes_hash:
        problems.append("RULE_OUTCOME_HASH_MISMATCH")

    score_hash = getattr(run, "score_hash", None)
    if not isinstance(score_hash, str) or not score_hash:
        problems.append("SCORE_HASH_MISSING")
    elif not _SHA256_RE.fullmatch(score_hash):
        problems.append("SCORE_HASH_MALFORMED")

    previous_hash = getattr(run, "previous_hash", None)
    if previous_hash is not None and (
        not isinstance(previous_hash, str) or not _SHA256_RE.fullmatch(previous_hash)
    ):
        problems.append("PREVIOUS_HASH_MALFORMED")

    flags_snapshot = getattr(run, "flags_snapshot", None)
    if not isinstance(flags_snapshot, list) or any(
        not isinstance(item, dict) for item in flags_snapshot
    ):
        problems.append("FLAGS_SNAPSHOT_MALFORMED")

    fact_provenance_snapshot = getattr(run, "fact_provenance_snapshot", None)
    if not isinstance(fact_provenance_snapshot, list):
        problems.append("FACT_PROVENANCE_SNAPSHOT_MALFORMED")

    score_breakdown_snapshot = getattr(run, "score_breakdown_snapshot", None)
    if not isinstance(score_breakdown_snapshot, dict):
        problems.append("SCORE_BREAKDOWN_SNAPSHOT_MISSING")

    calculated_at = getattr(run, "calculated_at", None)
    engine_version = getattr(run, "engine_version", None)
    trigger_source = getattr(run, "trigger_source", None)
    company_id = getattr(run, "company_id", None)
    if (
        outcomes
        and outcomes_hash_valid
        and isinstance(outcomes_hash, str)
        and score_hash
        and _SHA256_RE.fullmatch(score_hash)
        and isinstance(flags_snapshot, list)
        and all(isinstance(item, dict) for item in flags_snapshot)
        and isinstance(fact_provenance_snapshot, list)
        and isinstance(score_breakdown_snapshot, dict)
        and calculated_at is not None
        and callable(getattr(calculated_at, "isoformat", None))
        and engine_version
        and trigger_source
        and company_id is not None
    ):
        expected_score_hash = calculate_evaluation_score_hash(
            previous_hash=previous_hash,
            company_id=company_id,
            score=getattr(run, "score", None),
            risk_band=getattr(run, "risk_band", None),
            calculated_at=calculated_at,
            engine_version=engine_version,
            trigger_source=trigger_source,
            flags_snapshot=flags_snapshot,
            fact_provenance_snapshot=fact_provenance_snapshot,
            score_breakdown_snapshot=score_breakdown_snapshot,
            rule_outcomes_hash=outcomes_hash,
            rule_outcomes_snapshot=outcomes,
        )
        if expected_score_hash != score_hash:
            problems.append("SCORE_HASH_MISMATCH")

    return problems
