"""Append-only source, mapping, product-owner release and deadline registries."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class LegalSource(Base):
    __tablename__ = "legal_sources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    source_key: Mapped[str] = mapped_column(String(120), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(20), nullable=False, server_default="BD")
    instrument_title: Mapped[str] = mapped_column(String(500), nullable=False)
    issuing_authority: Mapped[str] = mapped_column(String(250), nullable=False)
    instrument_type: Mapped[str] = mapped_column(String(80), nullable=False)
    official_url: Mapped[str] = mapped_column(Text, nullable=False)
    citation: Mapped[str] = mapped_column(Text, nullable=False)
    version_label: Mapped[str] = mapped_column(String(120), nullable=False)
    publication_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    artifact_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    artifact_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class LegalRuleSourceMapping(Base):
    __tablename__ = "legal_rule_source_mappings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    rule_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("legal_rules.rule_id", ondelete="RESTRICT"), nullable=False
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("legal_sources.id", ondelete="RESTRICT"), nullable=False
    )
    mapping_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    provision_citation: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class LegalDeadlineDefinition(Base):
    __tablename__ = "legal_deadline_definitions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    rule_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("legal_rules.rule_id", ondelete="RESTRICT"), nullable=False
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("legal_sources.id", ondelete="RESTRICT"), nullable=False
    )
    mapping_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("legal_rule_source_mappings.id", ondelete="RESTRICT"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    trigger_fact_key: Mapped[str] = mapped_column(String(120), nullable=False)
    period_label: Mapped[str] = mapped_column(String(100), nullable=False)
    offset: Mapped[int] = mapped_column(Integer, nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    adjustment: Mapped[str] = mapped_column(String(20), nullable=False, server_default="NONE")
    exclude_trigger_day: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    holiday_calendar_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    holiday_source_citation: Mapped[str | None] = mapped_column(Text, nullable=True)
    holidays: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class LegalRuleReleaseEvent(Base):
    __tablename__ = "legal_rule_release_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    release_scope: Mapped[str | None] = mapped_column(String(20), nullable=True)
    decision: Mapped[str | None] = mapped_column(String(20), nullable=True)
    rule_id: Mapped[str | None] = mapped_column(
        String(50), ForeignKey("legal_rules.rule_id", ondelete="RESTRICT"), nullable=True
    )
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("legal_sources.id", ondelete="RESTRICT"), nullable=True
    )
    mapping_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("legal_rule_source_mappings.id", ondelete="RESTRICT"), nullable=True
    )
    deadline_definition_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("legal_deadline_definitions.id", ondelete="RESTRICT"), nullable=True
    )
    actor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    event_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    previous_event_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
