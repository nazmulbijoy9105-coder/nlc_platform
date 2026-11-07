"""Fail-closed statutory calendar pending independent rule-level legal approval.

The former calendar hard-coded statutory deadlines and penalties without
company-specific applicability, effective-dated law, verified trigger facts,
holiday/extension handling or counsel-approved rule provenance. Those events
must not be emitted as legal deadlines until the corresponding event types are
explicitly approved and covered by regression evidence.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import select

from app.models.company import Company

# No statutory calendar event has completed rule-level legal approval.
LEGAL_CALENDAR_RELEASED = False
VERIFIED_CALENDAR_EVENT_TYPES: frozenset[str] = frozenset()

# Penalty amounts are never inferred from a generic event type. This remains
# empty until each penalty provision, liable person, trigger, cap, temporal
# version and company/taxpayer scope is independently validated.
VERIFIED_PENALTY_EVENT_TYPES: frozenset[str] = frozenset()


def _generate_calendar(company: Company) -> list[dict]:
    """Return no statutory events while the legal calendar release gate is closed."""
    if not LEGAL_CALENDAR_RELEASED or not VERIFIED_CALENDAR_EVENT_TYPES:
        return []
    # Approved event generation must be implemented from versioned,
    # company-specific legal obligations; legacy generic date arithmetic is
    # intentionally not retained as a fallback.
    return []


class ComplianceCalendarService:
    def __init__(self, db):
        self.db = db

    async def get_calendar(
        self,
        company_id,
        *,
        include_past_days: int = 365,
        include_future_days: int = 365,
    ) -> list[dict]:
        result = await self.db.execute(
            select(Company).where(Company.id == company_id)
        )
        company = result.scalar_one_or_none()
        if company is None:
            return []
        return _generate_calendar(company)

    async def get_upcoming(self, company_id, days_ahead: int = 30) -> list[dict]:
        return await self.get_calendar(
            company_id,
            include_past_days=0,
            include_future_days=days_ahead,
        )

    async def get_overdue(self, company_id) -> list[dict]:
        return await self.get_calendar(
            company_id,
            include_past_days=365,
            include_future_days=0,
        )


def calculate_penalty(
    event_type: str,
    days_overdue: int,
    fy_count: int = 1,
) -> Optional[int]:
    """Return None: no statutory penalty calculation is currently approved."""
    return None
