"""Product-owner governed legal source registry and deterministic deadline controls.

This API records product-owner decisions without changing the statutory
verification_status on legal_rules. Customer-triggered deadline release also
requires an authenticated, authorized-document-backed VERIFIED CompanyFact.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from typing import Any, Literal
from urllib.parse import urlparse
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db_for_user, require_roles
from app.models.company_fact import CompanyFact
from app.models.compliance_calendar import ComplianceCalendarEvent
from app.models.enums import CalendarEventStatus, CalendarEventType
from app.models.legal_provenance import (
    LegalDeadlineDefinition,
    LegalRuleReleaseEvent,
    LegalRuleSourceMapping,
    LegalSource,
)
from app.models.rules import LegalRule
from app.services.legal_deadline_engine import DeadlineRule, calculate_deadline_candidate

router = APIRouter(
    prefix="/legal-provenance",
    tags=["Legal Source Provenance"],
    dependencies=[Depends(require_roles("SUPER_ADMIN"))],
)

MappingKind = Literal["RULE_BASIS", "DEADLINE_BASIS", "PENALTY_BASIS"]
ReleaseScope = Literal["SCORING", "DEADLINE"]
Decision = Literal["APPROVED", "REVOKED"]


class SourceCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    source_key: str = Field(min_length=3, max_length=120)
    jurisdiction: str = Field(default="BD", min_length=2, max_length=20)
    instrument_title: str = Field(min_length=5, max_length=500)
    issuing_authority: str = Field(min_length=2, max_length=250)
    instrument_type: str = Field(min_length=2, max_length=80)
    official_url: str = Field(min_length=10, max_length=2000)
    citation: str = Field(min_length=5, max_length=2000)
    version_label: str = Field(min_length=1, max_length=120)
    publication_date: date | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    artifact_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    artifact_uri: str | None = Field(default=None, max_length=2000)

    @field_validator("official_url")
    @classmethod
    def require_https_reference(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("official_url must be an absolute HTTPS URL")
        return value

    @field_validator("artifact_uri")
    @classmethod
    def require_https_artifact_uri(cls, value: str | None) -> str | None:
        if value is not None:
            parsed = urlparse(value)
            if parsed.scheme != "https" or not parsed.netloc:
                raise ValueError("artifact_uri must be an absolute HTTPS URI")
        return value


class MappingCreate(BaseModel):
    rule_id: str = Field(min_length=3, max_length=50)
    source_id: UUID
    mapping_kind: MappingKind
    provision_citation: str = Field(min_length=3, max_length=2000)
    rationale: str = Field(min_length=10, max_length=4000)


class DeadlineDefinitionCreate(BaseModel):
    mapping_id: UUID
    event_type: str
    title: str = Field(min_length=3, max_length=300)
    trigger_fact_key: str = Field(min_length=2, max_length=120)
    period_label: str = Field(min_length=2, max_length=100)
    offset: int = Field(ge=0, le=36500)
    unit: Literal["DAYS", "CLEAR_DAYS", "MONTHS", "YEARS"]
    adjustment: Literal["NONE", "FOLLOWING", "PRECEDING"] = "NONE"
    exclude_trigger_day: bool = False
    effective_from: date
    effective_to: date | None = None
    holiday_calendar_version: str | None = Field(default=None, max_length=100)
    holiday_source_citation: str | None = Field(default=None, max_length=2000)
    holidays: list[date] = Field(default_factory=list, max_length=500)

    @field_validator("event_type")
    @classmethod
    def known_event_type(cls, value: str) -> str:
        allowed = {item.value for item in CalendarEventType}
        if value not in allowed:
            raise ValueError(f"event_type must be one of {sorted(allowed)}")
        return value

    @field_validator("holidays")
    @classmethod
    def require_holiday_provenance(cls, value, info):
        # The paired-field check also runs in the route to keep Pydantic's
        # validation independent of request field ordering.
        return value


class ProductOwnerDecision(BaseModel):
    rule_id: str = Field(min_length=3, max_length=50)
    mapping_id: UUID
    release_scope: ReleaseScope
    decision: Decision
    reason: str = Field(min_length=10, max_length=2000)
    deadline_definition_id: UUID | None = None


class DeadlinePreviewRequest(BaseModel):
    company_id: UUID
    definition_id: UUID
    fact_id: UUID


async def _append_event(
    db: AsyncSession,
    *,
    event_type: str,
    actor_id: UUID,
    reason: str,
    rule_id: str | None = None,
    source_id: UUID | None = None,
    mapping_id: UUID | None = None,
    deadline_definition_id: UUID | None = None,
    release_scope: str | None = None,
    decision: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> LegalRuleReleaseEvent:
    # Serialize the global chain writer. The lock is transaction-scoped and
    # prevents two concurrent API requests from using the same predecessor.
    await db.execute(text("SELECT pg_advisory_xact_lock(741113, 1)"))
    previous = (
        await db.execute(
            select(LegalRuleReleaseEvent.event_hash)
            .order_by(LegalRuleReleaseEvent.created_at.desc(), LegalRuleReleaseEvent.id.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    created_at = datetime.now(timezone.utc)
    payload = {
        "event_type": event_type,
        "release_scope": release_scope,
        "decision": decision,
        "rule_id": rule_id,
        "source_id": str(source_id) if source_id else None,
        "mapping_id": str(mapping_id) if mapping_id else None,
        "deadline_definition_id": str(deadline_definition_id) if deadline_definition_id else None,
        "actor_id": str(actor_id),
        "reason": reason,
        "metadata": metadata or {},
        "previous_event_hash": previous,
        "created_at": created_at.isoformat(),
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    event = LegalRuleReleaseEvent(
        event_type=event_type,
        release_scope=release_scope,
        decision=decision,
        rule_id=rule_id,
        source_id=source_id,
        mapping_id=mapping_id,
        deadline_definition_id=deadline_definition_id,
        actor_id=actor_id,
        reason=reason,
        event_metadata=metadata or {},
        previous_event_hash=previous,
        event_hash=digest,
        created_at=created_at,
    )
    db.add(event)
    await db.flush()
    return event


def _source_state(source: LegalSource) -> str:
    # Recording a caller-supplied URI/hash is not proof that the artifact bytes
    # were fetched, checked or placed in immutable storage.
    return "ARTIFACT_REFERENCE_RECORDED" if source.artifact_sha256 else "REFERENCE_ONLY"


@router.post("/sources", status_code=201)
async def register_source(
    body: SourceCreate,
    db: AsyncSession = Depends(get_db_for_user),
    current_user=Depends(get_current_user),
):
    if (body.artifact_sha256 is None) != (body.artifact_uri is None):
        raise HTTPException(422, "artifact_sha256 and artifact_uri must be supplied together")
    if body.effective_to and body.effective_from and body.effective_to < body.effective_from:
        raise HTTPException(422, "effective_to cannot precede effective_from")
    exists = (
        await db.execute(
            select(LegalSource.id).where(
                LegalSource.source_key == body.source_key,
                LegalSource.version_label == body.version_label,
            )
        )
    ).scalar_one_or_none()
    if exists:
        raise HTTPException(409, "This source_key/version_label is already registered")
    source = LegalSource(**body.model_dump(), created_by=current_user.id)
    db.add(source)
    await db.flush()
    event = await _append_event(
        db,
        event_type="SOURCE_REGISTERED",
        actor_id=current_user.id,
        reason=f"Registered source reference: {body.instrument_title}",
        source_id=source.id,
        metadata={
            "source_key": body.source_key,
            "version_label": body.version_label,
            "source_state": _source_state(source),
            "official_url": body.official_url,
            "artifact_hash_recorded": bool(body.artifact_sha256),
            "artifact_bytes_independently_checked": False,
        },
    )
    return {
        "source_id": str(source.id),
        "source_state": _source_state(source),
        "event_id": str(event.id),
        "event_hash": event.event_hash,
        "note": "Source reference registered; this does not set legal verification to VERIFIED.",
    }


@router.post("/mappings", status_code=201)
async def map_rule_to_source(
    body: MappingCreate,
    db: AsyncSession = Depends(get_db_for_user),
    current_user=Depends(get_current_user),
):
    rule = (
        await db.execute(select(LegalRule).where(LegalRule.rule_id == body.rule_id))
    ).scalar_one_or_none()
    if rule is None:
        raise HTTPException(404, "Legal rule not found")
    source = (
        await db.execute(select(LegalSource).where(LegalSource.id == body.source_id))
    ).scalar_one_or_none()
    if source is None:
        raise HTTPException(404, "Registered source not found")
    mapping = LegalRuleSourceMapping(
        **body.model_dump(),
        created_by=current_user.id,
    )
    db.add(mapping)
    await db.flush()
    event = await _append_event(
        db,
        event_type="RULE_SOURCE_MAPPED",
        actor_id=current_user.id,
        reason=f"Mapped {body.rule_id} to {source.instrument_title}",
        rule_id=body.rule_id,
        source_id=source.id,
        mapping_id=mapping.id,
        metadata={
            "mapping_kind": body.mapping_kind,
            "provision_citation": body.provision_citation,
            "rationale": body.rationale,
        },
    )
    return {
        "mapping_id": str(mapping.id),
        "rule_id": mapping.rule_id,
        "source_id": str(mapping.source_id),
        "event_id": str(event.id),
        "event_hash": event.event_hash,
    }


@router.post("/deadlines/definitions", status_code=201)
async def register_deadline_definition(
    body: DeadlineDefinitionCreate,
    db: AsyncSession = Depends(get_db_for_user),
    current_user=Depends(get_current_user),
):
    if body.effective_to and body.effective_to < body.effective_from:
        raise HTTPException(422, "effective_to cannot precede effective_from")
    if body.holidays and not (body.holiday_calendar_version and body.holiday_source_citation):
        raise HTTPException(422, "Holiday dates require a versioned calendar and source citation")
    mapping = (
        await db.execute(
            select(LegalRuleSourceMapping).where(
                LegalRuleSourceMapping.id == body.mapping_id,
                LegalRuleSourceMapping.mapping_kind == "DEADLINE_BASIS",
            )
        )
    ).scalar_one_or_none()
    if mapping is None:
        raise HTTPException(422, "A DEADLINE_BASIS source mapping is required")
    definition = LegalDeadlineDefinition(
        rule_id=mapping.rule_id,
        source_id=mapping.source_id,
        mapping_id=mapping.id,
        event_type=body.event_type,
        title=body.title,
        trigger_fact_key=body.trigger_fact_key,
        period_label=body.period_label,
        offset=body.offset,
        unit=body.unit,
        adjustment=body.adjustment,
        exclude_trigger_day=body.exclude_trigger_day,
        effective_from=body.effective_from,
        effective_to=body.effective_to,
        holiday_calendar_version=body.holiday_calendar_version,
        holiday_source_citation=body.holiday_source_citation,
        holidays=[item.isoformat() for item in body.holidays],
        created_by=current_user.id,
    )
    db.add(definition)
    await db.flush()
    event = await _append_event(
        db,
        event_type="DEADLINE_RULE_REGISTERED",
        actor_id=current_user.id,
        reason=f"Registered deadline definition: {body.title}",
        rule_id=mapping.rule_id,
        source_id=mapping.source_id,
        mapping_id=mapping.id,
        deadline_definition_id=definition.id,
        release_scope="DEADLINE",
        metadata={
            "event_type": body.event_type,
            "trigger_fact_key": body.trigger_fact_key,
            "offset": body.offset,
            "unit": body.unit,
            "adjustment": body.adjustment,
            "effective_from": body.effective_from.isoformat(),
            "effective_to": body.effective_to.isoformat() if body.effective_to else None,
        },
    )
    return {
        "definition_id": str(definition.id),
        "rule_id": definition.rule_id,
        "release_state": "REGISTERED_NOT_RELEASED",
        "event_id": str(event.id),
        "event_hash": event.event_hash,
    }


@router.post("/decisions", status_code=201)
async def record_product_owner_decision(
    body: ProductOwnerDecision,
    db: AsyncSession = Depends(get_db_for_user),
    current_user=Depends(get_current_user),
):
    mapping = (
        await db.execute(
            select(LegalRuleSourceMapping).where(
                LegalRuleSourceMapping.id == body.mapping_id,
                LegalRuleSourceMapping.rule_id == body.rule_id,
            )
        )
    ).scalar_one_or_none()
    if mapping is None:
        raise HTTPException(404, "Rule/source mapping does not match the supplied rule")
    deadline_definition = None
    if body.release_scope == "SCORING":
        from app.rule_engine.engine import PRODUCT_SCORING_RULE_IDS
        if body.rule_id not in PRODUCT_SCORING_RULE_IDS:
            raise HTTPException(422, "This rule is excluded from the product scoring set")
        if mapping.mapping_kind != "RULE_BASIS":
            raise HTTPException(422, "SCORING approval requires a RULE_BASIS mapping")
        if body.deadline_definition_id is not None:
            raise HTTPException(422, "A scoring decision cannot reference a deadline definition")
    else:
        if mapping.mapping_kind != "DEADLINE_BASIS":
            raise HTTPException(422, "DEADLINE approval requires a DEADLINE_BASIS mapping")
        if body.deadline_definition_id is None:
            raise HTTPException(422, "deadline_definition_id is required for a deadline decision")
        deadline_definition = (
            await db.execute(
                select(LegalDeadlineDefinition).where(
                    LegalDeadlineDefinition.id == body.deadline_definition_id,
                    LegalDeadlineDefinition.mapping_id == mapping.id,
                    LegalDeadlineDefinition.rule_id == body.rule_id,
                )
            )
        ).scalar_one_or_none()
        if deadline_definition is None:
            raise HTTPException(404, "Deadline definition does not match the rule/source mapping")
    source = (
        await db.execute(select(LegalSource).where(LegalSource.id == mapping.source_id))
    ).scalar_one_or_none()
    if source is None:
        raise HTTPException(404, "Source reference not found")
    event = await _append_event(
        db,
        event_type=(
            "PRODUCT_OWNER_APPROVED" if body.decision == "APPROVED"
            else "PRODUCT_OWNER_REVOKED"
        ),
        actor_id=current_user.id,
        reason=body.reason,
        rule_id=body.rule_id,
        source_id=source.id,
        mapping_id=mapping.id,
        deadline_definition_id=body.deadline_definition_id,
        release_scope=body.release_scope,
        decision=body.decision,
        metadata={
            "source_state": _source_state(source),
            "legal_verification_status_unchanged": True,
            "decision_basis": "AUTHENTICATED_SUPER_ADMIN_PRODUCT_OWNER",
        },
    )
    return {
        "event_id": str(event.id),
        "event_hash": event.event_hash,
        "rule_id": body.rule_id,
        "release_scope": body.release_scope,
        "decision": body.decision,
        "legal_verification_status": "UNCHANGED",
    }


@router.post("/deadlines/preview")
async def preview_or_release_deadline(
    body: DeadlinePreviewRequest,
    db: AsyncSession = Depends(get_db_for_user),
    current_user=Depends(get_current_user),
):
    definition = (
        await db.execute(
            select(LegalDeadlineDefinition).where(
                LegalDeadlineDefinition.id == body.definition_id
            )
        )
    ).scalar_one_or_none()
    if definition is None:
        raise HTTPException(404, "Deadline definition not found")
    fact = (
        await db.execute(
            select(CompanyFact).where(
                CompanyFact.id == body.fact_id,
                CompanyFact.company_id == body.company_id,
            )
        )
    ).scalar_one_or_none()
    if fact is None:
        raise HTTPException(404, "Company fact not found in this tenant")
    if fact.fact_key != definition.trigger_fact_key:
        raise HTTPException(422, "Company fact key does not match the deadline trigger")
    if not isinstance(fact.fact_value, (str, dict)):
        raise HTTPException(422, "Trigger fact must contain an ISO date value")
    raw_date = fact.fact_value.get("date") or fact.fact_value.get("value") if isinstance(fact.fact_value, dict) else fact.fact_value
    try:
        trigger_date = date.fromisoformat(raw_date)
    except (TypeError, ValueError):
        raise HTTPException(422, "Trigger fact value must be an ISO YYYY-MM-DD date") from None

    source = (
        await db.execute(select(LegalSource).where(LegalSource.id == definition.source_id))
    ).scalar_one_or_none()
    if source is None:
        raise HTTPException(409, "Deadline source reference is missing")
    approved = (
        await db.execute(
            select(LegalRuleReleaseEvent.id).where(
                LegalRuleReleaseEvent.event_type == "PRODUCT_OWNER_APPROVED",
                LegalRuleReleaseEvent.decision == "APPROVED",
                LegalRuleReleaseEvent.release_scope == "DEADLINE",
                LegalRuleReleaseEvent.rule_id == definition.rule_id,
                LegalRuleReleaseEvent.source_id == definition.source_id,
                LegalRuleReleaseEvent.mapping_id == definition.mapping_id,
                LegalRuleReleaseEvent.deadline_definition_id == definition.id,
            ).order_by(
                LegalRuleReleaseEvent.created_at.desc(),
                LegalRuleReleaseEvent.id.desc(),
            ).limit(1)
        )
    ).scalar_one_or_none()
    revoked = (
        await db.execute(
            select(LegalRuleReleaseEvent.id).where(
                LegalRuleReleaseEvent.event_type == "PRODUCT_OWNER_REVOKED",
                LegalRuleReleaseEvent.decision == "REVOKED",
                LegalRuleReleaseEvent.release_scope == "DEADLINE",
                LegalRuleReleaseEvent.rule_id == definition.rule_id,
                LegalRuleReleaseEvent.source_id == definition.source_id,
                LegalRuleReleaseEvent.mapping_id == definition.mapping_id,
                LegalRuleReleaseEvent.deadline_definition_id == definition.id,
            ).order_by(
                LegalRuleReleaseEvent.created_at.desc(),
                LegalRuleReleaseEvent.id.desc(),
            ).limit(1)
        )
    ).scalar_one_or_none()
    # The latest decision wins; a later revoke invalidates an earlier approval.
    is_owner_approved = approved is not None and (
        revoked is None
        or str(revoked) < str(approved)
    )
    if revoked is not None and approved is not None:
        latest_decision = (
            await db.execute(
                select(LegalRuleReleaseEvent.event_type).where(
                    LegalRuleReleaseEvent.release_scope == "DEADLINE",
                    LegalRuleReleaseEvent.rule_id == definition.rule_id,
                    LegalRuleReleaseEvent.source_id == definition.source_id,
                    LegalRuleReleaseEvent.mapping_id == definition.mapping_id,
                    LegalRuleReleaseEvent.deadline_definition_id == definition.id,
                    LegalRuleReleaseEvent.decision.in_(["APPROVED", "REVOKED"]),
                ).order_by(
                    LegalRuleReleaseEvent.created_at.desc(),
                    LegalRuleReleaseEvent.id.desc(),
                ).limit(1)
            )
        ).scalar_one_or_none()
        is_owner_approved = latest_decision == "PRODUCT_OWNER_APPROVED"

    holidays = frozenset(date.fromisoformat(item) for item in definition.holidays)
    rule = DeadlineRule(
        rule_id=definition.rule_id,
        source_citation=f"{source.instrument_title}, {definition.mapping_id}",
        source_version=source.version_label,
        effective_from=definition.effective_from,
        effective_to=definition.effective_to,
        offset=definition.offset,
        unit=definition.unit,
        adjustment=definition.adjustment,
        exclude_trigger_day=definition.exclude_trigger_day,
        approved=is_owner_approved,
    )
    candidate = calculate_deadline_candidate(
        rule,
        trigger_date=trigger_date,
        applicable=True,
        holidays=holidays,
    )
    if candidate is None:
        return {
            "status": "NO_CANDIDATE",
            "candidate_due_date": None,
            "customer_calendar_write": False,
            "message": "Trigger is outside the registered rule's effective interval.",
        }

    fact_is_verified = (
        fact.trust_level == "AUTHORIZED_DOCUMENT_BACKED"
        and fact.verification_status == "VERIFIED"
        and fact.verified_by is not None
        and fact.verified_at is not None
        and fact.document_id is not None
        and fact.source_reference
    )
    release_ready = is_owner_approved and fact_is_verified
    if not release_ready:
        return {
            "status": "PREVIEW_ONLY",
            "candidate_due_date": candidate.isoformat(),
            "release_state": "PRODUCT_OWNER_NOT_APPROVED" if not is_owner_approved else "TRIGGER_FACT_NOT_VERIFIED",
            "trigger_fact_id": str(fact.id),
            "trigger_fact_verification": fact.verification_status,
            "source_state": _source_state(source),
            "customer_calendar_write": False,
            "message": "Calculated date candidate only; no statutory deadline has been activated or persisted.",
        }

    existing = (
        await db.execute(
            select(ComplianceCalendarEvent).where(
                ComplianceCalendarEvent.company_id == body.company_id,
                ComplianceCalendarEvent.event_type == CalendarEventType(definition.event_type),
                ComplianceCalendarEvent.period_label == definition.period_label,
            )
        )
    ).scalar_one_or_none()
    if existing is not None and existing.status in (
        CalendarEventStatus.COMPLETED,
        CalendarEventStatus.WAIVED,
    ):
        return {
            "status": "HISTORICAL_EVENT_PRESERVED",
            "candidate_due_date": candidate.isoformat(),
            "customer_calendar_write": False,
            "message": "Completed or waived event history is immutable.",
        }
    manifest_payload = {
        "rule_id": definition.rule_id,
        "source_id": str(source.id),
        "source_version": source.version_label,
        "mapping_id": str(definition.mapping_id),
        "deadline_definition_id": str(definition.id),
        "trigger_fact_id": str(fact.id),
        "trigger_fact_source_reference": fact.source_reference,
        "trigger_date": trigger_date.isoformat(),
        "due_date": candidate.isoformat(),
        "unit": definition.unit,
        "offset": definition.offset,
        "adjustment": definition.adjustment,
        "holidays": sorted(item.isoformat() for item in holidays),
        "product_owner_approval": True,
    }
    manifest_hash = hashlib.sha256(
        json.dumps(manifest_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if existing is None:
        existing = ComplianceCalendarEvent(
            company_id=body.company_id,
            event_type=CalendarEventType(definition.event_type),
            title=definition.title,
            description="Product-owner released date derived from a verified company fact. Review underlying source and evidence.",
            due_date=candidate,
            reminder_30_days=candidate - timedelta(days=30),
            reminder_14_days=candidate - timedelta(days=14),
            reminder_7_days=candidate - timedelta(days=7),
            period_label=definition.period_label,
            status=CalendarEventStatus.UPCOMING,
            is_statutory=True,
        )
        db.add(existing)
    else:
        existing.title = definition.title
        existing.due_date = candidate
        existing.reminder_30_days = candidate - timedelta(days=30)
        existing.reminder_14_days = candidate - timedelta(days=14)
        existing.reminder_7_days = candidate - timedelta(days=7)
    existing.statutory_basis = source.citation[:200]
    existing.legal_rule_id = definition.rule_id
    existing.legal_source_citation = source.citation
    existing.legal_source_version = source.version_label
    existing.legal_effective_from = definition.effective_from
    existing.legal_effective_to = definition.effective_to
    existing.legal_trigger_date = trigger_date
    existing.trigger_evidence_ref = fact.source_reference
    existing.legal_manifest_sha256 = manifest_hash
    await db.flush()
    return {
        "status": "PRODUCT_OWNER_RELEASED",
        "candidate_due_date": candidate.isoformat(),
        "calendar_event_id": str(existing.id),
        "manifest_sha256": manifest_hash,
        "customer_calendar_write": True,
        "legal_verification_status": "UNCHANGED",
        "notice": "This is a product-owner released compliance workflow deadline, not an independent legal opinion or certification.",
    }


@router.get("/rules/{rule_id}")
async def get_rule_provenance(
    rule_id: str,
    db: AsyncSession = Depends(get_db_for_user),
):
    rule = (
        await db.execute(select(LegalRule).where(LegalRule.rule_id == rule_id))
    ).scalar_one_or_none()
    if rule is None:
        raise HTTPException(404, "Legal rule not found")
    mappings = (
        await db.execute(
            select(LegalRuleSourceMapping).where(
                LegalRuleSourceMapping.rule_id == rule_id
            ).order_by(LegalRuleSourceMapping.created_at.asc())
        )
    ).scalars().all()
    results = []
    for mapping in mappings:
        source = (
            await db.execute(select(LegalSource).where(LegalSource.id == mapping.source_id))
        ).scalar_one_or_none()
        if source is None:
            continue
        approvals = (
            await db.execute(
                select(LegalRuleReleaseEvent).where(
                    LegalRuleReleaseEvent.rule_id == rule_id,
                    LegalRuleReleaseEvent.mapping_id == mapping.id,
                    LegalRuleReleaseEvent.source_id == source.id,
                    LegalRuleReleaseEvent.decision.in_(["APPROVED", "REVOKED"]),
                ).order_by(
                    LegalRuleReleaseEvent.created_at.desc(),
                    LegalRuleReleaseEvent.id.desc(),
                )
            )
        ).scalars().all()
        latest = {}
        for event in approvals:
            if event.release_scope not in latest:
                latest[event.release_scope] = event.decision
        results.append({
            "mapping_id": str(mapping.id),
            "mapping_kind": mapping.mapping_kind,
            "provision_citation": mapping.provision_citation,
            "rationale": mapping.rationale,
            "source": {
                "source_id": str(source.id),
                "title": source.instrument_title,
                "authority": source.issuing_authority,
                "official_url": source.official_url,
                "citation": source.citation,
                "version_label": source.version_label,
                "state": _source_state(source),
                "artifact_bytes_checked": False,
            },
            "product_owner_decisions": latest,
        })
    return {
        "rule_id": rule.rule_id,
        "legal_verification_status": rule.verification_status,
        "product_owner_source_mappings": results,
        "independent_legal_verification_claimed": False,
    }
