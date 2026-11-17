"""Immutable canonical identity and evidence snapshots for compliance findings."""
from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint, Date, DateTime, ForeignKey, Integer, String, Text,
    UniqueConstraint, text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class ComplianceFindingBinding(Base):
    """One immutable rule/revision/evidence manifest binding per compliance flag."""

    __tablename__ = "compliance_finding_bindings"
    __table_args__ = (
        UniqueConstraint("compliance_flag_id", name="uq_finding_binding_compliance_flag"),
        CheckConstraint(
            "length(btrim(source_namespace)) > 0 AND length(btrim(historical_rule_id)) > 0",
            name="ck_finding_binding_lookup_key_nonempty",
        ),
        CheckConstraint(
            "attribution_status IN ('CURRENT_EVALUATION','ATTRIBUTED','UNATTRIBUTED','AMBIGUOUS','QUARANTINED')",
            name="ck_finding_binding_attribution_status",
        ),
        CheckConstraint(
            "evidence_status IN ('COMPLETE','PARTIAL','MISSING','INVALID','CONFLICT','UNVERIFIED')",
            name="ck_finding_binding_evidence_status",
        ),
        CheckConstraint(
            "(resolution_status = 'RESOLVED' AND canonical_rule_id IS NOT NULL "
            "AND alias_id IS NOT NULL AND revision_id IS NOT NULL AND revision_number > 0 "
            "AND definition_hash ~ '^[0-9a-f]{64}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    compliance_flag_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_flags.id", ondelete="RESTRICT"), nullable=False)
    evaluation_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_evaluation_runs.id", ondelete="RESTRICT"))
    source_namespace: Mapped[str] = mapped_column(String(255), nullable=False)
    historical_rule_id: Mapped[str] = mapped_column(String(100), nullable=False)
    resolution_status: Mapped[str] = mapped_column(String(40), nullable=False)
    attribution_status: Mapped[str] = mapped_column(String(24), nullable=False, server_default="CURRENT_EVALUATION")
    attribution_basis: Mapped[str | None] = mapped_column(Text)
    attribution_evidence_hash: Mapped[str | None] = mapped_column(String(64))
    attribution_reviewed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    attribution_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    canonical_rule_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_identities.id", ondelete="RESTRICT"))
    alias_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_aliases.id", ondelete="RESTRICT"))
    revision_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_revisions.id", ondelete="RESTRICT"))
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    revision_number: Mapped[int | None] = mapped_column(Integer)
    definition_hash: Mapped[str | None] = mapped_column(String(64))
    evaluator_name: Mapped[str | None] = mapped_column(String(255))
    evaluator_version: Mapped[str | None] = mapped_column(String(100))
    evaluator_artifact_hash: Mapped[str | None] = mapped_column(String(64))
    evidence_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="MISSING")
    evidence_manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    finding_snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))


class ComplianceFindingEvidence(Base):
    """Immutable, source-checked snapshot of one company fact used by a finding."""

    __tablename__ = "compliance_finding_evidence"
    __table_args__ = (
        UniqueConstraint("binding_id", "company_fact_id", name="uq_finding_evidence_fact"),
        CheckConstraint("length(btrim(evidence_role)) > 0", name="ck_finding_evidence_role_nonempty"),
        CheckConstraint("trust_level IN ('USER_ASSERTED','AUTHORIZED_DOCUMENT_BACKED')", name="ck_finding_evidence_trust_level"),
        CheckConstraint("verification_status IN ('UNVERIFIED','VERIFIED','REJECTED','SUPERSEDED')", name="ck_finding_evidence_verification_status"),
        CheckConstraint("fact_value_hash ~ '^[0-9a-f]{64}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    binding_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_finding_bindings.id", ondelete="RESTRICT"), nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    company_fact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("company_facts.id", ondelete="RESTRICT"), nullable=False)
    evidence_role: Mapped[str] = mapped_column(String(80), nullable=False)
    fact_key: Mapped[str] = mapped_column(String(120), nullable=False)
    fact_value_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    trust_level: Mapped[str] = mapped_column(String(40), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False)
    observed_on: Mapped[date] = mapped_column(Date, nullable=False)
    source_reference: Mapped[str | None] = mapped_column(Text)
    document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="RESTRICT"))
    document_sha256: Mapped[str | None] = mapped_column(String(64))
    asserted_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    authorized_uploader_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    evidence_hash: Mapped[str] = mapped_column(String(64), nullable=False)
) OR "
            "(resolution_status <> 'RESOLVED' AND revision_id IS NULL "
            "AND revision_number IS NULL AND definition_hash IS NULL)",
            name="ck_finding_binding_resolved_metadata",
        ),
        CheckConstraint("evidence_manifest_hash ~ '^[0-9a-f]{64}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    compliance_flag_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_flags.id", ondelete="RESTRICT"), nullable=False)
    evaluation_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_evaluation_runs.id", ondelete="RESTRICT"))
    source_namespace: Mapped[str] = mapped_column(String(255), nullable=False)
    historical_rule_id: Mapped[str] = mapped_column(String(100), nullable=False)
    resolution_status: Mapped[str] = mapped_column(String(40), nullable=False)
    attribution_status: Mapped[str] = mapped_column(String(24), nullable=False, server_default="CURRENT_EVALUATION")
    canonical_rule_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_identities.id", ondelete="RESTRICT"))
    alias_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_aliases.id", ondelete="RESTRICT"))
    revision_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_revisions.id", ondelete="RESTRICT"))
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    revision_number: Mapped[int | None] = mapped_column(Integer)
    definition_hash: Mapped[str | None] = mapped_column(String(64))
    evaluator_name: Mapped[str | None] = mapped_column(String(255))
    evaluator_version: Mapped[str | None] = mapped_column(String(100))
    evaluator_artifact_hash: Mapped[str | None] = mapped_column(String(64))
    evidence_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="MISSING")
    evidence_manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    finding_snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))


class ComplianceFindingEvidence(Base):
    """Immutable, source-checked snapshot of one company fact used by a finding."""

    __tablename__ = "compliance_finding_evidence"
    __table_args__ = (
        UniqueConstraint("binding_id", "company_fact_id", name="uq_finding_evidence_fact"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    binding_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_finding_bindings.id", ondelete="RESTRICT"), nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    company_fact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("company_facts.id", ondelete="RESTRICT"), nullable=False)
    evidence_role: Mapped[str] = mapped_column(String(80), nullable=False)
    fact_key: Mapped[str] = mapped_column(String(120), nullable=False)
    fact_value_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    trust_level: Mapped[str] = mapped_column(String(40), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False)
    observed_on: Mapped[date] = mapped_column(Date, nullable=False)
    source_reference: Mapped[str | None] = mapped_column(Text)
    document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    document_sha256: Mapped[str | None] = mapped_column(String(64))
    asserted_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    authorized_uploader_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    evidence_hash: Mapped[str] = mapped_column(String(64), nullable=False)
", name="ck_finding_binding_evidence_hash"),
        CheckConstraint("finding_snapshot_hash ~ '^[0-9a-f]{64}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    compliance_flag_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_flags.id", ondelete="RESTRICT"), nullable=False)
    evaluation_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_evaluation_runs.id", ondelete="RESTRICT"))
    source_namespace: Mapped[str] = mapped_column(String(255), nullable=False)
    historical_rule_id: Mapped[str] = mapped_column(String(100), nullable=False)
    resolution_status: Mapped[str] = mapped_column(String(40), nullable=False)
    attribution_status: Mapped[str] = mapped_column(String(24), nullable=False, server_default="CURRENT_EVALUATION")
    canonical_rule_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_identities.id", ondelete="RESTRICT"))
    alias_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_aliases.id", ondelete="RESTRICT"))
    revision_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_revisions.id", ondelete="RESTRICT"))
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    revision_number: Mapped[int | None] = mapped_column(Integer)
    definition_hash: Mapped[str | None] = mapped_column(String(64))
    evaluator_name: Mapped[str | None] = mapped_column(String(255))
    evaluator_version: Mapped[str | None] = mapped_column(String(100))
    evaluator_artifact_hash: Mapped[str | None] = mapped_column(String(64))
    evidence_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="MISSING")
    evidence_manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    finding_snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))


