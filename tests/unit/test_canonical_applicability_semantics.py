"""Regression tests for the canonical three-state applicability contract."""

from canonical_architecture.evaluator import evaluate_rule
from canonical_architecture.lifecycle_engine import CanonicalLifecycleEngine
from canonical_architecture.statutory_rules import (
    RuleState,
    STATUTORY_RULE_REGISTRY,
    evaluate_applicability,
)


def test_inc005_uses_a_typed_foreign_shareholder_fact():
    rule = STATUTORY_RULE_REGISTRY["INC-005"]

    assert rule.applies_if == "has_foreign_shareholder"
    assert evaluate_applicability(rule, {}) is RuleState.UNKNOWN
    assert evaluate_applicability(rule, {"has_foreign_shareholder": False}) is RuleState.NOT_APPLICABLE
    assert evaluate_applicability(rule, {"has_foreign_shareholder": True}) is None
    assert evaluate_applicability(rule, {"has_foreign_shareholder": "true"}) is RuleState.UNKNOWN


def test_inc006_requires_all_three_screening_conditions():
    rule = STATUTORY_RULE_REGISTRY["INC-006"]

    assert rule.applies_if_all == ("has_foreign_shareholder", "bida_registered")
    assert rule.applies_if_lt == (("remittance_amount_usd", 50000),)
    assert evaluate_applicability(
        rule,
        {
            "has_foreign_shareholder": True,
            "bida_registered": True,
            "remittance_amount_usd": 49999.99,
        },
    ) is None


def test_inc006_missing_required_fact_is_unknown_not_not_applicable():
    rule = STATUTORY_RULE_REGISTRY["INC-006"]

    assert evaluate_applicability(
        rule,
        {"has_foreign_shareholder": True, "bida_registered": True},
    ) is RuleState.UNKNOWN


def test_inc006_false_predicate_is_not_applicable_even_if_another_fact_is_missing():
    rule = STATUTORY_RULE_REGISTRY["INC-006"]

    assert evaluate_applicability(
        rule,
        {"has_foreign_shareholder": False},
    ) is RuleState.NOT_APPLICABLE


def test_inc006_threshold_boundary_is_not_applicable():
    rule = STATUTORY_RULE_REGISTRY["INC-006"]
    for amount in (50000, 50000.01, 100000):
        assert evaluate_applicability(
            rule,
            {
                "has_foreign_shareholder": True,
                "bida_registered": True,
                "remittance_amount_usd": amount,
            },
        ) is RuleState.NOT_APPLICABLE


def test_inc006_boolean_or_non_numeric_remittance_is_unknown():
    rule = STATUTORY_RULE_REGISTRY["INC-006"]
    for amount in (True, "49999", None):
        assert evaluate_applicability(
            rule,
            {
                "has_foreign_shareholder": True,
                "bida_registered": True,
                "remittance_amount_usd": amount,
            },
        ) is RuleState.UNKNOWN


def test_descriptive_tax_applicability_is_not_executed_as_a_fact_key():
    rule = STATUTORY_RULE_REGISTRY["TAX-002"]

    assert rule.applicability_unresolved is True
    assert rule.applicability_notes.startswith("CONDITIONAL")
    assert evaluate_applicability(rule, {}) is RuleState.UNKNOWN
    finding = evaluate_rule(rule, {}, {})
    assert finding.state is RuleState.UNKNOWN


def test_descriptive_charge_and_membership_scope_remain_unknown():
    for rule_id in ("CHG-001", "MEM-001"):
        rule = STATUTORY_RULE_REGISTRY[rule_id]
        assert rule.applicability_unresolved is True
        assert evaluate_applicability(rule, {}) is RuleState.UNKNOWN


def test_canonical_evaluator_returns_unknown_for_missing_inc005_fact():
    rule = STATUTORY_RULE_REGISTRY["INC-005"]
    finding = evaluate_rule(rule, {}, {})
    assert finding.state is RuleState.UNKNOWN
    assert "applicability unresolved" in finding.reason


