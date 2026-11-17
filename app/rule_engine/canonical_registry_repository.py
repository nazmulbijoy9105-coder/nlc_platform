"""Read-only SQLAlchemy adapter for the canonical legal-rule registry.

The adapter never creates sessions, changes roles, commits, or grants access.
Callers must pass an application session already established by the normal
authentication/RLS dependency. Database grants and RLS remain authoritative.
The current registry migration intentionally grants runtime roles no SELECT;
until a separately reviewed policy/grant migration is applied, access fails
closed as REGISTRY_UNAVAILABLE.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rules import LegalRuleAlias, LegalRuleIdentity, LegalRuleRevision
from app.rule_engine.canonical_identity import RuleResolution, resolve_rule_identity


def _row_identity(row: LegalRuleIdentity) -> dict[str, Any]:
    return {
        "identity_status": row.identity_status,
        "jurisdiction": row.jurisdiction,
    }


def _row_alias(row: LegalRuleAlias) -> dict[str, Any]:
    return {
        "source_namespace": row.source_namespace,
        "historical_rule_id": row.historical_rule_id,
        "canonical_rule_id": str(row.canonical_rule_id),
        "resolution_status": row.resolution_status,
        "valid_from": row.valid_from,
        "valid_to": row.valid_to,
    }


def _row_revision(row: LegalRuleRevision) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "canonical_rule_id": str(row.canonical_rule_id),
        "revision_number": row.revision_number,
        "effective_from": row.effective_from,
        "effective_to": row.effective_to,
        "definition_json": row.definition_json,
        "definition_hash": row.definition_hash,
        "approval_state": row.approval_state,
    }


async def resolve_from_registry(
    session: AsyncSession,
    *,
    source_namespace: str,
    historical_rule_id: str,
    effective_date: date,
    jurisdiction: str,
) -> RuleResolution:
    """Load one namespaced alias and its identity/revisions, then resolve.

    A date-time is rejected by the pure resolver before any database query.
    DB permission/connectivity failures are reported without leaking SQL or
    connection details. No fallback to legacy legal_rules is permitted.
    """
    if not isinstance(effective_date, date) or isinstance(effective_date, datetime):
        return resolve_rule_identity(
            source_namespace=source_namespace,
            historical_rule_id=historical_rule_id,
            effective_date=effective_date,
            aliases=(),
            identities={},
            revisions=(),
        )
    if not source_namespace or not historical_rule_id or not jurisdiction:
        return RuleResolution(
            status="INVALID_LOOKUP_KEY",
            source_namespace=source_namespace,
            historical_rule_id=historical_rule_id,
            effective_date=effective_date,
            detail="Source namespace, historical rule ID and jurisdiction are required.",
        )

    try:
        alias_rows = (
            await session.execute(
                select(LegalRuleAlias).where(
                    LegalRuleAlias.source_namespace == source_namespace,
                    LegalRuleAlias.historical_rule_id == historical_rule_id,
                )
            )
        ).scalars().all()

        if not alias_rows:
            return resolve_rule_identity(
                source_namespace=source_namespace,
                historical_rule_id=historical_rule_id,
                effective_date=effective_date,
                aliases=(),
                identities={},
                revisions=(),
            )

        identity_ids = {row.canonical_rule_id for row in alias_rows}
        identity_rows = (
            await session.execute(
                select(LegalRuleIdentity).where(LegalRuleIdentity.id.in_(identity_ids))
            )
        ).scalars().all()
        if not identity_rows:
            # Alias rows have a restrictive FK to identities. A missing target
            # here therefore indicates an RLS/visibility problem, not a valid
            # absent identity; do not misreport it as a clean "not found".
            return RuleResolution(
                status="REGISTRY_UNAVAILABLE",
                source_namespace=source_namespace,
                historical_rule_id=historical_rule_id,
                effective_date=effective_date,
                detail="Registry alias exists but its canonical identity is not visible to this database session.",
            )
        identities = {str(row.id): _row_identity(row) for row in identity_rows}

        revision_rows = (
            await session.execute(
                select(LegalRuleRevision).where(
                    LegalRuleRevision.canonical_rule_id.in_(identity_ids)
                )
            )
        ).scalars().all()

        # Never let an alias silently cross a jurisdiction boundary.
        for identity in identities.values():
            if identity.get("jurisdiction") != jurisdiction:
                return RuleResolution(
                    status="JURISDICTION_MISMATCH",
                    source_namespace=source_namespace,
                    historical_rule_id=historical_rule_id,
                    effective_date=effective_date,
                    detail="Canonical identity jurisdiction does not match the requested jurisdiction.",
                )

        return resolve_rule_identity(
            source_namespace=source_namespace,
            historical_rule_id=historical_rule_id,
            effective_date=effective_date,
            aliases=[_row_alias(row) for row in alias_rows],
            identities=identities,
            revisions=[_row_revision(row) for row in revision_rows],
        )
    except DBAPIError:
        return RuleResolution(
            status="REGISTRY_UNAVAILABLE",
            source_namespace=source_namespace,
            historical_rule_id=historical_rule_id,
            effective_date=effective_date,
            detail="Canonical registry could not be read with the supplied database session.",
        )