class ComplianceFindingEvidence(Base):
    """Immutable, source-checked snapshot of one company fact used by a finding."""

    __tablename__ = "compliance_finding_evidence"
    __table_args__ = (
        UniqueConstraint("binding_id", "company_fact_id", name="uq_finding_evidence_fact"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    binding_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_finding_bindings.id", ondelete="RESTRICT"), nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    company_fact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("company_facts.id", ondelete="RESTRICT"), nullable=False)
    evidence_role: Mapped[str] = mapped_column(String(80), nullable=False)
    fact_key: Mapped[str] = mapped_column(String(120), nullable=False)
    fact_value_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    trust_level: Mapped[str] = mapped_column(String(40), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False)
    observed_on: Mapped[date] = mapped_column(Date, nullable=False)
    source_reference: Mapped[str | None] = mapped_column(Text)
    document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    document_sha256: Mapped[str | None] = mapped_column(String(64))
    asserted_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    authorized_uploader_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    evidence_hash: Mapped[str] = mapped_column(String(64), nullable=False)
", name="ck_finding_binding_snapshot_hash"),
        CheckConstraint(
            "evaluator_artifact_hash IS NULL OR evaluator_artifact_hash ~ '^[0-9a-f]{64}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    compliance_flag_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_flags.id", ondelete="RESTRICT"), nullable=False)
    evaluation_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_evaluation_runs.id", ondelete="RESTRICT"))
    source_namespace: Mapped[str] = mapped_column(String(255), nullable=False)
    historical_rule_id: Mapped[str] = mapped_column(String(100), nullable=False)
    resolution_status: Mapped[str] = mapped_column(String(40), nullable=False)
    attribution_status: Mapped[str] = mapped_column(String(24), nullable=False, server_default="CURRENT_EVALUATION")
    canonical_rule_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_identities.id", ondelete="RESTRICT"))
    alias_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_aliases.id", ondelete="RESTRICT"))
    revision_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_revisions.id", ondelete="RESTRICT"))
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    revision_number: Mapped[int | None] = mapped_column(Integer)
    definition_hash: Mapped[str | None] = mapped_column(String(64))
    evaluator_name: Mapped[str | None] = mapped_column(String(255))
    evaluator_version: Mapped[str | None] = mapped_column(String(100))
    evaluator_artifact_hash: Mapped[str | None] = mapped_column(String(64))
    evidence_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="MISSING")
    evidence_manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    finding_snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))


class ComplianceFindingEvidence(Base):
    """Immutable, source-checked snapshot of one company fact used by a finding."""

    __tablename__ = "compliance_finding_evidence"
    __table_args__ = (
        UniqueConstraint("binding_id", "company_fact_id", name="uq_finding_evidence_fact"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    binding_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_finding_bindings.id", ondelete="RESTRICT"), nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    company_fact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("company_facts.id", ondelete="RESTRICT"), nullable=False)
    evidence_role: Mapped[str] = mapped_column(String(80), nullable=False)
    fact_key: Mapped[str] = mapped_column(String(120), nullable=False)
    fact_value_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    trust_level: Mapped[str] = mapped_column(String(40), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False)
    observed_on: Mapped[date] = mapped_column(Date, nullable=False)
    source_reference: Mapped[str | None] = mapped_column(Text)
    document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    document_sha256: Mapped[str | None] = mapped_column(String(64))
    asserted_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    authorized_uploader_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    evidence_hash: Mapped[str] = mapped_column(String(64), nullable=False)
",
            name="ck_finding_binding_evaluator_hash",
        ),
        CheckConstraint(
            "attribution_evidence_hash IS NULL OR attribution_evidence_hash ~ '^[0-9a-f]{64}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    compliance_flag_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_flags.id", ondelete="RESTRICT"), nullable=False)
    evaluation_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_evaluation_runs.id", ondelete="RESTRICT"))
    source_namespace: Mapped[str] = mapped_column(String(255), nullable=False)
    historical_rule_id: Mapped[str] = mapped_column(String(100), nullable=False)
    resolution_status: Mapped[str] = mapped_column(String(40), nullable=False)
    attribution_status: Mapped[str] = mapped_column(String(24), nullable=False, server_default="CURRENT_EVALUATION")
    canonical_rule_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_identities.id", ondelete="RESTRICT"))
    alias_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_aliases.id", ondelete="RESTRICT"))
    revision_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_revisions.id", ondelete="RESTRICT"))
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    revision_number: Mapped[int | None] = mapped_column(Integer)
    definition_hash: Mapped[str | None] = mapped_column(String(64))
    evaluator_name: Mapped[str | None] = mapped_column(String(255))
    evaluator_version: Mapped[str | None] = mapped_column(String(100))
    evaluator_artifact_hash: Mapped[str | None] = mapped_column(String(64))
    evidence_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="MISSING")
    evidence_manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    finding_snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))


class ComplianceFindingEvidence(Base):
    """Immutable, source-checked snapshot of one company fact used by a finding."""

    __tablename__ = "compliance_finding_evidence"
    __table_args__ = (
        UniqueConstraint("binding_id", "company_fact_id", name="uq_finding_evidence_fact"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    binding_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_finding_bindings.id", ondelete="RESTRICT"), nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    company_fact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("company_facts.id", ondelete="RESTRICT"), nullable=False)
    evidence_role: Mapped[str] = mapped_column(String(80), nullable=False)
    fact_key: Mapped[str] = mapped_column(String(120), nullable=False)
    fact_value_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    trust_level: Mapped[str] = mapped_column(String(40), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False)
    observed_on: Mapped[date] = mapped_column(Date, nullable=False)
    source_reference: Mapped[str | None] = mapped_column(Text)
    document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    document_sha256: Mapped[str | None] = mapped_column(String(64))
    asserted_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    authorized_uploader_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    evidence_hash: Mapped[str] = mapped_column(String(64), nullable=False)
",
            name="ck_finding_binding_attribution_evidence_hash",
        ),
        CheckConstraint(
            "(attribution_status = 'ATTRIBUTED' AND attribution_basis IS NOT NULL "
            "AND btrim(attribution_basis) <> '' AND attribution_evidence_hash IS NOT NULL "
            "AND attribution_reviewed_by IS NOT NULL AND attribution_reviewed_at IS NOT NULL) "
            "OR (attribution_status <> 'ATTRIBUTED' AND attribution_basis IS NULL "
            "AND attribution_evidence_hash IS NULL AND attribution_reviewed_by IS NULL "
            "AND attribution_reviewed_at IS NULL)",
            name="ck_finding_binding_attribution_review_gate",
        ),
        CheckConstraint(
            "attribution_status <> 'ATTRIBUTED' OR "
            "(resolution_status = 'RESOLVED' AND evidence_status = 'COMPLETE')",
            name="ck_finding_binding_attribution_requires_identity_evidence",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    compliance_flag_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_flags.id", ondelete="RESTRICT"), nullable=False)
    evaluation_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_evaluation_runs.id", ondelete="RESTRICT"))
    source_namespace: Mapped[str] = mapped_column(String(255), nullable=False)
    historical_rule_id: Mapped[str] = mapped_column(String(100), nullable=False)
    resolution_status: Mapped[str] = mapped_column(String(40), nullable=False)
    attribution_status: Mapped[str] = mapped_column(String(24), nullable=False, server_default="CURRENT_EVALUATION")
    canonical_rule_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_identities.id", ondelete="RESTRICT"))
    alias_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_aliases.id", ondelete="RESTRICT"))
    revision_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_revisions.id", ondelete="RESTRICT"))
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    revision_number: Mapped[int | None] = mapped_column(Integer)
    definition_hash: Mapped[str | None] = mapped_column(String(64))
    evaluator_name: Mapped[str | None] = mapped_column(String(255))
    evaluator_version: Mapped[str | None] = mapped_column(String(100))
    evaluator_artifact_hash: Mapped[str | None] = mapped_column(String(64))
    evidence_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="MISSING")
    evidence_manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    finding_snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))


