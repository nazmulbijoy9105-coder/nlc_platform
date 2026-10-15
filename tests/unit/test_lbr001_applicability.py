"""LBR-001 applicability (R-003) and unknown handling (R-008)."""
import pytest


def _ids(output):
    return [f.rule_id for f in output.flags]


@pytest.mark.parametrize("is_mfg", [None, False])
def test_lbr001_silent_unless_confirmed_manufacturing(rule_engine, build_profile, is_mfg):
    out = rule_engine.evaluate(build_profile(is_manufacturing=is_mfg, factory_license_obtained=False))
    assert "LBR-001" not in _ids(out)


def test_lbr001_fires_for_manufacturing_without_license(rule_engine, build_profile):
    out = rule_engine.evaluate(build_profile(is_manufacturing=True, factory_license_obtained=False))
    assert "LBR-001" in _ids(out)


def test_lbr001_silent_for_manufacturing_with_license(rule_engine, build_profile):
    out = rule_engine.evaluate(build_profile(is_manufacturing=True, factory_license_obtained=True))
    assert "LBR-001" not in _ids(out)


def test_unknown_applicability_matches_compliant_baseline(rule_engine, build_profile):
    base = rule_engine.evaluate(build_profile())
    unknown = rule_engine.evaluate(build_profile(is_manufacturing=None, factory_license_obtained=False))
    assert _ids(unknown) == _ids(base)
    assert unknown.score_breakdown.final_score == base.score_breakdown.final_score
    assert unknown.score_breakdown.risk_band == base.score_breakdown.risk_band
