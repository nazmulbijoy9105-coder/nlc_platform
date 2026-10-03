"""
NLC — GATE E4: Legal Source / Provenance Governance Tests
Proves that no rule can be marked as VERIFIED without a valid legal source.
"""
import pytest
from canonical_architecture.legal_reconciliation import LEGAL_RECONCILIATION, verify_provision, get_reconciliation_status

def test_all_rules_start_as_reconcile():
    """Ensure no rule is accidentally marked as VERIFIED before legal review."""
    for rule_id, recon_data in LEGAL_RECONCILIATION.items():
        assert recon_data["verified"] is False, f"Rule {rule_id} is marked as VERIFIED without legal review!"
        assert get_reconciliation_status(rule_id) == "RECONCILE", f"Rule {rule_id} status is not RECONCILE!"

def test_cannot_verify_without_source():
    """Proves that a rule cannot be verified without providing a legal source."""
    rule_id = "INC-001"
    
    # Attempt to verify without a source (should fail)
    success = verify_provision(rule_id, verified_by="admin@nlc.com", source="")
    assert not success, "System allowed verification without a legal source!"
    
    # Attempt to verify with a valid source (should succeed)
    success = verify_provision(rule_id, verified_by="admin@nlc.com", source="Companies Act 1994, Section 11 (Verified)")
    assert success, "System failed to verify a rule with a valid source!"
    assert get_reconciliation_status(rule_id) == "VERIFIED"