class ComplianceFindingEvidence(Base):
    """Immutable, source-checked snapshot of one company fact used by a finding."""

    __tablename__ = "compliance_finding_evidence"
    __table_args__ = (
        UniqueConstraint("binding_id", "company_fact_id", name="uq_finding_evidence_fact"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    binding_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_finding_bindings.id", ondelete="RESTRICT"), nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    company_fact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("company_facts.id", ondelete="RESTRICT"), nullable=False)
    evidence_role: Mapped[str] = mapped_column(String(80), nullable=False)
    fact_key: Mapped[str] = mapped_column(String(120), nullable=False)
    fact_value_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    trust_level: Mapped[str] = mapped_column(String(40), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False)
    observed_on: Mapped[date] = mapped_column(Date, nullable=False)
    source_reference: Mapped[str | None] = mapped_column(Text)
    document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    document_sha256: Mapped[str | None] = mapped_column(String(64))
    asserted_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    authorized_uploader_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    evidence_hash: Mapped[str] = mapped_column(String(64), nullable=False)
", name="ck_finding_evidence_fact_value_hash"),
        CheckConstraint("evidence_hash ~ '^[0-9a-f]{64}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    binding_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_finding_bindings.id", ondelete="RESTRICT"), nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    company_fact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("company_facts.id", ondelete="RESTRICT"), nullable=False)
    evidence_role: Mapped[str] = mapped_column(String(80), nullable=False)
    fact_key: Mapped[str] = mapped_column(String(120), nullable=False)
    fact_value_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    trust_level: Mapped[str] = mapped_column(String(40), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False)
    observed_on: Mapped[date] = mapped_column(Date, nullable=False)
    source_reference: Mapped[str | None] = mapped_column(Text)
    document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    document_sha256: Mapped[str | None] = mapped_column(String(64))
    asserted_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    authorized_uploader_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    evidence_hash: Mapped[str] = mapped_column(String(64), nullable=False)
) OR "
            "(resolution_status <> 'RESOLVED' AND revision_id IS NULL "
            "AND revision_number IS NULL AND definition_hash IS NULL)",
            name="ck_finding_binding_resolved_metadata",
        ),
        CheckConstraint("evidence_manifest_hash ~ '^[0-9a-f]{64}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    compliance_flag_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_flags.id", ondelete="RESTRICT"), nullable=False)
    evaluation_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_evaluation_runs.id", ondelete="RESTRICT"))
    source_namespace: Mapped[str] = mapped_column(String(255), nullable=False)
    historical_rule_id: Mapped[str] = mapped_column(String(100), nullable=False)
    resolution_status: Mapped[str] = mapped_column(String(40), nullable=False)
    attribution_status: Mapped[str] = mapped_column(String(24), nullable=False, server_default="CURRENT_EVALUATION")
    canonical_rule_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_identities.id", ondelete="RESTRICT"))
    alias_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_aliases.id", ondelete="RESTRICT"))
    revision_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_revisions.id", ondelete="RESTRICT"))
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    revision_number: Mapped[int | None] = mapped_column(Integer)
    definition_hash: Mapped[str | None] = mapped_column(String(64))
    evaluator_name: Mapped[str | None] = mapped_column(String(255))
    evaluator_version: Mapped[str | None] = mapped_column(String(100))
    evaluator_artifact_hash: Mapped[str | None] = mapped_column(String(64))
    evidence_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="MISSING")
    evidence_manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    finding_snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))


class ComplianceFindingEvidence(Base):
    """Immutable, source-checked snapshot of one company fact used by a finding."""

    __tablename__ = "compliance_finding_evidence"
    __table_args__ = (
        UniqueConstraint("binding_id", "company_fact_id", name="uq_finding_evidence_fact"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    binding_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_finding_bindings.id", ondelete="RESTRICT"), nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    company_fact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("company_facts.id", ondelete="RESTRICT"), nullable=False)
    evidence_role: Mapped[str] = mapped_column(String(80), nullable=False)
    fact_key: Mapped[str] = mapped_column(String(120), nullable=False)
    fact_value_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    trust_level: Mapped[str] = mapped_column(String(40), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False)
    observed_on: Mapped[date] = mapped_column(Date, nullable=False)
    source_reference: Mapped[str | None] = mapped_column(Text)
    document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    document_sha256: Mapped[str | None] = mapped_column(String(64))
    asserted_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    authorized_uploader_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    evidence_hash: Mapped[str] = mapped_column(String(64), nullable=False)
", name="ck_finding_binding_evidence_hash"),
        CheckConstraint("finding_snapshot_hash ~ '^[0-9a-f]{64}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    compliance_flag_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_flags.id", ondelete="RESTRICT"), nullable=False)
    evaluation_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_evaluation_runs.id", ondelete="RESTRICT"))
    source_namespace: Mapped[str] = mapped_column(String(255), nullable=False)
    historical_rule_id: Mapped[str] = mapped_column(String(100), nullable=False)
    resolution_status: Mapped[str] = mapped_column(String(40), nullable=False)
    attribution_status: Mapped[str] = mapped_column(String(24), nullable=False, server_default="CURRENT_EVALUATION")
    canonical_rule_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_identities.id", ondelete="RESTRICT"))
    alias_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_aliases.id", ondelete="RESTRICT"))
    revision_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_revisions.id", ondelete="RESTRICT"))
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    revision_number: Mapped[int | None] = mapped_column(Integer)
    definition_hash: Mapped[str | None] = mapped_column(String(64))
    evaluator_name: Mapped[str | None] = mapped_column(String(255))
    evaluator_version: Mapped[str | None] = mapped_column(String(100))
    evaluator_artifact_hash: Mapped[str | None] = mapped_column(String(64))
    evidence_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="MISSING")
    evidence_manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    finding_snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))


