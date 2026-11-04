"""Authenticated Articles of Association verification workflow.

Source documents are immutable/version-pinned. Verification requires a
separate legal reviewer; decisions and revocations are append-only audited.
"""
from __future__ import annotations

import asyncio
import hashlib
import re
import uuid
from datetime import UTC, date, datetime
from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.core.config import get_settings
from app.core.dependencies import (
    get_current_user,
    get_db_for_user,
    require_company_access,
    require_roles,
)
from app.models.documents import (
    ArticlesVerification,
    ArticlesVerificationEvent,
    Document,
)
from app.models.enums import DocumentType
from app.models.user import User

router = APIRouter()
logger = structlog.get_logger(__name__)


class ArticlesUploadResponse(BaseModel):
    document_id: str
    company_id: str
    title: str
    checksum_sha256: str
    file_size_bytes: int
    status: str


class ArticlesSubmitRequest(BaseModel):
    document_id: uuid.UUID


class ArticlesReviewRequest(BaseModel):
    decision: Literal["VERIFIED", "REJECTED"]
    effective_from: date | None = None
    quorum_variation_exists: bool | None = None
    quorum_required: int | None = Field(default=None, ge=1, le=100)
    clause_reference: str | None = Field(default=None, min_length=1, max_length=255)
    quorum_clause_text: str | None = Field(default=None, min_length=1, max_length=10000)
    reviewer_note: str | None = None


class ArticlesRevokeRequest(BaseModel):
    reason: str = Field(min_length=10, max_length=4000)


def _verification_payload(item: ArticlesVerification) -> dict:
    return {
        "id": str(item.id),
        "company_id": str(item.company_id),
        "document_id": str(item.document_id),
        "source_checksum_sha256": item.source_checksum_sha256,
        "source_document_version": item.source_document_version,
        "status": item.status,
        "submitted_by": str(item.submitted_by),
        "submitted_at": item.submitted_at.isoformat(),
        "reviewed_by": str(item.reviewed_by) if item.reviewed_by else None,
        "reviewed_at": item.reviewed_at.isoformat() if item.reviewed_at else None,
        "effective_from": item.effective_from.isoformat() if item.effective_from else None,
        "quorum_variation_exists": item.quorum_variation_exists,
        "quorum_required": item.quorum_required,
        "clause_reference": item.clause_reference,
        "quorum_clause_text": item.quorum_clause_text,
        "reviewer_note": item.reviewer_note,
        "revoked_by": str(item.revoked_by) if item.revoked_by else None,
        "revoked_at": item.revoked_at.isoformat() if item.revoked_at else None,
        "revocation_reason": item.revocation_reason,
    }


def _event_payload(event: ArticlesVerificationEvent) -> dict:
    return {
        "id": str(event.id),
        "verification_id": str(event.verification_id),
        "actor_id": str(event.actor_id),
        "action": event.action,
        "previous_status": event.previous_status,
        "new_status": event.new_status,
        "source_checksum_sha256": event.source_checksum_sha256,
        "note": event.note,
        "created_at": event.created_at.isoformat(),
    }



@router.post(
    "/companies/{company_id}/articles-document",
    response_model=ArticlesUploadResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles("ADMIN_STAFF", "LEGAL_STAFF", "SUPER_ADMIN"))],
)
async def upload_articles_document(
    company_id: uuid.UUID,
    file: UploadFile = File(...),
    _: uuid.UUID = Depends(require_company_access()),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    """Upload a source PDF; compute its SHA-256 before it can be reviewed."""
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=415, detail="Only PDF Articles documents are accepted.")
    payload = await file.read(20 * 1024 * 1024 + 1)
    if not payload or len(payload) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Articles PDF must be between 1 byte and 20 MB.")
    if not payload.startswith(b"%PDF-"):
        raise HTTPException(status_code=422, detail="Uploaded file does not have a valid PDF signature.")

    checksum = hashlib.sha256(payload).hexdigest()
    document_id = uuid.uuid4()
    settings = get_settings()
    s3_key = (
        f"{settings.s3_document_prefix}ARTICLES_OF_ASSOCIATION/"
        f"{company_id}/{document_id}.pdf"
    )
    document = Document(
        id=document_id,
        company_id=company_id,
        document_type=DocumentType.ARTICLES_OF_ASSOCIATION,
        title="Articles of Association (uploaded source)",
        version=1,
        s3_key=s3_key,
        file_size_bytes=len(payload),
        mime_type="application/pdf",
        checksum_sha256=checksum,
        ai_generated=False,
        in_review_queue=True,
        human_approved=False,
        auto_sent_blocked=True,
        is_client_visible=False,
        created_by=current_user.id,
        is_active=True,
    )
    db.add(document)
    await db.flush()

    def _put_source_pdf():
        import boto3
        client = boto3.client(
            "s3",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_key_id,
            aws_secret_access_key=settings.aws_secret,
        )
        client.put_object(
            Bucket=settings.s3_bucket_name,
            Key=s3_key,
            Body=payload,
            ContentType="application/pdf",
            ServerSideEncryption="AES256",
            Metadata={
                "document_id": str(document_id),
                "company_id": str(company_id),
                "sha256": checksum,
            },
        )

    try:
        await asyncio.to_thread(_put_source_pdf)
    except Exception:
        await db.rollback()
        logger.exception("Articles source PDF upload failed", company_id=str(company_id))
        raise HTTPException(status_code=503, detail="Articles document storage is temporarily unavailable.")

    return ArticlesUploadResponse(
        document_id=str(document.id),
        company_id=str(company_id),
        title=document.title,
        checksum_sha256=checksum,
        file_size_bytes=len(payload),
        status="UPLOADED_PENDING_REVIEW",
    )


