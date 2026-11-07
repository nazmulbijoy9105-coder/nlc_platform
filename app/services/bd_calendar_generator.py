"""Legacy statutory-calendar generator, deliberately disabled.

The former implementation emitted hard-coded AGM and tax dates without
rule-level approval, company-specific applicability, temporal-law versioning,
holiday/extension checks or verified event provenance. Customer-facing
calendar generation is now owned by ComplianceCalendarService and remains
unavailable until the independent legal release gate is opened.
"""
from datetime import date
from typing import NoReturn
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


class BDCalendarGenerator:
    """Compatibility shim that refuses to emit unapproved statutory dates."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_for_company(
        self,
        company_id: UUID | str,
        incorporation_date: date,
        fye: date,
        years_ahead: int = 3,
    ) -> NoReturn:
        raise RuntimeError(
            "Legacy BDCalendarGenerator is disabled: statutory calendar events "
            "require the independently approved ComplianceCalendarService release gate."
        )
