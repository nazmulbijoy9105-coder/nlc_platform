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

from sqlalchemy import select

from app.models.compliance import ComplianceEvaluationRun
from app.compliance.rule_outcome_ledger import hash_rule_outcomes_snapshot

from canonical_architecture.rjsc_scope import (
    RJSC_RULE_SCOPE,
    RJSC_SCOPE_VERSION,
    is_rjsc_rule_in_scope,
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_UNMAPPED_SOURCE = "ENGINE_FINDING_WITHOUT_ACTIVE_CATALOGUE_RULE"
UNRELEASED_REASON_GATE_CLOSED = "LEGAL_SCORE_RELEASE_GATE_CLOSED"
UNRELEASED_REASON_INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE_FOR_SCORE"
_UNRELEASED_REASONS = frozenset(
    {UNRELEASED_REASON_GATE_CLOSED, UNRELEASED_REASON_INSUFFICIENT_EVIDENCE}
)


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
            # New-format snapshots must carry one consistent versioned scope
            # identity on every catalogue row. Historical pre-scope runs remain
            # readable, but cannot be silently upgraded to this scope version.
            scoped_rows = [
                item for item in outcomes
                if "scope_class" in item or "scope_version" in item
            ]
            if scoped_rows:
                if len(scoped_rows) != len(outcomes) or any(
                    item.get("scope_version") != RJSC_SCOPE_VERSION
                    or item.get("scope_class") != (
                        "IN_SCOPE_RJSC"
                        if is_rjsc_rule_in_scope(item["rule_id"])
                        else "OUT_OF_SCOPE"
                    )
                    for item in outcomes
                ):
                    problems.append("RJSC_SCOPE_IDENTITY_MISMATCH")
                if set(rule_ids) != set(RJSC_RULE_SCOPE):
                    problems.append("RJSC_RULE_OUTCOME_SCOPE_COVERAGE_MISMATCH")

            catalogue_count = sum(
                1 for item in outcomes
                if item.get("assessment_source") not in {
                    _UNMAPPED_SOURCE,
                    "CATALOGUE_IDENTITY_CONFLICT_NOT_ATTRIBUTED",
                }
            )
            if getattr(run, "rule_catalogue_count", None) != catalogue_count:
                problems.append("RULE_CATALOGUE_COUNT_MISMATCH")
            allowed_sources = {
                "ENGINE_FINDING",
                "NO_FINDING_EMITTED_NOT_PROOF_OF_COMPLIANCE",
                "IDENTITY_MISMATCH_NOT_ATTRIBUTED",
                "ENGINE_FINDING_WITH_IDENTITY_CONFLICT",
                _UNMAPPED_SOURCE,
                "CATALOGUE_IDENTITY_CONFLICT_NOT_ATTRIBUTED",
                "OUT_OF_SCOPE",
            }
            if any(item.get("assessment_source") not in allowed_sources for item in outcomes):
                problems.append("RULE_OUTCOME_SOURCE_UNRECOGNIZED")
            if any(
                not isinstance(item.get("findings"), list)
                or any(not isinstance(finding, dict) for finding in item.get("findings", []))
                for item in outcomes
            ):
                problems.append("RULE_OUTCOME_FINDINGS_MALFORMED")
            else:
                for item in outcomes:
                    source = item.get("assessment_source")
                    findings = item["findings"]
                    if source == "OUT_OF_SCOPE":
                        if (
                            item.get("scope_class") != "OUT_OF_SCOPE"
                            or not item.get("scope_version")
                            or item.get("outcome_state") != "OUT_OF_SCOPE"
                            or findings
                            or item.get("identity_conflicts")
                        ):
                            problems.append("RJSC_OUT_OF_SCOPE_OUTCOME_MALFORMED")
                            break
                        continue
                    if source == "NO_FINDING_EMITTED_NOT_PROOF_OF_COMPLIANCE" and findings:
                        problems.append("RULE_OUTCOME_SOURCE_FINDINGS_CONTRADICTION")
                        break
                    if source == "ENGINE_FINDING" and not findings:
                        problems.append("RULE_OUTCOME_SOURCE_FINDINGS_CONTRADICTION")
                        break
                    conflicts = item.get("identity_conflicts", [])
                    if not isinstance(conflicts, list) or any(
                        not isinstance(conflict, dict)
                        or conflict.get("resolution_status") != "UNRESOLVED_STATUTORY_IDENTITY_MISMATCH"
                        or not isinstance(conflict.get("binding_reason"), str)
                        or not conflict.get("binding_reason", "").strip()
                        or "flag_code" not in conflict
                        or "flag_statutory_basis" not in conflict
                        or "engine_statutory_basis" not in conflict
                        or "catalogue_statutory_basis" not in conflict
                        or (
                            conflict.get("flag_code") is not None
                            and (
                                not isinstance(conflict.get("flag_code"), str)
                                or not conflict.get("flag_code", "").strip()
                            )
                        )
                        for conflict in conflicts
                    ):
                        problems.append("RULE_OUTCOME_IDENTITY_CONFLICTS_MALFORMED")
                        break
                    if source in {
                        "ENGINE_FINDING",
                        "NO_FINDING_EMITTED_NOT_PROOF_OF_COMPLIANCE",
                    } and conflicts:
                        problems.append("RULE_OUTCOME_SOURCE_CONFLICT_CONTRADICTION")
                        break
                    if source == _UNMAPPED_SOURCE and not findings:
                        problems.append("RULE_OUTCOME_SOURCE_FINDINGS_CONTRADICTION")
                        break
                    if source == "CATALOGUE_IDENTITY_CONFLICT_NOT_ATTRIBUTED" and (
                        findings or not conflicts
                    ):
                        problems.append("RULE_OUTCOME_IDENTITY_CONFLICT_SHAPE_INVALID")
                        break
                    if source == "IDENTITY_MISMATCH_NOT_ATTRIBUTED" and (
                        findings or not conflicts
                    ):
                        problems.append("RULE_OUTCOME_IDENTITY_CONFLICT_SHAPE_INVALID")
                        break
                    if source == "ENGINE_FINDING_WITH_IDENTITY_CONFLICT" and (
                        not findings or not conflicts
                    ):
                        problems.append("RULE_OUTCOME_IDENTITY_CONFLICT_SHAPE_INVALID")
                        break

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
    elif getattr(run, "evaluation_status", None) == "NOT_RELEASED":
        # A withheld evaluation is auditable without fabricating a score.
        # Keep this envelope deliberately minimal: no deductions, module
        # scores, raw total, coverage or inferred risk classification.
        expected_unreleased_fields = {
            "snapshot_schema_version",
            "status",
            "reason",
            "score",
            "risk_band",
            "scoring_data",
        }
        if (
            set(score_breakdown_snapshot) != expected_unreleased_fields
            or type(score_breakdown_snapshot.get("snapshot_schema_version")) is not int
            or score_breakdown_snapshot["snapshot_schema_version"] != 1
            or score_breakdown_snapshot.get("status") != "NOT_RELEASED"
            or not isinstance(score_breakdown_snapshot.get("reason"), str)
            or score_breakdown_snapshot["reason"] not in _UNRELEASED_REASONS
            or score_breakdown_snapshot.get("score") is not None
            or score_breakdown_snapshot.get("risk_band") != "NOT_EVALUATED"
            or score_breakdown_snapshot.get("scoring_data") != "WITHHELD"
            or getattr(run, "score", None) is not None
            or getattr(getattr(run, "risk_band", None), "value", getattr(run, "risk_band", None)) != "NOT_EVALUATED"
        ):
            problems.append("UNRELEASED_SCORE_BREAKDOWN_INVALID")

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



async def evaluation_run_chain_problem(db: Any, run: Any) -> str | None:
    """Verify previous_hash points to the immediately preceding run for this company."""
    if getattr(run, "company_id", None) is None or getattr(run, "calculated_at", None) is None:
        return "PREVIOUS_HASH_CHAIN_CONTEXT_MISSING"
    previous_result = await db.execute(
        select(ComplianceEvaluationRun.id, ComplianceEvaluationRun.score_hash)
        .where(
            ComplianceEvaluationRun.company_id == run.company_id,
            ComplianceEvaluationRun.calculated_at < run.calculated_at,
        )
        .order_by(ComplianceEvaluationRun.calculated_at.desc())
        .limit(1)
    )
    previous_row = previous_result.one_or_none()
    if previous_row is None:
        expected_previous_hash = None
    else:
        expected_previous_hash = previous_row.score_hash
        if not isinstance(expected_previous_hash, str) or not _SHA256_RE.fullmatch(
            expected_previous_hash
        ):
            return "PREVIOUS_HASH_PREDECESSOR_HASH_INVALID"
    if getattr(run, "previous_hash", None) != expected_previous_hash:
        return "PREVIOUS_HASH_CHAIN_MISMATCH"
    return None