@router.post(
    "/companies/{company_id}/articles-verification",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles("ADMIN_STAFF", "LEGAL_STAFF", "SUPER_ADMIN"))],
)
async def submit_articles_for_verification(
    company_id: uuid.UUID,
    body: ArticlesSubmitRequest,
    _: uuid.UUID = Depends(require_company_access()),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    document = await db.scalar(
        select(Document).where(
            Document.id == body.document_id,
            Document.company_id == company_id,
            Document.is_active.is_(True),
            Document.document_type == DocumentType.ARTICLES_OF_ASSOCIATION,
            Document.ai_generated.is_(False),
        )
    )
    if (
        document is None
        or not document.s3_key
        or not document.checksum_sha256
        or re.fullmatch(r"[0-9a-fA-F]{64}", document.checksum_sha256) is None
    ):
        raise HTTPException(
            status_code=422,
            detail="A manually uploaded, active Articles document with storage reference and SHA-256 checksum is required.",
        )

    existing = await db.scalar(
        select(ArticlesVerification.id)
        .where(
            ArticlesVerification.company_id == company_id,
            ArticlesVerification.status == "PENDING",
        )
        .with_for_update()
        .limit(1)
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail="An Articles verification submission is already pending. Review it before submitting another copy.",
        )

    now = datetime.now(UTC)
    item = ArticlesVerification(
        company_id=company_id,
        document_id=document.id,
        source_checksum_sha256=document.checksum_sha256.lower(),
        source_document_version=document.version,
        status="PENDING",
        submitted_by=current_user.id,
        submitted_at=now,
    )
    try:
        db.add(item)
        await db.flush()
        db.add(ArticlesVerificationEvent(
            company_id=company_id,
            verification_id=item.id,
            actor_id=current_user.id,
            action="SUBMITTED",
            previous_status=None,
            new_status="PENDING",
            source_checksum_sha256=item.source_checksum_sha256,
            note="Source document submitted for independent legal review.",
            created_at=now,
        ))
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="An Articles verification is already pending.")
    return _verification_payload(item)


@router.get(
    "/companies/{company_id}/articles-verification",
)
async def list_articles_verifications(
    company_id: uuid.UUID,
    _: uuid.UUID = Depends(require_company_access()),
    db: AsyncSession = Depends(get_db_for_user),
):
    items = (await db.scalars(
        select(ArticlesVerification)
        .where(ArticlesVerification.company_id == company_id)
        .order_by(ArticlesVerification.submitted_at.desc())
    )).all()
    return [_verification_payload(item) for item in items]


