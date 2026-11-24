"""Versioned rule-level scope registry for the RJSC-only assessment.

Scope is separate from statutory validity, applicability, evidence sufficiency,
and independent legal approval. Out-of-scope means excluded from this product
assessment, never that the underlying legal duty is inapplicable or waived.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_SCOPE_PATH = Path(__file__).with_name("rjsc_scope_registry_v1.json")
_EXPECTED_SCHEMA = "nlc.rule-assessment-scope"
_EXPECTED_ASSESSMENT_SCOPE = "RJSC_ONLY"
_ALLOWED_SCOPE_CLASSES = frozenset({"IN_SCOPE_RJSC", "OUT_OF_SCOPE"})


def _load_scope_registry() -> tuple[str, dict[str, dict[str, Any]]]:
    payload = json.loads(_SCOPE_PATH.read_text(encoding="utf-8"))
    if payload.get("schema") != _EXPECTED_SCHEMA:
        raise RuntimeError("RJSC scope registry schema mismatch")
    if payload.get("assessment_scope") != _EXPECTED_ASSESSMENT_SCOPE:
        raise RuntimeError("RJSC scope registry must declare RJSC_ONLY")
    version = payload.get("scope_version")
    if not isinstance(version, str) or not version.strip():
        raise RuntimeError("RJSC scope registry version is required")
    rows = payload.get("rules")
    if not isinstance(rows, list) or len(rows) != payload.get("expected_rule_count"):
        raise RuntimeError("RJSC scope registry rule count mismatch")

    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise RuntimeError("RJSC scope registry rows must be objects")
        rule_id = row.get("rule_id")
        scope_class = row.get("scope_class")
        if not isinstance(rule_id, str) or not rule_id.strip():
            raise RuntimeError("RJSC scope registry contains an empty rule ID")
        if rule_id in result:
            raise RuntimeError(f"Duplicate RJSC scope classification: {rule_id}")
        if scope_class not in _ALLOWED_SCOPE_CLASSES:
            raise RuntimeError(f"Unknown RJSC scope class for {rule_id}: {scope_class}")
        expected_eligibility = scope_class == "IN_SCOPE_RJSC"
        for gate in ("score_eligible", "risk_eligible", "rescue_eligible", "release_eligible"):
            if row.get(gate) is not expected_eligibility:
                raise RuntimeError(f"Inconsistent {gate} for RJSC scope rule {rule_id}")
        if not row.get("rationale") or not row.get("boundary"):
            raise RuntimeError(f"RJSC scope rationale/boundary missing for {rule_id}")
        result[rule_id] = row
    return version, result


RJSC_SCOPE_VERSION, RJSC_RULE_SCOPE = _load_scope_registry()
RJSC_IN_SCOPE_RULE_IDS = frozenset(
    rule_id for rule_id, row in RJSC_RULE_SCOPE.items()
    if row["scope_class"] == "IN_SCOPE_RJSC"
)
RJSC_OUT_OF_SCOPE_RULE_IDS = frozenset(RJSC_RULE_SCOPE) - RJSC_IN_SCOPE_RULE_IDS


def is_rjsc_rule_in_scope(rule_id: str) -> bool:
    """Fail closed: only an explicitly classified IN_SCOPE_RJSC ID is in scope."""
    row = RJSC_RULE_SCOPE.get(rule_id)
    return bool(row and row["scope_class"] == "IN_SCOPE_RJSC")


def assert_rjsc_scope_parity(canonical_rule_ids) -> None:
    """Require exact identity parity; unknown/missing rules block release."""
    canonical = frozenset(canonical_rule_ids)
    classified = frozenset(RJSC_RULE_SCOPE)
    if canonical != classified:
        raise RuntimeError(
            "RJSC scope identity parity failure: "
            f"unclassified={sorted(canonical - classified)} "
            f"orphaned={sorted(classified - canonical)}"
        )



def filter_rjsc_items(items, *, rule_id_getter=lambda item: getattr(item, "rule_id", None)):
    """Return only items explicitly admitted by this immutable scope version.

    Unknown IDs fail closed. The function does not mutate or reinterpret items.
    """
    return [
        item for item in items
        if isinstance(rule_id_getter(item), str)
        and is_rjsc_rule_in_scope(rule_id_getter(item))
    ]


def rjsc_scope_identity() -> dict[str, Any]:
    """Stable identity material shared by every RJSC decision and audit hash."""
    return {
        "assessment_scope": "RJSC_ONLY",
        "scope_version": RJSC_SCOPE_VERSION,
        "in_scope_rule_ids": sorted(RJSC_IN_SCOPE_RULE_IDS),
        "out_of_scope_rule_ids": sorted(RJSC_OUT_OF_SCOPE_RULE_IDS),
    }
