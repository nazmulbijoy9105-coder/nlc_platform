"""PostgreSQL invariants for canonical and duplicate compliance flags."""
from __future__ import annotations

from datetime import date
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.compliance import ComplianceFlag
from app.models.enums import FlagStatus, RevenueTier, SeverityLevel

pytestmark = [pytest.mark.integration]


def _flag(company_id: uuid.UUID, *, status: FlagStatus, duplicate_of_id=None) -> ComplianceFlag:
    return ComplianceFlag(
        id=uuid.uuid4(),
        company_id=company_id,
        rule_id="DIR-001",
        rule_version="test",
        flag_code="DIR-001",
        statutory_basis="Pending independent legal validation",
        severity=SeverityLevel.NOT_EVALUATED,
        score_impact=0,
        revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
        evaluation_state="UNKNOWN",
        flag_status=status,
        duplicate_of_id=duplicate_of_id,
        triggered_date=date.today(),
        description="Test-only internal review signal",
        resolution_notes=(
            "Duplicate record only; the underlying legal or compliance matter "
            "has not been resolved."
            if status == FlagStatus.DUPLICATE
            else None
        ),
    )


@pytest.mark.asyncio
async def test_duplicate_flag_is_linked_and_not_counted_as_active(db, db_company):
    canonical = _flag(db_company.id, status=FlagStatus.ACTIVE)
    db.add(canonical)
    await db.flush()

    duplicate = _flag(
        db_company.id,
        status=FlagStatus.DUPLICATE,
        duplicate_of_id=canonical.id,
    )
    db.add(duplicate)
    await db.flush()

    stored_duplicate = await db.get(ComplianceFlag, duplicate.id)
    active = (
        await db.execute(
            select(ComplianceFlag).where(
                ComplianceFlag.company_id == db_company.id,
                ComplianceFlag.rule_id == "DIR-001",
                ComplianceFlag.flag_status == FlagStatus.ACTIVE,
            )
        )
    ).scalars().all()

    assert stored_duplicate is not None
    assert stored_duplicate.flag_status == FlagStatus.DUPLICATE
    assert stored_duplicate.duplicate_of_id == canonical.id
    assert "underlying legal or compliance matter has not been resolved" in stored_duplicate.resolution_notes
    assert [flag.id for flag in active] == [canonical.id]


@pytest.mark.asyncio
async def test_database_rejects_second_active_flag_for_same_company_rule(db, db_company):
    canonical = _flag(db_company.id, status=FlagStatus.ACTIVE)
    db.add(canonical)
    await db.flush()

    with pytest.raises(IntegrityError):
        async with db.begin_nested():
            db.add(_flag(db_company.id, status=FlagStatus.ACTIVE))
            await db.flush()
