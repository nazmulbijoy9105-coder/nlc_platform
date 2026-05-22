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

    async def get_all(
        self,
        *,
        active_only: bool = True,
        rule_type: str | None = None,
    ) -> list[LegalRule]:
        """
        Get all ILRMF rules.
        _get_all_legal_rules stub implementation.
        """
        filters = []
        if active_only:
            filters.append(LegalRule.is_active)
        if rule_type:
            filters.append(LegalRule.rule_type == rule_type)
        result = await self.db.execute(
            select(LegalRule)
            .where(*filters) if filters else select(LegalRule)
            .order_by(LegalRule.rule_id)
        )
        return list(result.scalars().all())

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
        *,
        change_reason: str,
        changed_by: uuid.UUID,
        sro_reference: str | None = None,
        # Updatable fields
        rule_name: str | None = None,
        statutory_basis: str | None = None,
        description: str | None = None,
        default_severity: str | None = None,
        score_impact: int | None = None,
        revenue_tier: str | None = None,
        is_active: bool | None = None,
        rule_condition: dict | None = None,
    ) -> LegalRule | None:
        """
        Update a legal rule with mandatory version history.
        AI Constitution Article 1: change_reason is REQUIRED.
        _version_legal_rule + _update_legal_rule stub implementation.

        Order:
        1. Fetch current rule (validation)
        2. Snapshot current state to LegalRuleVersion (append-only)
        3. Apply updates
        4. Increment rule_version
        5. Update last_modified_by + last_modified_at
        """
        rule = await self.get_by_rule_id(rule_id)
        if not rule:
            return None

        # ── Step 1: Snapshot current state ─────────────────────────
        await self._create_version_snapshot(
            rule=rule,
            change_reason=change_reason,
            changed_by=changed_by,
            sro_reference=sro_reference,
        )

        # ── Step 2: Increment version ───────────────────────────────
        current_version = rule.rule_version or "1.0"
        try:
            major, minor = current_version.split(".")
            new_version = f"{major}.{int(minor) + 1}"
        except (ValueError, AttributeError):
            new_version = "1.1"

        # ── Step 3: Apply updates ───────────────────────────────────
        updates: dict[str, Any] = {
            "rule_version":     new_version,
            "last_modified_by": changed_by,
            "last_modified_at": datetime.now(UTC),
        }
        if rule_name is not None:
            updates["rule_name"] = rule_name
        if statutory_basis is not None:
            updates["statutory_basis"] = statutory_basis
        if description is not None:
            updates["description"] = description
        if default_severity is not None:
            updates["default_severity"] = default_severity
        if score_impact is not None:
            updates["score_impact"] = score_impact
        if revenue_tier is not None:
            updates["revenue_tier"] = revenue_tier
        if is_active is not None:
            updates["is_active"] = is_active
        if rule_condition is not None:
            updates["rule_condition"] = rule_condition

        return await self.update_instance(rule, **updates)

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
