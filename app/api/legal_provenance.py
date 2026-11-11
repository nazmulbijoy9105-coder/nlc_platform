"""Product-owner governed legal source registry and deterministic deadline controls.

This API records product-owner decisions without changing the statutory
verification_status on legal_rules. Customer-triggered deadline release also
requires an authenticated, authorized-document-backed VERIFIED CompanyFact.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timedelta, timezone
from typing import Any, Literal, cast
from urllib.parse import urlparse
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.company_authorization import ensure_staff_company_scope
from app.core.dependencies import get_current_user, get_db_for_user, require_company_access, require_roles
from app.core.entitlement import require_entitlement
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

router = APIRouter(prefix="/legal-provenance", tags=["Legal Source Provenance"])


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

    @model_validator(mode="after")
    def validate_artifact_pair(self):
        if (self.artifact_sha256 is None) != (self.artifact_uri is None):
            raise ValueError("artifact_sha256 and artifact_uri must be supplied together")
        if self.effective_to and self.effective_from and self.effective_to < self.effective_from:
            raise ValueError("effective_to cannot precede effective_from")
        return self

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

class ProductOwnerDecision(BaseModel):
    rule_id: str = Field(min_length=3, max_length=50)
    mapping_id: UUID
    release_scope: ReleaseScope
    decision: Decision
    reason: str = Field(min_length=10, max_length=2000)
    deadline_definition_id: UUID | None = None


class DeadlinePreviewRequest(BaseModel):
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
            .order_by(LegalRuleReleaseEvent.sequence_no.desc())
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


# Curated official-register references. These are references only: no file bytes,
# amendments, provision interpretation or legal verification are inferred here.
BD_STARTER_SOURCE_CATALOG: tuple[dict[str, Any], ...] = (
    {
        "source_key": "BD-COMPANIES-ACT-1994",
        "jurisdiction": "BD",
        "instrument_title": "Companies Act, 1994",
        "issuing_authority": "Government of Bangladesh",
        "instrument_type": "ACT",
        "official_url": "https://bdlaws.minlaw.gov.bd/act-print-788.html",
        "citation": "Act No. XVIII of 1994; published 12 September 1994",
        "version_label": "1994-base-text-amendment-chain-not-yet-reconciled",
        "publication_date": date(1994, 9, 12),
    },
    {
        "source_key": "BD-BSEC-CGC-2018",
        "jurisdiction": "BD",
        "instrument_title": "Corporate Governance Code, 2018",
        "issuing_authority": "Bangladesh Securities and Exchange Commission",
        "instrument_type": "CODE",
        "official_url": "https://sec.gov.bd/act-rules-and-regulations",
        "citation": "Corporate Governance Code, 2018; BSEC official regulations register",
        "version_label": "2018-base-code-official-register-reference",
    },
    {
        "source_key": "BD-BSEC-CGC-AMENDMENT-2023-11-20",
        "jurisdiction": "BD",
        "instrument_title": "Amendment to Corporate Governance Code, 2018",
        "issuing_authority": "Bangladesh Securities and Exchange Commission",
        "instrument_type": "NOTIFICATION",
        "official_url": "https://sec.gov.bd/act-rules-and-regulations",
        "citation": "BSEC notification of amendment to Corporate Governance Code, 2018; listed 20 November 2023",
        "version_label": "bsec-amendment-notification-2023-11-20",
        "publication_date": date(2023, 11, 20),
    },
    {
        "source_key": "BD-LABOUR-ACT-2006",
        "jurisdiction": "BD",
        "instrument_title": "Bangladesh Labour Act, 2006",
        "issuing_authority": "Government of Bangladesh",
        "instrument_type": "ACT",
        "official_url": "https://bdlaws.minlaw.gov.bd/act-details-952.html?lang=en",
        "citation": "Act No. XLII of 2006; published 11 October 2006",
        "version_label": "2006-base-text-amendment-chain-not-yet-reconciled",
        "publication_date": date(2006, 10, 11),
    },
    {
        "source_key": "BD-LABOUR-AMENDMENT-ACT-2026",
        "jurisdiction": "BD",
        "instrument_title": "Bangladesh Labour (Amendment) Act, 2026",
        "issuing_authority": "Government of Bangladesh; Ministry of Labour and Employment",
        "instrument_type": "ACT",
        "official_url": "https://mole.gov.bd/pages/legislative-informations",
        "citation": "Ministry of Labour legislative information entry; published 16 April 2026",
        "version_label": "ministry-listing-publication-2026-04-16",
        "publication_date": date(2026, 4, 16),
    },
    {
        "source_key": "BD-INCOME-TAX-ACT-2023-AUTHENTIC-EN-2025",
        "jurisdiction": "BD",
        "instrument_title": "Income Tax Act, 2023 — Authentic English Text",
        "issuing_authority": "National Board of Revenue",
        "instrument_type": "ACT",
        "official_url": "https://nbr.gov.bd/uploads/acts/3190-SRO-404-NBR-16_October_2025(10455-10741).pdf",
        "citation": "Act No. XII of 2023; S.R.O. No. 404-Law/2025; notification dated 8 October 2025, Gazette published 16 October 2025",
        "version_label": "authentic-english-text-sro-404-2025-10-16",
        "publication_date": date(2025, 10, 16),
    },
    {
        "source_key": "BD-FINANCE-ACT-2026",
        "jurisdiction": "BD",
        "instrument_title": "Finance Act, 2026",
        "issuing_authority": "Government of Bangladesh; National Board of Revenue register",
        "instrument_type": "ACT",
        "official_url": "https://nbr.gov.bd/uploads/acts/Finance_Act_2026.pdf",
        "citation": "Finance Act, 2026; NBR register date 6 July 2026",
        "version_label": "finance-act-2026-nbr-publication-2026-07-06",
        "publication_date": date(2026, 7, 6),
    },
    {
        "source_key": "BD-VAT-SD-ACT-2012-AUTHENTIC-EN-2025",
        "jurisdiction": "BD",
        "instrument_title": "Value Added Tax and Supplementary Duty Act, 2012 — Authentic English Text",
        "issuing_authority": "Government of Bangladesh; National Board of Revenue",
        "instrument_type": "ACT",
        "official_url": "https://bdlaws.minlaw.gov.bd/upload/act/2026-01-18-15-14-21-72.-Value-Added-Tax-and-Supplementary-Duty-Act%2C-2012.pdf",
        "citation": "Act No. XLVII of 2012; S.R.O. No. 440-Law/2025/326-Mushak dated 5 November 2025",
        "version_label": "authentic-english-text-sro-440-2025-11-05",
        "publication_date": date(2025, 11, 5),
    },
    {
        "source_key": "BD-FOREIGN-EXCHANGE-REGULATION-ACT-1947",
        "jurisdiction": "BD",
        "instrument_title": "Foreign Exchange Regulation Act, 1947",
        "issuing_authority": "Government of Bangladesh",
        "instrument_type": "ACT",
        "official_url": "https://bdlaws.minlaw.gov.bd/act-print-218.html",
        "citation": "Act No. VII of 1947; dated 11 March 1947",
        "version_label": "1947-base-text-amendment-chain-not-yet-reconciled",
        "publication_date": date(1947, 3, 11),
    },
    {
        "source_key": "BD-STAMP-ACT-1899",
        "jurisdiction": "BD",
        "instrument_title": "Stamp Act, 1899",
        "issuing_authority": "Government of Bangladesh",
        "instrument_type": "ACT",
        "official_url": "https://bdlaws.minlaw.gov.bd/act-print-77.html",
        "citation": "Act No. II of 1899; dated 27 January 1899",
        "version_label": "1899-base-text-schedule-and-amendment-chain-not-yet-reconciled",
        "publication_date": date(1899, 1, 27),
    },
)


class StarterSourceImport(BaseModel):
    source_keys: list[str] = Field(min_length=1, max_length=20)
    reason: str = Field(min_length=10, max_length=2000)


@router.get("/starter-sources", dependencies=[Depends(require_roles("SUPER_ADMIN"))])
async def get_starter_source_catalog(
    db: AsyncSession = Depends(get_db_for_user),
    current_user=Depends(get_current_user),
):
    """Return vetted official-register references and registration state."""
    existing = (
        await db.execute(select(LegalSource.source_key, LegalSource.version_label))
    ).all()
    existing_keys = {(key, version) for key, version in existing}
    return [
        {
            **{
                key: (value.isoformat() if isinstance(value, date) else value)
                for key, value in candidate.items()
            },
            "registration_state": (
                "REGISTERED" if (candidate["source_key"], candidate["version_label"]) in existing_keys
                else "NOT_REGISTERED"
            ),
            "artifact_state": "REFERENCE_ONLY",
            "artifact_bytes_checked": False,
            "rule_mappings_created": False,
            "owner_approval_created": False,
        }
        for candidate in BD_STARTER_SOURCE_CATALOG
    ]


@router.post("/starter-sources/register", status_code=201,
             dependencies=[Depends(require_roles("SUPER_ADMIN"))])
async def register_starter_source_references(
    body: StarterSourceImport,
    db: AsyncSession = Depends(get_db_for_user),
    current_user=Depends(get_current_user),
):
    """Explicit, idempotent owner action; imports references only, never approvals."""
    catalog = {item["source_key"]: item for item in BD_STARTER_SOURCE_CATALOG}
    unknown = sorted(set(body.source_keys) - set(catalog))
    if unknown:
        raise HTTPException(422, f"Unknown starter source keys: {unknown}")

    results = []
    for source_key in dict.fromkeys(body.source_keys):
        candidate = catalog[source_key]
        existing = (
            await db.execute(
                select(LegalSource).where(
                    LegalSource.source_key == source_key,
                    LegalSource.version_label == candidate["version_label"],
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            results.append({
                "source_key": source_key,
                "source_id": str(existing.id),
                "state": "ALREADY_REGISTERED",
            })
            continue

        source_values = dict(candidate)
        source = LegalSource(
            **source_values,
            created_by=current_user.id,
            # Starter entries are references only. No hash/URI is fabricated.
            artifact_sha256=None,
            artifact_uri=None,
        )
        db.add(source)
        await db.flush()
        event = await _append_event(
            db,
            event_type="SOURCE_REGISTERED",
            actor_id=current_user.id,
            reason=body.reason,
            source_id=source.id,
            metadata={
                "source_key": source_key,
                "version_label": source.version_label,
                "registration_method": "EXPLICIT_SUPER_ADMIN_STARTER_CATALOG_SELECTION",
                "source_state": "REFERENCE_ONLY",
                "artifact_bytes_checked": False,
                "rule_mappings_created": False,
                "owner_approval_created": False,
            },
        )
        results.append({
            "source_key": source_key,
            "source_id": str(source.id),
            "event_id": str(event.id),
            "event_hash": event.event_hash,
            "state": "SOURCE_REGISTERED_REFERENCE_ONLY",
        })

    return {
        "registered": sum(item["state"] == "SOURCE_REGISTERED_REFERENCE_ONLY" for item in results),
        "already_registered": sum(item["state"] == "ALREADY_REGISTERED" for item in results),
        "sources": results,
        "legal_verification_status_changed": False,
        "rule_mappings_created": False,
        "product_owner_approval_created": False,
    }


@router.post("/sources", status_code=201, dependencies=[Depends(require_roles("SUPER_ADMIN"))])
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


@router.post("/mappings", status_code=201, dependencies=[Depends(require_roles("SUPER_ADMIN"))])
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


@router.post("/deadlines/definitions", status_code=201, dependencies=[Depends(require_roles("SUPER_ADMIN"))])
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


@router.post("/decisions", status_code=201, dependencies=[Depends(require_roles("SUPER_ADMIN"))])
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


@router.post(
    "/companies/{company_id}/deadlines/{definition_id}/preview",
    dependencies=[
        Depends(require_company_access("company_id")),
        Depends(require_entitlement("compliance_package")),
    ],
)
async def preview_or_release_deadline(
    company_id: UUID,
    definition_id: UUID,
    body: DeadlinePreviewRequest,
    db: AsyncSession = Depends(get_db_for_user),
    current_user=Depends(get_current_user),
):
    if current_user.role == "LEGAL_STAFF":
        await ensure_staff_company_scope(company_id, current_user, db)
    definition = (
        await db.execute(
            select(LegalDeadlineDefinition).where(
                LegalDeadlineDefinition.id == definition_id
            )
        )
    ).scalar_one_or_none()
    if definition is None:
        raise HTTPException(404, "Deadline definition not found")
    fact = (
        await db.execute(
            select(CompanyFact).where(
                CompanyFact.id == body.fact_id,
                CompanyFact.company_id == company_id,
            )
        )
    ).scalar_one_or_none()
    if fact is None:
        raise HTTPException(404, "Company fact not found in this tenant")
    if fact.fact_key != definition.trigger_fact_key:
        raise HTTPException(422, "Company fact key does not match the deadline trigger")
    if not isinstance(fact.fact_value, (str, dict)):
        raise HTTPException(422, "Trigger fact must contain an ISO date value")
    raw_date: Any = (
        fact.fact_value.get("date") or fact.fact_value.get("value")
        if isinstance(fact.fact_value, dict)
        else fact.fact_value
    )
    if not isinstance(raw_date, str):
        raise HTTPException(422, "Trigger fact value must be an ISO YYYY-MM-DD date")
    try:
        trigger_date = date.fromisoformat(raw_date)
    except (TypeError, ValueError):
        raise HTTPException(422, "Trigger fact value must be an ISO YYYY-MM-DD date") from None

    source = (
        await db.execute(select(LegalSource).where(LegalSource.id == definition.source_id))
    ).scalar_one_or_none()
    if source is None:
        raise HTTPException(409, "Deadline source reference is missing")
    latest_decision = (
        await db.execute(
            select(LegalRuleReleaseEvent).where(
                LegalRuleReleaseEvent.release_scope == "DEADLINE",
                LegalRuleReleaseEvent.rule_id == definition.rule_id,
                LegalRuleReleaseEvent.source_id == definition.source_id,
                LegalRuleReleaseEvent.mapping_id == definition.mapping_id,
                LegalRuleReleaseEvent.deadline_definition_id == definition.id,
                LegalRuleReleaseEvent.decision.in_(["APPROVED", "REVOKED"]),
            ).order_by(LegalRuleReleaseEvent.sequence_no.desc()).limit(1)
        )
    ).scalar_one_or_none()
    is_owner_approved = (
        latest_decision is not None
        and latest_decision.event_type == "PRODUCT_OWNER_APPROVED"
        and latest_decision.decision == "APPROVED"
    )
    mapping = (
        await db.execute(
            select(LegalRuleSourceMapping).where(
                LegalRuleSourceMapping.id == definition.mapping_id
            )
        )
    ).scalar_one_or_none()
    if mapping is None:
        raise HTTPException(409, "Deadline source mapping is missing")
    effective_from = max(
        definition.effective_from,
        source.effective_from or definition.effective_from,
    )
    effective_to_candidates = [
        value for value in (definition.effective_to, source.effective_to) if value is not None
    ]
    effective_to = min(effective_to_candidates) if effective_to_candidates else None
    if effective_to is not None and effective_to < effective_from:
        return {
            "status": "NO_CANDIDATE",
            "candidate_due_date": None,
            "customer_calendar_write": False,
            "message": "The source and deadline-definition effective periods do not overlap.",
        }
    holidays = frozenset(date.fromisoformat(str(item)) for item in definition.holidays)
    rule = DeadlineRule(
        rule_id=definition.rule_id,
        source_citation=mapping.provision_citation,
        source_version=source.version_label,
        effective_from=effective_from,
        effective_to=effective_to,
        offset=definition.offset,
        unit=cast(Literal["DAYS", "CLEAR_DAYS", "MONTHS", "YEARS"], definition.unit),
        adjustment=cast(Literal["NONE", "FOLLOWING", "PRECEDING"], definition.adjustment),
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
                ComplianceCalendarEvent.company_id == company_id,
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
        "source_url": source.official_url,
        "source_artifact_sha256": source.artifact_sha256,
        "provision_citation": mapping.provision_citation,
        "effective_from": effective_from.isoformat(),
        "effective_to": effective_to.isoformat() if effective_to else None,
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
            company_id=company_id,
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
    existing.legal_effective_from = effective_from
    existing.legal_effective_to = effective_to
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


@router.get("/sources", dependencies=[Depends(require_roles("SUPER_ADMIN"))])
async def list_legal_sources(
    limit: int = Query(200, ge=1, le=500),
    db: AsyncSession = Depends(get_db_for_user),
    current_user=Depends(get_current_user),
):
    """List registered official-source references for authorised source stewards."""
    rows = (
        await db.execute(
            select(LegalSource)
            .order_by(LegalSource.jurisdiction, LegalSource.instrument_title, LegalSource.version_label)
            .limit(limit)
        )
    ).scalars().all()
    return [
        {
            "source_id": str(row.id),
            "source_key": row.source_key,
            "jurisdiction": row.jurisdiction,
            "instrument_title": row.instrument_title,
            "issuing_authority": row.issuing_authority,
            "instrument_type": row.instrument_type,
            "official_url": row.official_url,
            "citation": row.citation,
            "version_label": row.version_label,
            "publication_date": row.publication_date.isoformat() if row.publication_date else None,
            "effective_from": row.effective_from.isoformat() if row.effective_from else None,
            "effective_to": row.effective_to.isoformat() if row.effective_to else None,
            "artifact_state": _source_state(row),
            "artifact_bytes_checked": False,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


@router.get("/deadlines/definitions", dependencies=[Depends(require_roles("SUPER_ADMIN"))])
async def list_deadline_definitions(
    limit: int = Query(200, ge=1, le=500),
    db: AsyncSession = Depends(get_db_for_user),
    current_user=Depends(get_current_user),
):
    rows = (
        await db.execute(
            select(LegalDeadlineDefinition)
            .order_by(LegalDeadlineDefinition.rule_id, LegalDeadlineDefinition.effective_from)
            .limit(limit)
        )
    ).scalars().all()
    result = []
    for definition in rows:
        latest = (
            await db.execute(
                select(LegalRuleReleaseEvent)
                .where(
                    LegalRuleReleaseEvent.deadline_definition_id == definition.id,
                    LegalRuleReleaseEvent.release_scope == "DEADLINE",
                    LegalRuleReleaseEvent.decision.in_(["APPROVED", "REVOKED"]),
                )
                .order_by(LegalRuleReleaseEvent.sequence_no.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        result.append({
            "definition_id": str(definition.id),
            "rule_id": definition.rule_id,
            "source_id": str(definition.source_id),
            "mapping_id": str(definition.mapping_id),
            "event_type": definition.event_type,
            "title": definition.title,
            "trigger_fact_key": definition.trigger_fact_key,
            "period_label": definition.period_label,
            "offset": definition.offset,
            "unit": definition.unit,
            "adjustment": definition.adjustment,
            "effective_from": definition.effective_from.isoformat(),
            "effective_to": definition.effective_to.isoformat() if definition.effective_to else None,
            "owner_decision": (
                latest.decision if latest and latest.event_type == "PRODUCT_OWNER_APPROVED"
                else "REVOKED" if latest else "PENDING"
            ),
        })
    return result


@router.get("/mappings", dependencies=[Depends(require_roles("SUPER_ADMIN"))])
async def list_legal_rule_mappings(
    rule_id: str | None = None,
    limit: int = Query(500, ge=1, le=1000),
    db: AsyncSession = Depends(get_db_for_user),
    current_user=Depends(get_current_user),
):
    statement = (
        select(LegalRuleSourceMapping, LegalSource)
        .join(LegalSource, LegalSource.id == LegalRuleSourceMapping.source_id)
        .order_by(LegalRuleSourceMapping.rule_id, LegalRuleSourceMapping.created_at)
        .limit(limit)
    )
    if rule_id:
        statement = statement.where(LegalRuleSourceMapping.rule_id == rule_id)
    rows = (await db.execute(statement)).all()
    return [
        {
            "mapping_id": str(mapping.id),
            "rule_id": mapping.rule_id,
            "source_id": str(source.id),
            "source_title": source.instrument_title,
            "source_version": source.version_label,
            "mapping_kind": mapping.mapping_kind,
            "provision_citation": mapping.provision_citation,
            "rationale": mapping.rationale,
            "created_at": mapping.created_at.isoformat() if mapping.created_at else None,
        }
        for mapping, source in rows
    ]


@router.get("/events", dependencies=[Depends(require_roles("SUPER_ADMIN"))])
async def list_legal_release_events(
    rule_id: str | None = None,
    limit: int = Query(500, ge=1, le=1000),
    db: AsyncSession = Depends(get_db_for_user),
    current_user=Depends(get_current_user),
):
    statement = (
        select(LegalRuleReleaseEvent)
        .order_by(LegalRuleReleaseEvent.sequence_no.desc())
        .limit(limit)
    )
    if rule_id:
        statement = statement.where(LegalRuleReleaseEvent.rule_id == rule_id)
    rows = (await db.execute(statement)).scalars().all()
    return [
        {
            "event_id": str(event.id),
            "sequence_no": event.sequence_no,
            "event_type": event.event_type,
            "release_scope": event.release_scope,
            "decision": event.decision,
            "rule_id": event.rule_id,
            "source_id": str(event.source_id) if event.source_id else None,
            "mapping_id": str(event.mapping_id) if event.mapping_id else None,
            "deadline_definition_id": str(event.deadline_definition_id) if event.deadline_definition_id else None,
            "actor_id": str(event.actor_id),
            "reason": event.reason,
            "event_hash": event.event_hash,
            "previous_event_hash": event.previous_event_hash,
            "created_at": event.created_at.isoformat() if event.created_at else None,
        }
        for event in rows
    ]


@router.get("/rules/{rule_id}")
async def get_rule_provenance(
    rule_id: str,
    db: AsyncSession = Depends(get_db_for_user),
    current_user=Depends(get_current_user),
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
