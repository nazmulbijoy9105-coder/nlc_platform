"""Fail-closed statutory calendar and penalty service.

Only explicit, source-versioned, approved event definitions with verified
trigger evidence may be persisted. No Bangladesh-law defaults are embedded.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import select

from app.models.company import Company
from app.models.compliance_calendar import ComplianceCalendarEvent
from app.models.enums import CalendarEventStatus, CalendarEventType
from app.services.legal_deadline_engine import (
    DeadlineRule,
    PenaltyRule,
    calculate_approved_penalty,
    calculate_deadline,
)

# Production remains fail-closed until the versioned approval register and
# exact event allowlist are completed. Tests may inject approved definitions.
LEGAL_CALENDAR_RELEASED = False
VERIFIED_CALENDAR_EVENT_TYPES: frozenset[str] = frozenset()
VERIFIED_CALENDAR_RULE_IDS: frozenset[str] = frozenset()
VERIFIED_PENALTY_EVENT_TYPES: frozenset[str] = frozenset()
VERIFIED_PENALTY_RULE_IDS: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class CalendarEventDefinition:
    event_type: CalendarEventType
    title: str
    period_label: str
    rule: DeadlineRule
    trigger_date: date
    applicable: bool
    trigger_evidence_verified: bool
    trigger_evidence_ref: str
    description: str | None = None
    holidays: frozenset[date] = frozenset()
    holiday_calendar_version: str | None = None
    holiday_source_citation: str | None = None


# Populated only from the reviewed, versioned legal event manifest.
APPROVED_CALENDAR_EVENT_DEFINITIONS: tuple[CalendarEventDefinition, ...] = ()
# Exact source-versioned penalty objects are registered here only after legal
# review. A caller-created PenaltyRule with approved=True is not approval.
APPROVED_PENALTY_RULES: tuple[tuple[str, PenaltyRule], ...] = ()

def calendar_manifest_is_released() -> bool:
    """True only for a non-empty, internally consistent approved event manifest."""
    if (
        LEGAL_CALENDAR_RELEASED is not True
        or not VERIFIED_CALENDAR_EVENT_TYPES
        or not VERIFIED_CALENDAR_RULE_IDS
        or not APPROVED_CALENDAR_EVENT_DEFINITIONS
    ):
        return False

    keys: set[tuple[str, str]] = set()
    for definition in APPROVED_CALENDAR_EVENT_DEFINITIONS:
        if (
            not isinstance(definition, CalendarEventDefinition)
            or not isinstance(definition.event_type, CalendarEventType)
            or not isinstance(definition.rule, DeadlineRule)
            or definition.event_type.value not in VERIFIED_CALENDAR_EVENT_TYPES
            or definition.rule.rule_id not in VERIFIED_CALENDAR_RULE_IDS
            or definition.rule.approved is not True
            or not isinstance(definition.title, str)
            or not definition.title.strip()
            or not isinstance(definition.period_label, str)
            or not definition.period_label.strip()
            or (definition.holidays and not (
                definition.holiday_calendar_version
                and definition.holiday_source_citation
            ))
        ):
            return False
        key = (definition.event_type.value, definition.period_label)
        if key in keys:
            return False
        keys.add(key)
    return True



def _generate_calendar(company: Company) -> list[dict]:
    """Legacy compatibility function: never synthesizes statutory dates."""
    if not calendar_manifest_is_released():
        return []
    return []


class ComplianceCalendarService:
    def __init__(self, db):
        self.db = db

    async def generate_approved_events(
        self,
        company_id,
        definitions: list[CalendarEventDefinition],
    ) -> list[ComplianceCalendarEvent]:
        """Calculate and persist approved events with source/evidence provenance.

        This method is intentionally unavailable until the global release gate,
        rule/event allowlists and exact approved event manifest are released.
        Definitions are explicit inputs, not inferred from company defaults.
        """
        if not calendar_manifest_is_released():
            raise PermissionError("Statutory calendar generation is not released.")
        if not definitions:
            raise PermissionError("No counsel-approved calendar event definitions are registered.")
        result = await self.db.execute(
            select(Company).where(Company.id == company_id)
        )
        company = result.scalar_one_or_none()
        if company is None:
            return []

        persisted: list[ComplianceCalendarEvent] = []
        for definition in definitions:
            if not isinstance(definition, CalendarEventDefinition):
                raise PermissionError("Calendar input is not a registered event definition.")
            event_type = definition.event_type.value
            if (
                event_type not in VERIFIED_CALENDAR_EVENT_TYPES
                or definition.rule.rule_id not in VERIFIED_CALENDAR_RULE_IDS
                or definition.rule.approved is not True
                or definition not in APPROVED_CALENDAR_EVENT_DEFINITIONS
            ):
                raise PermissionError(
                    "Calendar definition is not an exact counsel-approved "
                    "event/rule manifest entry."
                )
            if not isinstance(definition.trigger_evidence_ref, str) or not definition.trigger_evidence_ref.strip():
                raise ValueError("A verified trigger evidence reference is required")
            if definition.holidays and not (
                definition.holiday_calendar_version
                and definition.holiday_source_citation
            ):
                raise ValueError(
                    "Holiday dates require a versioned holiday calendar source citation"
                )
            due_date = calculate_deadline(
                definition.rule,
                trigger_date=definition.trigger_date,
                applicable=definition.applicable,
                trigger_evidence_verified=definition.trigger_evidence_verified,
                holidays=definition.holidays,
            )
            if due_date is None:
                continue

            manifest_payload = {
                "rule_id": definition.rule.rule_id,
                "source": definition.rule.source_citation,
                "source_version": definition.rule.source_version,
                "effective_from": definition.rule.effective_from.isoformat(),
                "effective_to": (
                    definition.rule.effective_to.isoformat()
                    if definition.rule.effective_to else None
                ),
                "trigger_date": definition.trigger_date.isoformat(),
                "trigger_evidence_ref": definition.trigger_evidence_ref,
                "due_date": due_date.isoformat(),
                "event_type": event_type,
                "title": definition.title,
                "period_label": definition.period_label,
                "offset": definition.rule.offset,
                "unit": definition.rule.unit,
                "adjustment": definition.rule.adjustment,
                "exclude_trigger_day": definition.rule.exclude_trigger_day,
                "holidays": sorted(day.isoformat() for day in definition.holidays),
                "holiday_calendar_version": definition.holiday_calendar_version,
                "holiday_source_citation": definition.holiday_source_citation,
            }
            manifest_hash = hashlib.sha256(
                json.dumps(manifest_payload, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()

            existing_result = await self.db.execute(
                select(ComplianceCalendarEvent).where(
                    ComplianceCalendarEvent.company_id == company_id,
                    ComplianceCalendarEvent.event_type == definition.event_type,
                    ComplianceCalendarEvent.period_label == definition.period_label,
                )
            )
            event = existing_result.scalar_one_or_none()
            if event is None:
                event = ComplianceCalendarEvent(
                    company_id=company_id,
                    event_type=definition.event_type,
                    title=definition.title,
                    description=definition.description,
                    due_date=due_date,
                    reminder_30_days=due_date - timedelta(days=30),
                    reminder_14_days=due_date - timedelta(days=14),
                    reminder_7_days=due_date - timedelta(days=7),
                    period_label=definition.period_label,
                    status=CalendarEventStatus.UPCOMING,
                    is_statutory=True,
                )
                self.db.add(event)
            elif event.status in (
                CalendarEventStatus.COMPLETED,
                CalendarEventStatus.WAIVED,
            ):
                # Completed/waived records are immutable audit history.
                persisted.append(event)
                continue
            else:
                event.title = definition.title
                event.description = definition.description
                event.due_date = due_date
                event.reminder_30_days = due_date - timedelta(days=30)
                event.reminder_14_days = due_date - timedelta(days=14)
                event.reminder_7_days = due_date - timedelta(days=7)

            # Keep provenance attached to both new and refreshed events.
            event.statutory_basis = definition.rule.source_citation[:200]
            event.legal_rule_id = definition.rule.rule_id
            event.legal_source_citation = definition.rule.source_citation
            event.legal_source_version = definition.rule.source_version
            event.legal_effective_from = definition.rule.effective_from
            event.legal_effective_to = definition.rule.effective_to
            event.legal_trigger_date = definition.trigger_date
            event.trigger_evidence_ref = definition.trigger_evidence_ref
            event.legal_manifest_sha256 = manifest_hash
            persisted.append(event)

        await self.db.flush()
        return persisted

    async def get_calendar(
        self,
        company_id,
        *,
        include_past_days: int = 365,
        include_future_days: int = 365,
    ) -> list[dict]:
        if not calendar_manifest_is_released():
            return []
        result = await self.db.execute(
            select(Company).where(Company.id == company_id)
        )
        company = result.scalar_one_or_none()
        if company is None:
            return []
        today = date.today()
        event_result = await self.db.execute(
            select(ComplianceCalendarEvent).where(
                ComplianceCalendarEvent.company_id == company_id,
                ComplianceCalendarEvent.due_date >= today - timedelta(days=include_past_days),
                ComplianceCalendarEvent.due_date <= today + timedelta(days=include_future_days),
            ).order_by(ComplianceCalendarEvent.due_date.asc())
        )
        events = event_result.scalars().all()
        return [
            {
                "id": str(event.id),
                "company_id": str(event.company_id),
                "event_type": event.event_type.value,
                "title": event.title,
                "description": event.description,
                "due_date": event.due_date.isoformat(),
                "period_label": event.period_label,
                "status": event.status.value,
                "is_statutory": event.is_statutory,
                "statutory_basis": event.statutory_basis,
                "legal_rule_id": event.legal_rule_id,
                "legal_source_version": event.legal_source_version,
                "legal_manifest_sha256": event.legal_manifest_sha256,
            }
            for event in events
        ]

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
    """Legacy API: returns None until a source-specific PenaltyRule is supplied."""
    return None


def calculate_rule_penalty(
    rule: PenaltyRule,
    *,
    event_type: str,
    days_overdue: int,
    due_date: date,
    trigger_date: date,
    as_of: date,
    applicable: bool,
    trigger_evidence_verified: bool,
) -> Decimal | None:
    """Apply only an explicitly approved penalty rule for an approved event type."""
    if (
        event_type not in VERIFIED_PENALTY_EVENT_TYPES
        or rule.rule_id not in VERIFIED_PENALTY_RULE_IDS
        or rule.approved is not True
        or (event_type, rule) not in APPROVED_PENALTY_RULES
    ):
        return None
    return calculate_approved_penalty(
        rule,
        days_overdue=days_overdue,
        due_date=due_date,
        trigger_date=trigger_date,
        as_of=as_of,
        applicable=applicable,
        trigger_evidence_verified=trigger_evidence_verified,
    )
