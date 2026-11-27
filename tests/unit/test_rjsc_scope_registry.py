from datetime import date

import pytest
from canonical_architecture.rjsc_scope import (
    RJSC_IN_SCOPE_RULE_IDS,
    RJSC_OUT_OF_SCOPE_RULE_IDS,
    RJSC_RULE_SCOPE,
    RJSC_SCOPE_VERSION,
    assert_rjsc_scope_parity,
    is_rjsc_rule_in_scope,
)
from canonical_architecture.statutory_rules import STATUTORY_RULE_REGISTRY


def test_every_canonical_rule_has_exactly_one_versioned_rjsc_scope_classification():
    assert RJSC_SCOPE_VERSION == "RJSC_SCOPE_2026-11-24.1"
    assert len(RJSC_RULE_SCOPE) == 85
    assert_rjsc_scope_parity(STATUTORY_RULE_REGISTRY)
    assert RJSC_IN_SCOPE_RULE_IDS.isdisjoint(RJSC_OUT_OF_SCOPE_RULE_IDS)
    assert RJSC_IN_SCOPE_RULE_IDS | RJSC_OUT_OF_SCOPE_RULE_IDS == set(STATUTORY_RULE_REGISTRY)


def test_out_of_scope_rules_are_not_eligible_for_any_rjsc_decision_gate():
    for rule_id in RJSC_OUT_OF_SCOPE_RULE_IDS:
        row = RJSC_RULE_SCOPE[rule_id]
        assert row["score_eligible"] is False
        assert row["risk_eligible"] is False
        assert row["rescue_eligible"] is False
        assert row["release_eligible"] is False
        assert is_rjsc_rule_in_scope(rule_id) is False


def test_unknown_rule_identity_fails_closed():
    assert is_rjsc_rule_in_scope("UNKNOWN-999") is False


def test_known_rjsc_rule_is_explicitly_classified():
    assert is_rjsc_rule_in_scope("AR-001") is True



