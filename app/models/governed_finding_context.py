"""Append-only global legal finding-context catalogue models."""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class LegalRuleFindingContext(Base):
    """Immutable version of server-authored context for one historical rule."""

    __tablename__ = "legal_rule_finding_contexts"
    __table_args__ = (
        UniqueConstraint(
            "historical_rule_id",
            "catalog_version",
            name="uq_legal_finding_context_rule_version",
        ),
        Index(
            "ix_legal_finding_context_lookup",
            "historical_rule_id",
            "source_namespace",
            "jurisdiction",
            "catalog_version",
        ),
        CheckConstraint(
            "length(btrim(historical_rule_id)) > 0 "
            "AND length(btrim(catalog_version)) > 0 "
            "AND length(btrim(source_namespace)) > 0 "
            "AND length(btrim(jurisdiction)) > 0 "
            "AND length(btrim(source_instrument)) > 0 "
            "AND length(btrim(source_provision)) > 0 "
            "AND length(btrim(effective_date_basis)) > 0 "
            "AND length(btrim(effective_date_source_ref)) > 0",
            name="ck_legal_finding_context_required_text",
        ),
        CheckConstraint(
            "context_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_legal_finding_context_digest",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    historical_rule_id: Mapped[str] = mapped_column(String(100), nullable=False)
    catalog_version: Mapped[str] = mapped_column(String(100), nullable=False)
    source_namespace: Mapped[str] = mapped_column(String(255), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(32), nullable=False)
    source_instrument: Mapped[str] = mapped_column(String(500), nullable=False)
    source_provision: Mapped[str] = mapped_column(String(255), nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    effective_date_basis: Mapped[str] = mapped_column(Text, nullable=False)
    effective_date_source_ref: Mapped[str] = mapped_column(String(1000), nullable=False)
    context_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    context_canonical: Mapped[str] = mapped_column(Text, nullable=False)
    context_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    authored_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    authored_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class LegalRuleFindingContextReview(Base):
    """Immutable independent legal-review decision bound to a context digest."""

    __tablename__ = "legal_rule_finding_context_reviews"
    __table_args__ = (
        CheckConstraint(
            "review_status IN ('APPROVED','REJECTED','REVOKED')",
            name="ck_legal_finding_context_review_status",
        ),
        CheckConstraint(
            "length(btrim(review_basis)) > 0",
            name="ck_legal_finding_context_review_basis",
        ),
        CheckConstraint(
            "reviewed_context_sha256 ~ '^[0-9a-f]{64}$'",
            name="ck_legal_finding_context_review_digest",
        ),
        Index(
            "ix_legal_finding_context_reviews_latest",
            "context_id",
            "reviewed_at",
            "id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    context_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("legal_rule_finding_contexts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    review_status: Mapped[str] = mapped_column(String(20), nullable=False)
    reviewed_context_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    review_basis: Mapped[str] = mapped_column(Text, nullable=False)
    reviewed_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
