"""Live six-state coverage collected from the immutable company evaluation ledger."""
from __future__ import annotations

from pathlib import Path
from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.compliance import ComplianceEvaluationRun
from app.models.rules import LegalRule
from canonical_architecture.coverage_report import (
    CoverageInvariantError,
    RuleCoverageReport,
    build_registry_coverage,
)
from canonical_architecture.statutory_rules import STATUTORY_RULE_REGISTRY


def _static_registry_report() -> RuleCoverageReport:
    engine_path = Path(__file__).resolve().parents[1] / "rule_engine" / "engine.py"
    try:
        engine_source = engine_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"Cannot read canonical rule engine source: {engine_path}") from exc
    return build_registry_coverage(engine_source, STATUTORY_RULE_REGISTRY)


def build_live_rule_coverage_payload(
    *,
    company_id: uuid.UUID,
    static_report: RuleCoverageReport,
    legal_rules: list[Any],
    latest_run: Any | None,
) -> dict[str, Any]:
    """Build and validate the live funnel without deriving applicability from findings."""
    rows_by_id = {str(row.rule_id): row for row in legal_rules}
    active_ids = frozenset(
        rule_id for rule_id, row in rows_by_id.items() if bool(row.is_active)
    )

    hold_reasons: dict[str, str] = {}
    for rule_id in static_report.implemented - active_ids:
        row = rows_by_id.get(rule_id)
        if row is None:
            hold_reasons[rule_id] = "DATABASE_RULE_ROW_MISSING"
        else:
            verification_status = str(
                getattr(row, "verification_status", "UNKNOWN") or "UNKNOWN"
            )
            hold_reasons[rule_id] = (
                f"DATABASE_RULE_INACTIVE: verification_status={verification_status}"
            )

    applicable_ids: frozenset[str] | None = None
    evaluated_ids: frozenset[str] | None = None
    applicability_counts: dict[str, int] | None = None
    not_evaluated_applicable: int | None = None
    orphan_findings: list[dict[str, str]] = []
    reporting_status = "NO_EVALUATION_RUN"

    snapshot: list[dict[str, Any]] | None = None
    if latest_run is not None:
        raw_snapshot = getattr(latest_run, "rule_outcomes_snapshot", None)
        if isinstance(raw_snapshot, list):
            snapshot = raw_snapshot

    if snapshot is not None:
        active_snapshot_items = [
            item for item in snapshot
            if item.get("assessment_source") != "ENGINE_FINDING_WITHOUT_ACTIVE_CATALOGUE_RULE"
        ]
        snapshot_active_ids = frozenset(
            str(item.get("rule_id"))
            for item in active_snapshot_items
            if item.get("rule_id")
        )
        if snapshot_active_ids != active_ids:
            raise CoverageInvariantError([
                "Latest evaluation catalogue does not match the current active database catalogue; "
                "run a fresh company evaluation before reporting coverage. "
                f"snapshot_only={sorted(snapshot_active_ids - active_ids)}, "
                f"database_only={sorted(active_ids - snapshot_active_ids)}"
            ])

        has_status = ["applicability_status" in item for item in active_snapshot_items]
        if any(has_status) and not all(has_status):
            raise CoverageInvariantError([
                "Latest evaluation has a partial applicability snapshot; refusing to infer missing statuses."
            ])

        if active_snapshot_items and all(has_status):
            valid_statuses = {"APPLICABLE", "NOT_APPLICABLE", "UNKNOWN"}
            invalid = {
                str(item.get("rule_id")): item.get("applicability_status")
                for item in active_snapshot_items
                if item.get("applicability_status") not in valid_statuses
            }
            if invalid:
                raise CoverageInvariantError([
                    f"Invalid explicit applicability statuses in latest evaluation: {invalid!r}"
                ])

            applicable_ids = frozenset(
                str(item["rule_id"])
                for item in active_snapshot_items
                if item.get("applicability_status") == "APPLICABLE"
            )
            evaluated_ids = frozenset(
                str(item["rule_id"])
                for item in active_snapshot_items
                if item.get("applicability_status") == "APPLICABLE"
                and item.get("assessment_source") == "ENGINE_FINDING"
            )
            applicability_counts = {
                status: sum(
                    1 for item in active_snapshot_items
                    if item.get("applicability_status") == status
                )
                for status in ("APPLICABLE", "NOT_APPLICABLE", "UNKNOWN")
            }
            not_evaluated_applicable = len(applicable_ids - evaluated_ids)
            reporting_status = "LIVE_APPLICABILITY_COLLECTED"
        else:
            reporting_status = "LEGACY_RUN_APPLICABILITY_NOT_COLLECTED"

        orphan_findings = [
            {
                "rule_id": str(item.get("rule_id")),
                "assessment_source": str(item.get("assessment_source")),
            }
            for item in snapshot
            if item.get("assessment_source") == "ENGINE_FINDING_WITHOUT_ACTIVE_CATALOGUE_RULE"
        ]

    report = RuleCoverageReport(
        registered=static_report.registered,
        implemented=static_report.implemented,
        deferred=static_report.deferred,
        active=active_ids,
        applicable=applicable_ids,
        evaluated=evaluated_ids,
        deferred_reasons=static_report.deferred_reasons,
        active_hold_reasons=hold_reasons,
    )
    report.validate()

    run_payload = None
    if latest_run is not None:
        run_payload = {
            "id": str(latest_run.id),
            "calculated_at": latest_run.calculated_at.isoformat(),
            "engine_version": latest_run.engine_version,
            "score_hash": latest_run.score_hash,
            "rule_outcomes_hash": latest_run.rule_outcomes_hash,
            "rule_catalogue_count": latest_run.rule_catalogue_count,
        }

    return {
        "company_id": str(company_id),
        "scope": "COMPANY_LATEST_EVALUATION",
        "reporting_status": reporting_status,
        **report.to_dict(),
        "latest_evaluation_run": run_payload,
        "applicability_status_counts": applicability_counts,
        "applicable_but_not_evaluated_count": not_evaluated_applicable,
        "orphan_engine_findings": orphan_findings,
    }


async def load_live_rule_coverage(
    db: AsyncSession,
    company_id: uuid.UUID,
) -> dict[str, Any]:
    """Read the current catalogue and latest tenant-scoped evaluation from Postgres."""
    static_report = _static_registry_report()
    legal_rules = list(
        (
            await db.execute(
                select(LegalRule).order_by(LegalRule.rule_id)
            )
        ).scalars().all()
    )
    latest_run = (
        await db.execute(
            select(ComplianceEvaluationRun)
            .where(ComplianceEvaluationRun.company_id == company_id)
            .order_by(
                ComplianceEvaluationRun.calculated_at.desc(),
                ComplianceEvaluationRun.id.desc(),
            )
            .limit(1)
        )
    ).scalar_one_or_none()

    return build_live_rule_coverage_payload(
        company_id=company_id,
        static_report=static_report,
        legal_rules=legal_rules,
        latest_run=latest_run,
    )
