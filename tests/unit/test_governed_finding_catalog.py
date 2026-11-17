from datetime import date, datetime, timezone
from uuid import UUID

import pytest

from app.rule_engine.finding_context import RuleFindingContext
from app.rule_engine.governed_finding_catalog import (
    GovernedFindingContextCatalog,
    GovernedRuleFindingContext,
    finding_context_digest,
)


AUTHOR = "00000000-0000-0000-0000-000000000001"
REVIEWER = "00000000-0000-0000-0000-000000000002"
AUTHORED_AT = datetime(2026, 1, 1, tzinfo=timezone.utc)
REVIEWED_AT = datetime(2026, 1, 2, tzinfo=timezone.utc)


def _context(rule_id="AGM-001", **changes):
    values = {
        "historical_rule_id": rule_id,
        "source_namespace": "nlc-rule-engine:stable-v2",
        "jurisdiction": "BD",
        "effective_date": date(2026, 1, 1),
        "effective_date_basis": "Reviewed legal register determination",
        "effective_date_source_ref": "legal-register:BD:AGM-001:v1",
        "required_fact_keys": ("agm_held",),
        "evidence_roles_by_fact_key": {"agm_held": "AGM_OCCURRENCE"},
    }
    values.update(changes)
    return RuleFindingContext(**values)


def _entry(context=None, **changes):
    selected = context or _context()
    values = {
        "context": selected,
        "source_instrument": "Companies Act 1994",
        "source_provision": "Section 81",
        "authored_by": AUTHOR,
        "authored_at": AUTHORED_AT,
    }
    values.update(changes)
    return GovernedRuleFindingContext(**values)


def _approved(context=None, **changes):
    selected = context or _context()
    values = {
        "context": selected,
        "source_instrument": "Companies Act 1994",
        "source_provision": "Section 81",
        "authored_by": AUTHOR,
        "authored_at": AUTHORED_AT,
        "review_status": "APPROVED",
        "reviewed_by": REVIEWER,
        "reviewed_at": REVIEWED_AT,
        "review_basis": "Independent counsel review record REF-001",
        "reviewed_context_sha256": finding_context_digest(selected),
    }
    values.update(changes)
    return GovernedRuleFindingContext(**values)


def test_review_required_context_is_not_usable():
    entry = _entry()
    assert entry.is_usable_for_binding is False


def test_approved_context_requires_independent_reviewer_and_exact_digest():
    entry = _approved()
    assert entry.is_usable_for_binding is True
    assert entry.reviewed_context_sha256 == finding_context_digest(entry.context)


def test_author_cannot_approve_own_context():
    with pytest.raises(ValueError, match="independent"):
        _approved(reviewed_by=AUTHOR)


def test_approval_rejects_context_digest_mismatch():
    with pytest.raises(ValueError, match="digest"):
        _approved(reviewed_context_sha256="a" * 64)


def test_approval_rejects_review_timestamp_before_authorship():
    with pytest.raises(ValueError, match="precede"):
        _approved(reviewed_at=datetime(2025, 12, 31, tzinfo=timezone.utc))


def test_approval_requires_timezone_aware_timestamps():
    with pytest.raises(ValueError, match="timezone-aware"):
        _entry(authored_at=datetime(2026, 1, 1))


def test_rejected_context_is_never_usable():
    entry = _entry(
        review_status="REJECTED",
        reviewed_by=REVIEWER,
        reviewed_at=REVIEWED_AT,
        review_basis="Rejected by independent counsel",
    )
    assert entry.is_usable_for_binding is False


def test_unreviewed_entry_cannot_smuggle_review_metadata():
    with pytest.raises(ValueError, match="cannot carry legal-review fields"):
        _entry(reviewed_by=REVIEWER)


def test_catalog_rejects_any_emitted_context_not_approved():
    catalog = GovernedFindingContextCatalog(
        "bd-context-v1",
        {"AGM-001": _entry()},
    )
    with pytest.raises(ValueError, match="not independently legally approved"):
        catalog.require_approved_coverage(["AGM-001"])


def test_catalog_returns_only_exact_approved_coverage():
    catalog = GovernedFindingContextCatalog(
        "bd-context-v1",
        {"AGM-001": _approved()},
    )
    contexts = catalog.require_approved_coverage(["AGM-001"])
    assert contexts["AGM-001"].historical_rule_id == "AGM-001"


def test_catalog_rejects_partial_coverage():
    catalog = GovernedFindingContextCatalog(
        "bd-context-v1",
        {"AGM-001": _approved()},
    )
    with pytest.raises(ValueError, match="missing contexts: INC-002"):
        catalog.require_approved_coverage(["AGM-001", "INC-002"])


def test_catalog_mapping_and_returned_context_map_are_immutable():
    catalog = GovernedFindingContextCatalog(
        "bd-context-v1",
        {"AGM-001": _approved()},
    )
    with pytest.raises(TypeError):
        catalog.entries_by_rule_id["INC-002"] = _approved(_context("INC-002"))
    contexts = catalog.require_approved_coverage(["AGM-001"])
    with pytest.raises(TypeError):
        contexts["INC-002"] = _context("INC-002")


def test_context_mutation_after_approval_changes_digest_and_is_detected():
    original = _context()
    approved = _approved(original)
    changed = _context(effective_date=date(2026, 2, 1))
    with pytest.raises(ValueError, match="digest"):
        _approved(changed, reviewed_context_sha256=approved.reviewed_context_sha256)


def test_actor_ids_are_canonical_uuids():
    with pytest.raises(ValueError, match="UUID"):
        _entry(authored_by="not-a-user-id")
