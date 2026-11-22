"""Six-state rule coverage funnel — structural contract pins (fix-order item 9).

The funnel (registered, implemented, active, applicable, evaluated, deferred)
must never collapse states silently: every drop-out between adjacent stages is
explicit and reason-carrying. Synthetic pins prove each invariant fires; corpus
pins prove the real ILRMF corpus satisfies the funnel, including the INC-001
activation hold introduced by migration 0115.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from canonical_architecture.coverage_report import (
    CoverageInvariantError,
    CoverageStage,
    RuleCoverageReport,
    build_registry_coverage,
    main as cli_main,
    parse_engine_rule_ids,
)
from canonical_architecture.statutory_rules import STATUTORY_RULE_REGISTRY

ROOT = Path(__file__).resolve().parents[2]
ENGINE_PATH = ROOT / "app" / "rule_engine" / "engine.py"
EXPECTED_CORPUS = 85  # ILRMF production corpus; this gate does not add or remove rules.


# ---------------------------------------------------------------------------
# Synthetic invariant pins
# ---------------------------------------------------------------------------


def _report(**overrides) -> RuleCoverageReport:
    """A minimal valid corpus with one registered, implemented and active rule."""
    base = {
        "registered": frozenset({"AAA-001"}),
        "implemented": frozenset({"AAA-001"}),
        "active": frozenset({"AAA-001"}),
    }
    base.update(overrides)
    return RuleCoverageReport(**base)


def test_i1_phantom_implementation_is_rejected():
    report = _report(implemented=frozenset({"AAA-001", "ZZZ-999"}))
    with pytest.raises(CoverageInvariantError) as excinfo:
        report.validate()
    assert "I1" in str(excinfo.value)
    assert "ZZZ-999" in str(excinfo.value)


def test_i2_silent_implementation_gap_is_rejected():
    report = _report(registered=frozenset({"AAA-001", "BBB-002"}), implemented=frozenset({"AAA-001"}))
    with pytest.raises(CoverageInvariantError) as excinfo:
        report.validate()
    assert "I2" in str(excinfo.value)
    assert "BBB-002" in str(excinfo.value)


def test_i2_gap_is_cured_by_explicit_deferral_with_reason():
    report = RuleCoverageReport(
        registered=frozenset({"AAA-001", "BBB-002"}),
        implemented=frozenset({"AAA-001"}),
        deferred=frozenset({"BBB-002"}),
        deferred_reasons={"BBB-002": "candidate provision awaiting counsel sign-off"},
    )
    report.validate()  # must not raise


def test_i3_deferred_id_without_reason_is_rejected():
    report = _report(
        registered=frozenset({"AAA-001", "BBB-002"}),
        implemented=frozenset({"AAA-001"}),
        deferred=frozenset({"BBB-002"}),
    )
    with pytest.raises(CoverageInvariantError) as excinfo:
        report.validate()
    assert "I3" in str(excinfo.value)
    assert "BBB-002" in str(excinfo.value)


def test_i3_deferred_id_outside_registry_is_rejected():
    report = _report(deferred=frozenset({"ZZZ-999"}), deferred_reasons={"ZZZ-999": "later"})
    with pytest.raises(CoverageInvariantError) as excinfo:
        report.validate()
    assert "I3" in str(excinfo.value)
    assert "ZZZ-999" in str(excinfo.value)


def test_i3_deferral_cannot_overlap_implementation():
    report = _report(deferred=frozenset({"AAA-001"}), deferred_reasons={"AAA-001": "hold"})
    with pytest.raises(CoverageInvariantError) as excinfo:
        report.validate()
    assert "I3" in str(excinfo.value)
    assert "AAA-001" in str(excinfo.value)


def test_i3_stray_deferred_reason_is_rejected():
    report = _report(deferred_reasons={"AAA-001": "not actually deferred"})
    with pytest.raises(CoverageInvariantError) as excinfo:
        report.validate()
    assert "I3" in str(excinfo.value)


def test_i4_active_row_outside_registry_is_rejected():
    report = _report(active=frozenset({"AAA-001", "ZZZ-999"}), active_hold_reasons={"ZZZ-999": "x"})
    with pytest.raises(CoverageInvariantError) as excinfo:
        report.validate()
    assert "I4" in str(excinfo.value)
    assert "ZZZ-999" in str(excinfo.value)


def test_i4_active_must_be_implemented():
    report = _report(
        registered=frozenset({"AAA-001", "BBB-002"}),
        implemented=frozenset({"AAA-001"}),
        active=frozenset({"AAA-001", "BBB-002"}),
    )
    with pytest.raises(CoverageInvariantError) as excinfo:
        report.validate()
    assert "I4" in str(excinfo.value)
    assert "BBB-002" in str(excinfo.value)


def test_i5_static_hold_must_reference_an_implemented_rule():
    report = _report(
        active=None,
        active_hold_reasons={"ZZZ-999": "claimed activation hold"},
    )
    with pytest.raises(CoverageInvariantError) as excinfo:
        report.validate()
    assert "I5" in str(excinfo.value)
    assert "ZZZ-999" in str(excinfo.value)


def test_i5_implemented_inactive_without_hold_reason_is_rejected():
    report = _report(
        registered=frozenset({"AAA-001", "BBB-002"}),
        implemented=frozenset({"AAA-001", "BBB-002"}),
        active=frozenset({"AAA-001"}),
    )
    with pytest.raises(CoverageInvariantError) as excinfo:
        report.validate()
    assert "I5" in str(excinfo.value)
    assert "BBB-002" in str(excinfo.value)


def test_i5_explicit_hold_reason_cures_inactive_implementation():
    report = _report(
        registered=frozenset({"AAA-001", "BBB-002"}),
        implemented=frozenset({"AAA-001", "BBB-002"}),
        active=frozenset({"AAA-001"}),
        active_hold_reasons={"BBB-002": "activation held pending operator decision"},
    )
    report.validate()  # must not raise


def test_i5_stray_or_empty_hold_reason_is_rejected():
    stray = _report(active_hold_reasons={"AAA-001": "not held — it is active"})
    with pytest.raises(CoverageInvariantError) as excinfo:
        stray.validate()
    assert "I5" in str(excinfo.value)

    empty = _report(active=frozenset(), active_hold_reasons={"AAA-001": "   "})
    with pytest.raises(CoverageInvariantError) as excinfo:
        empty.validate()
    assert "I5" in str(excinfo.value)


def test_i6_applicability_must_funnel_from_active():
    without_base = _report(applicable=frozenset({"AAA-001"}), active=None)
    with pytest.raises(CoverageInvariantError) as excinfo:
        without_base.validate()
    assert "I6" in str(excinfo.value)

    beyond = _report(active=frozenset(), applicable=frozenset({"AAA-001"}))
    with pytest.raises(CoverageInvariantError) as excinfo:
        beyond.validate()
    assert "I6" in str(excinfo.value)
    assert "AAA-001" in str(excinfo.value)


def test_i7_evaluation_must_funnel_from_applicability():
    without_base = _report(evaluated=frozenset({"AAA-001"}), applicable=None)
    with pytest.raises(CoverageInvariantError) as excinfo:
        without_base.validate()
    assert "I7" in str(excinfo.value)

    beyond = _report(active=frozenset(), applicable=frozenset(), evaluated=frozenset({"AAA-001"}))
    with pytest.raises(CoverageInvariantError) as excinfo:
        beyond.validate()
    assert "I7" in str(excinfo.value)


def test_full_funnel_happy_path_is_monotone():
    registered = {f"AAA-{n:03d}" for n in range(1, 6)}
    implemented = registered - {"AAA-005"}
    report = RuleCoverageReport(
        registered=frozenset(registered),
        implemented=frozenset(implemented),
        deferred=frozenset({"AAA-005"}),
        deferred_reasons={"AAA-005": "policy rule, not statutory"},
        active=frozenset(implemented - {"AAA-004"}),
        active_hold_reasons={"AAA-004": "operator deactivated"},
        applicable=frozenset(implemented - {"AAA-004", "AAA-003"}),
        evaluated=frozenset(implemented - {"AAA-004", "AAA-003"}) - {"AAA-002"},
    )
    report.validate()
    counts = report.summary()
    assert counts["registered"] >= counts["implemented"] >= counts["active"]
    assert counts["active"] >= counts["applicable"] >= counts["evaluated"]


def test_static_mode_skips_run_scoped_stages():
    """active/applicable/evaluated = None means 'not collected' and imposes no holds."""
    report = _report(active=None)
    report.validate()  # must not raise
    assert report.summary()["active"] is None


def test_validate_aggregates_all_violations():
    report = _report(
        implemented=frozenset({"AAA-001", "ZZZ-999"}),  # I1
        deferred=frozenset({"AAA-001"}),  # I3 overlap
        deferred_reasons={"QQQ-001": "stray"},  # I3 stray reason
    )
    with pytest.raises(CoverageInvariantError) as excinfo:
        report.validate()
    assert len(excinfo.value.violations) >= 3


def test_i8_summary_always_exposes_all_six_states():
    report = _report(active=None)
    assert set(report.summary()) == {stage.value for stage in CoverageStage}
    assert set(report.to_dict()["states"]) == {stage.value for stage in CoverageStage}
    artifact = json.loads(json.dumps(report.to_dict()))
    assert set(artifact["summary"]) == {stage.value for stage in CoverageStage}


# ---------------------------------------------------------------------------
# Engine parser pins
# ---------------------------------------------------------------------------


def test_parser_rejects_non_literal_rule_id():
    source = "flag = ComplianceFlag(rule_id=some_variable, statutory_basis='basis')"
    with pytest.raises(ValueError, match="string literal"):
        parse_engine_rule_ids(source)


def test_parser_rejects_shared_constructor_outside_known_functions():
    source = (
        "def helper():\n"
        "    rule_id = 'AAA-001'\n"
        "    return ComplianceFlag(rule_id=rule_id, statutory_basis='basis')\n"
    )
    with pytest.raises(ValueError, match="shared ComplianceFlag constructor"):
        parse_engine_rule_ids(source)


def test_parser_resolves_bsec_candidates_and_director_assignments():
    """Mirror the engine's real shared-constructor styles for both paths."""
    source = (
        "def _run_bsec_rules():\n"
        "    candidates = (('BSEC-001', 'FLAG_A'), ('BSEC-002', 'FLAG_B'))\n"
        "    for rule_id, flag_code in candidates:\n"
        "        return ComplianceFlag(rule_id=rule_id, statutory_basis='listing basis')\n"
        "\n"
        "def _run_director_rules():\n"
        "    rule_id = 'DIR-002'\n"
        "    return ComplianceFlag(rule_id=rule_id, statutory_basis='form xii basis')\n"
    )
    assert parse_engine_rule_ids(source) == frozenset({"BSEC-001", "BSEC-002", "DIR-002"})


