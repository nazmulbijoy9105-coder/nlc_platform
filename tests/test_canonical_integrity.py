import dataclasses

from canonical_architecture import (
    AuditTrail, EvidenceStatus, Finding, Invariant, INVARIANT_RULES,
    RESERVED_UNDEFINED, RescueMode, RescueState, RuleState,
    STATUTORY_RESCUE_REGISTRY, STATUTORY_RULE_REGISTRY, can_close,
    compute_score, evaluate_all, evaluate_rule, get_rescue_plan,
)

INV_IDS = {i.value for i in Invariant}
PRESENT = EvidenceStatus.VERIFIED_PRESENT
ABSENT = EvidenceStatus.VERIFIED_ABSENT


def _ev(rule_id, status):
    return {e: status for e in STATUTORY_RULE_REGISTRY[rule_id].evidence_required}


# --- structure -------------------------------------------------------------
def test_invariant_refs_resolve():
    for rid, r in STATUTORY_RULE_REGISTRY.items():
        assert not set(r.invariants) - INV_IDS, rid


def test_all_invariants_have_text_and_reserved_are_undefined():
    assert set(Invariant) == set(INVARIANT_RULES)
    assert not RESERVED_UNDEFINED & INV_IDS


def test_exceptions_declare_r004_and_not_applicable():
    for rid, r in STATUTORY_RULE_REGISTRY.items():
        if r.exceptions:
            assert "R-004" in r.invariants and RuleState.NOT_APPLICABLE in r.evaluation_states, rid


def test_every_rule_has_rescue_and_back_reference():  # R-012
    assert set(STATUTORY_RULE_REGISTRY) == set(STATUTORY_RESCUE_REGISTRY)
    for rid, rd in STATUTORY_RESCUE_REGISTRY.items():
        assert rd.triggered_by == rid


def test_no_provision_silently_verified():
    assert all(r.provision_status.value == "RECONCILE" for r in STATUTORY_RULE_REGISTRY.values())


# --- evaluation ------------------------------------------------------------
def test_missing_evidence_is_unknown_not_noncompliant():  # R-008
    for r in STATUTORY_RULE_REGISTRY.values():
        f = evaluate_rule(r, {"IS_MANUFACTURING": True}, {})
        assert f.state is RuleState.UNKNOWN, r.rule_id


def test_unknown_has_no_score_impact():  # R-008/R-010
    assert compute_score(evaluate_all({"IS_MANUFACTURING": True}, {})) == 100


def test_verified_absent_is_noncompliant_and_present_is_compliant():
    r = STATUTORY_RULE_REGISTRY["TAX-001"]
    assert evaluate_rule(r, {}, _ev("TAX-001", ABSENT)).state is RuleState.NON_COMPLIANT
    assert evaluate_rule(r, {}, _ev("TAX-001", PRESENT)).state is RuleState.COMPLIANT


def test_partial_evidence_is_unknown():
    r = STATUTORY_RULE_REGISTRY["INC-001"]
    assert evaluate_rule(r, {}, {"MOA_FILED": PRESENT}).state is RuleState.UNKNOWN


def test_conflicting_is_contradictory():  # R-009
    r = STATUTORY_RULE_REGISTRY["TAX-001"]
    ev = {"TIN_CERTIFICATE": EvidenceStatus.CONFLICTING}
    assert evaluate_rule(r, {}, ev).state is RuleState.CONTRADICTORY


def test_applicability_and_exceptions():  # R-003/R-004
    lbr = STATUTORY_RULE_REGISTRY["LBR-001"]
    assert evaluate_rule(lbr, {}, {}).state is RuleState.UNKNOWN
    assert evaluate_rule(lbr, {"IS_MANUFACTURING": False}, {}).state is RuleState.NOT_APPLICABLE
    ar = STATUTORY_RULE_REGISTRY["AR-001"]
    assert evaluate_rule(ar, {"DORMANT_STRIKE_OFF": True}, {}).state is RuleState.NOT_APPLICABLE


def test_crescent_textiles_scores_50():
    flags = ["INC-001", "LBR-001", "TAX-001", "TL-001", "DIR-005", "DIR-006"]
    evidence = {}
    for rid in flags:
        evidence.update(_ev(rid, ABSENT))
    findings = evaluate_all({"IS_MANUFACTURING": True}, evidence)
    assert {f.rule_id for f in findings if f.state is RuleState.NON_COMPLIANT} == set(flags)
    assert compute_score(findings) == 50


# --- rescue ----------------------------------------------------------------
def test_unmapped_finding_is_surfaced_not_auto_rescued():  # R-013
    plan = get_rescue_plan([Finding("ZZZ-999", RuleState.NON_COMPLIANT)])
    assert plan.steps == () and plan.unmapped == ("ZZZ-999",)


def test_prerequisite_blocks_until_satisfied():  # R-015
    f = [Finding("AR-001", RuleState.NON_COMPLIANT)]
    blocked = get_rescue_plan(f).steps[0]
    assert blocked.state is RescueState.BLOCKED and blocked.blocked_by == ("AGM_HELD",)
    ready = get_rescue_plan(f, {"AGM_HELD"}).steps[0]
    assert ready.state is RescueState.IDENTIFIED and ready.blocked_by == ()


def test_unknown_opens_evidence_rescue_only():  # R-008/R-014
    step = get_rescue_plan([Finding("TAX-001", RuleState.UNKNOWN)]).steps[0]
    assert step.mode is RescueMode.ESTABLISH_EVIDENCE
    assert step.state is RescueState.WAITING_EVIDENCE


def test_compliant_and_not_applicable_open_no_rescue():  # R-014
    plan = get_rescue_plan([Finding("TAX-001", RuleState.COMPLIANT),
                            Finding("LBR-001", RuleState.NOT_APPLICABLE)])
    assert plan.steps == () and plan.unmapped == ()


def test_red_before_yellow_ordering():
    plan = get_rescue_plan([Finding("TL-001", RuleState.NON_COMPLIANT),
                            Finding("INC-001", RuleState.NON_COMPLIANT)])
    assert [s.triggered_by for s in plan.steps] == ["INC-001", "TL-001"]


def test_close_requires_verified_compliant():  # R-019
    assert can_close(RuleState.COMPLIANT, True)
    assert not can_close(RuleState.COMPLIANT, False)
    assert not can_close(RuleState.UNKNOWN, True)


# --- audit -----------------------------------------------------------------
def test_audit_chain_detects_tampering():  # R-020
    t = AuditTrail()
    for i in range(3):
        t.record("EVAL", f"rule-{i}", {"n": i})
    assert t.verify()
    t._events[1] = dataclasses.replace(t._events[1], detail_json='{"n": 99}')
    assert not t.verify()