class ComplianceFindingEvidence(Base):
    """Immutable, source-checked snapshot of one company fact used by a finding."""

    __tablename__ = "compliance_finding_evidence"
    __table_args__ = (
        UniqueConstraint("binding_id", "company_fact_id", name="uq_finding_evidence_fact"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    binding_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_finding_bindings.id", ondelete="RESTRICT"), nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    company_fact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("company_facts.id", ondelete="RESTRICT"), nullable=False)
    evidence_role: Mapped[str] = mapped_column(String(80), nullable=False)
    fact_key: Mapped[str] = mapped_column(String(120), nullable=False)
    fact_value_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    trust_level: Mapped[str] = mapped_column(String(40), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False)
    observed_on: Mapped[date] = mapped_column(Date, nullable=False)
    source_reference: Mapped[str | None] = mapped_column(Text)
    document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    document_sha256: Mapped[str | None] = mapped_column(String(64))
    asserted_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    authorized_uploader_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    evidence_hash: Mapped[str] = mapped_column(String(64), nullable=False)
", name="ck_finding_binding_snapshot_hash"),
        CheckConstraint(
            "evaluator_artifact_hash IS NULL OR evaluator_artifact_hash ~ '^[0-9a-f]{64}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    compliance_flag_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_flags.id", ondelete="RESTRICT"), nullable=False)
    evaluation_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_evaluation_runs.id", ondelete="RESTRICT"))
    source_namespace: Mapped[str] = mapped_column(String(255), nullable=False)
    historical_rule_id: Mapped[str] = mapped_column(String(100), nullable=False)
    resolution_status: Mapped[str] = mapped_column(String(40), nullable=False)
    attribution_status: Mapped[str] = mapped_column(String(24), nullable=False, server_default="CURRENT_EVALUATION")
    canonical_rule_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_identities.id", ondelete="RESTRICT"))
    alias_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_aliases.id", ondelete="RESTRICT"))
    revision_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_revisions.id", ondelete="RESTRICT"))
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    revision_number: Mapped[int | None] = mapped_column(Integer)
    definition_hash: Mapped[str | None] = mapped_column(String(64))
    evaluator_name: Mapped[str | None] = mapped_column(String(255))
    evaluator_version: Mapped[str | None] = mapped_column(String(100))
    evaluator_artifact_hash: Mapped[str | None] = mapped_column(String(64))
    evidence_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="MISSING")
    evidence_manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    finding_snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))


class ComplianceFindingEvidence(Base):
    """Immutable, source-checked snapshot of one company fact used by a finding."""

    __tablename__ = "compliance_finding_evidence"
    __table_args__ = (
        UniqueConstraint("binding_id", "company_fact_id", name="uq_finding_evidence_fact"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    binding_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_finding_bindings.id", ondelete="RESTRICT"), nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    company_fact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("company_facts.id", ondelete="RESTRICT"), nullable=False)
    evidence_role: Mapped[str] = mapped_column(String(80), nullable=False)
    fact_key: Mapped[str] = mapped_column(String(120), nullable=False)
    fact_value_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    trust_level: Mapped[str] = mapped_column(String(40), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False)
    observed_on: Mapped[date] = mapped_column(Date, nullable=False)
    source_reference: Mapped[str | None] = mapped_column(Text)
    document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    document_sha256: Mapped[str | None] = mapped_column(String(64))
    asserted_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    authorized_uploader_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    evidence_hash: Mapped[str] = mapped_column(String(64), nullable=False)
",
            name="ck_finding_binding_evaluator_hash",
        ),
        CheckConstraint(
            "attribution_evidence_hash IS NULL OR attribution_evidence_hash ~ '^[0-9a-f]{64}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    compliance_flag_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_flags.id", ondelete="RESTRICT"), nullable=False)
    evaluation_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_evaluation_runs.id", ondelete="RESTRICT"))
    source_namespace: Mapped[str] = mapped_column(String(255), nullable=False)
    historical_rule_id: Mapped[str] = mapped_column(String(100), nullable=False)
    resolution_status: Mapped[str] = mapped_column(String(40), nullable=False)
    attribution_status: Mapped[str] = mapped_column(String(24), nullable=False, server_default="CURRENT_EVALUATION")
    canonical_rule_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_identities.id", ondelete="RESTRICT"))
    alias_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_aliases.id", ondelete="RESTRICT"))
    revision_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_revisions.id", ondelete="RESTRICT"))
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    revision_number: Mapped[int | None] = mapped_column(Integer)
    definition_hash: Mapped[str | None] = mapped_column(String(64))
    evaluator_name: Mapped[str | None] = mapped_column(String(255))
    evaluator_version: Mapped[str | None] = mapped_column(String(100))
    evaluator_artifact_hash: Mapped[str | None] = mapped_column(String(64))
    evidence_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="MISSING")
    evidence_manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    finding_snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))


class ComplianceFindingEvidence(Base):
    """Immutable, source-checked snapshot of one company fact used by a finding."""

    __tablename__ = "compliance_finding_evidence"
    __table_args__ = (
        UniqueConstraint("binding_id", "company_fact_id", name="uq_finding_evidence_fact"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    binding_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_finding_bindings.id", ondelete="RESTRICT"), nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    company_fact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("company_facts.id", ondelete="RESTRICT"), nullable=False)
    evidence_role: Mapped[str] = mapped_column(String(80), nullable=False)
    fact_key: Mapped[str] = mapped_column(String(120), nullable=False)
    fact_value_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    trust_level: Mapped[str] = mapped_column(String(40), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False)
    observed_on: Mapped[date] = mapped_column(Date, nullable=False)
    source_reference: Mapped[str | None] = mapped_column(Text)
    document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    document_sha256: Mapped[str | None] = mapped_column(String(64))
    asserted_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    authorized_uploader_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    evidence_hash: Mapped[str] = mapped_column(String(64), nullable=False)
",
            name="ck_finding_binding_attribution_evidence_hash",
        ),
        CheckConstraint(
            "(attribution_status = 'ATTRIBUTED' AND attribution_basis IS NOT NULL "
            "AND btrim(attribution_basis) <> '' AND attribution_evidence_hash IS NOT NULL "
            "AND attribution_reviewed_by IS NOT NULL AND attribution_reviewed_at IS NOT NULL) "
            "OR (attribution_status <> 'ATTRIBUTED' AND attribution_basis IS NULL "
            "AND attribution_evidence_hash IS NULL AND attribution_reviewed_by IS NULL "
            "AND attribution_reviewed_at IS NULL)",
            name="ck_finding_binding_attribution_review_gate",
        ),
        CheckConstraint(
            "attribution_status <> 'ATTRIBUTED' OR "
            "(resolution_status = 'RESOLVED' AND evidence_status = 'COMPLETE')",
            name="ck_finding_binding_attribution_requires_identity_evidence",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    compliance_flag_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_flags.id", ondelete="RESTRICT"), nullable=False)
    evaluation_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_evaluation_runs.id", ondelete="RESTRICT"))
    source_namespace: Mapped[str] = mapped_column(String(255), nullable=False)
    historical_rule_id: Mapped[str] = mapped_column(String(100), nullable=False)
    resolution_status: Mapped[str] = mapped_column(String(40), nullable=False)
    attribution_status: Mapped[str] = mapped_column(String(24), nullable=False, server_default="CURRENT_EVALUATION")
    canonical_rule_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_identities.id", ondelete="RESTRICT"))
    alias_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_aliases.id", ondelete="RESTRICT"))
    revision_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_revisions.id", ondelete="RESTRICT"))
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    revision_number: Mapped[int | None] = mapped_column(Integer)
    definition_hash: Mapped[str | None] = mapped_column(String(64))
    evaluator_name: Mapped[str | None] = mapped_column(String(255))
    evaluator_version: Mapped[str | None] = mapped_column(String(100))
    evaluator_artifact_hash: Mapped[str | None] = mapped_column(String(64))
    evidence_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="MISSING")
    evidence_manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    finding_snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))


