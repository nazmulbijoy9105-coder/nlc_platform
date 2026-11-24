from datetime import date, datetime

import pytest

from app.rule_engine.finding_context import (
    FindingContextCatalog,
    RuleFindingContext,
)


def _context(rule_id="AGM-001", **overrides):
    values = {
        "historical_rule_id": rule_id,
        "source_namespace": "nlc-rule-engine:stable-v2",
        "jurisdiction": "BD",
        "effective_date": date(2026, 1, 1),
        "effective_date_basis": "Counsel-reviewed operative-date determination",
        "effective_date_source_ref": "legal-register:BD:AGM-001:revision-1",
        "required_fact_keys": ("agm_held", "agm_date"),
        "evidence_roles_by_fact_key": {
            "agm_held": "AGM_OCCURRENCE",
            "agm_date": "AGM_DATE",
        },
    }
    values.update(overrides)
    return RuleFindingContext(**values)


def test_context_accepts_explicit_trusted_legal_date_and_evidence_contract():
    context = _context()
    assert context.effective_date == date(2026, 1, 1)
    assert context.required_fact_keys == ("agm_held", "agm_date")
    assert context.evidence_roles_by_fact_key["agm_held"] == "AGM_OCCURRENCE"


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_namespace", ""),
        ("jurisdiction", ""),
        ("effective_date_basis", ""),
        ("effective_date_source_ref", ""),
        ("historical_rule_id", ""),
    ],
)
def test_context_rejects_missing_authoritative_metadata(field, value):
    with pytest.raises(ValueError):
        _context(**{field: value})


@pytest.mark.parametrize(
    "value",
    [None, "2026-01-01", datetime(2026, 1, 1, 12, 0)],
)
def test_context_rejects_missing_or_non_date_effective_date(value):
    with pytest.raises(ValueError, match="effective_date"):
        _context(effective_date=value)


def test_context_rejects_empty_and_duplicate_required_fact_keys():
    with pytest.raises(ValueError, match="required_fact_keys entry"):
        _context(required_fact_keys=("agm_held", " "))
    with pytest.raises(ValueError, match="duplicates"):
        _context(required_fact_keys=("agm_held", "agm_held"))


def test_context_rejects_evidence_roles_for_undeclared_facts():
    with pytest.raises(ValueError, match="declared required_fact_keys"):
        _context(evidence_roles_by_fact_key={"unrelated_fact": "ROLE"})


def test_context_exposes_immutable_evidence_role_mapping():
    context = _context()
    with pytest.raises(TypeError):
        context.evidence_roles_by_fact_key["agm_held"] = "CHANGED"


def test_catalog_requires_exact_coverage_for_emitted_findings():
    catalog = FindingContextCatalog(
        catalog_version="bd-rule-context-v1",
        contexts_by_rule_id={"AGM-001": _context()},
    )
    assert set(catalog.require_exact_coverage(["AGM-001"])) == {"AGM-001"}


def test_catalog_rejects_missing_context_instead_of_partial_binding():
    catalog = FindingContextCatalog(
        catalog_version="bd-rule-context-v1",
        contexts_by_rule_id={"AGM-001": _context()},
    )
    with pytest.raises(ValueError, match="missing contexts: INC-002"):
        catalog.require_exact_coverage(["AGM-001", "INC-002"])


def test_catalog_rejects_unused_context_to_expose_stale_configuration():
    catalog = FindingContextCatalog(
        catalog_version="bd-rule-context-v1",
        contexts_by_rule_id={
            "AGM-001": _context(),
            "INC-002": _context("INC-002"),
        },
    )
    with pytest.raises(ValueError, match="unused contexts: INC-002"):
        catalog.require_exact_coverage(["AGM-001"])


def test_catalog_rejects_duplicate_emitted_rule_ids():
    catalog = FindingContextCatalog(
        catalog_version="bd-rule-context-v1",
        contexts_by_rule_id={"AGM-001": _context()},
    )
    with pytest.raises(ValueError, match="duplicate rule IDs"):
        catalog.require_exact_coverage(["AGM-001", "AGM-001"])


def test_catalog_rejects_context_key_that_does_not_match_rule_identity():
    with pytest.raises(ValueError, match="does not match"):
        FindingContextCatalog(
            catalog_version="bd-rule-context-v1",
            contexts_by_rule_id={"INC-002": _context("AGM-001")},
        )


def test_catalog_mapping_is_immutable():
    catalog = FindingContextCatalog(
        catalog_version="bd-rule-context-v1",
        contexts_by_rule_id={"AGM-001": _context()},
    )
    with pytest.raises(TypeError):
        catalog.contexts_by_rule_id["INC-002"] = _context("INC-002")
