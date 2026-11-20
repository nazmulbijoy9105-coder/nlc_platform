from canonical_architecture.live_coverage import build_live_rule_coverage_report


ENGINE = """
def evaluate():
    ComplianceFlag(rule_id="AGM-001")
"""


def test_missing_finding_is_unknown_applicability_not_not_applicable():
    report = build_live_rule_coverage_report(
        engine_source=ENGINE,
        registry={"AGM-001": object()},
        database_rule_rows=[{
            "rule_id": "AGM-001",
            "is_active": True,
            "verification_status": "PENDING",
        }],
        run_snapshot=[{
            "rule_id": "AGM-001",
            "outcome_state": "NOT_EVALUATED",
            "applicability_state": "UNKNOWN",
            "applicability_source": "NO_EXPLICIT_ENGINE_DECISION",
            "applicability_reason": "No applicability decision emitted.",
        }],
    )

    assert report["summary"]["registered"] == 1
    assert report["summary"]["implemented"] == 1
    assert report["summary"]["active"] == 1
    assert report["summary"]["applicable"] == 0
    assert report["summary"]["evaluated"] == 0
    assert report["applicability_summary"] == {
        "APPLICABLE": 0,
        "NOT_APPLICABLE": 0,
        "UNKNOWN": 1,
    }
    assert report["applicability_results"]["AGM-001"]["applicability_state"] == "UNKNOWN"
    assert report["validation_status"] == "PASS"


def test_only_explicit_applicable_and_evaluated_rows_enter_the_funnel():
    report = build_live_rule_coverage_report(
        engine_source=ENGINE,
        registry={"AGM-001": object()},
        database_rule_rows=[{
            "rule_id": "AGM-001",
            "is_active": True,
            "verification_status": "PENDING",
        }],
        run_snapshot=[{
            "rule_id": "AGM-001",
            "outcome_state": "NON_COMPLIANT",
            "applicability_state": "APPLICABLE",
            "applicability_source": "ENGINE_CONDITIONAL_APPLICABILITY",
            "applicability_reason": "Engine marked condition applicable.",
        }],
    )

    assert report["summary"]["applicable"] == 1
    assert report["summary"]["evaluated"] == 1
    assert report["applicability_summary"]["APPLICABLE"] == 1


def test_missing_snapshot_row_is_explicit_unknown():
    report = build_live_rule_coverage_report(
        engine_source=ENGINE,
        registry={"AGM-001": object()},
        database_rule_rows=[{
            "rule_id": "AGM-001",
            "is_active": True,
            "verification_status": "PENDING",
        }],
        run_snapshot=[],
    )

    result = report["applicability_results"]["AGM-001"]
    assert result["applicability_state"] == "UNKNOWN"
    assert result["applicability_source"] == "MISSING_RUN_SNAPSHOT_ROW"
    assert report["summary"]["applicable"] == 0


def test_no_evaluation_run_keeps_run_scoped_stages_uncollected():
    report = build_live_rule_coverage_report(
        engine_source=ENGINE,
        registry={"AGM-001": object()},
        database_rule_rows=[{
            "rule_id": "AGM-001",
            "is_active": True,
            "verification_status": "PENDING",
        }],
        run_snapshot=None,
    )

    assert report["summary"]["active"] == 1
    assert report["summary"]["applicable"] is None
    assert report["summary"]["evaluated"] is None
    assert report["applicability_results"] is None


def test_active_unimplemented_database_rule_is_reported_as_invariant_failure():
    report = build_live_rule_coverage_report(
        engine_source=ENGINE,
        registry={"AGM-001": object()},
        database_rule_rows=[
            {"rule_id": "AGM-001", "is_active": True, "verification_status": "PENDING"},
            {"rule_id": "INC-002", "is_active": True, "verification_status": "ACTIVE"},
        ],
        run_snapshot=[],
    )

    assert report["validation_status"] == "FAILED"
    assert any("phantom active" in item for item in report["validation_violations"])