class ComplianceFindingEvidence(Base):
    """Immutable, source-checked snapshot of one company fact used by a finding."""

    __tablename__ = "compliance_finding_evidence"
    __table_args__ = (
        UniqueConstraint("binding_id", "company_fact_id", name="uq_finding_evidence_fact"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    binding_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_finding_bindings.id", ondelete="RESTRICT"), nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    company_fact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("company_facts.id", ondelete="RESTRICT"), nullable=False)
    evidence_role: Mapped[str] = mapped_column(String(80), nullable=False)
    fact_key: Mapped[str] = mapped_column(String(120), nullable=False)
    fact_value_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    trust_level: Mapped[str] = mapped_column(String(40), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False)
    observed_on: Mapped[date] = mapped_column(Date, nullable=False)
    source_reference: Mapped[str | None] = mapped_column(Text)
    document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    document_sha256: Mapped[str | None] = mapped_column(String(64))
    asserted_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    authorized_uploader_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    evidence_hash: Mapped[str] = mapped_column(String(64), nullable=False)
", name="ck_finding_evidence_hash"),
        CheckConstraint("document_sha256 IS NULL OR document_sha256 ~ '^[0-9a-f]{64}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    binding_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_finding_bindings.id", ondelete="RESTRICT"), nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    company_fact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("company_facts.id", ondelete="RESTRICT"), nullable=False)
    evidence_role: Mapped[str] = mapped_column(String(80), nullable=False)
    fact_key: Mapped[str] = mapped_column(String(120), nullable=False)
    fact_value_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    trust_level: Mapped[str] = mapped_column(String(40), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False)
    observed_on: Mapped[date] = mapped_column(Date, nullable=False)
    source_reference: Mapped[str | None] = mapped_column(Text)
    document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    document_sha256: Mapped[str | None] = mapped_column(String(64))
    asserted_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    authorized_uploader_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    evidence_hash: Mapped[str] = mapped_column(String(64), nullable=False)
) OR "
            "(resolution_status <> 'RESOLVED' AND revision_id IS NULL "
            "AND revision_number IS NULL AND definition_hash IS NULL)",
            name="ck_finding_binding_resolved_metadata",
        ),
        CheckConstraint("evidence_manifest_hash ~ '^[0-9a-f]{64}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    compliance_flag_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_flags.id", ondelete="RESTRICT"), nullable=False)
    evaluation_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_evaluation_runs.id", ondelete="RESTRICT"))
    source_namespace: Mapped[str] = mapped_column(String(255), nullable=False)
    historical_rule_id: Mapped[str] = mapped_column(String(100), nullable=False)
    resolution_status: Mapped[str] = mapped_column(String(40), nullable=False)
    attribution_status: Mapped[str] = mapped_column(String(24), nullable=False, server_default="CURRENT_EVALUATION")
    canonical_rule_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_identities.id", ondelete="RESTRICT"))
    alias_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_aliases.id", ondelete="RESTRICT"))
    revision_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_revisions.id", ondelete="RESTRICT"))
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    revision_number: Mapped[int | None] = mapped_column(Integer)
    definition_hash: Mapped[str | None] = mapped_column(String(64))
    evaluator_name: Mapped[str | None] = mapped_column(String(255))
    evaluator_version: Mapped[str | None] = mapped_column(String(100))
    evaluator_artifact_hash: Mapped[str | None] = mapped_column(String(64))
    evidence_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="MISSING")
    evidence_manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    finding_snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))


class ComplianceFindingEvidence(Base):
    """Immutable, source-checked snapshot of one company fact used by a finding."""

    __tablename__ = "compliance_finding_evidence"
    __table_args__ = (
        UniqueConstraint("binding_id", "company_fact_id", name="uq_finding_evidence_fact"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    binding_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_finding_bindings.id", ondelete="RESTRICT"), nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    company_fact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("company_facts.id", ondelete="RESTRICT"), nullable=False)
    evidence_role: Mapped[str] = mapped_column(String(80), nullable=False)
    fact_key: Mapped[str] = mapped_column(String(120), nullable=False)
    fact_value_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    trust_level: Mapped[str] = mapped_column(String(40), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False)
    observed_on: Mapped[date] = mapped_column(Date, nullable=False)
    source_reference: Mapped[str | None] = mapped_column(Text)
    document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    document_sha256: Mapped[str | None] = mapped_column(String(64))
    asserted_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    authorized_uploader_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    evidence_hash: Mapped[str] = mapped_column(String(64), nullable=False)
", name="ck_finding_binding_evidence_hash"),
        CheckConstraint("finding_snapshot_hash ~ '^[0-9a-f]{64}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    compliance_flag_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_flags.id", ondelete="RESTRICT"), nullable=False)
    evaluation_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_evaluation_runs.id", ondelete="RESTRICT"))
    source_namespace: Mapped[str] = mapped_column(String(255), nullable=False)
    historical_rule_id: Mapped[str] = mapped_column(String(100), nullable=False)
    resolution_status: Mapped[str] = mapped_column(String(40), nullable=False)
    attribution_status: Mapped[str] = mapped_column(String(24), nullable=False, server_default="CURRENT_EVALUATION")
    canonical_rule_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_identities.id", ondelete="RESTRICT"))
    alias_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_aliases.id", ondelete="RESTRICT"))
    revision_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_revisions.id", ondelete="RESTRICT"))
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    revision_number: Mapped[int | None] = mapped_column(Integer)
    definition_hash: Mapped[str | None] = mapped_column(String(64))
    evaluator_name: Mapped[str | None] = mapped_column(String(255))
    evaluator_version: Mapped[str | None] = mapped_column(String(100))
    evaluator_artifact_hash: Mapped[str | None] = mapped_column(String(64))
    evidence_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="MISSING")
    evidence_manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    finding_snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))


class ComplianceFindingEvidence(Base):
    """Immutable, source-checked snapshot of one company fact used by a finding."""

    __tablename__ = "compliance_finding_evidence"
    __table_args__ = (
        UniqueConstraint("binding_id", "company_fact_id", name="uq_finding_evidence_fact"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    binding_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_finding_bindings.id", ondelete="RESTRICT"), nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    company_fact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("company_facts.id", ondelete="RESTRICT"), nullable=False)
    evidence_role: Mapped[str] = mapped_column(String(80), nullable=False)
    fact_key: Mapped[str] = mapped_column(String(120), nullable=False)
    fact_value_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    trust_level: Mapped[str] = mapped_column(String(40), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False)
    observed_on: Mapped[date] = mapped_column(Date, nullable=False)
    source_reference: Mapped[str | None] = mapped_column(Text)
    document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    document_sha256: Mapped[str | None] = mapped_column(String(64))
    asserted_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    authorized_uploader_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    evidence_hash: Mapped[str] = mapped_column(String(64), nullable=False)
", name="ck_finding_binding_snapshot_hash"),
        CheckConstraint(
            "evaluator_artifact_hash IS NULL OR evaluator_artifact_hash ~ '^[0-9a-f]{64}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    compliance_flag_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_flags.id", ondelete="RESTRICT"), nullable=False)
    evaluation_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_evaluation_runs.id", ondelete="RESTRICT"))
    source_namespace: Mapped[str] = mapped_column(String(255), nullable=False)
    historical_rule_id: Mapped[str] = mapped_column(String(100), nullable=False)
    resolution_status: Mapped[str] = mapped_column(String(40), nullable=False)
    attribution_status: Mapped[str] = mapped_column(String(24), nullable=False, server_default="CURRENT_EVALUATION")
    canonical_rule_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_identities.id", ondelete="RESTRICT"))
    alias_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_aliases.id", ondelete="RESTRICT"))
    revision_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_revisions.id", ondelete="RESTRICT"))
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    revision_number: Mapped[int | None] = mapped_column(Integer)
    definition_hash: Mapped[str | None] = mapped_column(String(64))
    evaluator_name: Mapped[str | None] = mapped_column(String(255))
    evaluator_version: Mapped[str | None] = mapped_column(String(100))
    evaluator_artifact_hash: Mapped[str | None] = mapped_column(String(64))
    evidence_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="MISSING")
    evidence_manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    finding_snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))