@pytest.mark.parametrize("rule_id", sorted(RJSC_OUT_OF_SCOPE_RULE_IDS))
def test_injecting_any_out_of_scope_rule_cannot_change_any_engine_rjsc_decision(
    monkeypatch, rule_id
):
    import app.rule_engine.engine as engine_module
    from app.rule_engine.engine import (
        CompanyProfile,
        ComplianceFlag,
        NLCRuleEngine,
        RevenueTier,
        RuleState,
        Severity,
    )

    module_methods = (
        "_run_incorporation_rules",
        "_run_auditor_rules",
        "_run_agm_rules",
        "_run_annual_return_rules",
        "_run_director_rules",
        "_run_shareholder_rules",
        "_run_transfer_rules",
        "_run_register_rules",
        "_run_office_rules",
        "_run_capital_rules",
        "_run_insolvency_rules",
        "_run_labour_rules",
        "_run_companies_act_extended_rules",
        "_run_bsec_rules",
        "_run_fx_rules",
        "_run_tax_rules",
        "_run_board_meeting_rules",
        "_run_accounts_rules",
        "_run_structural_change_rules",
        "_run_escalation_rules",
    )
    for method_name in module_methods:
        monkeypatch.setattr(NLCRuleEngine, method_name, lambda self, company: None)

    profile = CompanyProfile(company_id="scope-test-company", company_name="Scope Test Ltd")

    monkeypatch.setattr(engine_module, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(
        engine_module, "PRODUCT_SCORING_RULE_IDS",
        frozenset(engine_module.PRODUCT_SCORING_RULE_IDS | {"AR-001", rule_id}),
    )
    monkeypatch.setattr(
        engine_module, "SCORE_DEDUCTION_RULE_IDS",
        frozenset(engine_module.SCORE_DEDUCTION_RULE_IDS | {"AR-001", rule_id}),
    )
    monkeypatch.setattr(
        engine_module, "VERIFIED_RULE_IDS",
        frozenset(engine_module.VERIFIED_RULE_IDS | {"AR-001", rule_id}),
    )
    monkeypatch.setattr(
        engine_module, "AUTHORIZED_BLACK_OVERRIDE_RULE_IDS",
        frozenset(engine_module.AUTHORIZED_BLACK_OVERRIDE_RULE_IDS | {rule_id}),
    )

    baseline = NLCRuleEngine(today=date(2026, 11, 24)).evaluate(profile)

    # Positive control: prove this test setup can actually change an RJSC score.
    # Without this assertion, a broken/no-op scorer could make the injected
    # OUT_OF_SCOPE comparison pass vacuously.
    in_scope_control = ComplianceFlag(
        rule_id="AGM-001",
        flag_code="IN_SCOPE_SCORING_CONTROL",
        severity=Severity.RED,
        score_impact=25,
        revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
        description="Confirmed in-scope scoring control",
        statutory_basis="Companies Act 1994, Section 81(1)",
        state=RuleState.NON_COMPLIANT,
        eval_state="VIOLATION",
    )
    control_score = NLCRuleEngine(today=date(2026, 11, 24))._calculate_score(
        [in_scope_control], profile
    )
    assert control_score.raw_total < baseline.score_breakdown.raw_total
    assert control_score.final_score < baseline.score_breakdown.final_score
    assert control_score.score_hash != baseline.score_breakdown.score_hash

    injected = ComplianceFlag(
        rule_id=rule_id,
        flag_code="MALICIOUS_OUT_OF_SCOPE_INJECTION",
        severity=Severity.BLACK,
        score_impact=100,
        revenue_tier=RevenueTier.CORPORATE_RESCUE,
        description="Adversarial out-of-scope finding",
        statutory_basis="Injected test-only basis",
        state=RuleState.NON_COMPLIANT,
        eval_state="VIOLATION",
        is_black_override=True,
    )
    monkeypatch.setattr(
        NLCRuleEngine,
        "_run_incorporation_rules",
        lambda self, company: self._add_flag(injected),
    )
    actual = NLCRuleEngine(today=date(2026, 11, 24)).evaluate(profile)

    assert [flag.rule_id for flag in actual.flags] == [rule_id]
    assert actual.flags[0].score_impact == 100
    assert actual.score_breakdown.final_score == baseline.score_breakdown.final_score
    assert actual.score_breakdown.raw_total == baseline.score_breakdown.raw_total
    assert actual.score_breakdown.risk_band == baseline.score_breakdown.risk_band
    assert actual.score_breakdown.score_hash == baseline.score_breakdown.score_hash
    assert actual.score_breakdown.active_flag_count == baseline.score_breakdown.active_flag_count
    assert actual.score_breakdown.black_flag_count == baseline.score_breakdown.black_flag_count
    assert actual.rescue_sequence == baseline.rescue_sequence
    assert actual.rescue_dispositions == baseline.rescue_dispositions


@pytest.mark.parametrize("rule_id", sorted(RJSC_OUT_OF_SCOPE_RULE_IDS))
def test_out_of_scope_flag_injection_cannot_change_persisted_rjsc_outcome_snapshot(rule_id):
    from types import SimpleNamespace

    from app.compliance.rule_outcome_ledger import (
        build_rule_outcomes_snapshot,
        hash_rule_outcomes_snapshot,
    )

    in_scope_rule = SimpleNamespace(
        rule_id="AR-001",
        rule_version="1",
        statutory_basis="Companies Act 1994, Section 36",
        verification_status="PENDING",
        verified_by=None,
        verified_at=None,
    )
    out_of_scope_rule = SimpleNamespace(rule_id=rule_id)
    catalogue = [in_scope_rule, out_of_scope_rule]
    injected = SimpleNamespace(
        rule_id=rule_id,
        flag_code="INJECTED_OUT_OF_SCOPE_BREACH",
        state="NON_COMPLIANT",
        severity="BLACK",
        eval_state="VIOLATION",
        description="must not enter the RJSC outcome ledger",
        statutory_basis="Income Tax Act",
    )

    baseline = build_rule_outcomes_snapshot(catalogue, [])
    contaminated = build_rule_outcomes_snapshot(
        catalogue,
        [injected],
        applicability_results={
            "TAX-001": {
                "status": "APPLICABLE",
                "reason": "injected applicability",
                "fact_evidence": [{"fact": "external"}],
            }
        },
    )
    assert contaminated == baseline
    assert hash_rule_outcomes_snapshot(contaminated) == hash_rule_outcomes_snapshot(baseline)
    excluded = next(row for row in contaminated if row["rule_id"] == rule_id)
    assert excluded["scope_class"] == "OUT_OF_SCOPE"
    assert excluded["outcome_state"] == "OUT_OF_SCOPE"
    assert excluded["findings"] == []
    assert excluded["identity_conflicts"] == []


def test_rjsc_release_gate_requires_scope_registry_parity_and_scope_is_not_legal_approval():
    from app.rule_engine.engine import legal_score_is_released

    assert_rjsc_scope_parity(STATUTORY_RULE_REGISTRY)
    assert len(RJSC_OUT_OF_SCOPE_RULE_IDS) == 26
    assert all(
        RJSC_RULE_SCOPE[rule_id]["release_eligible"] is False
        for rule_id in RJSC_OUT_OF_SCOPE_RULE_IDS
    )
    assert all(
        RJSC_RULE_SCOPE[rule_id]["legal_review_status"]
        == "REQUIRES_INDEPENDENT_LEGAL_REVIEW"
        for rule_id in RJSC_RULE_SCOPE
    )
    # Release availability remains subject to the independent product/legal
    # release controls; scope classification itself never approves a rule.
    assert isinstance(legal_score_is_released(), bool)



@pytest.mark.parametrize("rule_id", sorted(RJSC_OUT_OF_SCOPE_RULE_IDS))
def test_out_of_scope_profile_and_catalogue_injection_cannot_change_rjsc_score_hash(
    monkeypatch, rule_id
):
    import app.rule_engine.engine as engine_module
    from app.rule_engine.engine import CompanyProfile, NLCRuleEngine

    baseline_profile = CompanyProfile(
        company_id="scope-hash-company",
        company_name="Scope Hash Ltd",
    )
    injected_profile = CompanyProfile(
        company_id="scope-hash-company",
        company_name="Scope Hash Ltd",
        trade_license_obtained=True,
        tin_obtained=True,
        vat_registered=True,
        is_manufacturing=True,
        bsec_listed=True,
        foreign_exchange_violation=True,
        verified_fact_keys=frozenset({
            "trade_license_obtained",
            "tin_obtained",
            "vat_registered",
            "is_manufacturing",
        }),
        catalogue_rule_versions={rule_id: "attacker-version"},
        catalogue_rule_active={rule_id: True},
        catalogue_rule_bases={rule_id: "external-regulator basis"},
        catalogue_identity_conflicts={
            rule_id: {
                "rule_id": rule_id,
                "binding_reason": "STATUTORY_BASIS_MISMATCH",
                "catalogue_is_active": True,
            }
        },
    )

    monkeypatch.setattr(
        engine_module,
        "PRODUCT_SCORING_RULE_IDS",
        frozenset(engine_module.PRODUCT_SCORING_RULE_IDS | {rule_id}),
    )
    monkeypatch.setattr(
        engine_module,
        "VERIFIED_RULE_IDS",
        frozenset(engine_module.VERIFIED_RULE_IDS | {rule_id}),
    )
    monkeypatch.setattr(
        engine_module,
        "SCORE_DEDUCTION_RULE_IDS",
        frozenset(engine_module.SCORE_DEDUCTION_RULE_IDS | {rule_id}),
    )
    monkeypatch.setattr(
        engine_module,
        "AUTHORIZED_BLACK_OVERRIDE_RULE_IDS",
        frozenset(engine_module.AUTHORIZED_BLACK_OVERRIDE_RULE_IDS | {rule_id}),
    )

    baseline = NLCRuleEngine(today=date(2026, 11, 24))._calculate_score(
        [], baseline_profile
    )
    injected = NLCRuleEngine(today=date(2026, 11, 24))._calculate_score(
        [], injected_profile
    )

    assert injected.final_score == baseline.final_score
    assert injected.raw_total == baseline.raw_total
    assert injected.risk_band == baseline.risk_band
    assert injected.score_hash == baseline.score_hash



@pytest.mark.parametrize("rule_id", sorted(RJSC_OUT_OF_SCOPE_RULE_IDS))
def test_out_of_scope_allowlist_entry_cannot_open_rjsc_release_gate(monkeypatch, rule_id):
    import app.rule_engine.engine as engine_module

    monkeypatch.setattr(engine_module, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(engine_module, "PRODUCT_SCORING_RULE_IDS", frozenset({rule_id}))
    assert engine_module.legal_score_is_released() is False
