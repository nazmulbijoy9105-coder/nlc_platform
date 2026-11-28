"""Company fact lifecycle integrated with the existing document vault."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.company_fact import CompanyFact
from app.compliance.fact_provenance import business_date_today, is_internal_profile_fact_key
from app.models.documents import Document
from app.compliance.fact_provenance import coerce_company_profile_fact_value
from app.services.score_invalidation import invalidate_company_score


class CompanyFactService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _mark_company_facts_changed(self, company_id: uuid.UUID) -> None:
        """Clear cached statutory results whenever source facts change."""
        await invalidate_company_score(self.db, company_id)

    @staticmethod
    def _normalize_fact_key(fact_key: str) -> str:
        from dataclasses import fields
        from typing import get_args, get_origin, get_type_hints

        from app.rule_engine import CompanyProfile

        normalized = fact_key.strip()
        allowed = {
            item.name
            for item in fields(CompanyProfile)
            if not is_internal_profile_fact_key(item.name)
        } - {"company_id", "company_name"}
        if normalized not in allowed:
            raise HTTPException(
                status_code=422,
                detail="fact_key must be a supported CompanyProfile fact; company identity and reviewer/system metadata are read-only.",
            )
        annotation = get_type_hints(CompanyProfile).get(normalized)
        candidates = get_args(annotation) or (annotation,)
        if (
            annotation in (list, dict, set, tuple)
            or get_origin(annotation) in (list, dict, set, tuple)
            or any(
                candidate in (list, dict, set, tuple)
                or get_origin(candidate) in (list, dict, set, tuple)
                for candidate in candidates
            )
        ):
            raise HTTPException(
                status_code=422,
                detail="Structured collection facts require a dedicated typed workflow and cannot be asserted through this scalar fact endpoint.",
            )
        return normalized

    async def _latest_fact_id(
        self, company_id: uuid.UUID, fact_key: str
    ) -> uuid.UUID | None:
        result = await self.db.execute(
            select(CompanyFact.id)
            .where(
                CompanyFact.company_id == company_id,
                CompanyFact.fact_key == fact_key,
            )
            .order_by(CompanyFact.created_at.desc(), CompanyFact.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def assert_fact(
        self, *, company_id: uuid.UUID, fact_key: str, fact_value: Any,
        actor_id: uuid.UUID, observed_on: date, source_reference: str | None = None,
    ) -> CompanyFact:
        if observed_on > business_date_today():
            raise HTTPException(status_code=422, detail="observed_on cannot be in the future.")
        normalized_key = self._normalize_fact_key(fact_key)
        try:
            fact_value = coerce_company_profile_fact_value(normalized_key, fact_value)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        fact_value = jsonable_encoder(fact_value)
        await self.db.execute(
            select(Company.id).where(Company.id == company_id).with_for_update()
        )
        previous_id = await self._latest_fact_id(company_id, normalized_key)
        fact = CompanyFact(
            company_id=company_id, fact_key=normalized_key, fact_value=fact_value,
            trust_level="USER_ASSERTED", asserted_by=actor_id, observed_on=observed_on,
            source_reference=source_reference, verification_status="UNVERIFIED",
            supersedes_fact_id=previous_id,
        )
        self.db.add(fact)
        await self.db.flush()
        await self._mark_company_facts_changed(company_id)
        from app.services.domain_events import DomainEventType, publish_domain_event
        await publish_domain_event(
            self.db, company_id=company_id,
            event_type=DomainEventType.COMPANY_FACT_ASSERTED,
            aggregate_type="company_fact", aggregate_id=fact.id, actor_id=actor_id,
            payload={"fact_key": normalized_key, "trust_level": fact.trust_level,
                     "verification_status": fact.verification_status},
        )
        await self.db.refresh(fact)
        return fact

    async def record_document_fact(
        self, *, document_id: uuid.UUID, fact_key: str, fact_value: Any,
        actor_id: uuid.UUID, observed_on: date,
    ) -> CompanyFact:
        if observed_on > business_date_today():
            raise HTTPException(status_code=422, detail="observed_on cannot be in the future.")
        result = await self.db.execute(
            select(Document).where(Document.id == document_id, Document.is_active.is_(True))
        )
        document = result.scalar_one_or_none()
        if document is None:
            raise HTTPException(status_code=404, detail="Active source document not found.")
        if document.ai_generated:
            raise HTTPException(
                status_code=422,
                detail="AI-generated drafts cannot be used as source evidence for company facts.",
            )
        if document.created_by is None or document.created_at is None:
            raise HTTPException(
                status_code=422,
                detail="The source document has no recorded uploader/timestamp and cannot establish document provenance.",
            )
        normalized_key = fact_key.strip()
        if normalized_key in {"agm_court_order_evidence", "agm_court_order_lawyer_decision"}:
            if not isinstance(fact_value, dict):
                raise HTTPException(status_code=422, detail="AGM court-order facts must be structured objects.")
            try:
                if normalized_key == "agm_court_order_evidence":
                    from app.compliance.agm_court_order import AgmCourtOrderEvidence
                    parsed_order = AgmCourtOrderEvidence.from_mapping(fact_value)
                    if parsed_order.authenticated or parsed_order.verified_by or parsed_order.verified_at:
                        raise ValueError("Court-order authentication metadata is assigned only by the independent fact-verification step.")
                else:
                    from app.compliance.agm_court_order import AgmLawyerDecision
                    AgmLawyerDecision.from_mapping(fact_value)
            except (TypeError, ValueError) as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
        else:
            normalized_key = self._normalize_fact_key(normalized_key)
            try:
                fact_value = coerce_company_profile_fact_value(normalized_key, fact_value)
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
        fact_value = jsonable_encoder(fact_value)
        await self.db.execute(
            select(Company.id).where(Company.id == document.company_id).with_for_update()
        )
        previous_id = await self._latest_fact_id(document.company_id, normalized_key)
        fact = CompanyFact(
            company_id=document.company_id,
            fact_key=normalized_key,
            fact_value=fact_value,
            trust_level="AUTHORIZED_DOCUMENT_BACKED",
            asserted_by=actor_id,
            observed_on=observed_on,
            source_reference=f"document:{document.id}",
            document_id=document.id,
            authorized_uploader_id=document.created_by,
            uploaded_at=document.created_at,
            verification_status="UNVERIFIED",
            supersedes_fact_id=previous_id,
        )
        self.db.add(fact)
        await self.db.flush()
        await self._mark_company_facts_changed(document.company_id)
        from app.services.domain_events import DomainEventType, publish_domain_event
        await publish_domain_event(
            self.db, company_id=document.company_id,
            event_type=DomainEventType.COMPANY_FACT_ASSERTED,
            aggregate_type="company_fact", aggregate_id=fact.id, actor_id=actor_id,
            payload={"fact_key": normalized_key, "trust_level": fact.trust_level,
                     "verification_status": fact.verification_status,
                     "source_document_id": str(document.id)},
        )
        await self.db.refresh(fact)
        return fact

    async def verify_fact(
        self, *, fact_id: uuid.UUID, reviewer_id: uuid.UUID,
        decision: str, note: str | None = None,
    ) -> CompanyFact:
        decision = decision.upper()
        if decision not in {"VERIFIED", "REJECTED"}:
            raise HTTPException(status_code=422, detail="Decision must be VERIFIED or REJECTED. Supersession is recorded by creating a new fact version.")
        result = await self.db.execute(select(CompanyFact).where(CompanyFact.id == fact_id))
        fact = result.scalar_one_or_none()
        if fact is None:
            raise HTTPException(status_code=404, detail="Company fact not found.")

        # Serialize verification against concurrent fact-version creation.
        # Fact writers take the same company-row lock before linking a successor.
        await self.db.execute(
            select(Company.id).where(Company.id == fact.company_id).with_for_update()
        )
        locked_result = await self.db.execute(
            select(CompanyFact).where(CompanyFact.id == fact_id).with_for_update()
        )
        fact = locked_result.scalar_one_or_none()
        if fact is None:
            raise HTTPException(status_code=404, detail="Company fact not found.")
        if fact.trust_level != "AUTHORIZED_DOCUMENT_BACKED" or fact.document_id is None:
            raise HTTPException(status_code=422, detail="Only document-backed facts can be document-verified.")
        if fact.verification_status == "SUPERSEDED":
            raise HTTPException(status_code=409, detail="A superseded fact cannot be re-verified; create a new fact version.")
        successor = await self.db.execute(
            select(CompanyFact.id).where(CompanyFact.supersedes_fact_id == fact.id).limit(1)
        )
        if successor.scalar_one_or_none() is not None:
            raise HTTPException(status_code=409, detail="A newer fact version already supersedes this record.")
        if decision == "VERIFIED":
            doc_result = await self.db.execute(
                select(Document).where(
                    Document.id == fact.document_id,
                    Document.company_id == fact.company_id,
                    Document.is_active.is_(True),
                    Document.ai_generated.is_(False),
                )
            )
            source_document = doc_result.scalar_one_or_none()
            if source_document is None:
                raise HTTPException(status_code=409, detail="Source document is no longer an active eligible vault document.")
            if (
                source_document.created_by != fact.authorized_uploader_id
                or source_document.created_at != fact.uploaded_at
            ):
                raise HTTPException(
                    status_code=409,
                    detail="Source document uploader or upload timestamp no longer matches the recorded fact provenance.",
                )
            verified_at = datetime.now(timezone.utc)
            if fact.fact_key == "agm_court_order_evidence":
                from app.compliance.agm_court_order import AgmCourtOrderEvidence
                order_payload = dict(fact.fact_value or {})
                order = AgmCourtOrderEvidence.from_mapping(order_payload)
                if order.order_status == "UNKNOWN":
                    raise HTTPException(
                        status_code=422,
                        detail="A current court-order status must be checked and recorded before verification.",
                    )
                if reviewer_id == fact.authorized_uploader_id:
                    raise HTTPException(
                        status_code=403,
                        detail="The document uploader cannot independently verify the court-order fact.",
                    )
                order_payload.update({
                    "authenticated": True,
                    "verified_by": str(reviewer_id),
                    "verified_at": verified_at.isoformat(),
                })
                fact.fact_value = jsonable_encoder(order_payload)
                # The 30-day freshness window measures the independent
                # operative-status check, not the historical order date or
                # the uploader's self-reported observation date.
                fact.observed_on = business_date_today()
            elif fact.fact_key == "agm_court_order_lawyer_decision":
                from app.compliance.agm_court_order import AgmLawyerDecision
                decision_payload = dict(fact.fact_value or {})
                lawyer_decision = AgmLawyerDecision.from_mapping(decision_payload)
                if (
                    str(reviewer_id) == lawyer_decision.reviewer_id
                    or str(reviewer_id) != lawyer_decision.reviewer_qualification_verified_by
                    or lawyer_decision.reviewer_qualification_verified_at > verified_at
                ):
                    raise HTTPException(
                        status_code=403,
                        detail="The decision's counsel qualification must be verified by a separate reviewer recorded as its qualification verifier.",
                    )
            fact.verified_by = reviewer_id
            fact.verified_at = verified_at
        else:
            fact.verified_by = None
            fact.verified_at = None
        fact.verification_status = decision
        fact.verification_note = note
        await self.db.flush()
        await self._mark_company_facts_changed(fact.company_id)
        from app.services.domain_events import DomainEventType, publish_domain_event
        await publish_domain_event(
            self.db, company_id=fact.company_id,
            event_type=DomainEventType.COMPANY_FACT_VERIFIED,
            aggregate_type="company_fact", aggregate_id=fact.id, actor_id=reviewer_id,
            payload={"fact_key": fact.fact_key, "verification_status": decision},
        )
        await self.db.refresh(fact)
        return fact

    async def list_current(self, company_id: uuid.UUID) -> list[CompanyFact]:
        result = await self.db.execute(
            select(CompanyFact)
            .where(CompanyFact.company_id == company_id)
            .order_by(CompanyFact.fact_key, CompanyFact.created_at.desc(), CompanyFact.id.desc())
        )
        latest: dict[str, CompanyFact] = {}
        for fact in result.scalars().all():
            latest.setdefault(fact.fact_key, fact)
        return [
            fact for fact in latest.values()
            if fact.verification_status not in {"REJECTED", "SUPERSEDED"}
        ]


def fact_response(fact: CompanyFact) -> dict[str, Any]:
    payload = fact.provenance_payload()
    payload.update({
        "company_id": str(fact.company_id),
        "fact_value": fact.fact_value,
        "verification_note": fact.verification_note,
    })
    return payload