class ComplianceFindingEvidence(Base):
    """Immutable, source-checked snapshot of one company fact used by a finding."""

    __tablename__ = "compliance_finding_evidence"
    __table_args__ = (
        UniqueConstraint("binding_id", "company_fact_id", name="uq_finding_evidence_fact"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    binding_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_finding_bindings.id", ondelete="RESTRICT"), nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    company_fact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("company_facts.id", ondelete="RESTRICT"), nullable=False)
    evidence_role: Mapped[str] = mapped_column(String(80), nullable=False)
    fact_key: Mapped[str] = mapped_column(String(120), nullable=False)
    fact_value_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    trust_level: Mapped[str] = mapped_column(String(40), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False)
    observed_on: Mapped[date] = mapped_column(Date, nullable=False)
    source_reference: Mapped[str | None] = mapped_column(Text)
    document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    document_sha256: Mapped[str | None] = mapped_column(String(64))
    asserted_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    authorized_uploader_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    evidence_hash: Mapped[str] = mapped_column(String(64), nullable=False)
",
            name="ck_finding_binding_evaluator_hash",
        ),
        CheckConstraint(
            "attribution_evidence_hash IS NULL OR attribution_evidence_hash ~ '^[0-9a-f]{64}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    compliance_flag_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_flags.id", ondelete="RESTRICT"), nullable=False)
    evaluation_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_evaluation_runs.id", ondelete="RESTRICT"))
    source_namespace: Mapped[str] = mapped_column(String(255), nullable=False)
    historical_rule_id: Mapped[str] = mapped_column(String(100), nullable=False)
    resolution_status: Mapped[str] = mapped_column(String(40), nullable=False)
    attribution_status: Mapped[str] = mapped_column(String(24), nullable=False, server_default="CURRENT_EVALUATION")
    canonical_rule_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_identities.id", ondelete="RESTRICT"))
    alias_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_aliases.id", ondelete="RESTRICT"))
    revision_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_revisions.id", ondelete="RESTRICT"))
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    revision_number: Mapped[int | None] = mapped_column(Integer)
    definition_hash: Mapped[str | None] = mapped_column(String(64))
    evaluator_name: Mapped[str | None] = mapped_column(String(255))
    evaluator_version: Mapped[str | None] = mapped_column(String(100))
    evaluator_artifact_hash: Mapped[str | None] = mapped_column(String(64))
    evidence_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="MISSING")
    evidence_manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    finding_snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))


class ComplianceFindingEvidence(Base):
    """Immutable, source-checked snapshot of one company fact used by a finding."""

    __tablename__ = "compliance_finding_evidence"
    __table_args__ = (
        UniqueConstraint("binding_id", "company_fact_id", name="uq_finding_evidence_fact"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    binding_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_finding_bindings.id", ondelete="RESTRICT"), nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    company_fact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("company_facts.id", ondelete="RESTRICT"), nullable=False)
    evidence_role: Mapped[str] = mapped_column(String(80), nullable=False)
    fact_key: Mapped[str] = mapped_column(String(120), nullable=False)
    fact_value_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    trust_level: Mapped[str] = mapped_column(String(40), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False)
    observed_on: Mapped[date] = mapped_column(Date, nullable=False)
    source_reference: Mapped[str | None] = mapped_column(Text)
    document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    document_sha256: Mapped[str | None] = mapped_column(String(64))
    asserted_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    authorized_uploader_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    evidence_hash: Mapped[str] = mapped_column(String(64), nullable=False)
",
            name="ck_finding_binding_attribution_evidence_hash",
        ),
        CheckConstraint(
            "(attribution_status = 'ATTRIBUTED' AND attribution_basis IS NOT NULL "
            "AND btrim(attribution_basis) <> '' AND attribution_evidence_hash IS NOT NULL "
            "AND attribution_reviewed_by IS NOT NULL AND attribution_reviewed_at IS NOT NULL) "
            "OR (attribution_status <> 'ATTRIBUTED' AND attribution_basis IS NULL "
            "AND attribution_evidence_hash IS NULL AND attribution_reviewed_by IS NULL "
            "AND attribution_reviewed_at IS NULL)",
            name="ck_finding_binding_attribution_review_gate",
        ),
        CheckConstraint(
            "attribution_status <> 'ATTRIBUTED' OR "
            "(resolution_status = 'RESOLVED' AND evidence_status = 'COMPLETE')",
            name="ck_finding_binding_attribution_requires_identity_evidence",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    compliance_flag_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_flags.id", ondelete="RESTRICT"), nullable=False)
    evaluation_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_evaluation_runs.id", ondelete="RESTRICT"))
    source_namespace: Mapped[str] = mapped_column(String(255), nullable=False)
    historical_rule_id: Mapped[str] = mapped_column(String(100), nullable=False)
    resolution_status: Mapped[str] = mapped_column(String(40), nullable=False)
    attribution_status: Mapped[str] = mapped_column(String(24), nullable=False, server_default="CURRENT_EVALUATION")
    canonical_rule_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_identities.id", ondelete="RESTRICT"))
    alias_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_aliases.id", ondelete="RESTRICT"))
    revision_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_revisions.id", ondelete="RESTRICT"))
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    revision_number: Mapped[int | None] = mapped_column(Integer)
    definition_hash: Mapped[str | None] = mapped_column(String(64))
    evaluator_name: Mapped[str | None] = mapped_column(String(255))
    evaluator_version: Mapped[str | None] = mapped_column(String(100))
    evaluator_artifact_hash: Mapped[str | None] = mapped_column(String(64))
    evidence_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="MISSING")
    evidence_manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    finding_snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))


