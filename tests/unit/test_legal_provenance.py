"""Legal provenance governance: no runtime shortcut may self-approve a rule."""

from copy import deepcopy
from datetime import date
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.api.legal_provenance import MappingBulkCreate, MappingCreate, SourceCreate, _source_state
from app.services.legal_deadline_engine import (
    DeadlineRule,
    calculate_deadline,
    calculate_deadline_candidate,
)
from canonical_architecture.legal_reconciliation import (
    LEGAL_RECONCILIATION,
    get_reconciliation_status,
    verify_provision,
)
from canonical_architecture.statutory_rules import (
    ProvisionStatus,
    STATUTORY_RULE_REGISTRY,
)


@pytest.fixture(autouse=True)
def restore_legal_reconciliation_registry():
    snapshot = deepcopy(LEGAL_RECONCILIATION)
    yield
    LEGAL_RECONCILIATION.clear()
    LEGAL_RECONCILIATION.update(snapshot)


def test_all_rules_start_unverified_and_reconciled():
    """No statutory rule is verified without a reviewed provenance change."""
    assert set(LEGAL_RECONCILIATION) == set(STATUTORY_RULE_REGISTRY)
    assert len(LEGAL_RECONCILIATION) == 85
    for rule_id, record in LEGAL_RECONCILIATION.items():
        assert record["verified"] is False, rule_id
        assert record["verified_by"] is None, rule_id
        assert record["verified_at"] is None, rule_id
        assert record["source"] is None, rule_id
        assert get_reconciliation_status(rule_id) == "RECONCILE"
        assert STATUTORY_RULE_REGISTRY[rule_id].provision_status is ProvisionStatus.RECONCILE


@pytest.mark.parametrize(
    ("verified_by", "source"),
    [
        ("", "https://bdlaws.minlaw.gov.bd/act-788.html"),
        ("admin@nlc.com", "Companies Act 1994, Section 11 (Verified)"),
        ("independent counsel", "a plausible but unauditable source string"),
        ("admin@nlc.com", "https://example.com/claims-to-be-a-statute"),
    ],
)
def test_runtime_verification_cannot_promote_a_rule(verified_by, source):
    """Free-form runtime inputs cannot replace independent legal review."""
    before = deepcopy(LEGAL_RECONCILIATION["INC-001"])
    rule_before = STATUTORY_RULE_REGISTRY["INC-001"]
    assert verify_provision("INC-001", verified_by=verified_by, source=source) is False
    assert LEGAL_RECONCILIATION["INC-001"] == before
    assert STATUTORY_RULE_REGISTRY["INC-001"] is rule_before
    assert get_reconciliation_status("INC-001") == "RECONCILE"


def test_unknown_rule_id_is_not_silently_reported_as_reconciled():
    with pytest.raises(KeyError, match="unknown statutory rule"):
        get_reconciliation_status("FAKE-999")


# Product-owner infrastructure tests. These keep operational approval separate
# from statutory verification and make provisional arithmetic explicit.

def test_source_reference_state_does_not_claim_artifact_capture():
    reference_only = SimpleNamespace(artifact_sha256=None, artifact_uri=None)
    hash_reference = SimpleNamespace(
        artifact_sha256="a" * 64,
        artifact_uri="https://storage.example.test/legal/act.pdf",
    )
    assert _source_state(reference_only) == "REFERENCE_ONLY"
    assert _source_state(hash_reference) == "ARTIFACT_REFERENCE_RECORDED"


def test_source_registration_requires_https_and_paired_artifact_fields():
    base = {
        "source_key": "BD-CA-1994",
        "instrument_title": "Companies Act 1994",
        "issuing_authority": "Government of Bangladesh",
        "instrument_type": "ACT",
        "official_url": "https://bdlaws.minlaw.gov.bd/example",
        "citation": "Companies Act 1994",
        "version_label": "current-consolidated",
    }
    SourceCreate(**base)
    with pytest.raises(ValidationError):
        SourceCreate(**{**base, "official_url": "http://example.com/act"})
    with pytest.raises(ValidationError):
        SourceCreate(**{**base, "artifact_sha256": "a" * 64})


def _deadline_rule(*, approved: bool = False, effective_to: date | None = None):
    return DeadlineRule(
        rule_id="AGM-001",
        source_citation="Companies Act 1994, section-specific citation",
        source_version="test-v1",
        effective_from=date(2020, 1, 1),
        effective_to=effective_to,
        offset=30,
        unit="DAYS",
        approved=approved,
    )


