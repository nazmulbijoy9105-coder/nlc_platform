"""ORM metadata checks for governed finding-context persistence."""
from app.models.governed_finding_context import (
    LegalRuleFindingContext,
    LegalRuleFindingContextReview,
)


def test_context_model_has_versioned_source_and_digest_fields():
    columns = LegalRuleFindingContext.__table__.columns
    assert {
        "historical_rule_id", "catalog_version", "source_namespace",
        "jurisdiction", "source_instrument", "source_provision",
        "effective_date", "effective_date_basis", "effective_date_source_ref",
        "context_snapshot", "context_canonical", "context_sha256",
        "authored_by", "authored_at",
    } <= set(columns.keys())
    assert "company_id" not in columns
    assert "tenant_id" not in columns


def test_review_model_is_separate_append_only_decision_record():
    columns = LegalRuleFindingContextReview.__table__.columns
    assert {
        "context_id", "review_status", "reviewed_context_sha256",
        "review_basis", "reviewed_by", "reviewed_at",
    } <= set(columns.keys())
    assert "authored_by" not in columns
