"""LBR-001 applicability (R-003) and unknown handling (R-008)."""


def _ids(output):
    return [f.rule_id for f in output.flags]


def test_lbr001_reports_unknown_manufacturing_applicability(rule_engine, build_profile):
    out = rule_engine.evaluate(build_profile(is_manufacturing=None, factory_license_obtained=False))
    finding = next(f for f in out.flags if f.rule_id == "LBR-001")
    assert finding.flag_code == "FACTORY_LICENSE_APPLICABILITY_UNKNOWN"
    assert finding.eval_state == "UNKNOWN"
    assert finding.score_impact == 0


def test_lbr001_not_applicable_for_confirmed_non_manufacturing_company(rule_engine, build_profile):
    out = rule_engine.evaluate(build_profile(is_manufacturing=False, factory_license_obtained=False))
    assert "LBR-001" not in _ids(out)


def test_lbr001_fires_only_when_government_direction_requires_license(rule_engine, build_profile):
    out = rule_engine.evaluate(build_profile(is_manufacturing=True, factory_license_required_by_direction=True, factory_license_obtained=False))
    assert "LBR-001" in _ids(out)


def test_lbr001_reports_unknown_government_direction_when_manufacturing(rule_engine, build_profile):
    out = rule_engine.evaluate(build_profile(
        is_manufacturing=True,
        factory_license_required_by_direction=None,
        factory_license_obtained=False,
    ))
    finding = next(f for f in out.flags if f.rule_id == "LBR-001")
    assert finding.flag_code == "FACTORY_LICENSE_GOVERNMENT_DIRECTION_UNKNOWN"
    assert finding.eval_state == "UNKNOWN"
    assert finding.score_impact == 0


def test_lbr001_silent_for_manufacturing_with_license(rule_engine, build_profile):
    out = rule_engine.evaluate(build_profile(is_manufacturing=True, factory_license_required_by_direction=True, factory_license_obtained=True))
    assert "LBR-001" not in _ids(out)


def test_unknown_applicability_is_visible_but_non_scoring(rule_engine, build_profile):
    base = rule_engine.evaluate(build_profile(is_manufacturing=False))
    unknown = rule_engine.evaluate(build_profile(is_manufacturing=None, factory_license_obtained=False))
    assert "LBR-001" not in _ids(base)
    assert "LBR-001" in _ids(unknown)
    finding = next(f for f in unknown.flags if f.rule_id == "LBR-001")
    assert finding.severity.value == "NOT_EVALUATED"
    assert finding.eval_state == "UNKNOWN"
    assert finding.score_impact == 0
    assert unknown.score_breakdown.final_score == base.score_breakdown.final_score
