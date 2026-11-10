"""Versioned company facts linked to the existing authorized document vault."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base
from .mixins import TimestampMixin, UUIDPrimaryKeyMixin


class CompanyFact(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Append-only fact assertion; verification creates a new trust state, not a source upload."""

    __tablename__ = "company_facts"
    __table_args__ = (
        CheckConstraint(
            "(trust_level = 'USER_ASSERTED' AND document_id IS NULL "
            "AND authorized_uploader_id IS NULL AND uploaded_at IS NULL) OR "
            "(trust_level = 'AUTHORIZED_DOCUMENT_BACKED' AND document_id IS NOT NULL "
            "AND authorized_uploader_id IS NOT NULL AND uploaded_at IS NOT NULL)",
            name="ck_company_fact_trust_source",
        ),
        CheckConstraint(
            "length(btrim(fact_key)) > 0",
            name="ck_company_fact_fact_key_nonempty",
        ),
        CheckConstraint(
            "trust_level IN ('USER_ASSERTED', 'AUTHORIZED_DOCUMENT_BACKED')",
            name="ck_company_fact_trust_level",
        ),
        CheckConstraint(
            "verification_status IN ('UNVERIFIED', 'VERIFIED', 'REJECTED', 'SUPERSEDED')",
            name="ck_company_fact_verification_status",
        ),
        CheckConstraint(
            "(verification_status = 'VERIFIED' AND verified_by IS NOT NULL "
            "AND verified_at IS NOT NULL AND trust_level = 'AUTHORIZED_DOCUMENT_BACKED') OR "
            "(verification_status <> 'VERIFIED' AND verified_by IS NULL AND verified_at IS NULL)",
            name="ck_company_fact_verification_actor",
        ),
        Index("ix_company_facts_company_key_current", "company_id", "fact_key", "is_current"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    fact_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    fact_value: Mapped[Any] = mapped_column(JSONB, nullable=False)
    trust_level: Mapped[str] = mapped_column(String(40), nullable=False)
    asserted_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    observed_on: Mapped[date] = mapped_column(Date, nullable=False)
    source_reference: Mapped[str | None] = mapped_column(Text, nullable=True)

    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="RESTRICT"), nullable=True
    )
    authorized_uploader_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    verification_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="UNVERIFIED", server_default="UNVERIFIED"
    )
    verified_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verification_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    is_current: Mapped[bool] = mapped_column(nullable=False, default=True, server_default="true")
    supersedes_fact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("company_facts.id", ondelete="RESTRICT"), nullable=True
    )

    def provenance_payload(self) -> dict[str, Any]:
        """Stable JSON snapshot copied into each finding/evaluation."""
        if self.trust_level == "USER_ASSERTED":
            disclosure = "User-asserted company information; not independently verified."
        elif self.verification_status == "VERIFIED":
            disclosure = "Authorized document-backed fact checked by the recorded verifier."
        elif self.verification_status == "REJECTED":
            disclosure = "Supporting document was reviewed and rejected; fact is unverified."
        elif self.verification_status == "SUPERSEDED":
            disclosure = "Supporting document/fact was superseded; use the current fact record."
        else:
            disclosure = "Based on an authorized document upload that has not yet been verified."
        return {
            "fact_id": str(self.id),
            "fact_key": self.fact_key,
            "trust_level": self.trust_level,
            "asserted_by": str(self.asserted_by),
            "observed_on": self.observed_on.isoformat(),
            "source_reference": self.source_reference,
            "document_id": str(self.document_id) if self.document_id else None,
            "authorized_uploader_id": (
                str(self.authorized_uploader_id) if self.authorized_uploader_id else None
            ),
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
            "verification_status": self.verification_status,
            "verified_by": str(self.verified_by) if self.verified_by else None,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "verification_note": self.verification_note,
            "disclosure": disclosure,
            "scope_note": (
                "This is the set of current company facts supplied to the evaluation; "
                "it is not yet a rule-specific causal mapping."
            ),
        }