class ComplianceFindingEvidence(Base):
    """Immutable, source-checked snapshot of one company fact used by a finding."""

    __tablename__ = "compliance_finding_evidence"
    __table_args__ = (
        UniqueConstraint("binding_id", "company_fact_id", name="uq_finding_evidence_fact"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    binding_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_finding_bindings.id", ondelete="RESTRICT"), nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    company_fact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("company_facts.id", ondelete="RESTRICT"), nullable=False)
    evidence_role: Mapped[str] = mapped_column(String(80), nullable=False)
    fact_key: Mapped[str] = mapped_column(String(120), nullable=False)
    fact_value_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    trust_level: Mapped[str] = mapped_column(String(40), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False)
    observed_on: Mapped[date] = mapped_column(Date, nullable=False)
    source_reference: Mapped[str | None] = mapped_column(Text)
    document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    document_sha256: Mapped[str | None] = mapped_column(String(64))
    asserted_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    authorized_uploader_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    evidence_hash: Mapped[str] = mapped_column(String(64), nullable=False)
", name="ck_finding_evidence_document_hash"),
        CheckConstraint(
            "(trust_level = 'USER_ASSERTED' AND document_id IS NULL AND authorized_uploader_id IS NULL AND uploaded_at IS NULL) OR "
            "(trust_level = 'AUTHORIZED_DOCUMENT_BACKED' AND document_id IS NOT NULL AND authorized_uploader_id IS NOT NULL AND uploaded_at IS NOT NULL AND source_reference IS NOT NULL AND btrim(source_reference) <> '')",
            name="ck_finding_evidence_source_provenance",
        ),
        CheckConstraint(
            "(verification_status = 'VERIFIED' AND verified_by IS NOT NULL AND verified_at IS NOT NULL AND trust_level = 'AUTHORIZED_DOCUMENT_BACKED') OR "
            "(verification_status <> 'VERIFIED' AND verified_by IS NULL AND verified_at IS NULL)",
            name="ck_finding_evidence_verification_actor",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    binding_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_finding_bindings.id", ondelete="RESTRICT"), nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    company_fact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("company_facts.id", ondelete="RESTRICT"), nullable=False)
    evidence_role: Mapped[str] = mapped_column(String(80), nullable=False)
    fact_key: Mapped[str] = mapped_column(String(120), nullable=False)
    fact_value_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    trust_level: Mapped[str] = mapped_column(String(40), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False)
    observed_on: Mapped[date] = mapped_column(Date, nullable=False)
    source_reference: Mapped[str | None] = mapped_column(Text)
    document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    document_sha256: Mapped[str | None] = mapped_column(String(64))
    asserted_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    authorized_uploader_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    evidence_hash: Mapped[str] = mapped_column(String(64), nullable=False)
) OR "
            "(resolution_status <> 'RESOLVED' AND revision_id IS NULL "
            "AND revision_number IS NULL AND definition_hash IS NULL)",
            name="ck_finding_binding_resolved_metadata",
        ),
        CheckConstraint("evidence_manifest_hash ~ '^[0-9a-f]{64}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    compliance_flag_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_flags.id", ondelete="RESTRICT"), nullable=False)
    evaluation_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_evaluation_runs.id", ondelete="RESTRICT"))
    source_namespace: Mapped[str] = mapped_column(String(255), nullable=False)
    historical_rule_id: Mapped[str] = mapped_column(String(100), nullable=False)
    resolution_status: Mapped[str] = mapped_column(String(40), nullable=False)
    attribution_status: Mapped[str] = mapped_column(String(24), nullable=False, server_default="CURRENT_EVALUATION")
    canonical_rule_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_identities.id", ondelete="RESTRICT"))
    alias_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_aliases.id", ondelete="RESTRICT"))
    revision_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_revisions.id", ondelete="RESTRICT"))
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    revision_number: Mapped[int | None] = mapped_column(Integer)
    definition_hash: Mapped[str | None] = mapped_column(String(64))
    evaluator_name: Mapped[str | None] = mapped_column(String(255))
    evaluator_version: Mapped[str | None] = mapped_column(String(100))
    evaluator_artifact_hash: Mapped[str | None] = mapped_column(String(64))
    evidence_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="MISSING")
    evidence_manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    finding_snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))


class ComplianceFindingEvidence(Base):
    """Immutable, source-checked snapshot of one company fact used by a finding."""

    __tablename__ = "compliance_finding_evidence"
    __table_args__ = (
        UniqueConstraint("binding_id", "company_fact_id", name="uq_finding_evidence_fact"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    binding_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_finding_bindings.id", ondelete="RESTRICT"), nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    company_fact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("company_facts.id", ondelete="RESTRICT"), nullable=False)
    evidence_role: Mapped[str] = mapped_column(String(80), nullable=False)
    fact_key: Mapped[str] = mapped_column(String(120), nullable=False)
    fact_value_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    trust_level: Mapped[str] = mapped_column(String(40), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False)
    observed_on: Mapped[date] = mapped_column(Date, nullable=False)
    source_reference: Mapped[str | None] = mapped_column(Text)
    document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    document_sha256: Mapped[str | None] = mapped_column(String(64))
    asserted_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    authorized_uploader_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    evidence_hash: Mapped[str] = mapped_column(String(64), nullable=False)
", name="ck_finding_binding_evidence_hash"),
        CheckConstraint("finding_snapshot_hash ~ '^[0-9a-f]{64}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    compliance_flag_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_flags.id", ondelete="RESTRICT"), nullable=False)
    evaluation_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_evaluation_runs.id", ondelete="RESTRICT"))
    source_namespace: Mapped[str] = mapped_column(String(255), nullable=False)
    historical_rule_id: Mapped[str] = mapped_column(String(100), nullable=False)
    resolution_status: Mapped[str] = mapped_column(String(40), nullable=False)
    attribution_status: Mapped[str] = mapped_column(String(24), nullable=False, server_default="CURRENT_EVALUATION")
    canonical_rule_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_identities.id", ondelete="RESTRICT"))
    alias_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_aliases.id", ondelete="RESTRICT"))
    revision_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_revisions.id", ondelete="RESTRICT"))
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    revision_number: Mapped[int | None] = mapped_column(Integer)
    definition_hash: Mapped[str | None] = mapped_column(String(64))
    evaluator_name: Mapped[str | None] = mapped_column(String(255))
    evaluator_version: Mapped[str | None] = mapped_column(String(100))
    evaluator_artifact_hash: Mapped[str | None] = mapped_column(String(64))
    evidence_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="MISSING")
    evidence_manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    finding_snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))


class ComplianceFindingEvidence(Base):
    """Immutable, source-checked snapshot of one company fact used by a finding."""

    __tablename__ = "compliance_finding_evidence"
    __table_args__ = (
        UniqueConstraint("binding_id", "company_fact_id", name="uq_finding_evidence_fact"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    binding_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_finding_bindings.id", ondelete="RESTRICT"), nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    company_fact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("company_facts.id", ondelete="RESTRICT"), nullable=False)
    evidence_role: Mapped[str] = mapped_column(String(80), nullable=False)
    fact_key: Mapped[str] = mapped_column(String(120), nullable=False)
    fact_value_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    trust_level: Mapped[str] = mapped_column(String(40), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False)
    observed_on: Mapped[date] = mapped_column(Date, nullable=False)
    source_reference: Mapped[str | None] = mapped_column(Text)
    document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    document_sha256: Mapped[str | None] = mapped_column(String(64))
    asserted_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    authorized_uploader_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    evidence_hash: Mapped[str] = mapped_column(String(64), nullable=False)
", name="ck_finding_binding_snapshot_hash"),
        CheckConstraint(
            "evaluator_artifact_hash IS NULL OR evaluator_artifact_hash ~ '^[0-9a-f]{64}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    compliance_flag_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_flags.id", ondelete="RESTRICT"), nullable=False)
    evaluation_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_evaluation_runs.id", ondelete="RESTRICT"))
    source_namespace: Mapped[str] = mapped_column(String(255), nullable=False)
    historical_rule_id: Mapped[str] = mapped_column(String(100), nullable=False)
    resolution_status: Mapped[str] = mapped_column(String(40), nullable=False)
    attribution_status: Mapped[str] = mapped_column(String(24), nullable=False, server_default="CURRENT_EVALUATION")
    canonical_rule_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_identities.id", ondelete="RESTRICT"))
    alias_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_aliases.id", ondelete="RESTRICT"))
    revision_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_revisions.id", ondelete="RESTRICT"))
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    revision_number: Mapped[int | None] = mapped_column(Integer)
    definition_hash: Mapped[str | None] = mapped_column(String(64))
    evaluator_name: Mapped[str | None] = mapped_column(String(255))
    evaluator_version: Mapped[str | None] = mapped_column(String(100))
    evaluator_artifact_hash: Mapped[str | None] = mapped_column(String(64))
    evidence_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="MISSING")
    evidence_manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    finding_snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))


