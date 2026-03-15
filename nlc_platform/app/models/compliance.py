from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class ComplianceScore(Base):
    __tablename__ = "compliance_scores"

    id = Column(String(36), primary_key=True)
    company_id = Column(String(36), ForeignKey("companies.id"), nullable=False)
    score = Column(Integer, nullable=False)
    risk_band = Column(String(20), nullable=False)
    total_rules = Column(Integer, nullable=False)
    passed_rules = Column(Integer, nullable=False)
    failed_rules = Column(Integer, nullable=False)
    evaluated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    company = relationship("Company", back_populates="compliance_scores")


class Violation(Base):
    __tablename__ = "violations"

    id = Column(String(36), primary_key=True)
    company_id = Column(String(36), ForeignKey("companies.id"), nullable=False)
    rule_id = Column(String(36), ForeignKey("rule_definitions.id"), nullable=False)
    severity = Column(String(20), nullable=False)
    description = Column(Text, nullable=False)
    statutory_basis = Column(Text, nullable=True)
    score_impact = Column(Integer, nullable=False)
    is_resolved = Column(String(10), default="false")
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    company = relationship("Company", back_populates="violations")
    rule = relationship("RuleDefinition", back_populates="violations")


class RuleModule(Base):
    __tablename__ = "rule_modules"

    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    order = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    rules = relationship("RuleDefinition", back_populates="module", cascade="all, delete-orphan")


class RuleDefinition(Base):
    __tablename__ = "rule_definitions"

    id = Column(String(36), primary_key=True)
    module_id = Column(String(36), ForeignKey("rule_modules.id"), nullable=False)
    code = Column(String(20), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    statutory_reference = Column(Text, nullable=True)
    max_score = Column(Integer, nullable=False, default=5)
    is_active = Column(String(10), default="true")
    criteria = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    module = relationship("RuleModule", back_populates="rules")
    violations = relationship("Violation", back_populates="rule")
    criteria_list = relationship("RuleCriteria", back_populates="rule", cascade="all, delete-orphan")


class RuleCriteria(Base):
    __tablename__ = "rule_criteria"

    id = Column(String(36), primary_key=True)
    rule_id = Column(String(36), ForeignKey("rule_definitions.id"), nullable=False)
    description = Column(Text, nullable=False)
    check_type = Column(String(50), nullable=False)
    check_value = Column(String(255), nullable=True)
    score_impact = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    rule = relationship("RuleDefinition", back_populates="criteria_list")
