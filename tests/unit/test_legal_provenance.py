"""Legal provenance governance: no runtime shortcut may self-approve a rule."""

from copy import deepcopy

import pytest

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
