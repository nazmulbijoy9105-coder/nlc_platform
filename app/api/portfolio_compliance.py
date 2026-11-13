"""Authenticated SUPER_ADMIN portfolio evaluation and release workflow.

Reactivation changes only the platform is_active flag. Statutory company status,
facts, evidence and historical evaluation runs are deliberately untouched.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.dependencies import get_current_user, get_db_for_user, require_roles
from app.compliance.evaluation_integrity import evaluation_run_integrity_problems
from app.models.company import Company
from app.models.compliance import ComplianceEvaluationRun
from app.models.rules import LegalRule
from app.models.user import User
from app.rule_engine.engine import RULE_ENGINE_VERSION
from app.services.compliance_service import ComplianceService
from app.services.notification_service import ActivityService
from canonical_architecture.scoring_spec import SCORING_SPEC_VERSION

router = APIRouter(prefix="/portfolio/compliance", tags=["portfolio-compliance"])


class RuleOutcomeAggregateRequest(BaseModel):
    run_ids: list[uuid.UUID] = Field(min_length=1, max_length=100)


class ReactivationRequest(BaseModel):
    company_ids: list[uuid.UUID] = Field(min_length=1, max_length=50)
    reason: str = Field(min_length=10, max_length=1000)


def _validation(run: ComplianceEvaluationRun, company: Company) -> dict[str, Any]:
    snapshot = run.score_breakdown_snapshot
    problems: list[str] = evaluation_run_integrity_problems(run)
    if run.evaluation_status != "COMPLETED":
        problems.append("RUN_NOT_COMPLETED")
    if not run.score_hash:
        problems.append("SCORE_HASH_MISSING")
    if not run.engine_version or run.engine_version != RULE_ENGINE_VERSION:
        problems.append("ENGINE_VERSION_MISMATCH")
    if not isinstance(snapshot, dict):
        problems.append("SCORE_SNAPSHOT_MISSING")
        snapshot = {}
    if snapshot.get("scoring_spec_version") != SCORING_SPEC_VERSION:
        problems.append("SCORING_SPEC_VERSION_MISMATCH")
    if snapshot.get("score_reconciles") is not True:
        problems.append("SCORE_RECONCILIATION_FAILED")
    if snapshot.get("final_score") != run.score:
        problems.append("RUN_SCORE_MISMATCH")
    if run.score != company.current_compliance_score:
        problems.append("COMPANY_SCORE_MISMATCH")
    if run.risk_band != company.current_risk_band:
        problems.append("COMPANY_RISK_BAND_MISMATCH")
    if company.last_evaluated_at != run.calculated_at:
        problems.append("LATEST_EVALUATION_TIMESTAMP_MISMATCH")
    return {
        "valid": not problems,
        "problems": problems,
        "evaluation_run_id": str(run.id),
        "evaluation_status": run.evaluation_status,
        "score": run.score,
        "risk_band": getattr(run.risk_band, "value", run.risk_band),
        "score_hash": run.score_hash,
        "rule_outcomes_hash": run.rule_outcomes_hash,
        "rule_catalogue_count": run.rule_catalogue_count,
        "engine_version": run.engine_version,
        "scoring_spec_version": snapshot.get("scoring_spec_version"),
        "calculated_at": run.calculated_at.isoformat() if run.calculated_at else None,
        "pdf_eligible": not problems,
    }


@router.post("/rule-outcomes/aggregate", dependencies=[Depends(require_roles("SUPER_ADMIN"))])
async def aggregate_rule_outcomes(
    body: RuleOutcomeAggregateRequest,
    db=Depends(get_db_for_user),
):
    """Aggregate immutable rule outcome ledgers for exact evaluation-run IDs."""
    if len(set(body.run_ids)) != len(body.run_ids):
        raise HTTPException(status_code=422, detail="Duplicate evaluation run IDs are not allowed.")

    rows = await db.execute(
        select(ComplianceEvaluationRun).where(ComplianceEvaluationRun.id.in_(body.run_ids))
    )
    runs_by_id = {run.id: run for run in rows.scalars().all()}
    if len(runs_by_id) != len(body.run_ids):
        raise HTTPException(status_code=404, detail="One or more evaluation runs were not found.")

    active_rule_result = await db.execute(
        select(LegalRule.rule_id).where(LegalRule.is_active.is_(True))
    )
    active_rule_ids = set(active_rule_result.scalars().all())
    if not active_rule_ids:
        raise HTTPException(status_code=409, detail="Active legal-rule catalogue is empty.")

    aggregate: dict[str, int] = {}
    unmapped_aggregate: dict[str, int] = {}
    results: list[dict[str, Any]] = []
    total_rule_company_rows = 0
    emitted_outcome_rows = 0
    not_evaluated_rows = 0
    total_unmapped_rule_ids = 0
    seen_company_ids: set[uuid.UUID] = set()

    for run_id in body.run_ids:
        run = runs_by_id[run_id]
        company = await db.get(Company, run.company_id)
        snapshot = run.rule_outcomes_snapshot
        problems: list[str] = []
        if company is None:
            problems.append("COMPANY_NOT_FOUND")
        if run.evaluation_status != "COMPLETED":
            problems.append("RUN_NOT_COMPLETED")
        if not isinstance(snapshot, list) or not snapshot:
            problems.append("RULE_OUTCOME_SNAPSHOT_MISSING")
            snapshot = []
        catalogue_items = [
            item for item in snapshot
            if isinstance(item, dict)
            and item.get("assessment_source") != "ENGINE_FINDING_WITHOUT_ACTIVE_CATALOGUE_RULE"
        ]
        unmapped_items = [
            item for item in snapshot
            if isinstance(item, dict)
            and item.get("assessment_source") == "ENGINE_FINDING_WITHOUT_ACTIVE_CATALOGUE_RULE"
        ]
        if run.rule_catalogue_count != len(catalogue_items):
            problems.append("RULE_CATALOGUE_COUNT_MISMATCH")
        catalogue_ids = [item.get("rule_id") for item in catalogue_items]
        if len(catalogue_ids) != len(active_rule_ids) or set(catalogue_ids) != active_rule_ids:
            problems.append("ACTIVE_CATALOGUE_ID_SET_MISMATCH")
        if run.company_id in seen_company_ids:
            problems.append("DUPLICATE_COMPANY_RUN")
        seen_company_ids.add(run.company_id)
        if not run.rule_outcomes_hash:
            problems.append("RULE_OUTCOME_HASH_MISSING")
        else:
            actual_hash = hashlib.sha256(json.dumps(
                snapshot, sort_keys=True, separators=(",", ":"), default=str
            ).encode()).hexdigest()
            if actual_hash != run.rule_outcomes_hash:
                problems.append("RULE_OUTCOME_HASH_MISMATCH")
        if company is not None:
            latest = await db.execute(
                select(ComplianceEvaluationRun.id)
                .where(ComplianceEvaluationRun.company_id == company.id)
                .order_by(ComplianceEvaluationRun.calculated_at.desc())
                .limit(1)
            )
            if latest.scalar_one_or_none() != run.id:
                problems.append("RUN_NOT_LATEST_FOR_COMPANY")
            validation = _validation(run, company)
            if not validation["valid"]:
                problems.extend(validation["problems"])

        ids = [item.get("rule_id") for item in snapshot if isinstance(item, dict)]
        if len(ids) != len(snapshot) or len(set(ids)) != len(ids):
            problems.append("RULE_OUTCOME_IDS_MALFORMED_OR_DUPLICATED")
        if any(item.get("verification_status") != "UNMAPPED" for item in unmapped_items):
            problems.append("UNMAPPED_OUTCOME_MARKER_INVALID")

        counts: dict[str, int] = {}
        for item in catalogue_items:
            state = str(item.get("outcome_state") or "UNKNOWN")
            counts[state] = counts.get(state, 0) + 1
        unmapped_counts: dict[str, int] = {}
        for item in unmapped_items:
            state = str(item.get("outcome_state") or "UNKNOWN")
            unmapped_counts[state] = unmapped_counts.get(state, 0) + 1

        valid = not problems
        results.append({
            "company_id": str(run.company_id),
            "company_name": company.company_name if company is not None else None,
            "evaluation_run_id": str(run.id),
            "score_hash": run.score_hash,
            "engine_version": run.engine_version,
            "scoring_spec_version": (
                run.score_breakdown_snapshot.get("scoring_spec_version")
                if isinstance(run.score_breakdown_snapshot, dict) else None
            ),
            "rule_catalogue_count": len(catalogue_items),
            "outcome_counts": counts,
            "unmapped_rule_id_count": len(unmapped_items),
            "unmapped_outcome_counts": unmapped_counts,
            "valid": valid,
            "problems": problems,
        })
        if valid:
            total_rule_company_rows += len(catalogue_items)
            for state, count in counts.items():
                aggregate[state] = aggregate.get(state, 0) + count
            for state, count in unmapped_counts.items():
                unmapped_aggregate[state] = unmapped_aggregate.get(state, 0) + count
            total_unmapped_rule_ids += len(unmapped_items)
            not_evaluated_rows += counts.get("NOT_EVALUATED", 0)
            emitted_outcome_rows += len(catalogue_items) - counts.get("NOT_EVALUATED", 0)

    valid_results = sum(item["valid"] for item in results)
    return {
        "requested_runs": len(body.run_ids),
        "validated_runs": valid_results,
        "rejected_runs": len(body.run_ids) - valid_results,
        "aggregate_counts": aggregate,
        "unmapped_engine_outcome_counts": unmapped_aggregate,
        "validated_rule_company_rows": total_rule_company_rows,
        "active_catalogue_rule_count": len(active_rule_ids),
        "unmapped_rule_id_rows": total_unmapped_rule_ids,
        "engine_outcome_rows": emitted_outcome_rows,
        "not_evaluated_rows": not_evaluated_rows,
        "potential_rule_company_rows": total_rule_company_rows,
        "expected_rule_company_rows": len(active_rule_ids) * valid_results,
        "portfolio_reconciles": (
            valid_results == len(body.run_ids)
            and total_rule_company_rows == len(active_rule_ids) * len(body.run_ids)
        ),
        "disclaimer": (
            "An absent finding is NOT_EVALUATED, never COMPLIANT. "
            "These records count engine-emitted outcomes and unevaluated catalogue rows; "
            "they do not establish independent legal verification or counsel approval."
        ),
        "results": results,
    }


@router.get("/inactive", dependencies=[Depends(require_roles("SUPER_ADMIN"))])
async def list_inactive_companies(db=Depends(get_db_for_user)):
    rows = await db.execute(
        select(Company).where(Company.is_active.is_(False)).order_by(Company.company_name)
    )
    return [
        {
            "company_id": str(company.id),
            "company_name": company.company_name,
            "registration_number": company.registration_number,
            "company_status": getattr(company.company_status, "value", company.company_status),
            "is_dormant": company.is_dormant,
            "is_active": company.is_active,
        }
        for company in rows.scalars().all()
    ]


@router.post("/reactivate", dependencies=[Depends(require_roles("SUPER_ADMIN"))])
async def reactivate_companies(
    body: ReactivationRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db_for_user),
):
    if len(set(body.company_ids)) != len(body.company_ids):
        raise HTTPException(status_code=422, detail="Duplicate company IDs are not allowed.")
    rows = await db.execute(
        select(Company).where(Company.id.in_(body.company_ids)).with_for_update()
    )
    companies = list(rows.scalars().all())
    if len(companies) != len(body.company_ids):
        raise HTTPException(status_code=404, detail="One or more company records were not found.")
    activity = ActivityService(db)
    results = []
    for company in companies:
        if company.is_active:
            results.append({"company_id": str(company.id), "status": "ALREADY_ACTIVE"})
            continue
        # Deliberately mutate only the platform lifecycle flag.
        company.is_active = True
        await db.flush()
        await activity.log(
            actor_user_id=current_user.id,
            company_id=company.id,
            action="COMPANY_PLATFORM_REACTIVATED",
            resource_type="company",
            resource_id=company.id,
            description="SUPER_ADMIN reactivated platform access; statutory status and evidence were preserved.",
            ip_address=request.client.host if request.client else None,
            detail={
                "reason": body.reason,
                "changed_field": "is_active",
                "previous_is_active": False,
                "new_is_active": True,
                "company_status_preserved": getattr(company.company_status, "value", company.company_status),
                "is_dormant_preserved": company.is_dormant,
            },
        )
        results.append({"company_id": str(company.id), "status": "REACTIVATED"})
    await db.commit()
    return {"requested": len(body.company_ids), "results": results}


@router.post("/evaluate-all", dependencies=[Depends(require_roles("SUPER_ADMIN"))])
async def evaluate_all_companies(
    request: Request,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db_for_user),
):
    """Evaluate every platform-active company; each company gets an independent outcome."""
    rows = await db.execute(
        select(Company).where(Company.is_active.is_(True)).order_by(Company.company_name)
    )
    companies = list(rows.scalars().all())
    outcomes: list[dict[str, Any]] = []
    service = ComplianceService(db)
    for company in companies:
        company_name = company.company_name
        try:
            async with db.begin_nested():
                await service.evaluate_company(
                    company_id=company.id, trigger_source="SUPER_ADMIN_PORTFOLIO"
                )
                await db.flush()
                latest_result = await db.execute(
                    select(ComplianceEvaluationRun)
                    .where(ComplianceEvaluationRun.company_id == company.id)
                    .order_by(ComplianceEvaluationRun.calculated_at.desc())
                    .limit(1)
                )
                run = latest_result.scalar_one_or_none()
                await db.refresh(company)
                if run is None:
                    raise ValueError("Evaluation returned without an authoritative run.")
                validated = _validation(run, company)
                await ActivityService(db).log(
                    actor_user_id=current_user.id,
                    company_id=company.id,
                    action="PORTFOLIO_COMPLIANCE_EVALUATED",
                    resource_type="compliance_evaluation_run",
                    resource_id=run.id,
                    description="Company processed by SUPER_ADMIN portfolio evaluation.",
                    ip_address=request.client.host if request.client else None,
                    detail={
                        "evaluation_run_id": str(run.id),
                        "validation": validated,
                        "trigger_source": "SUPER_ADMIN_PORTFOLIO",
                    },
                )
                outcomes.append({
                    "company_id": str(company.id),
                    "company_name": company_name,
                    "status": "VALIDATED" if validated["valid"] else (
                        "NOT_RELEASED" if run.evaluation_status != "COMPLETED" else "VALIDATION_FAILED"
                    ),
                    **validated,
                })
        except Exception as exc:
            outcomes.append({
                "company_id": str(company.id),
                "company_name": company_name,
                "status": "FAILED",
                "error": str(exc)[:500],
                "pdf_eligible": False,
            })
    await db.commit()
    return {
        "total": len(companies),
        "validated": sum(item["status"] == "VALIDATED" for item in outcomes),
        "not_released": sum(item["status"] == "NOT_RELEASED" for item in outcomes),
        "failed": sum(item["status"] in {"FAILED", "VALIDATION_FAILED"} for item in outcomes),
        "pdf_eligible": sum(item.get("pdf_eligible") is True for item in outcomes),
        "results": outcomes,
        "disclaimer": "Product scoring release is not independent legal verification, legal advice or certification.",
    }

@router.post("/evaluate/{company_id}", dependencies=[Depends(require_roles("SUPER_ADMIN"))])
async def evaluate_one_company(
    company_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db_for_user),
):
    company = await db.get(Company, company_id)
    if company is None or not company.is_active:
        raise HTTPException(status_code=404, detail="Active company not found.")
    try:
        async with db.begin_nested():
            await ComplianceService(db).evaluate_company(
                company_id=company.id, trigger_source="SUPER_ADMIN_PORTFOLIO"
            )
            await db.flush()
            latest_result = await db.execute(
                select(ComplianceEvaluationRun)
                .where(ComplianceEvaluationRun.company_id == company.id)
                .order_by(ComplianceEvaluationRun.calculated_at.desc())
                .limit(1)
            )
            run = latest_result.scalar_one_or_none()
            await db.refresh(company)
            if run is None:
                raise ValueError("Evaluation returned without an authoritative run.")
            validated = _validation(run, company)
            await ActivityService(db).log(
                actor_user_id=current_user.id,
                company_id=company.id,
                action="PORTFOLIO_COMPLIANCE_EVALUATED",
                resource_type="compliance_evaluation_run",
                resource_id=run.id,
                description="Company processed by SUPER_ADMIN portfolio evaluation.",
                ip_address=request.client.host if request.client else None,
                detail={"evaluation_run_id": str(run.id), "validation": validated,
                        "trigger_source": "SUPER_ADMIN_PORTFOLIO"},
            )
        await db.commit()
        return {
            "company_id": str(company.id),
            "company_name": company.company_name,
            "status": "VALIDATED" if validated["valid"] else (
                "NOT_RELEASED" if run.evaluation_status != "COMPLETED" else "VALIDATION_FAILED"
            ),
            **validated,
        }
    except Exception:
        await db.rollback()
        raise