class ComplianceFindingEvidence(Base):
    """Immutable, source-checked snapshot of one company fact used by a finding."""

    __tablename__ = "compliance_finding_evidence"
    __table_args__ = (
        UniqueConstraint("binding_id", "company_fact_id", name="uq_finding_evidence_fact"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    binding_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_finding_bindings.id", ondelete="RESTRICT"), nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    company_fact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("company_facts.id", ondelete="RESTRICT"), nullable=False)
    evidence_role: Mapped[str] = mapped_column(String(80), nullable=False)
    fact_key: Mapped[str] = mapped_column(String(120), nullable=False)
    fact_value_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    trust_level: Mapped[str] = mapped_column(String(40), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False)
    observed_on: Mapped[date] = mapped_column(Date, nullable=False)
    source_reference: Mapped[str | None] = mapped_column(Text)
    document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    document_sha256: Mapped[str | None] = mapped_column(String(64))
    asserted_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    authorized_uploader_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    evidence_hash: Mapped[str] = mapped_column(String(64), nullable=False)
",
            name="ck_finding_binding_evaluator_hash",
        ),
        CheckConstraint(
            "attribution_evidence_hash IS NULL OR attribution_evidence_hash ~ '^[0-9a-f]{64}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    compliance_flag_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_flags.id", ondelete="RESTRICT"), nullable=False)
    evaluation_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_evaluation_runs.id", ondelete="RESTRICT"))
    source_namespace: Mapped[str] = mapped_column(String(255), nullable=False)
    historical_rule_id: Mapped[str] = mapped_column(String(100), nullable=False)
    resolution_status: Mapped[str] = mapped_column(String(40), nullable=False)
    attribution_status: Mapped[str] = mapped_column(String(24), nullable=False, server_default="CURRENT_EVALUATION")
    canonical_rule_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_identities.id", ondelete="RESTRICT"))
    alias_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_aliases.id", ondelete="RESTRICT"))
    revision_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_revisions.id", ondelete="RESTRICT"))
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    revision_number: Mapped[int | None] = mapped_column(Integer)
    definition_hash: Mapped[str | None] = mapped_column(String(64))
    evaluator_name: Mapped[str | None] = mapped_column(String(255))
    evaluator_version: Mapped[str | None] = mapped_column(String(100))
    evaluator_artifact_hash: Mapped[str | None] = mapped_column(String(64))
    evidence_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="MISSING")
    evidence_manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    finding_snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))


class ComplianceFindingEvidence(Base):
    """Immutable, source-checked snapshot of one company fact used by a finding."""

    __tablename__ = "compliance_finding_evidence"
    __table_args__ = (
        UniqueConstraint("binding_id", "company_fact_id", name="uq_finding_evidence_fact"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    binding_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_finding_bindings.id", ondelete="RESTRICT"), nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    company_fact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("company_facts.id", ondelete="RESTRICT"), nullable=False)
    evidence_role: Mapped[str] = mapped_column(String(80), nullable=False)
    fact_key: Mapped[str] = mapped_column(String(120), nullable=False)
    fact_value_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    trust_level: Mapped[str] = mapped_column(String(40), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False)
    observed_on: Mapped[date] = mapped_column(Date, nullable=False)
    source_reference: Mapped[str | None] = mapped_column(Text)
    document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    document_sha256: Mapped[str | None] = mapped_column(String(64))
    asserted_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    authorized_uploader_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    evidence_hash: Mapped[str] = mapped_column(String(64), nullable=False)
",
            name="ck_finding_binding_attribution_evidence_hash",
        ),
        CheckConstraint(
            "(attribution_status = 'ATTRIBUTED' AND attribution_basis IS NOT NULL "
            "AND btrim(attribution_basis) <> '' AND attribution_evidence_hash IS NOT NULL "
            "AND attribution_reviewed_by IS NOT NULL AND attribution_reviewed_at IS NOT NULL) "
            "OR (attribution_status <> 'ATTRIBUTED' AND attribution_basis IS NULL "
            "AND attribution_evidence_hash IS NULL AND attribution_reviewed_by IS NULL "
            "AND attribution_reviewed_at IS NULL)",
            name="ck_finding_binding_attribution_review_gate",
        ),
        CheckConstraint(
            "attribution_status <> 'ATTRIBUTED' OR "
            "(resolution_status = 'RESOLVED' AND evidence_status = 'COMPLETE')",
            name="ck_finding_binding_attribution_requires_identity_evidence",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    compliance_flag_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_flags.id", ondelete="RESTRICT"), nullable=False)
    evaluation_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_evaluation_runs.id", ondelete="RESTRICT"))
    source_namespace: Mapped[str] = mapped_column(String(255), nullable=False)
    historical_rule_id: Mapped[str] = mapped_column(String(100), nullable=False)
    resolution_status: Mapped[str] = mapped_column(String(40), nullable=False)
    attribution_status: Mapped[str] = mapped_column(String(24), nullable=False, server_default="CURRENT_EVALUATION")
    canonical_rule_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_identities.id", ondelete="RESTRICT"))
    alias_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_aliases.id", ondelete="RESTRICT"))
    revision_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("legal_rule_revisions.id", ondelete="RESTRICT"))
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    revision_number: Mapped[int | None] = mapped_column(Integer)
    definition_hash: Mapped[str | None] = mapped_column(String(64))
    evaluator_name: Mapped[str | None] = mapped_column(String(255))
    evaluator_version: Mapped[str | None] = mapped_column(String(100))
    evaluator_artifact_hash: Mapped[str | None] = mapped_column(String(64))
    evidence_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="MISSING")
    evidence_manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    finding_snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))


class ComplianceFindingEvidence(Base):
    """Immutable, source-checked snapshot of one company fact used by a finding."""

    __tablename__ = "compliance_finding_evidence"
    __table_args__ = (
        UniqueConstraint("binding_id", "company_fact_id", name="uq_finding_evidence_fact"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    binding_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("compliance_finding_bindings.id", ondelete="RESTRICT"), nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False)
    company_fact_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("company_facts.id", ondelete="RESTRICT"), nullable=False)
    evidence_role: Mapped[str] = mapped_column(String(80), nullable=False)
    fact_key: Mapped[str] = mapped_column(String(120), nullable=False)
    fact_value_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    trust_level: Mapped[str] = mapped_column(String(40), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(20), nullable=False)
    observed_on: Mapped[date] = mapped_column(Date, nullable=False)
    source_reference: Mapped[str | None] = mapped_column(Text)
    document_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    document_sha256: Mapped[str | None] = mapped_column(String(64))
    asserted_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    authorized_uploader_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    evidence_hash: Mapped[str] = mapped_column(String(64), nullable=False)
