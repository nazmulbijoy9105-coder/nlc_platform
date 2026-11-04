"""
NEUM LEX COUNSEL — ORM LAYER
documents.py — Document, DocumentAccessLog, AIPromptTemplate, AIOutputLog
AI Constitution Article 3: Complete AI drafting workflow enforced here.
PII sanitized → AI drafts → human review → approval → release.
auto_sent_blocked = TRUE always. Human approval mandatory.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    Index,
    text,
    ForeignKey,
    ForeignKeyConstraint,
    UniqueConstraint,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base
from .enums import AiModel, DocumentType
from .mixins import AuditMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    import uuid
    from datetime import datetime

    from .company import Company


# ═══════════════════════════════════════════════════════════════════
# DOCUMENT
# ═══════════════════════════════════════════════════════════════════
class Document(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    All documents — AI-generated and manually uploaded.
    AI Constitution Article 3: in_review_queue = TRUE until human approves.
    human_approved = FALSE blocks client access.
    auto_sent_blocked = TRUE always — never auto-send to client.
    """
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("company_id", "id", name="uq_documents_company_id_id"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Document Identity ─────────────────────────────────────────
    document_type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType, name="document_type"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    financial_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)

    # ── Storage ───────────────────────────────────────────────────
    # S3 path — never expose directly; use pre-signed URLs
    s3_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # ── AI Governance (AI Constitution Article 3) ─────────────────
    ai_generated: Mapped[bool] = mapped_column(
        Boolean, default=False, index=True
    )
    ai_model_used: Mapped[AiModel | None] = mapped_column(
        Enum(AiModel, name="ai_model"), nullable=True
    )
    ai_output_log_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
        comment="Reference to ai_output_log record"
    )

    # MANDATORY AI GOVERNANCE FLAGS — never skip
    in_review_queue: Mapped[bool] = mapped_column(
        Boolean, default=True,
        comment="AI Constitution Art.3: TRUE until human reviews"
    )
    human_approved: Mapped[bool] = mapped_column(
        Boolean, default=False,
        comment="AI Constitution Art.3: Required before client sees document"
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    auto_sent_blocked: Mapped[bool] = mapped_column(
        Boolean, default=True,
        comment="AI Constitution Art.3: ALWAYS TRUE — never auto-send to client"
    )

    # ── Access ────────────────────────────────────────────────────
    is_client_visible: Mapped[bool] = mapped_column(Boolean, default=False)
    client_released_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Metadata ─────────────────────────────────────────────────
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # ── Relationships ─────────────────────────────────────────────
    company: Mapped[Company] = relationship(
        "Company", back_populates="documents"
    )
    access_logs: Mapped[list[DocumentAccessLog]] = relationship(
        "DocumentAccessLog", back_populates="document", lazy="noload"
    )

    def __repr__(self) -> str:
        return (
            f"<Document {self.document_type} — {self.title[:40]} "
            f"approved={self.human_approved}>"
        )


class ArticlesVerification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Version-pinned human review of a company's Articles of Association."""

    __tablename__ = "articles_verifications"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING', 'VERIFIED', 'REJECTED', 'REVOKED', 'SUPERSEDED')",
            name="ck_articles_verifications_status",
        ),
        CheckConstraint(
            "source_checksum_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_articles_verifications_checksum",
        ),
        CheckConstraint(
            "source_document_version >= 1",
            name="ck_articles_verifications_document_version",
        ),
        CheckConstraint(
            "quorum_required IS NULL OR quorum_required BETWEEN 1 AND 100",
            name="ck_articles_verifications_quorum",
        ),
        CheckConstraint(
            "status <> 'VERIFIED' OR (effective_from IS NOT NULL AND clause_reference IS NOT NULL)",
            name="ck_articles_verifications_verified_fields",
        ),
        CheckConstraint(
            "status <> 'VERIFIED' OR quorum_variation_exists = FALSE OR quorum_clause_text IS NOT NULL",
            name="ck_articles_verifications_quorum_text",
        ),
        CheckConstraint(
            "quorum_variation_exists = FALSE OR quorum_required IS NOT NULL",
            name="ck_articles_verifications_variation_quorum",
        ),
        CheckConstraint(
            "(status = 'PENDING' AND reviewed_by IS NULL AND reviewed_at IS NULL) "
            "OR (status IN ('VERIFIED', 'REJECTED', 'REVOKED', 'SUPERSEDED') AND reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)",
            name="ck_articles_verifications_review_metadata",
        ),
        CheckConstraint(
            "status <> 'VERIFIED' OR reviewed_by IS DISTINCT FROM submitted_by",
            name="ck_articles_verifications_four_eyes",
        ),
        UniqueConstraint("company_id", "id", name="uq_articles_verifications_company_id"),
        ForeignKeyConstraint(
            ["company_id", "document_id"],
            ["documents.company_id", "documents.id"],
            ondelete="RESTRICT",
            name="fk_articles_verifications_company_document",
        ),
        CheckConstraint(
            "(status = 'REVOKED' AND revoked_by IS NOT NULL AND revoked_at IS NOT NULL AND revocation_reason IS NOT NULL) OR "
            "(status <> 'REVOKED' AND revoked_by IS NULL AND revoked_at IS NULL AND revocation_reason IS NULL)",
            name="ck_articles_verifications_revocation_metadata",
        ),
        Index(
            "uq_articles_verifications_pending",
            "company_id",
            unique=True,
            postgresql_where=text("status = 'PENDING'"),
        ),
        Index(
            "uq_articles_verifications_verified",
            "company_id",
            unique=True,
            postgresql_where=text("status = 'VERIFIED'"),
        ),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True,
    )
    source_checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    source_document_version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING", server_default="PENDING", index=True)
    submitted_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False,
    )
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    quorum_variation_exists: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    quorum_required: Mapped[int | None] = mapped_column(Integer, nullable=True)
    clause_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    quorum_clause_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewer_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    revoked_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revocation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class ArticlesVerificationEvent(AuditMixin, Base):
    """Append-only event trail for Articles verification lifecycle."""

    __tablename__ = "articles_verification_events"
    __table_args__ = (
        CheckConstraint(
            "action IN ('SUBMITTED', 'VERIFIED', 'REJECTED', 'REVOKED', 'SUPERSEDED')",
            name="ck_articles_verification_events_action",
        ),
        ForeignKeyConstraint(
            ["company_id", "verification_id"],
            ["articles_verifications.company_id", "articles_verifications.id"],
            ondelete="RESTRICT",
            name="fk_articles_verification_events_company_parent",
        ),
    )


    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    verification_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True,
    )
    actor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False,
    )
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    previous_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    new_status: Mapped[str] = mapped_column(String(20), nullable=False)
    source_checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DocumentAccessLog(AuditMixin, Base):
    """
    Immutable log of every document access.
    AI Constitution Article 6: All document access audited.
    """
    __tablename__ = "document_access_log"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    accessed_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    access_type: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="VIEW | DOWNLOAD | EXPORT | SHARE"
    )
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    accessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # ── Relationships ─────────────────────────────────────────────
    document: Mapped[Document] = relationship(
        "Document", back_populates="access_logs"
    )


