"""Deterministic, fail-closed resolution of historical rule identifiers.

This module is deliberately pure: callers must supply rows obtained through an
authorised repository. It performs no database access and grants no legal or
scoring approval. A successful identity resolution is not a legal conclusion.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Mapping, Sequence


@dataclass(frozen=True, slots=True)
class RuleResolution:
    status: str
    source_namespace: str
    historical_rule_id: str
    effective_date: date
    canonical_rule_id: str | None = None
    revision_id: str | None = None
    revision_number: int | None = None
    approval_state: str | None = None
    definition_hash: str | None = None
    detail: str = ""

    @property
    def resolved(self) -> bool:
        return self.status == "RESOLVED"


def _as_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


def canonical_definition_hash(definition: Mapping[str, Any]) -> str:
    """SHA-256 of canonical UTF-8 JSON; keys/order/spacing cannot alter digest."""
    payload = json.dumps(
        definition,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def resolve_rule_identity(
    *,
    source_namespace: str,
    historical_rule_id: str,
    effective_date: date,
    aliases: Sequence[Mapping[str, Any]],
    identities: Mapping[str, Mapping[str, Any]],
    revisions: Sequence[Mapping[str, Any]],
) -> RuleResolution:
    """Resolve one namespaced legacy ID and select exactly one dated revision.

    No fallback to an unnamespaced ID is permitted. Duplicate active mappings,
    unknown identities, overlapping revisions, invalid hashes, and non-active
    identities fail closed. Approval state is returned as metadata only; this
    resolver never authorises statutory scoring.
    """
    base = dict(
        source_namespace=source_namespace,
        historical_rule_id=historical_rule_id,
        effective_date=effective_date,
    )
    if not isinstance(effective_date, date) or isinstance(effective_date, datetime):
        return RuleResolution(
            status="INVALID_EFFECTIVE_DATE", **base,
            detail="effective_date must be a date without a time component.",
        )
    if not source_namespace or not historical_rule_id:
        return RuleResolution(
            status="INVALID_LOOKUP_KEY", **base,
            detail="Source namespace and historical rule ID are both required.",
        )

    matching = [
        alias for alias in aliases
        if alias.get("source_namespace") == source_namespace
        and alias.get("historical_rule_id") == historical_rule_id
    ]
    if not matching:
        return RuleResolution(
            status="UNRESOLVED", **base,
            detail="No exact source-namespaced alias exists; no legacy fallback is allowed.",
        )

    applicable: list[Mapping[str, Any]] = []
    for alias in matching:
        start = _as_date(alias.get("valid_from"))
        end = _as_date(alias.get("valid_to"))
        if alias.get("valid_from") is not None and start is None:
            return RuleResolution(
                status="INVALID_ALIAS_INTERVAL", **base,
                detail="Alias valid_from is not a valid ISO date.",
            )
        if alias.get("valid_to") is not None and end is None:
            return RuleResolution(
                status="INVALID_ALIAS_INTERVAL", **base,
                detail="Alias valid_to is not a valid ISO date.",
            )
        if start is not None and effective_date < start:
            continue
        if end is not None and effective_date >= end:
            continue
        applicable.append(alias)

    if not applicable:
        return RuleResolution(
            status="ALIAS_OUT_OF_DATE", **base,
            detail="Matching alias exists, but none is valid on the requested date.",
        )

    states = {str(alias.get("resolution_status", "UNRESOLVED")).upper()
              for alias in applicable}
    if "AMBIGUOUS" in states or len(applicable) != 1:
        return RuleResolution(
            status="AMBIGUOUS", **base,
            detail="Multiple applicable aliases or an explicitly ambiguous alias exist.",
        )
    alias = applicable[0]
    alias_state = str(alias.get("resolution_status", "UNRESOLVED")).upper()
    if alias_state == "RETIRED":
        return RuleResolution(
            status="RETIRED", **base,
            detail="The matching alias is retired.",
        )
    if alias_state != "RESOLVED":
        return RuleResolution(
            status="UNRESOLVED", **base,
            detail=f"Alias resolution state is {alias_state}; RESOLVED is required.",
        )

    canonical_id = str(alias.get("canonical_rule_id") or "")
    identity = identities.get(canonical_id)
    if not canonical_id or identity is None:
        return RuleResolution(
            status="IDENTITY_MISSING", **base,
            detail="Resolved alias points to no supplied canonical identity.",
        )

    identity_status = str(identity.get("identity_status", "QUARANTINED")).upper()
    if identity_status == "RETIRED":
        return RuleResolution(
            status="RETIRED", **base, canonical_rule_id=canonical_id,
            detail="Canonical identity is retired.",
        )
    if identity_status != "ACTIVE":
        return RuleResolution(
            status="IDENTITY_QUARANTINED", **base, canonical_rule_id=canonical_id,
            detail=f"Canonical identity status is {identity_status}; ACTIVE is required.",
        )

    dated_revisions: list[Mapping[str, Any]] = []
    for revision in revisions:
        if str(revision.get("canonical_rule_id")) != canonical_id:
            continue
        start = _as_date(revision.get("effective_from"))
        end = _as_date(revision.get("effective_to"))
        if start is None:
            return RuleResolution(
                status="INVALID_REVISION_INTERVAL", **base,
                canonical_rule_id=canonical_id,
                detail="A revision has a missing or invalid effective_from date.",
            )
        if revision.get("effective_to") is not None and end is None:
            return RuleResolution(
                status="INVALID_REVISION_INTERVAL", **base,
                canonical_rule_id=canonical_id,
                detail="A revision has an invalid effective_to date.",
            )
        if end is not None and end <= start:
            return RuleResolution(
                status="INVALID_REVISION_INTERVAL", **base,
                canonical_rule_id=canonical_id,
                detail="Revision effective interval must be non-empty and half-open.",
            )
        if start <= effective_date and (end is None or effective_date < end):
            dated_revisions.append(revision)

    if not dated_revisions:
        return RuleResolution(
            status="NO_EFFECTIVE_REVISION", **base, canonical_rule_id=canonical_id,
            detail="No revision covers the requested effective date.",
        )
    if len(dated_revisions) != 1:
        return RuleResolution(
            status="AMBIGUOUS_REVISION", **base, canonical_rule_id=canonical_id,
            detail="More than one revision covers the requested effective date.",
        )

    revision = dated_revisions[0]
    definition = revision.get("definition_json")
    expected_hash = str(revision.get("definition_hash") or "").lower()
    if not isinstance(definition, Mapping) or not expected_hash:
        return RuleResolution(
            status="INVALID_REVISION_HASH", **base, canonical_rule_id=canonical_id,
            detail="Revision definition or SHA-256 digest is missing.",
        )
    try:
        actual_hash = canonical_definition_hash(definition)
    except (TypeError, ValueError):
        return RuleResolution(
            status="INVALID_REVISION_HASH", **base, canonical_rule_id=canonical_id,
            detail="Revision definition cannot be canonically serialized as JSON.",
        )
    if actual_hash != expected_hash:
        return RuleResolution(
            status="INVALID_REVISION_HASH", **base, canonical_rule_id=canonical_id,
            detail="Revision definition does not match its stored SHA-256 digest.",
        )

    try:
        revision_number = int(revision["revision_number"])
    except (KeyError, TypeError, ValueError):
        return RuleResolution(
            status="INVALID_REVISION_METADATA", **base,
            canonical_rule_id=canonical_id,
            detail="Revision number is missing or invalid.",
        )
    if revision_number < 1:
        return RuleResolution(
            status="INVALID_REVISION_METADATA", **base,
            canonical_rule_id=canonical_id,
            detail="Revision number must be positive.",
        )

    return RuleResolution(
        status="RESOLVED",
        **base,
        canonical_rule_id=canonical_id,
        revision_id=str(revision.get("id") or "") or None,
        revision_number=revision_number,
        approval_state=str(revision.get("approval_state", "REVIEW_REQUIRED")),
        definition_hash=actual_hash,
        detail="Identity and dated revision resolved. This is not legal approval or scoring authorisation.",
    )
