"""
app/api/rules.py — Legal Rules Router
NEUM LEX COUNSEL

AI Constitution Article 1: Only Super Admin may modify rules.
Every change creates an immutable legal_rule_versions snapshot.

Endpoints:
  GET   /rules                    List all 32 ILRMF rules
  GET   /rules/{rule_id}          Get single rule with version history
  PATCH /rules/{rule_id}          Update a rule (SUPER_ADMIN only — creates version snapshot)
  GET   /rules/{rule_id}/history  Rule version history
  GET   /rules/black-overrides    List the 4 BLACK override rules
  GET   /rules/summary            Aggregate stats per rule type / severity

Governance notes:
  - rule_id (e.g. "AGM-001") is immutable — cannot be changed after creation
  - score_impact cannot exceed the pre-set module maximum
  - Every update records changed_by, changed_at, change_reason
  - Rule engine picks up changes on next warm-up or cache refresh
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.dependencies import (
    get_current_user,
    get_db_for_user,
    require_roles,
)
from app.services.notification_service import ActivityService
from app.services.rules_service import RulesService

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.enums import SeverityLevel
    from app.models.user import User

logger = structlog.get_logger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class RuleUpdateRequest(BaseModel):
    """
    Only the operational fields may be updated.
    rule_id, rule_type, and statutory_basis are immutable.
    """
    rule_name: str | None = Field(None, min_length=3, max_length=255)
    description: str | None = None
    default_severity: SeverityLevel | None = None
    score_impact: int | None = Field(None, ge=0, le=50)
    is_active: bool | None = None
    # Required for audit trail
    change_reason: str = Field(
        min_length=10,
        max_length=500,
        description="Mandatory: explain why this rule is being changed",
    )


class RuleResponse(BaseModel):
    rule_id: str
    rule_name: str
    rule_type: str
    statutory_basis: str
    description: str
    default_severity: str
    score_impact: int
    revenue_tier: str
    is_black_override: bool
    is_active: bool
    version: int
    created_at: str
    updated_at: str | None


class RuleVersionResponse(BaseModel):
    version_id: str
    rule_id: str
    version: int
    previous_severity: str | None
    new_severity: str | None
    previous_score_impact: int | None
    new_score_impact: int | None
    change_reason: str
    changed_by_id: str
    changed_at: str


class RuleSummaryResponse(BaseModel):
    total_rules: int
    active_rules: int
    inactive_rules: int
    black_override_rules: int
    by_module: dict[str, int]
    by_severity: dict[str, int]
    total_max_deduction: int


class MessageResponse(BaseModel):
    message: str
    success: bool = True


# ---------------------------------------------------------------------------
# Serialiser
# ---------------------------------------------------------------------------

def _rule_to_response(rule) -> RuleResponse:
    return RuleResponse(
        rule_id=rule.rule_id,
        rule_name=rule.rule_name,
        rule_type=rule.rule_type,
        statutory_basis=rule.statutory_basis,
        description=rule.description,
        default_severity=rule.default_severity,
        score_impact=rule.score_impact,
        revenue_tier=rule.revenue_tier,
        is_black_override=rule.is_black_override,
        is_active=rule.is_active,
        version=rule.version,
        created_at=rule.created_at.isoformat(),
        updated_at=rule.updated_at.isoformat() if rule.updated_at else None,
    )


# ---------------------------------------------------------------------------
# GET /rules — All rules
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=list[RuleResponse],
    summary="List all ILRMF legal rules",
    description="Returns all 32 rules. No auth restriction — clients may see rule metadata.",
)
async def list_rules(
    rule_type: str | None = None,
    severity: SeverityLevel | None = None,
    is_active: bool | None = None,
    is_black_override: bool | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = RulesService(db)
    rules = await svc.get_all(
        rule_type=rule_type,
        severity=severity,
        is_active=is_active,
        is_black_override=is_black_override,
    )
    return [_rule_to_response(r) for r in rules]


# ---------------------------------------------------------------------------
# GET /rules/summary — Aggregate stats
# ---------------------------------------------------------------------------

@router.get(
    "/summary",
    response_model=RuleSummaryResponse,
    summary="Rule engine summary statistics",
)
async def get_rule_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = RulesService(db)
    rules = await svc.get_all()

    by_module: dict[str, int] = {}
    by_severity: dict[str, int] = {}
    total_max_deduction = 0
    black_overrides = 0
    active_count = 0

    for r in rules:
        # Module = prefix before first hyphen (AGM-001 → AGM)
        module = r.rule_id.split("-")[0]
        by_module[module] = by_module.get(module, 0) + 1
        by_severity[r.default_severity] = by_severity.get(r.default_severity, 0) + 1
        if r.is_active:
            active_count += 1
            total_max_deduction += r.score_impact
        if r.is_black_override:
            black_overrides += 1

    return RuleSummaryResponse(
        total_rules=len(rules),
        active_rules=active_count,
        inactive_rules=len(rules) - active_count,
        black_override_rules=black_overrides,
        by_module=by_module,
        by_severity=by_severity,
        total_max_deduction=total_max_deduction,
    )


# ---------------------------------------------------------------------------
# GET /rules/black-overrides — The 4 BLACK override rules
# ---------------------------------------------------------------------------

@router.get(
    "/black-overrides",
    response_model=list[RuleResponse],
    summary="List all BLACK override rules",
    description="Returns rules where is_black_override=True (AUD-003, TR-005, ESC-002, ESC-003).",
)
async def get_black_overrides(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = RulesService(db)
    rules = await svc.get_black_override_rules()
    return [_rule_to_response(r) for r in rules]


# ---------------------------------------------------------------------------
# GET /rules/{rule_id} — Single rule with history
# ---------------------------------------------------------------------------

@router.get(
    "/{rule_id}",
    response_model=RuleResponse,
    summary="Get a single rule by its rule_id",
)
async def get_rule(
    rule_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = RulesService(db)
    rule = await svc.get_by_rule_id(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail=f"Rule '{rule_id}' not found.")
    return _rule_to_response(rule)


# ---------------------------------------------------------------------------
# PATCH /rules/{rule_id} — Update (SUPER_ADMIN only)
# ---------------------------------------------------------------------------

@router.patch(
    "/{rule_id}",
    response_model=RuleResponse,
    dependencies=[Depends(require_roles("SUPER_ADMIN"))],
    summary="Update a legal rule (Super Admin only — creates version snapshot)",
    description=(
        "AI Constitution Article 1: Only Super Admin may modify rules. "
        "Every update creates an immutable version record in legal_rule_versions. "
        "rule_id and statutory_basis are immutable."
    ),
)
async def update_rule(
    rule_id: str,
    body: RuleUpdateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = RulesService(db)
    activity = ActivityService(db)

    existing = await svc.get_by_rule_id(rule_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Rule '{rule_id}' not found.")

    # Validate BLACK override rules cannot have severity changed to non-BLACK
    update_data = body.model_dump(exclude={"change_reason"}, exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided for update.")

    if existing.is_black_override:
        new_severity = update_data.get("default_severity")
        if new_severity and new_severity != "BLACK":
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Rule '{rule_id}' is a BLACK override rule. "
                    f"Its severity cannot be changed to a non-BLACK value. "
                    f"Contact NLC legal technology team if this change is intentional."
                ),
            )

    updated_rule = await svc.update_rule(
        rule_id=rule_id,
        updates=update_data,
        change_reason=body.change_reason,
        changed_by=current_user.id,
    )

    await activity.log(
        action="LEGAL_RULE_UPDATED",
        resource_type="legal_rule",
        resource_id=rule_id,
        description=(
            f"Rule '{rule_id}' updated by Super Admin. "
            f"Fields: {list(update_data.keys())}. "
            f"Reason: {body.change_reason}"
        ),
        ip_address=request.client.host if request.client else None,
        actor_user_id=current_user.id,
    )

    logger.warning(
        "legal_rule_updated",
        rule_id=rule_id,
        changed_by=str(current_user.id),
        fields=list(update_data.keys()),
        change_reason=body.change_reason,
    )
    return _rule_to_response(updated_rule)


# ---------------------------------------------------------------------------
# GET /rules/{rule_id}/history — Version history
# ---------------------------------------------------------------------------

@router.get(
    "/{rule_id}/history",
    response_model=list[RuleVersionResponse],
    dependencies=[Depends(require_roles("ADMIN_STAFF", "SUPER_ADMIN"))],
    summary="Get the version history for a rule",
)
async def get_rule_history(
    rule_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = RulesService(db)
    existing = await svc.get_by_rule_id(rule_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Rule '{rule_id}' not found.")

    versions = await svc.get_version_history(rule_id)
    return [
        RuleVersionResponse(
            version_id=str(v.id),
            rule_id=v.rule_id,
            version=v.version,
            previous_severity=v.previous_severity,
            new_severity=v.new_severity,
            previous_score_impact=v.previous_score_impact,
            new_score_impact=v.new_score_impact,
            change_reason=v.change_reason,
            changed_by_id=str(v.changed_by_id),
            changed_at=v.changed_at.isoformat(),
        )
        for v in versions
    ]
