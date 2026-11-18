"""Fail-closed invalidation for company compliance score caches."""

from __future__ import annotations

import uuid

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.company import Company
from app.models.enums import RiskBand


async def invalidate_company_score(db: AsyncSession, company_id: uuid.UUID) -> None:
    """Clear the cached score whenever an evaluation input changes.

    This is deliberately destructive only to derived cache fields. It never
    changes legal rule metadata, company facts, or historical evaluation runs.
    A new completed evaluation is required before a score can be released.
    """
    await db.execute(
        update(Company)
        .where(Company.id == company_id)
        .values(
            current_compliance_score=None,
            current_risk_band=RiskBand.NOT_EVALUATED,
            last_evaluated_at=None,
        )
    )
