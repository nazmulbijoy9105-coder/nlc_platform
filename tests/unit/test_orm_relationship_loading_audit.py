"""Regression tests for SQLAlchemy relationship integrity and loading policy."""
from scripts.audit_orm_relationship_loading import build_report


def test_all_registered_relationships_have_resolvable_reciprocal_mappings():
    report = build_report()
    assert report["mapped_models"] >= 20
    assert report["relationship_count"] >= 30
    mismatches = [
        warning for warning in report["warnings"]
        if warning["code"] == "BACK_POPULATES_MISMATCH"
    ]
    assert mismatches == []


def test_high_volume_company_evaluation_relationship_requires_explicit_loading():
    report = build_report()
    company_eval = [
        item for item in report["relationships"]
        if item["model"] == "Company" and item["relationship"] == "evaluation_runs"
    ]
    assert len(company_eval) == 1
    assert company_eval[0]["lazy"] == "raise"


def test_document_access_logs_and_user_activity_logs_are_not_implicitly_loaded():
    report = build_report()
    expected = {
        ("Document", "access_logs"),
        ("User", "activity_logs"),
    }
    actual = {
        (item["model"], item["relationship"])
        for item in report["relationships"]
        if item["lazy"] == "raise"
    }
    assert expected <= actual
