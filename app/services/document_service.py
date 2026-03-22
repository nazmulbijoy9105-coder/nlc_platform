"""
NEUM LEX COUNSEL — Document Service
app/services/document_service.py

Implements _get_prompt_template, _call_ai_drafting_api,
_store_ai_document, _approve_document, _get_document,
_generate_pdf_and_presign stubs.

AI Constitution Article 3 — ALL AI DOCUMENT GOVERNANCE:
  ✓ PII sanitized BEFORE sending to AI (never send real names to external AI)
  ✓ Every AI call logged in ai_output_log with prompt_hash
  ✓ Every AI document starts with in_review_queue=True
  ✓ human_approved=False until staff explicitly approves
  ✓ auto_sent_blocked=ALWAYS True — never auto-send to client
  ✓ liability_disclaimer ALWAYS appended from template
  ✓ is_client_visible=False until admin explicitly releases
"""
from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.documents import AIOutputLog, AIPromptTemplate, Document, DocumentAccessLog
from app.models.enums import AiModel, DocumentType, SeverityLevel
from app.services.base import BaseService

logger = logging.getLogger("nlc.document")


# ═══════════════════════════════════════════════════════════════════════
# AI PROMPT TEMPLATE SERVICE
# ═══════════════════════════════════════════════════════════════════════

