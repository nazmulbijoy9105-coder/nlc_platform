"""Structural safeguards for unresolved applicability-model entries."""

from canonical_architecture.applicability_model import APPLICABILITY_REGISTRY


def test_applicability_registry_count_is_explicit_candidate_inventory():
    # This is a count of candidate mappings, not legally verified rules.
    assert len(APPLICABILITY_REGISTRY) == 41


def test_dir_007_does_not_claim_universal_scope_or_verified_deadline():
    rule = APPLICABILITY_REGISTRY["DIR-007"]
    assert rule.applies_to == ("UNCONFIRMED_REQUIRES_COUNSEL_MAPPING",)
    assert rule.conditions == ("director_appointed",)
    assert "UNRESOLVED" in rule.notes
    assert "Do not infer a filing breach" in rule.notes