def test_lifecycle_and_canonical_evaluator_share_inc005_applicability_states():
    engine = CanonicalLifecycleEngine()

    assert engine.evaluate_finding("INC-005", {}) is RuleState.UNKNOWN
    assert engine.evaluate_finding(
        "INC-005", {"has_foreign_shareholder": False}
    ) is RuleState.NOT_APPLICABLE
    assert engine.evaluate_finding(
        "INC-005",
        {
            "has_foreign_shareholder": True,
            "INC-005:SUBSCRIPTION_OR_ALLOTMENT_RECORD": True,
            "INC-005:AD_BANK_ENCASHMENT_CERTIFICATE_OR_PERMITTED_FC_ACCOUNT_EVIDENCE": True,
            "INC-005:REMITTANCE_IDENTITY_AND_BANK_PROVENANCE": True,
            "INC-005:CURRENT_BANGLADESH_BANK_CIRCULAR_VERSION": True,
        },
    ) is RuleState.COMPLIANT


def test_lifecycle_preserves_unknown_for_unstructured_tax_scope():
    engine = CanonicalLifecycleEngine()
    assert engine.evaluate_finding(
        "TAX-002", {"DOCUMENTARY_EVIDENCE": True}
    ) is RuleState.UNKNOWN



def test_lbr001_missing_exception_facts_keep_applicability_unknown():
    rule = STATUTORY_RULE_REGISTRY["LBR-001"]

    assert evaluate_applicability(
        rule, {"LABOUR_LICENSE_SCOPE_VERIFIED": True}
    ) is RuleState.UNKNOWN
    assert evaluate_applicability(
        rule,
        {
            "LABOUR_LICENSE_SCOPE_VERIFIED": True,
            "VERIFIED_NON_APPLICABLE_ESTABLISHMENT_CATEGORY": False,
            "VERIFIED_NO_APPLICABLE_DIRECTION": False,
        },
    ) is None


def test_verified_lbr001_exception_makes_rule_not_applicable():
    rule = STATUTORY_RULE_REGISTRY["LBR-001"]

    assert evaluate_applicability(
        rule,
        {
            "LABOUR_LICENSE_SCOPE_VERIFIED": True,
            "VERIFIED_NON_APPLICABLE_ESTABLISHMENT_CATEGORY": True,
            "VERIFIED_NO_APPLICABLE_DIRECTION": False,
        },
    ) is RuleState.NOT_APPLICABLE



def test_inc006_canonical_and_lifecycle_evaluators_have_identical_applicability_results():
    """Facts and evidence are separate inputs; both paths must agree on INC-006."""
    rule = STATUTORY_RULE_REGISTRY["INC-006"]
    engine = CanonicalLifecycleEngine()
    cases = (
        ({}, RuleState.UNKNOWN),
        (
            {"has_foreign_shareholder": False},
            RuleState.NOT_APPLICABLE,
        ),
        (
            {
                "has_foreign_shareholder": True,
                "bida_registered": True,
            },
            RuleState.UNKNOWN,
        ),
        (
            {
                "has_foreign_shareholder": True,
                "bida_registered": True,
                "remittance_amount_usd": "49999",
            },
            RuleState.UNKNOWN,
        ),
        (
            {
                "has_foreign_shareholder": True,
                "bida_registered": True,
                "remittance_amount_usd": 50000,
            },
            RuleState.NOT_APPLICABLE,
        ),
        (
            {
                "has_foreign_shareholder": True,
                "bida_registered": True,
                "remittance_amount_usd": 49999.99,
            },
            RuleState.UNKNOWN,
        ),
    )

    for facts, expected in cases:
        canonical = evaluate_rule(rule, facts, {})
        lifecycle = engine.evaluate_finding("INC-006", {}, facts=facts)
        assert canonical.state is expected
        assert lifecycle is expected
        assert lifecycle is canonical.state


def test_inc006_lifecycle_does_not_treat_applicability_facts_as_evidence():
    engine = CanonicalLifecycleEngine()
    facts = {
        "has_foreign_shareholder": True,
        "bida_registered": True,
        "remittance_amount_usd": 49999,
    }

    assert engine.evaluate_finding("INC-006", {}, facts=facts) is RuleState.UNKNOWN
    assert engine.evaluate_finding(
        "INC-006",
        {"has_foreign_shareholder": True},
        facts=facts,
    ) is RuleState.UNKNOWN


def test_inc006_submit_new_evidence_accepts_separate_applicability_facts():
    engine = CanonicalLifecycleEngine()
    facts = {
        "has_foreign_shareholder": True,
        "bida_registered": True,
        "remittance_amount_usd": 49999,
    }

    assert engine.submit_new_evidence(
        "INC-006",
        {},
        facts=facts,
        verification_recorded=True,
    ) is RuleState.UNKNOWN
