"""Legacy statutory-calendar generator, deliberately disabled.

The former implementation emitted hard-coded AGM and tax dates without
rule-level approval, company-specific applicability, temporal-law versioning,
holiday/extension checks or verified event provenance. Customer-facing deadline persistence is now controlled by the source-backed
product-owner workflow and verified tenant facts. This compatibility shim must
not emit hard-coded dates.
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
            "must use the source-backed product-owner deadline registry and verified tenant facts."
        )
