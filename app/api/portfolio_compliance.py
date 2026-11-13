"""Authenticated SUPER_ADMIN portfolio evaluation and release workflow.

Reactivation changes only the platform is_active flag. Statutory company status,
facts, evidence and historical evaluation runs are deliberately untouched.
"""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.dependencies import get_current_user, get_db_for_user, require_roles
from app.models.company import Company
from app.models.compliance import ComplianceEvaluationRun
from app.models.user import User
from app.rule_engine.engine import RULE_ENGINE_VERSION
from app.services.compliance_service import ComplianceService
from app.services.notification_service import ActivityService
from canonical_architecture.scoring_spec import SCORING_SPEC_VERSION

router = APIRouter(prefix="/portfolio/compliance", tags=["portfolio-compliance"])


class ReactivationRequest(BaseModel):
    company_ids: list[uuid.UUID] = Field(min_length=1, max_length=50)
    reason: str = Field(min_length=10, max_length=1000)


def _validation(run: ComplianceEvaluationRun, company: Company) -> dict[str, Any]:
    snapshot = run.score_breakdown_snapshot
    problems: list[str] = []
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
        "engine_version": run.engine_version,
        "scoring_spec_version": snapshot.get("scoring_spec_version"),
        "calculated_at": run.calculated_at.isoformat() if run.calculated_at else None,
        "pdf_eligible": not problems,
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

