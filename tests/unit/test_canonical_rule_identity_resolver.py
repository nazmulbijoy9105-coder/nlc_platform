from datetime import date

import pytest

from app.rule_engine.canonical_identity import (
    canonical_definition_hash,
    resolve_rule_identity,
)


NS = "engine-build:abc123"
LEGACY = "INC-001"
CANONICAL = "00000000-0000-0000-0000-000000000001"
REVISION = "00000000-0000-0000-0000-000000000002"
DEFINITION = {"provision": "Companies Act 1994, s. 81", "obligation": "hold_agm"}
REVISION_ROW = {
    "id": REVISION,
    "canonical_rule_id": CANONICAL,
    "revision_number": 1,
    "effective_from": "2020-01-01",
    "effective_to": None,
    "definition_json": DEFINITION,
    "definition_hash": canonical_definition_hash(DEFINITION),
    "approval_state": "REVIEW_REQUIRED",
}
ALIAS_ROW = {
    "source_namespace": NS,
    "historical_rule_id": LEGACY,
    "canonical_rule_id": CANONICAL,
    "resolution_status": "RESOLVED",
    "valid_from": "2020-01-01",
    "valid_to": None,
}
IDENTITIES = {CANONICAL: {"identity_status": "ACTIVE"}}


def resolve(**overrides):
    args = {
        "source_namespace": NS,
        "historical_rule_id": LEGACY,
        "effective_date": date(2026, 1, 1),
        "aliases": [ALIAS_ROW],
        "identities": IDENTITIES,
        "revisions": [REVISION_ROW],
    }
    args.update(overrides)
    return resolve_rule_identity(**args)


def test_resolves_exact_namespaced_alias_and_effective_revision():
    result = resolve()
    assert result.status == "RESOLVED"
    assert result.canonical_rule_id == CANONICAL
    assert result.revision_id == REVISION
    assert result.revision_number == 1


def test_resolution_is_not_legal_or_scoring_approval():
    result = resolve()
    assert result.resolved
    assert result.approval_state == "REVIEW_REQUIRED"
    assert "not legal approval" in result.detail


def test_does_not_fallback_to_bare_legacy_identifier():
    result = resolve(source_namespace="different-engine-build")
    assert result.status == "UNRESOLVED"


def test_missing_alias_is_unresolved():
    result = resolve(aliases=[])
    assert result.status == "UNRESOLVED"


def test_multiple_applicable_aliases_are_ambiguous_even_same_target():
    result = resolve(aliases=[ALIAS_ROW, dict(ALIAS_ROW)])
    assert result.status == "AMBIGUOUS"


def test_explicit_ambiguous_alias_is_ambiguous():
    alias = dict(ALIAS_ROW, resolution_status="AMBIGUOUS")
    result = resolve(aliases=[alias])
    assert result.status == "AMBIGUOUS"


def test_unresolved_alias_never_resolves():
    alias = dict(ALIAS_ROW, resolution_status="UNRESOLVED")
    result = resolve(aliases=[alias])
    assert result.status == "UNRESOLVED"


def test_retired_alias_never_resolves():
    alias = dict(ALIAS_ROW, resolution_status="RETIRED")
    result = resolve(aliases=[alias])
    assert result.status == "RETIRED"


def test_alias_validity_uses_half_open_end_date():
    result = resolve(effective_date=date(2026, 1, 1),
                     aliases=[dict(ALIAS_ROW, valid_to="2026-01-01")])
    assert result.status == "ALIAS_OUT_OF_DATE"


def test_quarantined_identity_never_resolves():
    result = resolve(identities={CANONICAL: {"identity_status": "QUARANTINED"}})
    assert result.status == "IDENTITY_QUARANTINED"


def test_retired_identity_never_resolves():
    result = resolve(identities={CANONICAL: {"identity_status": "RETIRED"}})
    assert result.status == "RETIRED"


def test_unknown_identity_reference_fails_closed():
    alias = dict(ALIAS_ROW, canonical_rule_id="missing")
    result = resolve(aliases=[alias])
    assert result.status == "IDENTITY_MISSING"


def test_missing_effective_revision_fails_closed():
    result = resolve(revisions=[])
    assert result.status == "NO_EFFECTIVE_REVISION"


def test_overlapping_effective_revisions_are_ambiguous():
    second = dict(REVISION_ROW, id="revision-2", revision_number=2,
                  effective_from="2025-01-01")
    result = resolve(revisions=[REVISION_ROW, second])
    assert result.status == "AMBIGUOUS_REVISION"


def test_revision_hash_tampering_fails_closed():
    tampered = dict(REVISION_ROW, definition_json={"provision": "changed"})
    result = resolve(revisions=[tampered])
    assert result.status == "INVALID_REVISION_HASH"


def test_revision_missing_digest_fails_closed():
    missing = dict(REVISION_ROW, definition_hash="")
    result = resolve(revisions=[missing])
    assert result.status == "INVALID_REVISION_HASH"


def test_revision_end_date_is_exclusive():
    result = resolve(
        effective_date=date(2030, 1, 1),
        revisions=[dict(REVISION_ROW, effective_to="2030-01-01")],
    )
    assert result.status == "NO_EFFECTIVE_REVISION"


def test_definition_hash_is_key_order_independent():
    assert canonical_definition_hash({"a": 1, "b": 2}) == canonical_definition_hash(
        {"b": 2, "a": 1}
    )


def test_invalid_alias_date_fails_closed():
    result = resolve(aliases=[dict(ALIAS_ROW, valid_from="not-a-date")])
    assert result.status == "INVALID_ALIAS_INTERVAL"


def test_invalid_revision_interval_fails_closed():
    bad = dict(REVISION_ROW, effective_from="2026-02-01",
               effective_to="2026-01-01")
    result = resolve(revisions=[bad])
    assert result.status == "INVALID_REVISION_INTERVAL"


@pytest.mark.parametrize("source_namespace,historical_rule_id", [("", LEGACY), (NS, "")])
def test_empty_lookup_key_is_rejected(source_namespace, historical_rule_id):
    result = resolve(source_namespace=source_namespace,
                     historical_rule_id=historical_rule_id)
    assert result.status == "INVALID_LOOKUP_KEY"
