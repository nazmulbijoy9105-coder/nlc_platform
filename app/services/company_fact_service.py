"""Company fact lifecycle integrated with the existing document vault."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.company_fact import CompanyFact
from app.models.documents import Document


class CompanyFactService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _latest_fact_id(
        self, company_id: uuid.UUID, fact_key: str
    ) -> uuid.UUID | None:
        result = await self.db.execute(
            select(CompanyFact.id)
            .where(
                CompanyFact.company_id == company_id,
                CompanyFact.fact_key == fact_key,
                CompanyFact.is_current.is_(True),
            )
            .order_by(CompanyFact.created_at.desc(), CompanyFact.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def assert_fact(
        self, *, company_id: uuid.UUID, fact_key: str, fact_value: Any,
        actor_id: uuid.UUID, observed_on: date, source_reference: str | None = None,
    ) -> CompanyFact:
        normalized_key = fact_key.strip()
        if not normalized_key:
            raise HTTPException(status_code=422, detail="fact_key cannot be blank.")
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
        await self.db.refresh(fact)
        return fact

    async def record_document_fact(
        self, *, document_id: uuid.UUID, fact_key: str, fact_value: Any,
        actor_id: uuid.UUID, observed_on: date, source_reference: str | None = None,
    ) -> CompanyFact:
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
        if not normalized_key:
            raise HTTPException(status_code=422, detail="fact_key cannot be blank.")
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
            source_reference=source_reference or f"document:{document.id}",
            document_id=document.id,
            authorized_uploader_id=document.created_by,
            uploaded_at=document.created_at,
            verification_status="UNVERIFIED",
            supersedes_fact_id=previous_id,
        )
        self.db.add(fact)
        await self.db.flush()
        await self.db.refresh(fact)
        return fact

    async def verify_fact(
        self, *, fact_id: uuid.UUID, reviewer_id: uuid.UUID,
        decision: str, note: str | None = None,
    ) -> CompanyFact:
        decision = decision.upper()
        if decision not in {"VERIFIED", "REJECTED", "SUPERSEDED"}:
            raise HTTPException(status_code=422, detail="Decision must be VERIFIED, REJECTED or SUPERSEDED.")
        result = await self.db.execute(select(CompanyFact).where(CompanyFact.id == fact_id))
        fact = result.scalar_one_or_none()
        if fact is None:
            raise HTTPException(status_code=404, detail="Company fact not found.")
        if fact.trust_level != "AUTHORIZED_DOCUMENT_BACKED" or fact.document_id is None:
            raise HTTPException(status_code=422, detail="Only document-backed facts can be document-verified.")
        successor = await self.db.execute(
            select(CompanyFact.id).where(CompanyFact.supersedes_fact_id == fact.id).limit(1)
        )
        if successor.scalar_one_or_none() is not None:
            raise HTTPException(status_code=409, detail="A newer fact version already supersedes this record.")
        if decision == "VERIFIED":
            doc_result = await self.db.execute(
                select(Document.id).where(
                    Document.id == fact.document_id,
                    Document.company_id == fact.company_id,
                    Document.is_active.is_(True),
                    Document.ai_generated.is_(False),
                )
            )
            if doc_result.scalar_one_or_none() is None:
                raise HTTPException(status_code=409, detail="Source document is no longer an active eligible vault document.")
            fact.verified_by = reviewer_id
            fact.verified_at = datetime.now(timezone.utc)
        else:
            fact.verified_by = None
            fact.verified_at = None
        fact.verification_status = decision
        fact.verification_note = note
        await self.db.flush()
        await self.db.refresh(fact)
        return fact

    async def list_current(self, company_id: uuid.UUID) -> list[CompanyFact]:
        result = await self.db.execute(
            select(CompanyFact)
            .where(CompanyFact.company_id == company_id, CompanyFact.is_current.is_(True))
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
        "is_current": fact.is_current,
    })
    return payload