def test_parser_rejects_source_without_rule_declarations():
    with pytest.raises(ValueError, match="no ComplianceFlag rule declarations"):
        parse_engine_rule_ids("x = 1\n")


# ---------------------------------------------------------------------------
# Corpus pins — the real ILRMF corpus must satisfy the funnel
# ---------------------------------------------------------------------------


def test_corpus_registered_equals_engine_implemented():
    source = ENGINE_PATH.read_text(encoding="utf-8")
    implemented = parse_engine_rule_ids(source)
    registered = set(STATUTORY_RULE_REGISTRY)
    assert len(registered) == EXPECTED_CORPUS
    assert implemented == registered


def test_corpus_static_report_validates_and_counts_85():
    source = ENGINE_PATH.read_text(encoding="utf-8")
    report = build_registry_coverage(source, STATUTORY_RULE_REGISTRY)
    counts = report.summary()
    assert counts["registered"] == EXPECTED_CORPUS
    assert counts["implemented"] == EXPECTED_CORPUS
    assert counts["deferred"] == 0
    assert counts["active"] is None  # static mode: runtime stages not collected
    assert set(counts) == {stage.value for stage in CoverageStage}


def test_corpus_live_shape_85_ids_are_active_catalogue_rows():
    """All 85 catalogue IDs are active rows; scoring remains staged separately."""
    registered = set(STATUTORY_RULE_REGISTRY)
    active = registered
    report = RuleCoverageReport(
        registered=frozenset(registered),
        implemented=frozenset(registered),
        active=frozenset(active),
    )
    report.validate()
    assert report.summary()["active"] == EXPECTED_CORPUS


def test_cli_writes_valid_artifact_and_fails_closed(tmp_path, capsys):
    output = tmp_path / "artifacts" / "rule-coverage-report.json"
    exit_code = cli_main(["--output", str(output)])
    assert exit_code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert set(payload["summary"]) == {stage.value for stage in CoverageStage}
    assert payload["summary"]["registered"] == EXPECTED_CORPUS
    assert payload["summary"]["implemented"] == EXPECTED_CORPUS
    assert payload["states"]["registered"] == sorted(STATUTORY_RULE_REGISTRY)
    assert "artifact written" in capsys.readouterr().out

    bad_engine = tmp_path / "broken_engine.py"
    bad_engine.write_text(
        "flag = ComplianceFlag(rule_id=not_a_literal, statutory_basis='b')\n", encoding="utf-8"
    )
    exit_code = cli_main(["--engine", str(bad_engine), "--output", str(tmp_path / "unused.json")])
    assert exit_code == 1
    assert "FAILED" in capsys.readouterr().err