# ═══════════════════════════════════════════════════════════════════
# AI PROMPT TEMPLATE
# ═══════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════
# AI PROMPT TEMPLATE
# ═══════════════════════════════════════════════════════════════════
class AIPromptTemplate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Approved AI prompt templates — stored in DB, not hardcoded.
    AI Constitution Article 3: AI operates through approved prompts only.
    Only Super Admin can add/modify templates.
    Templates use {PLACEHOLDER} syntax for PII injection after AI call.
    """
    __tablename__ = "ai_prompt_templates"

    # ── Identity ──────────────────────────────────────────────────
    template_name: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )
    document_type: Mapped[DocumentType] = mapped_column(
        Enum(DocumentType, name="document_type"), nullable=False
    )
    version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0")

    # ── Template ──────────────────────────────────────────────────
    system_prompt: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="System instruction for AI — PII removed, {PLACEHOLDERS} used"
    )
    user_prompt_template: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="User message template with {COMPANY_NAME}, {FY}, etc."
    )
    output_format_instructions: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    # ── NEW: description & optional_placeholders ─────────────────
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        comment="Short description of what this template generates"
    )
    optional_placeholders: Mapped[list | None] = mapped_column(
        JSONB, nullable=True,
        comment="Optional {PLACEHOLDER} names this template uses"
    )
    # ── END NEW ──────────────────────────────────────────────────

    required_placeholders: Mapped[list | None] = mapped_column(
        JSONB, nullable=True,
        comment="List of {PLACEHOLDER} names this template uses"
    )

    # ── Disclaimer ────────────────────────────────────────────────
    liability_disclaimer: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="AI Constitution Art.5: Appended to every generated document"
    )

    # ── Governance ────────────────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    def __repr__(self) -> str:
        return f"<AIPromptTemplate {self.template_name} v{self.version}>"

# ═══════════════════════════════════════════════════════════════════
# AI OUTPUT LOG
# ═══════════════════════════════════════════════════════════════════
class AIOutputLog(AuditMixin, Base):
    """
    Immutable log of every AI call and output.
    AI Constitution Article 3 + Article 6: All AI outputs logged.
    Quarterly review requires sampling of this log.
    Append-only — no UPDATE or DELETE.
    """
    __tablename__ = "ai_output_log"

    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("companies.id"),
        nullable=True,
        index=True,
    )

    # ── Request ───────────────────────────────────────────────────
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_prompt_templates.id"), nullable=True
    )
    document_type: Mapped[DocumentType | None] = mapped_column(
        Enum(DocumentType, name="document_type"), nullable=True
    )
    ai_model: Mapped[AiModel] = mapped_column(
        Enum(AiModel, name="ai_model"), nullable=False
    )
    prompt_hash: Mapped[str] = mapped_column(
        String(64), nullable=False,
        comment="SHA256 of sanitized prompt — PII never stored here"
    )

    # ── Output ────────────────────────────────────────────────────
    output_token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    in_review_queue: Mapped[bool] = mapped_column(
        Boolean, default=True, index=True
    )
    human_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Quality ───────────────────────────────────────────────────
    was_modified_before_approval: Mapped[bool] = mapped_column(
        Boolean, default=False,
        comment="Was the AI draft changed before human approved?"
    )
    was_rejected: Mapped[bool] = mapped_column(Boolean, default=False)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Caller ────────────────────────────────────────────────────
    requested_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # ── Relationships ─────────────────────────────────────────────
    company: Mapped[Company | None] = relationship(
        "Company", back_populates="ai_outputs"
    )

    def __repr__(self) -> str:
        return (
            f"<AIOutputLog {self.document_type} "
            f"approved={self.human_approved} model={self.ai_model}>"
        )
