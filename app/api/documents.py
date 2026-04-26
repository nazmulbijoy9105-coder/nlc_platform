"""
app/api/documents.py — Documents Router
NEUM LEX COUNSEL

Endpoints:
  POST  /documents/generate              Request AI document generation (async)
  GET   /documents/{company_id}          List documents for a company
  GET   /documents/{document_id}         Get document detail + download URL
  POST  /documents/{document_id}/approve Mark document as human-approved (LEGAL_STAFF+)
  POST  /documents/{document_id}/release Release approved document to client
  GET   /documents/{document_id}/pdf     Get pre-signed S3 URL for PDF download
  GET   /documents/templates             List available document templates

AI Constitution Article 3 compliance:
  - AI-generated documents are NEVER auto-sent to clients
  - human_approved=FALSE by default, must be set TRUE by LEGAL_STAFF
  - auto_sent_blocked=TRUE always — enforced at service layer
  - Documents must be approved BEFORE they can be released to the client
  - All document access is logged to document_access_log
  - All AI calls are logged to ai_output_log (prompt_hash only — no PII)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.core.dependencies import (
    get_current_user,
    get_db_for_user,
    require_company_access,
    require_roles,
)
from app.services.document_service import DocumentService, PromptTemplateService
from app.services.notification_service import ActivityService

if TYPE_CHECKING:
    import uuid

    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.enums import DocumentType
    from app.models.user import User

logger = structlog.get_logger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class DocumentGenerateRequest(BaseModel):
    company_id: uuid.UUID
    document_type: DocumentType
    template_name: str = Field(description="e.g. AGM_MINUTES_STANDARD")
    template_params: dict = Field(
        default_factory=dict,
        description="Key-value pairs substituted into the prompt template placeholders",
    )
    notes: str | None = None


class DocumentApproveRequest(BaseModel):
    approval_note: str | None = None


class DocumentReleaseRequest(BaseModel):
    release_note: str | None = None
    notify_client: bool = True


class DocumentResponse(BaseModel):
    document_id: str
    company_id: str
    document_type: str
    template_name: str | None
    title: str | None
    # AI Constitution flags
    human_approved: bool
    in_review_queue: bool
    auto_sent_blocked: bool
    is_client_visible: bool
    # Status
    status: str
    approved_by_id: str | None
    approved_at: str | None
    client_released_at: str | None
    # File
    has_pdf: bool
    created_at: str
    notes: str | None


class TemplateResponse(BaseModel):
    template_name: str
    document_type: str
    description: str | None
    required_placeholders: list[str]
    optional_placeholders: list[str] | None
    is_active: bool


class GenerateJobResponse(BaseModel):
    """Returned immediately — generation is async."""
    job_queued: bool = True
    document_id: str | None = None
    message: str
    estimated_seconds: int = 15


class MessageResponse(BaseModel):
    message: str
    success: bool = True
    document_id: str | None = None


# ---------------------------------------------------------------------------
# Serialiser
# ---------------------------------------------------------------------------

def _doc_to_response(doc) -> DocumentResponse:
    return DocumentResponse(
        document_id=str(doc.id),
        company_id=str(doc.company_id),
        document_type=doc.document_type,
        template_name=doc.template_name,
        title=doc.title,
        human_approved=doc.human_approved,
        in_review_queue=doc.in_review_queue,
        auto_sent_blocked=doc.auto_sent_blocked,
        is_client_visible=doc.is_client_visible,
        status=doc.status,
        approved_by_id=str(doc.approved_by_id) if doc.approved_by_id else None,
        approved_at=doc.approved_at.isoformat() if doc.approved_at else None,
        client_released_at=doc.client_released_at.isoformat() if doc.client_released_at else None,
        has_pdf=bool(doc.s3_key),
        created_at=doc.created_at.isoformat(),
        notes=doc.notes,
    )


# ---------------------------------------------------------------------------
# GET /documents/templates — List available templates
# ---------------------------------------------------------------------------

@router.get(
    "/templates",
    response_model=list[TemplateResponse],
    summary="List all available AI document templates",
)
async def list_templates(
    document_type: DocumentType | None = None,
    db: AsyncSession = Depends(get_db_for_user),
    current_user: User = Depends(get_current_user),
):
    svc = PromptTemplateService(db)

    if document_type:
        templates = await svc.get_by_document_type(document_type)
    else:
        from sqlalchemy import select

        from app.models.documents import AIPromptTemplate
        result = await db.execute(
            select(AIPromptTemplate).where(AIPromptTemplate.is_active)
        )
        templates = result.scalars().all()

    return [
        TemplateResponse(
            template_name=t.template_name,
            document_type=t.document_type,
            description=t.description,
            required_placeholders=t.required_placeholders or [],
            optional_placeholders=t.optional_placeholders,
            is_active=t.is_active,
        )
        for t in templates
    ]


# ---------------------------------------------------------------------------
# POST /documents/generate — Async AI document generation
# ---------------------------------------------------------------------------

@router.post(
    "/generate",
    response_model=GenerateJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[
        Depends(require_roles("ADMIN_STAFF", "SUPER_ADMIN", "LEGAL_STAFF")),
    ],
    summary="Request AI document generation (asynchronous)",
    description=(
        "Queues an AI document generation task. "
        "The document will be in `in_review_queue=True, human_approved=False` state until "
        "a LEGAL_STAFF member approves it. Documents are NEVER released to clients without approval."
    ),
)
async def generate_document(
    body: DocumentGenerateRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    activity = ActivityService(db)

    # Validate template exists
    template_svc = PromptTemplateService(db)
    template = await template_svc.get_by_name(body.template_name)
    if not template:
        raise HTTPException(
            status_code=404,
            detail=f"Template '{body.template_name}' not found. Use GET /documents/templates for valid options.",
        )

    if not template.is_active:
        raise HTTPException(
            status_code=422,
            detail=f"Template '{body.template_name}' is currently inactive.",
        )

    # Validate required placeholders
    required = set(template.required_placeholders or [])
    provided = set(body.template_params.keys())
    missing = required - provided
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Missing required template parameters: {sorted(missing)}",
        )

    await activity.log(
        action="DOCUMENT_GENERATION_REQUESTED",
        resource_type="document",
        resource_id="pending",
        description=f"AI document generation requested: {body.template_name} for company {body.company_id}",
        ip_address=request.client.host if request.client else None,
        actor_user_id=current_user.id,
    )

    # Dispatch Celery task
    try:
        from app.worker.tasks import generate_ai_document_async
        task = generate_ai_document_async.apply_async(
            kwargs={
                "company_id": str(body.company_id),
                "document_type": body.document_type,
                "template_name": body.template_name,
                "template_params": body.template_params,
                "requested_by": str(current_user.id),
                "notes": body.notes,
            }
        )
        logger.info("document_generation_queued", task_id=task.id, template=body.template_name)
        return GenerateJobResponse(
            job_queued=True,
            message=(
                "Document generation queued. It will appear in the review queue once complete. "
                "A LEGAL_STAFF member must approve it before it can be released to the client."
            ),
            estimated_seconds=20,
        )
    except Exception as e:
        logger.error("document_generation_dispatch_failed", error=str(e))
        # Fallback: generate synchronously
        doc_svc = DocumentService(db)
        doc = await doc_svc.generate_ai_document(
            company_id=body.company_id,
            document_type=body.document_type,
            template_name=body.template_name,
            template_params=body.template_params,
            requested_by=current_user.id,
            notes=body.notes,
        )
        return GenerateJobResponse(
            job_queued=False,
            document_id=str(doc.id),
            message="Document generated synchronously (Celery unavailable). Requires approval before release.",
        )


# ---------------------------------------------------------------------------
# GET /documents/{company_id} — List documents for company
# ---------------------------------------------------------------------------

@router.get(
    "/{company_id}",
    response_model=list[DocumentResponse],
    dependencies=[Depends(require_company_access("company_id"))],
    summary="List all documents for a company",
)
async def list_documents(
    company_id: uuid.UUID,
    document_type: DocumentType | None = None,
    approved_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = DocumentService(db)

    # Clients only see released documents
    client_only = current_user.role in ("CLIENT_DIRECTOR", "CLIENT_VIEW_ONLY")

    docs = await svc.get_for_company(
        company_id=company_id,
        document_type=document_type,
        approved_only=approved_only or client_only,
        client_visible_only=client_only,
    )
    return [_doc_to_response(d) for d in docs]


# ---------------------------------------------------------------------------
# GET /documents/detail/{document_id} — Get single document
# ---------------------------------------------------------------------------

@router.get(
    "/detail/{document_id}",
    response_model=DocumentResponse,
    summary="Get document detail and record access log",
)
async def get_document(
    document_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = DocumentService(db)

    doc = await svc.get_by_id_or_404(document_id)

    # Clients may only view released documents
    if current_user.role in ("CLIENT_DIRECTOR", "CLIENT_VIEW_ONLY"):
        if not doc.is_client_visible:
            raise HTTPException(status_code=403, detail="This document is not yet available.")

    # Log access
    await svc.log_access(
        document_id=document_id,
        accessed_by=current_user.id,
        access_type="VIEW",
        ip_address=request.client.host if request.client else None,
    )
    return _doc_to_response(doc)


# ---------------------------------------------------------------------------
# POST /documents/detail/{document_id}/approve — Human approval
# ---------------------------------------------------------------------------

@router.post(
    "/detail/{document_id}/approve",
    response_model=DocumentResponse,
    dependencies=[Depends(require_roles("LEGAL_STAFF", "ADMIN_STAFF", "SUPER_ADMIN"))],
    summary="Approve an AI-generated document (sets human_approved=True)",
    description=(
        "AI Constitution Article 3: All AI-generated documents must be reviewed and approved "
        "by a qualified NLC legal professional before release to the client."
    ),
)
async def approve_document(
    document_id: uuid.UUID,
    body: DocumentApproveRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = DocumentService(db)
    activity = ActivityService(db)

    doc = await svc.approve_document(
        document_id=document_id,
        approved_by=current_user.id,
        approval_note=body.approval_note,
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    await activity.log(
        action="DOCUMENT_APPROVED",
        resource_type="document",
        resource_id=str(document_id),
        description=f"Document approved by {current_user.full_name}",
        ip_address=request.client.host if request.client else None,
        actor_user_id=current_user.id,
    )

    logger.info(
        "document_approved",
        document_id=str(document_id),
        approved_by=str(current_user.id),
    )
    return _doc_to_response(doc)


# ---------------------------------------------------------------------------
# POST /documents/detail/{document_id}/release — Release to client
# ---------------------------------------------------------------------------

@router.post(
    "/detail/{document_id}/release",
    response_model=MessageResponse,
    dependencies=[Depends(require_roles("LEGAL_STAFF", "ADMIN_STAFF", "SUPER_ADMIN"))],
    summary="Release an approved document to the client",
    description="Document must be human_approved=True before it can be released.",
)
async def release_document(
    document_id: uuid.UUID,
    body: DocumentReleaseRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = DocumentService(db)
    activity = ActivityService(db)

    doc = await svc.get_by_id_or_404(document_id)
    if not doc.human_approved:
        raise HTTPException(
            status_code=422,
            detail=(
                "This document has not been approved yet. "
                "A LEGAL_STAFF member must approve it before it can be released."
            ),
        )

    released_doc = await svc.release_to_client(
        document_id=document_id,
        released_by=current_user.id,
        notify_client=body.notify_client,
        release_note=body.release_note,
    )
    if not released_doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    await activity.log(
        action="DOCUMENT_RELEASED",
        resource_type="document",
        resource_id=str(document_id),
        description=f"Document released to client by {current_user.full_name}",
        ip_address=request.client.host if request.client else None,
        actor_user_id=current_user.id,
    )
    return MessageResponse(
        message="Document released to client successfully.",
        document_id=str(document_id),
    )


# ---------------------------------------------------------------------------
# GET /documents/detail/{document_id}/pdf — Pre-signed PDF URL
# ---------------------------------------------------------------------------

@router.get(
    "/detail/{document_id}/pdf",
    summary="Get a pre-signed S3 URL to download the document PDF",
)
async def get_pdf_url(
    document_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = DocumentService(db)
    ActivityService(db)

    doc = await svc.get_by_id_or_404(document_id)

    # Clients may only download approved, released documents
    if current_user.role in ("CLIENT_DIRECTOR", "CLIENT_VIEW_ONLY"):
        if not doc.is_client_visible or not doc.human_approved:
            raise HTTPException(
                status_code=403,
                detail="This document is not available for download.",
            )

    if not doc.s3_key:
        # Trigger PDF generation if not yet done
        try:
            from app.worker.tasks import render_pdf
            render_pdf.apply_async(kwargs={"document_id": str(document_id)})
            raise HTTPException(
                status_code=202,
                detail="PDF generation has been queued. Please try again in 30 seconds.",
            )
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=404, detail="PDF is not available for this document.")

    presigned_url = await svc.get_presigned_url(document_id)
    await svc.log_access(
        document_id=document_id,
        accessed_by=current_user.id,
        access_type="DOWNLOAD",
        ip_address=request.client.host if request.client else None,
    )

    return {
        "document_id": str(document_id),
        "download_url": presigned_url,
        "expires_in_seconds": 3600,
    }
