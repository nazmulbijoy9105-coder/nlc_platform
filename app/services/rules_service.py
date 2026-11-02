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
        # Preserve the complete material legal-rule state before mutation.
        # JSONB cannot reliably serialize date/datetime/UUID/Enum objects, so
        # normalize those values into stable JSON-compatible representations.
        def snapshot_value(value: Any) -> Any:
            if value is None:
                return None
            if hasattr(value, "value"):
                return value.value
            if isinstance(value, (datetime,)):
                return value.isoformat()
            if isinstance(value, uuid.UUID):
                return str(value)
            if hasattr(value, "isoformat"):
                return value.isoformat()
            return value

        previous_definition = {
            "id":                      snapshot_value(rule.id),
            "rule_id":                 rule.rule_id,
            "rule_type":               snapshot_value(rule.rule_type),
            "rule_name":               rule.rule_name,
            "statutory_basis":         rule.statutory_basis,
            "statutory_effective_date": snapshot_value(rule.statutory_effective_date),
            "description":             rule.description,
            "verification_status":    rule.verification_status,
            "verified_by":             rule.verified_by,
            "verified_at":             snapshot_value(rule.verified_at),
            "verification_notes":      rule.verification_notes,
            "rule_condition":          rule.rule_condition,
            "default_severity":        snapshot_value(rule.default_severity),
            "score_impact":            rule.score_impact,
            "revenue_tier":            snapshot_value(rule.revenue_tier),
            "is_black_override":       rule.is_black_override,
            "is_active":               rule.is_active,
            "rule_version":            rule.rule_version,
            "created_by":              snapshot_value(rule.created_by),
            "last_modified_by":        snapshot_value(rule.last_modified_by),
            "last_modified_at":        snapshot_value(rule.last_modified_at),
            "created_at":              snapshot_value(rule.created_at),
            "updated_at":              snapshot_value(rule.updated_at),
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