def test_date_preview_does_not_require_or_claim_rule_or_fact_approval():
    rule = _deadline_rule(approved=False)
    trigger = date(2026, 1, 1)
    assert calculate_deadline(
        rule,
        trigger_date=trigger,
        applicable=True,
        trigger_evidence_verified=False,
    ) is None
    assert calculate_deadline_candidate(
        rule,
        trigger_date=trigger,
        applicable=True,
    ) == date(2026, 1, 31)


def test_date_preview_preserves_unknown_or_out_of_effective_period():
    rule = _deadline_rule(approved=True, effective_to=date(2025, 12, 31))
    assert calculate_deadline_candidate(
        rule,
        trigger_date=date(2026, 1, 1),
        applicable=True,
    ) is None
    assert calculate_deadline_candidate(
        rule,
        trigger_date=date(2025, 1, 1),
        applicable=False,
    ) is None


def test_clear_day_preview_excludes_trigger_day_and_honours_holidays():
    rule = DeadlineRule(
        rule_id="AGM-CLR-001",
        source_citation="Fixture provision",
        source_version="fixture-v1",
        effective_from=date(2020, 1, 1),
        effective_to=None,
        offset=3,
        unit="CLEAR_DAYS",
        adjustment="NONE",
        approved=False,
    )
    assert calculate_deadline_candidate(
        rule,
        trigger_date=date(2026, 1, 1),
        applicable=True,
    ) == date(2026, 1, 5)


def test_customer_rule_provenance_route_requires_authentication_not_super_admin():
    from app.core.dependencies import get_current_user
    from app.api.legal_provenance import router

    route = next(
        route for route in router.routes
        if getattr(route, "path", None) == "/legal-provenance/rules/{rule_id}"
    )
    dependency_calls = {dependency.call for dependency in route.dependant.dependencies}
    assert get_current_user in dependency_calls
    assert all("require_roles" not in getattr(call, "__name__", "") for call in dependency_calls)


def test_source_registry_listing_remains_super_admin_only():
    from app.api.legal_provenance import router

    route = next(
        route for route in router.routes
        if getattr(route, "path", None) == "/legal-provenance/sources"
    )
    assert route.dependant.dependencies


def test_bd_starter_catalog_has_unique_official_source_version_keys():
    from app.api.legal_provenance import BD_STARTER_SOURCE_CATALOG

    assert len(BD_STARTER_SOURCE_CATALOG) == 10
    identities = [
        (source["source_key"], source["version_label"])
        for source in BD_STARTER_SOURCE_CATALOG
    ]
    assert len(identities) == len(set(identities))
    for source in BD_STARTER_SOURCE_CATALOG:
        assert source["source_key"].startswith("BD-")
        assert source["jurisdiction"] == "BD"
        assert source["official_url"].startswith("https://")
        assert source["instrument_title"]
        assert source["issuing_authority"]
        assert source["citation"]
        assert source["version_label"]
        # A catalogue reference is not evidence of archived source bytes.
        assert "artifact_sha256" not in source
        assert "artifact_uri" not in source


def test_starter_source_import_endpoint_is_super_admin_only():
    from app.api.legal_provenance import router
    from app.core.dependencies import get_current_user

    route = next(
        route for route in router.routes
        if getattr(route, "path", None) == "/legal-provenance/starter-sources/register"
    )
    dependencies = route.dependant.dependencies
    assert get_current_user in {dependency.call for dependency in dependencies}
    assert any(
        getattr(dependency.call, "__name__", "") == "role_checker"
        or "require_roles" in getattr(dependency.call, "__qualname__", "")
        for dependency in dependencies
    )


def test_bulk_mapping_request_is_bounded_and_requires_at_least_one_row():
    from uuid import uuid4

    mapping = MappingCreate(
        rule_id="AGM-001",
        source_id=uuid4(),
        mapping_kind="RULE_BASIS",
        provision_citation="Companies Act 1994, section 81",
        rationale="Maps the annual general meeting obligation to its statutory basis.",
    )
    assert len(MappingBulkCreate(mappings=[mapping]).mappings) == 1
    with pytest.raises(ValidationError):
        MappingBulkCreate(mappings=[])
    with pytest.raises(ValidationError):
        MappingBulkCreate(mappings=[mapping] * 101)


def test_bulk_mapping_endpoint_is_super_admin_only_and_actor_bound():
    from app.api.legal_provenance import router
    from app.core.dependencies import get_current_user

    route = next(
        route for route in router.routes
        if getattr(route, "path", None) == "/legal-provenance/mappings/bulk"
    )
    dependencies = route.dependant.dependencies
    assert get_current_user in {dependency.call for dependency in dependencies}
    assert any(
        getattr(dependency.call, "__name__", "") == "role_checker"
        or "require_roles" in getattr(dependency.call, "__qualname__", "")
        for dependency in dependencies
    )
