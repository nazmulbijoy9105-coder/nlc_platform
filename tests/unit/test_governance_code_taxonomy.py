from app.rule_engine.governance_code import (
    GOVERNANCE_CODE_REVIEW_RULES,
    GovernanceReviewClass,
    governance_review_rules,
)


def test_corporate_governance_code_is_not_applied_without_verified_listing_scope():
    assert governance_review_rules(
        bsec_listed=True,
        listing_verified=False,
    ) == ()
    assert governance_review_rules(
        bsec_listed=None,
        listing_verified=False,
    ) == ()


def test_verified_listed_issuer_gets_separate_documentary_and_judgment_reviews():
    rules = governance_review_rules(
        bsec_listed=True,
        listing_verified=True,
    )
    assert rules == GOVERNANCE_CODE_REVIEW_RULES
    assert any(r.review_class == GovernanceReviewClass.DOCUMENTARY for r in rules)
    assert any(r.review_class == GovernanceReviewClass.JUDGMENT for r in rules)
    assert all(r.minimum_evidence for r in rules)
    assert all(r.decision_boundary.strip() for r in rules)


def test_verified_listed_parent_subsidiary_receives_only_condition_two_review():
    rules = governance_review_rules(
        bsec_listed=False,
        listing_verified=True,
        subsidiary_of_listed_issuer=True,
        subsidiary_scope_verified=True,
    )
    assert rules
    assert all(r.condition.startswith("Condition 2") for r in rules)