@router.post(
    "/companies/{company_id}/articles-verification/{verification_id}/review",
    dependencies=[Depends(require_roles("LEGAL_STAFF"))],
)
async def review_articles_verification(
    company_id: uuid.UUID,
    verification_id: uuid.UUID,
    body: ArticlesReviewRequest,
    _: uuid.UUID = Depends(require_company_access()),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    item = await db.scalar(
        select(ArticlesVerification)
        .where(
            ArticlesVerification.id == verification_id,
            ArticlesVerification.company_id == company_id,
        )
        .with_for_update()
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Articles verification not found.")
    if item.status != "PENDING":
        raise HTTPException(status_code=409, detail="Only pending submissions can be reviewed.")
    if item.submitted_by == current_user.id:
        raise HTTPException(status_code=403, detail="The submitting user cannot review their own Articles submission.")

    document = await db.scalar(
        select(Document).where(
            Document.id == item.document_id,
            Document.company_id == company_id,
            Document.is_active.is_(True),
        )
    )
    if (
        document is None
        or document.checksum_sha256 is None
        or document.checksum_sha256.lower() != item.source_checksum_sha256
        or document.version != item.source_document_version
        or document.document_type != DocumentType.ARTICLES_OF_ASSOCIATION
    ):
        raise HTTPException(status_code=409, detail="Source document changed or is unavailable. Submit the current document for review.")

    now = datetime.now(UTC)
    if body.decision == "VERIFIED":
        if body.effective_from is None or not body.clause_reference or not body.clause_reference.strip() or body.quorum_variation_exists is None:
            raise HTTPException(status_code=422, detail="Verification requires effective_from, the exact quorum clause reference, and an explicit quorum-variation decision.")
        if body.quorum_variation_exists and body.quorum_required is None:
            raise HTTPException(status_code=422, detail="A numeric quorum is required when the Articles vary the statutory default.")
        if body.quorum_variation_exists and (not body.quorum_clause_text or not body.quorum_clause_text.strip()):
            raise HTTPException(status_code=422, detail="The exact alternative quorum clause text must be recorded.")
        if not body.quorum_variation_exists and body.quorum_required is not None:
            raise HTTPException(status_code=422, detail="Do not provide an alternative quorum when the reviewer confirms no variation.")
        current_verified = await db.scalar(
            select(ArticlesVerification)
            .where(
                ArticlesVerification.company_id == company_id,
                ArticlesVerification.status == "VERIFIED",
                ArticlesVerification.id != item.id,
            )
            .with_for_update()
            .limit(1)
        )
        if current_verified is not None:
            current_effective_from = current_verified.effective_from
            if isinstance(current_effective_from, datetime):
                current_effective_from = current_effective_from.date()
            if current_effective_from >= body.effective_from:
                raise HTTPException(
                    status_code=409,
                    detail="A replacement Articles verification must have a later effective date. Revoke the current verification before correcting historical dates.",
                )
            current_verified.status = "SUPERSEDED"
            await db.flush()
            db.add(ArticlesVerificationEvent(
                company_id=company_id,
                verification_id=current_verified.id,
                actor_id=current_user.id,
                action="SUPERSEDED",
                previous_status="VERIFIED",
                new_status="SUPERSEDED",
                source_checksum_sha256=current_verified.source_checksum_sha256,
                note=f"Superseded by verification submission {item.id}.",
                created_at=now,
            ))
            await db.flush()
        item.status = "VERIFIED"
        item.effective_from = body.effective_from
        item.quorum_variation_exists = body.quorum_variation_exists
        item.quorum_required = body.quorum_required
        item.clause_reference = body.clause_reference.strip()
        item.quorum_clause_text = body.quorum_clause_text.strip() if body.quorum_clause_text else None
        item.reviewer_note = body.reviewer_note
        action = "VERIFIED"
    else:
        if not body.reviewer_note or not body.reviewer_note.strip():
            raise HTTPException(status_code=422, detail="A reason is required when rejecting an Articles submission.")
        item.status = "REJECTED"
        item.reviewer_note = body.reviewer_note.strip()
        action = "REJECTED"

    item.reviewed_by = current_user.id
    item.reviewed_at = now
    await db.flush()
    db.add(ArticlesVerificationEvent(
        company_id=company_id,
        verification_id=item.id,
        actor_id=current_user.id,
        action=action,
        previous_status="PENDING",
        new_status=item.status,
        source_checksum_sha256=item.source_checksum_sha256,
        note=item.reviewer_note,
        created_at=now,
    ))
    await db.flush()
    return _verification_payload(item)


@router.post(
    "/companies/{company_id}/articles-verification/{verification_id}/revoke",
    dependencies=[Depends(require_roles("LEGAL_STAFF", "SUPER_ADMIN"))],
)
async def revoke_articles_verification(
    company_id: uuid.UUID,
    verification_id: uuid.UUID,
    body: ArticlesRevokeRequest,
    _: uuid.UUID = Depends(require_company_access()),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    item = await db.scalar(
        select(ArticlesVerification)
        .where(
            ArticlesVerification.id == verification_id,
            ArticlesVerification.company_id == company_id,
        )
        .with_for_update()
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Articles verification not found.")
    if item.status != "VERIFIED":
        raise HTTPException(status_code=409, detail="Only an active verified Articles record can be revoked.")
    if item.reviewed_by == current_user.id:
        raise HTTPException(status_code=403, detail="A different legal reviewer must revoke this verification.")

    if not body.reason.strip():
        raise HTTPException(status_code=422, detail="A non-empty revocation reason is required.")

    now = datetime.now(UTC)
    item.status = "REVOKED"
    item.revoked_by = current_user.id
    item.revoked_at = now
    item.revocation_reason = body.reason.strip()
    await db.flush()
    db.add(ArticlesVerificationEvent(
        company_id=company_id,
        verification_id=item.id,
        actor_id=current_user.id,
        action="REVOKED",
        previous_status="VERIFIED",
        new_status="REVOKED",
        source_checksum_sha256=item.source_checksum_sha256,
        note=item.revocation_reason,
        created_at=now,
    ))
    await db.flush()
    return _verification_payload(item)


@router.get(
    "/companies/{company_id}/articles-verification/{verification_id}/events",
)
async def list_articles_verification_events(
    company_id: uuid.UUID,
    verification_id: uuid.UUID,
    _: uuid.UUID = Depends(require_company_access()),
    db: AsyncSession = Depends(get_db_for_user),
):
    exists = await db.scalar(
        select(ArticlesVerification.id).where(
            ArticlesVerification.id == verification_id,
            ArticlesVerification.company_id == company_id,
        )
    )
    if exists is None:
        raise HTTPException(status_code=404, detail="Articles verification not found.")
    events = (await db.scalars(
        select(ArticlesVerificationEvent)
        .where(
            ArticlesVerificationEvent.company_id == company_id,
            ArticlesVerificationEvent.verification_id == verification_id,
        )
        .order_by(ArticlesVerificationEvent.created_at.asc())
    )).all()
    return [_event_payload(event) for event in events]
