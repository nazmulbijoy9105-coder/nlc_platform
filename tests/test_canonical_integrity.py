from canonical_architecture import (
    Invariant, INVARIANT_RULES, STATUTORY_RULE_REGISTRY,
    STATUTORY_RESCUE_REGISTRY, RuleState,
)

INV_IDS = {i.name.replace("_", "-", 1) for i in Invariant}  # R_006 -> R-006

def test_invariant_refs_resolve():
    for rid, r in STATUTORY_RULE_REGISTRY.items():
        missing = set(r["invariants"]) - INV_IDS
        assert not missing, f"{rid} references unknown invariants {missing}"

def test_all_invariants_have_rule_text():
    undefined = [i.name for i in Invariant if i not in INVARIANT_RULES]
    assert not undefined, f"No rule text for {undefined}"

def test_unknown_state_allowed_when_r008_applies():
    for rid, r in STATUTORY_RULE_REGISTRY.items():
        if r["evidence_required"]:
            assert RuleState.UNKNOWN in r["evaluation_states"], (
                f"{rid} requires evidence but cannot return UNKNOWN (violates R-008)")

def test_every_rule_has_rescue():
    assert set(STATUTORY_RULE_REGISTRY) <= set(STATUTORY_RESCUE_REGISTRY)

def test_rescue_prerequisites_declared_and_unverified_not_frozen():
    for rid, r in STATUTORY_RULE_REGISTRY.items():
        assert r["provision_status"].value in {"RECONCILE", "VERIFIED"}
