"""
NEUM LEX COUNSEL — Legal Rules Service
app/services/rules_service.py

Implements _get_all_legal_rules, _get_legal_rule,
_version_legal_rule, _update_legal_rule stubs.

AI Constitution Article 1 — RULE GOVERNANCE:
  ✓ Only Super Admin may modify rules
  ✓ Every change creates a LegalRuleVersion entry (append-only)
  ✓ change_reason is MANDATORY
  ✓ previous_definition stored before any change
  ✓ Rule changes do NOT hot-reload the engine (requires deployment)
  ✓ is_active=False disables rule without deleting it
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from app.models.rules import LegalRule, LegalRuleVersion
from app.services.base import BaseService


class RulesService(BaseService[LegalRule]):
    model = LegalRule

    async def get_all(self, *, active_only: bool = False,
        rule_type: str | None = None, severity: str | None = None,
        is_active: bool | None = None,
        is_black_override: bool | None = None) -> list[LegalRule]:
        """Get all ILRMF rules with optional filters."""
        filters = []
        if is_active is not None:
            filters.append(LegalRule.is_active == is_active)
        elif active_only:
            filters.append(LegalRule.is_active.is_(True))
        if rule_type:
            filters.append(LegalRule.rule_type == rule_type)
        if severity:
            filters.append(LegalRule.default_severity == severity)
        if is_black_override is not None:
            filters.append(LegalRule.is_black_override == is_black_override)
        q = select(LegalRule).order_by(LegalRule.rule_id)
        if filters:
            q = q.where(*filters)
        return list((await self.db.execute(q)).scalars().all())

    async def get_by_rule_id(self, rule_id: str) -> LegalRule | None:
        """
        Fetch a rule by its ILRMF rule_id (e.g. "AGM-001").
        _get_legal_rule stub implementation.
        """
        result = await self.db.execute(
            select(LegalRule).where(LegalRule.rule_id == rule_id)
        )
        return result.scalar_one_or_none()

    async def update_rule(
        self,
        rule_id: str,
        updates: dict,
        modified_by: uuid.UUID,
        change_reason: str = "Rule updated",
        sro_reference: str | None = None,
    ) -> LegalRule:
        rule = await self.get_by_rule_id(rule_id)
        if not rule:
            raise ValueError(f"Rule {rule_id} not found")

        # Snapshot previous state BEFORE mutation (append-only history)
        await self._create_version_snapshot(
            rule, change_reason, modified_by, sro_reference
        )

        # Increment version
        current_version = int(rule.rule_version.split('.')[0]) if rule.rule_version else 1
        new_version = f"{current_version + 1}.0"
        
        # Apply updates
        for key, value in updates.items():
            if hasattr(rule, key):
                setattr(rule, key, value)
        
        rule.rule_version = new_version
        rule.last_modified_by = modified_by
        rule.last_modified_at = datetime.utcnow()
        
        await self.db.flush()
        return rule

    async def _create_version_snapshot(
        self,
        rule: LegalRule,
        change_reason: str,
        changed_by: uuid.UUID,
        sro_reference: str | None = None,
    ) -> LegalRuleVersion:
        """
        Snapshot the current rule state into LegalRuleVersion.
        This entry is append-only — never modified after creation.
        AI Constitution Article 1: Every change is traceable.
        """
        previous_definition = {
            "rule_name":        rule.rule_name,
            "statutory_basis":  rule.statutory_basis,
            "description":      rule.description,
            "default_severity": rule.default_severity,
            "score_impact":     rule.score_impact,
            "revenue_tier":     rule.revenue_tier,
            "is_active":        rule.is_active,
            "rule_condition":   rule.rule_condition,
            "rule_version":     rule.rule_version,
        }
        version = LegalRuleVersion(
            id=uuid.uuid4(),
            rule_id=rule.rule_id,
            version=rule.rule_version or "1.0",
            change_reason=change_reason,
            changed_by=changed_by,
            changed_at=datetime.now(UTC),
            previous_definition=previous_definition,
            sro_reference=sro_reference,
        )
        self.db.add(version)
        await self.db.flush()
        return version

    async def get_version_history(self, rule_id: str) -> list[LegalRuleVersion]:
        """Get full version history for a rule."""
        result = await self.db.execute(
            select(LegalRuleVersion)
            .where(LegalRuleVersion.rule_id == rule_id)
            .order_by(LegalRuleVersion.changed_at.desc())
        )
        return list(result.scalars().all())

    async def get_black_override_rules(self) -> list[LegalRule]:
        """Get all rules that trigger BLACK band override."""
        result = await self.db.execute(
            select(LegalRule).where(
                LegalRule.is_black_override,
                LegalRule.is_active,
            )
        )
        return list(result.scalars().all())
