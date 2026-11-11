from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.entitlement import require_entitlement
from app.core.company_authorization import ensure_staff_company_scope
from app.core.dependencies import (
    get_current_user,
    get_db_for_user,
    require_company_access,
)
from app.api.legal_provenance import DeadlinePreviewRequest, preview_or_release_deadline
from app.models.company_fact import CompanyFact
from app.models.legal_provenance import LegalDeadlineDefinition
from app.services.compliance_calendar import (
    ComplianceCalendarService,
    calendar_manifest_is_released,
)


def _require_calendar_release() -> None:
    if not calendar_manifest_is_released():
        raise HTTPException(
            status_code=503,
            detail=(
                "No registered product-owner approved deadline manifest is available for generation."
            ),
        )


router = APIRouter(prefix="/calendar", tags=["Compliance Calendar"])


@router.post("/companies/{company_id}/generate",
            dependencies=[Depends(require_company_access("company_id")), Depends(require_entitlement("compliance_package"))])
async def generate_calendar(
    company_id: UUID,
    years_ahead: int = Query(3, ge=1, le=5),
    db: AsyncSession = Depends(get_db_for_user),
    current_user=Depends(get_current_user),
):
    if current_user.role == "LEGAL_STAFF":
        await ensure_staff_company_scope(company_id, current_user, db)
    # Use the same database-backed source/mapping/owner-decision lifecycle
    # used by per-deadline preview. The legacy static manifest is intentionally
    # empty and must not remain the customer calendar's only generation path.
    definitions = (
        await db.execute(
            select(LegalDeadlineDefinition).order_by(
                LegalDeadlineDefinition.rule_id,
                LegalDeadlineDefinition.effective_from,
            )
        )
    ).scalars().all()

    outcomes: list[dict] = []
    seen_event_keys: set[tuple[str, str]] = set()
    for definition in definitions:
        event_key = (definition.event_type, definition.period_label)
        if event_key in seen_event_keys:
            outcomes.append({
                "definition_id": str(definition.id),
                "rule_id": definition.rule_id,
                "status": "CONFLICTING_EVENT_KEY",
                "customer_calendar_write": False,
            })
            continue
        seen_event_keys.add(event_key)
        fact = (
            await db.execute(
                select(CompanyFact)
                .where(
                    CompanyFact.company_id == company_id,
                    CompanyFact.fact_key == definition.trigger_fact_key,
                )
                .order_by(CompanyFact.created_at.desc(), CompanyFact.id.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if fact is None:
            outcomes.append({
                "definition_id": str(definition.id),
                "rule_id": definition.rule_id,
                "status": "NO_TRIGGER_FACT",
                "customer_calendar_write": False,
            })
            continue
        try:
            outcome = await preview_or_release_deadline(
                company_id=company_id,
                definition_id=definition.id,
                body=DeadlinePreviewRequest(fact_id=fact.id),
                db=db,
                current_user=current_user,
            )
            outcomes.append({
                "definition_id": str(definition.id),
                **outcome,
            })
        except HTTPException as exc:
            # Keep a bad/missing mapping scoped to its definition; database
            # failures still propagate and roll back the enclosing request.
            outcomes.append({
                "definition_id": str(definition.id),
                "rule_id": definition.rule_id,
                "status": "DEFINITION_ERROR",
                "http_status": exc.status_code,
                "detail": exc.detail,
                "customer_calendar_write": False,
            })

    service = ComplianceCalendarService(db)
    events = await service.get_calendar(
        company_id,
        include_past_days=0,
        include_future_days=years_ahead * 366,
    )
    released = sum(item.get("status") == "PRODUCT_OWNER_RELEASED" for item in outcomes)
    return {
        "message": f"Processed {len(outcomes)} source-backed deadline definitions",
        "count": released,
        "processed": len(outcomes),
        "preview_only": sum(item.get("status") == "PREVIEW_ONLY" for item in outcomes),
        "without_trigger_fact": sum(item.get("status") == "NO_TRIGGER_FACT" for item in outcomes),
        "definition_errors": sum(item.get("status") == "DEFINITION_ERROR" for item in outcomes),
        "results": outcomes,
        "events": events,
        "no_obligation_inference": True,
    }


@router.get(
    "/companies/{company_id}",
    dependencies=[Depends(require_company_access("company_id")), Depends(require_entitlement("compliance_package"))],
)
async def get_calendar(
    company_id: UUID,
    days_ahead: int = Query(90, ge=30, le=365),
    db: AsyncSession = Depends(get_db_for_user),
    current_user=Depends(get_current_user),
):
    if current_user.role == "LEGAL_STAFF":
        await ensure_staff_company_scope(company_id, current_user, db)
    service = ComplianceCalendarService(db)
    events = await service.get_upcoming(company_id, days_ahead=days_ahead)
    return {
        "company_id": str(company_id),
        "events": events,
        "calendar_state": "HAS_RELEASED_EVENTS" if events else "NO_RELEASED_EVENTS",
        "no_obligation_inference": True,
    }