class PromptTemplateService(BaseService[AIPromptTemplate]):
    model = AIPromptTemplate

    async def get_by_name(self, template_name: str) -> Optional[AIPromptTemplate]:
        """Fetch template by name. Returns None if not found or inactive."""
        result = await self.db.execute(
            select(AIPromptTemplate).where(
                AIPromptTemplate.template_name == template_name,
                AIPromptTemplate.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_document_type(
        self, document_type: DocumentType
    ) -> Optional[AIPromptTemplate]:
        """Get the active template for a given document type."""
        result = await self.db.execute(
            select(AIPromptTemplate).where(
                AIPromptTemplate.document_type == document_type,
                AIPromptTemplate.is_active == True,
            )
        )
        return result.scalar_one_or_none()


# ═══════════════════════════════════════════════════════════════════════
# DOCUMENT SERVICE
# ═══════════════════════════════════════════════════════════════════════

class DocumentService(BaseService[Document]):
    model = Document

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)
        self._settings = get_settings()

    # ── AI Document Generation ────────────────────────────────────

    async def generate_ai_document(
        self,
        company_id: uuid.UUID,
        document_type: DocumentType,
        parameters: Dict[str, Any],
        template_name: Optional[str] = None,
        requested_by: Optional[uuid.UUID] = None,
        financial_year: Optional[int] = None,
    ) -> Document:
        """
        Full AI document generation pipeline.
        AI Constitution Article 3: PII never sent raw to external AI.

        Steps:
        1. Load template
        2. Sanitize PII from parameters
        3. Call AI provider
        4. Log AI call (append-only)
        5. Re-inject real values into output
        6. Append liability disclaimer
        7. Store document (in_review_queue=True, human_approved=False)
        8. Upload to S3
        """
        template_svc = PromptTemplateService(self.db)

        # ── Step 1: Load template ──────────────────────────────────
        template = (
            await template_svc.get_by_name(template_name)
            if template_name
            else await template_svc.get_by_document_type(document_type)
        )
        if not template:
            raise ValueError(
                f"No active AI template for document_type={document_type}. "
                f"Super Admin must create one before generation."
            )

        # ── Step 2: Sanitize PII ───────────────────────────────────
        sanitized_params = _sanitize_for_ai(parameters)

        # ── Step 3: Call AI ────────────────────────────────────────
        prompt_hash = hashlib.sha256(
            (template.system_prompt + str(sanitized_params)).encode()
        ).hexdigest()

        try:
            ai_content = await _call_ai_provider(
                template=template,
                params=sanitized_params,
                settings=self._settings,
            )
        except Exception as exc:
            logger.error(f"[DocumentService] AI call failed: {exc}")
            raise RuntimeError(f"AI drafting failed: {exc}") from exc

        # ── Step 4: Log AI call (append-only) ─────────────────────
        ai_log = await _log_ai_call(
            db=self.db,
            company_id=company_id,
            template_id=template.id,
            document_type=document_type,
            ai_model=_resolve_ai_model(self._settings),
            prompt_hash=prompt_hash,
            output_token_count=len(ai_content.split()),
            requested_by=requested_by,
        )

        # ── Step 5: Re-inject real values ─────────────────────────
        final_content = _reinject_real_values(ai_content, parameters)

        # ── Step 6: Append liability disclaimer ───────────────────
        final_content += f"\n\n---\n\n{template.liability_disclaimer}"

        # ── Step 7: Store document (AI Constitution Article 3) ─────
        document = await self.create(
            company_id=company_id,
            document_type=document_type,
            title=f"{document_type.replace('_', ' ').title()} — Draft",
            financial_year=financial_year,
            ai_generated=True,
            ai_model_used=_resolve_ai_model(self._settings),
            ai_output_log_id=ai_log.id,
            in_review_queue=True,          # AI Constitution: ALWAYS True on creation
            human_approved=False,           # AI Constitution: NEVER auto-approve
            auto_sent_blocked=True,         # AI Constitution: ALWAYS True
            is_client_visible=False,        # AI Constitution: Not visible until approved
            created_by=requested_by,
        )

        # ── Step 8: Upload to S3 (async background) ───────────────
        try:
            s3_key = await _upload_to_s3(
                document_id=document.id,
                content=final_content,
                document_type=document_type,
                settings=self._settings,
            )
            await self.update_instance(document, s3_key=s3_key)
        except Exception as exc:
            logger.error(f"[DocumentService] S3 upload failed: {exc}")
            # Don't fail the request — doc is in DB, S3 upload can be retried

        return document

    # ── Approval Workflow ─────────────────────────────────────────

    async def approve_document(
        self,
        document_id: uuid.UUID,
        approved_by: uuid.UUID,
    ) -> Optional[Document]:
        """
        Human approval of AI-generated document.
        AI Constitution Article 3: Only staff can approve. Never auto-approve.
        Sets human_approved=True and is_client_visible=False still (staff controls release).
        """
        doc = await self.get_by_id(document_id)
        if not doc:
            return None
        if not doc.ai_generated:
            logger.warning(f"approve_document called on non-AI doc {document_id}")

        now = datetime.now(timezone.utc)
        return await self.update_instance(
            doc,
            human_approved=True,
            approved_by=approved_by,
            approved_at=now,
            in_review_queue=False,
        )

    async def release_to_client(
        self,
        document_id: uuid.UUID,
        released_by: uuid.UUID,
    ) -> Optional[Document]:
        """
        Make a document visible to client users.
        AI Constitution: Must be approved before release.
        """
        doc = await self.get_by_id(document_id)
        if not doc:
            return None
        if doc.ai_generated and not doc.human_approved:
            raise ValueError(
                "AI Constitution violation: Document must be human-approved "
                "before releasing to client."
            )
        return await self.update_instance(
            doc,
            is_client_visible=True,
            client_released_at=datetime.now(timezone.utc),
        )

    # ── Access & Download ─────────────────────────────────────────

    async def log_access(
        self,
        document_id: uuid.UUID,
        accessed_by: uuid.UUID,
        access_type: str,  # VIEW | DOWNLOAD | EXPORT | SHARE
        ip_address: Optional[str] = None,
    ) -> None:
        """
        Log every document access for audit trail.
        AI Constitution Article 6: All document access logged.
        """
        log = DocumentAccessLog(
            id=uuid.uuid4(),
            document_id=document_id,
            accessed_by=accessed_by,
            access_type=access_type,
            ip_address=ip_address,
            accessed_at=datetime.now(timezone.utc),
        )
        self.db.add(log)
        await self.db.flush()

    async def get_presigned_url(self, document_id: uuid.UUID) -> str:
        """
        Generate a pre-signed S3 URL (15-min expiry) for secure document download.
        Never expose direct S3 paths.
        """
        doc = await self.get_by_id_or_404(document_id)
        if not doc.s3_key:
            raise ValueError("Document has not been uploaded to S3 yet.")
        return await _presign_s3_url(doc.s3_key, self._settings)

    async def generate_pdf_and_presign(self, document_id: uuid.UUID) -> str:
        """
        Generate a branded PDF from the document content and return a presigned URL.
        _generate_pdf_and_presign stub implementation.
        """
        doc = await self.get_by_id_or_404(document_id)
        if not doc.s3_key:
            raise ValueError("Document must be uploaded before PDF generation.")

        # Download current content from S3
        content = await _download_from_s3(doc.s3_key, self._settings)

        # Generate PDF via WeasyPrint
        pdf_bytes = await _render_pdf(content, doc.title, self._settings)

        # Upload PDF to S3
        pdf_key = doc.s3_key.replace(".txt", ".pdf").replace(".md", ".pdf")
        if not pdf_key.endswith(".pdf"):
            pdf_key += ".pdf"

        await _upload_bytes_to_s3(pdf_key, pdf_bytes, "application/pdf", self._settings)

        # Return presigned URL
        return await _presign_s3_url(pdf_key, self._settings)

    async def get_for_company(
        self,
        company_id: uuid.UUID,
        *,
        document_type: Optional[DocumentType] = None,
        include_unapproved: bool = False,
    ) -> List[Document]:
        """Get all documents for a company."""
        filters = [
            Document.company_id == company_id,
            Document.is_active == True,
        ]
        if document_type:
            filters.append(Document.document_type == document_type)
        if not include_unapproved:
            filters.append(Document.is_client_visible == True)

        result = await self.db.execute(
            select(Document)
            .where(*filters)
            .order_by(Document.created_at.desc())
        )
        return list(result.scalars().all())


# ═══════════════════════════════════════════════════════════════════════
# AI PROVIDER CALL
# ═══════════════════════════════════════════════════════════════════════

async def _call_ai_provider(template: AIPromptTemplate, params: Dict, settings) -> str:
    """
    Call the configured AI provider (OpenAI / Anthropic / Local LLM).
    Returns raw AI text output.
    AI Constitution: params are already sanitized before this call.
    """
    user_prompt = template.user_prompt_template
    for k, v in params.items():
        user_prompt = user_prompt.replace(f"{{{k.upper()}}}", str(v))

    if settings.ai_provider == "openai":
        return await _call_openai(template.system_prompt, user_prompt, settings)
    elif settings.ai_provider == "anthropic":
        return await _call_anthropic(template.system_prompt, user_prompt, settings)
    else:
        return await _call_local_llm(template.system_prompt, user_prompt, settings)


async def _call_openai(system_prompt: str, user_prompt: str, settings) -> str:
    """Call OpenAI Chat Completions API."""
    headers = {
        "Authorization": f"Bearer {settings.ai_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model":    "gpt-4-turbo-preview",
        "messages": [
            {"role": "system",  "content": system_prompt},
            {"role": "user",    "content": user_prompt},
        ],
        "max_tokens":   4096,
        "temperature":  0.1,   # Low temp for legal docs
    }
    async with httpx.AsyncClient(timeout=settings.ai_request_timeout_seconds) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


async def _call_anthropic(system_prompt: str, user_prompt: str, settings) -> str:
    """Call Anthropic Messages API."""
    headers = {
        "x-api-key":         settings.ai_key,
        "anthropic-version": "2023-06-01",
        "Content-Type":      "application/json",
    }
    payload = {
        "model":      "claude-3-sonnet-20240229",
        "max_tokens": 4096,
        "system":     system_prompt,
        "messages":   [{"role": "user", "content": user_prompt}],
    }
    async with httpx.AsyncClient(timeout=settings.ai_request_timeout_seconds) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()["content"][0]["text"]


async def _call_local_llm(system_prompt: str, user_prompt: str, settings) -> str:
    """Call local Ollama-compatible API."""
    payload = {
        "model":  settings.local_llm_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        "stream": False,
    }
    async with httpx.AsyncClient(timeout=settings.ai_request_timeout_seconds) as client:
        resp = await client.post(
            f"{settings.local_llm_base_url}/api/chat",
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]


async def _log_ai_call(
    db,
    company_id: uuid.UUID,
    template_id: uuid.UUID,
    document_type: DocumentType,
    ai_model: AiModel,
    prompt_hash: str,
    output_token_count: int,
    requested_by: Optional[uuid.UUID],
) -> AIOutputLog:
    """Append-only log entry for every AI call. AI Constitution Article 3 + 6."""
    log = AIOutputLog(
        id=uuid.uuid4(),
        company_id=company_id,
        template_id=template_id,
        document_type=document_type,
        ai_model=ai_model,
        prompt_hash=prompt_hash,
        output_token_count=output_token_count,
        in_review_queue=True,
        human_approved=False,
        requested_by=requested_by,
        requested_at=datetime.now(timezone.utc),
    )
    db.add(log)
    await db.flush()
    return log


def _resolve_ai_model(settings) -> AiModel:
    """Map settings.ai_provider to AiModel enum."""
    mapping = {"openai": AiModel.GPT4, "anthropic": AiModel.CLAUDE, "local_llm": AiModel.LOCAL_LLM}
    return mapping.get(settings.ai_provider, AiModel.LOCAL_LLM)


# ═══════════════════════════════════════════════════════════════════════
# PII SANITIZATION (AI Constitution Article 3)
# ═══════════════════════════════════════════════════════════════════════

_SENSITIVE_KEYS = {
    "company_name", "director_name", "shareholder_name",
    "nid_number", "passport_number", "contact_email",
    "address", "father_name", "registration_number",
}


def _sanitize_for_ai(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Replace PII values with {PLACEHOLDER} tokens before sending to AI.
    AI Constitution: Real client data NEVER sent to external AI services.
    """
    sanitized = {}
    for k, v in params.items():
        if k in _SENSITIVE_KEYS:
            sanitized[k] = f"{{{k.upper()}}}"
        else:
            sanitized[k] = v
    return sanitized


def _reinject_real_values(ai_output: str, real_params: Dict[str, Any]) -> str:
    """
    Substitute {PLACEHOLDER} tokens with real values in AI output.
    This happens LOCALLY — real values never leave the server.
    """
    for k, v in real_params.items():
        if k in _SENSITIVE_KEYS:
            ai_output = ai_output.replace(f"{{{k.upper()}}}", str(v))
    return ai_output


# ═══════════════════════════════════════════════════════════════════════
# S3 OPERATIONS
# ═══════════════════════════════════════════════════════════════════════

async def _upload_to_s3(
    document_id: uuid.UUID,
    content: str,
    document_type: DocumentType,
    settings,
) -> str:
    """Upload document content to S3. Returns the S3 key."""
    import boto3
    s3_key = f"{settings.s3_document_prefix}{document_type}/{document_id}.txt"
    client = boto3.client(
        "s3",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_key_id,
        aws_secret_access_key=settings.aws_secret,
    )
    client.put_object(
        Bucket=settings.s3_bucket_name,
        Key=s3_key,
        Body=content.encode("utf-8"),
        ContentType="text/plain; charset=utf-8",
        ServerSideEncryption="AES256",  # SSE-S3 encryption
        Metadata={"document_id": str(document_id), "document_type": document_type},
    )
    return s3_key


async def _upload_bytes_to_s3(key: str, data: bytes, content_type: str, settings) -> None:
    """Upload raw bytes to S3."""
    import boto3
    client = boto3.client(
        "s3",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_key_id,
        aws_secret_access_key=settings.aws_secret,
    )
    client.put_object(
        Bucket=settings.s3_bucket_name,
        Key=key,
        Body=data,
        ContentType=content_type,
        ServerSideEncryption="AES256",
    )


async def _download_from_s3(s3_key: str, settings) -> str:
    """Download document content from S3."""
    import boto3
    client = boto3.client(
        "s3",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_key_id,
        aws_secret_access_key=settings.aws_secret,
    )
    response = client.get_object(Bucket=settings.s3_bucket_name, Key=s3_key)
    return response["Body"].read().decode("utf-8")


async def _presign_s3_url(s3_key: str, settings) -> str:
    """Generate a pre-signed URL with expiry."""
    import boto3
    client = boto3.client(
        "s3",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_key_id,
        aws_secret_access_key=settings.aws_secret,
    )
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.s3_bucket_name, "Key": s3_key},
        ExpiresIn=settings.s3_presigned_url_expire_seconds,
    )


async def _render_pdf(content: str, title: str, settings) -> bytes:
    """
    Render document content to PDF using WeasyPrint.
    Uses NLC branded templates.
    """
    import jinja2
    import weasyprint

    loader = jinja2.FileSystemLoader(settings.pdf_template_path)
    env = jinja2.Environment(loader=loader, autoescape=True)

    try:
        template = env.get_template("document.html")
    except jinja2.TemplateNotFound:
        # Fallback minimal template
        html = f"""
        <html><head><style>
          body {{ font-family: Arial, sans-serif; padding: 40px; }}
          h1 {{ color: #1a1a2e; }}
          pre {{ white-space: pre-wrap; }}
        </style></head>
        <body>
          <h1>{title}</h1>
          <p><em>NEUM LEX COUNSEL — RJSC Compliance Intelligence</em></p>
          <hr/>
          <pre>{content}</pre>
          <hr/>
          <p><small>This document was prepared by Neum Lex Counsel. 
          It is not legal advice. Consult your legal counsel.</small></p>
        </body></html>
        """
    else:
        html = template.render(title=title, content=content)

    pdf = weasyprint.HTML(string=html).write_pdf()
    return pdf
