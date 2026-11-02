"""Regression tests for complete legal-rule version snapshots."""

from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.services.rules_service import RulesService


@pytest.mark.asyncio
async def test_rule_version_snapshot_preserves_material_legal_definition_fields():
    db = MagicMock()
    db.flush = AsyncMock()
    service = RulesService(db)

    changed_by = uuid4()
    rule = SimpleNamespace(
        rule_id="AGM-001",
        rule_type="AGM",
        rule_name="Annual general meeting",
        statutory_basis="Section 81, Companies Act 1994",
        statutory_effective_date=date(2024, 1, 1),
        description="Hold the annual general meeting within the statutory period.",
        verification_status="VERIFIED",
        verified_by="Independent legal reviewer",
        verified_at=date(2026, 10, 15),
        verification_notes="Checked against the current statutory text.",
        rule_condition={"company_type": ["PRIVATE_LIMITED"]},
        default_severity="RED",
        score_impact=15,
        revenue_tier="COMPLIANCE_PACKAGE",
        is_black_override=True,
        is_active=True,
        rule_version="2.4",
    )

    snapshot = await service._create_version_snapshot(
        rule=rule,
        change_reason="Regression test snapshot",
        changed_by=changed_by,
    )

    assert snapshot.previous_definition == {
        "rule_id": "AGM-001",
        "rule_type": "AGM",
        "rule_name": "Annual general meeting",
        "statutory_basis": "Section 81, Companies Act 1994",
        "statutory_effective_date": "2024-01-01",
        "description": "Hold the annual general meeting within the statutory period.",
        "verification_status": "VERIFIED",
        "verified_by": "Independent legal reviewer",
        "verified_at": "2026-10-15",
        "verification_notes": "Checked against the current statutory text.",
        "rule_condition": {"company_type": ["PRIVATE_LIMITED"]},
        "default_severity": "RED",
        "score_impact": 15,
        "revenue_tier": "COMPLIANCE_PACKAGE",
        "is_black_override": True,
        "is_active": True,
        "rule_version": "2.4",
    }
    db.add.assert_called_once_with(snapshot)
    db.flush.assert_awaited_once()
