from datetime import datetime, timezone
from types import SimpleNamespace
import uuid

import pytest

from app.compliance.live_rule_coverage import build_live_rule_coverage_payload
from canonical_architecture.coverage_report import CoverageInvariantError, RuleCoverageReport


def _static_report():
    ids = frozenset({"AGM-001", "AGM-002"})
    return RuleCoverageReport(registered=ids, implemented=ids)


def _rule(rule_id, active):
    return SimpleNamespace(
        rule_id=rule_id,
        is_active=active,
        verification_status="PENDING",
    )


def _run(snapshot):
    return SimpleNamespace(
        id=uuid.uuid4(),
        calculated_at=datetime(2026, 11, 20, tzinfo=timezone.utc),
        engine_version="2.1.0",
        score_hash="a" * 64,
        rule_outcomes_hash="b" * 64,
        rule_catalogue_count=len(snapshot),
        rule_outcomes_snapshot=snapshot,
    )


def test_live_coverage_uses_database_active_and_explicit_applicability_not_findings():
    snapshot = [
        {
            "rule_id": "AGM-001",
            "applicability_status": "APPLICABLE",
            "applicability_reason": "verified scope predicates",
            "assessment_source": "NO_FINDING_EMITTED_NOT_PROOF_OF_COMPLIANCE",
            "outcome_state": "NOT_EVALUATED",
        }
    ]
    payload = build_live_rule_coverage_payload(
        company_id=uuid.uuid4(),
        static_report=_static_report(),
        legal_rules=[_rule("AGM-001", True), _rule("AGM-002", False)],
        latest_run=_run(snapshot),
    )
    assert payload["summary"] == {
        "registered": 2,
        "implemented": 2,
        "active": 1,
        "applicable": 1,
        "evaluated": 0,
        "deferred": 0,
    }
    assert payload["states"]["applicable"] == ["AGM-001"]
    assert payload["states"]["evaluated"] == []
    assert payload["applicability_status_counts"] == {
        "APPLICABLE": 1,
        "NOT_APPLICABLE": 0,
        "UNKNOWN": 0,
    }
    assert payload["applicable_but_not_evaluated_count"] == 1


def test_live_coverage_counts_evaluated_only_when_engine_emitted_a_finding():
    snapshot = [
        {
            "rule_id": "AGM-001",
            "applicability_status": "APPLICABLE",
            "assessment_source": "ENGINE_FINDING",
            "outcome_state": "UNKNOWN",
        },
        {
            "rule_id": "AGM-002",
            "applicability_status": "UNKNOWN",
            "assessment_source": "NO_FINDING_EMITTED_NOT_PROOF_OF_COMPLIANCE",
            "outcome_state": "NOT_EVALUATED",
        },
    ]
    payload = build_live_rule_coverage_payload(
        company_id=uuid.uuid4(),
        static_report=_static_report(),
        legal_rules=[_rule("AGM-001", True), _rule("AGM-002", True)],
        latest_run=_run(snapshot),
    )
    assert payload["summary"]["applicable"] == 1
    assert payload["summary"]["evaluated"] == 1
    assert payload["applicability_status_counts"]["UNKNOWN"] == 1


def test_live_coverage_reports_uncollected_run_scoped_stages_as_null():
    payload = build_live_rule_coverage_payload(
        company_id=uuid.uuid4(),
        static_report=_static_report(),
        legal_rules=[_rule("AGM-001", True), _rule("AGM-002", False)],
        latest_run=None,
    )
    assert payload["summary"]["active"] == 1
    assert payload["summary"]["applicable"] is None
    assert payload["summary"]["evaluated"] is None
    assert payload["reporting_status"] == "NO_EVALUATION_RUN"


def test_legacy_snapshot_does_not_infer_applicability_from_missing_fields():
    snapshot = [
        {
            "rule_id": "AGM-001",
            "assessment_source": "ENGINE_FINDING",
            "outcome_state": "UNKNOWN",
        }
    ]
    payload = build_live_rule_coverage_payload(
        company_id=uuid.uuid4(),
        static_report=_static_report(),
        legal_rules=[_rule("AGM-001", True), _rule("AGM-002", False)],
        latest_run=_run(snapshot),
    )
    assert payload["summary"]["applicable"] is None
    assert payload["summary"]["evaluated"] is None
    assert payload["reporting_status"] == "LEGACY_RUN_APPLICABILITY_NOT_COLLECTED"


def test_live_coverage_fails_closed_when_evaluation_catalogue_is_stale():
    with pytest.raises(CoverageInvariantError, match="catalogue does not match"):
        build_live_rule_coverage_payload(
            company_id=uuid.uuid4(),
            static_report=_static_report(),
            legal_rules=[_rule("AGM-001", True), _rule("AGM-002", True)],
            latest_run=_run([
                {
                    "rule_id": "AGM-001",
                    "applicability_status": "UNKNOWN",
                    "assessment_source": "NO_FINDING_EMITTED_NOT_PROOF_OF_COMPLIANCE",
                }
            ]),
        )
