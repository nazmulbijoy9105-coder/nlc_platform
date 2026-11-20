"""Live six-state rule coverage collection over the current catalogue and one company run.

The collector is deliberately conservative: no matching run row, no applicability
field, or no emitted finding never becomes NOT_APPLICABLE or COMPLIANT.
"""
from __future__ import annotations

from typing import Any, Mapping

from canonical_architecture.coverage_report import (
    CoverageInvariantError,
    RuleCoverageReport,
    parse_engine_rule_ids,
)


_VALID_APPLICABILITY = {"APPLICABLE", "NOT_APPLICABLE", "UNKNOWN"}


def build_live_rule_coverage_report(
    *,
    engine_source: str,
    registry: Mapping[str, object],
    database_rule_rows: list[Mapping[str, Any]],
    run_snapshot: list[Mapping[str, Any]] | None,
) -> dict[str, Any]:
    """Build and validate a live funnel from DB catalogue rows and a run snapshot."""
    implemented = parse_engine_rule_ids(engine_source)
    registered = frozenset(registry)
    deferred: frozenset[str] = frozenset()
    deferred_reasons: dict[str, str] = {}

    rows_by_id = {str(row["rule_id"]): row for row in database_rule_rows}
    active = frozenset(
        rule_id for rule_id, row in rows_by_id.items()
        if bool(row.get("is_active"))
    )

    holds: dict[str, str] = {}
    for rule_id in sorted(implemented - active):
        row = rows_by_id.get(rule_id)
        if row is None:
            holds[rule_id] = (
                "No database catalogue row exists; activation is not established."
            )
        else:
            verification = str(row.get("verification_status") or "UNKNOWN")
            holds[rule_id] = (
                "Database catalogue row is inactive "
                f"(verification_status={verification}); not counted as active."
            )

    applicable: frozenset[str] | None = None
    evaluated: frozenset[str] | None = None
    applicability_results: dict[str, dict[str, Any]] | None = None

    if run_snapshot is not None:
        snapshot_by_id = {
            str(item["rule_id"]): item
            for item in run_snapshot
            if item.get("rule_id") is not None
        }
        result_rows: dict[str, dict[str, Any]] = {}
        applicable_ids: set[str] = set()
        evaluated_ids: set[str] = set()

        for rule_id in sorted(active):
            item = snapshot_by_id.get(rule_id)
            if item is None:
                state = "UNKNOWN"
                source = "MISSING_RUN_SNAPSHOT_ROW"
                reason = (
                    "No outcome row exists for this active rule in the selected "
                    "evaluation run; applicability is unknown."
                )
                outcome = "NOT_EVALUATED"
                conflict = False
            else:
                raw_state = str(item.get("applicability_state") or "UNKNOWN").upper()
                state = raw_state if raw_state in _VALID_APPLICABILITY else "UNKNOWN"
                source = str(
                    item.get("applicability_source")
                    or "LEGACY_SNAPSHOT_NO_EXPLICIT_APPLICABILITY"
                )
                reason = str(
                    item.get("applicability_reason")
                    or (
                        "This historical run predates explicit applicability "
                        "results; applicability is unknown."
                    )
                )
                outcome = str(item.get("outcome_state") or "NOT_EVALUATED").upper()
                conflict = bool(item.get("applicability_conflict", False))

            result_rows[rule_id] = {
                "applicability_state": state,
                "applicability_source": source,
                "applicability_reason": reason,
                "applicability_conflict": conflict,
                "outcome_state": outcome,
            }
            if state == "APPLICABLE":
                applicable_ids.add(rule_id)
                if outcome != "NOT_EVALUATED":
                    evaluated_ids.add(rule_id)

        applicability_results = result_rows
        applicable = frozenset(applicable_ids)
        evaluated = frozenset(evaluated_ids)

    report = RuleCoverageReport(
        registered=registered,
        implemented=implemented,
        deferred=deferred,
        active=active,
        applicable=applicable,
        evaluated=evaluated,
        deferred_reasons=deferred_reasons,
        active_hold_reasons=holds,
    )
    validation_status = "PASS"
    violations: list[str] = []
    try:
        report.validate()
    except CoverageInvariantError as exc:
        validation_status = "FAILED"
        violations = list(exc.violations)

    payload = report.to_dict()
    state_counts = None
    if applicability_results is not None:
        state_counts = {
            state: sum(
                1 for item in applicability_results.values()
                if item["applicability_state"] == state
            )
            for state in ("APPLICABLE", "NOT_APPLICABLE", "UNKNOWN")
        }

    return {
        **payload,
        "validation_status": validation_status,
        "validation_violations": violations,
        "applicability_results": applicability_results,
        "applicability_summary": state_counts,
        "applicability_semantics": (
            "APPLICABLE and NOT_APPLICABLE require an explicit engine result. "
            "Missing findings, missing snapshot rows, and legacy snapshots map "
            "to UNKNOWN; they never imply non-applicability or compliance."
        ),
    }
