from app.rule_engine.engine import RuleState, Severity


def _flag(output, rule_id):
    return next(flag for flag in output.flags if flag.rule_id == rule_id)


def test_inc005_encashment_record_absence_is_review_only(rule_engine, build_profile):
    profile = build_profile(
        has_foreign_shareholder=True,
        foreign_shareholding_pct=25,
        encashment_certificate_uploaded=False,
        remittance_amount_usd=75000,
        bida_registered=True,
    )
    output = rule_engine.evaluate(profile)
    flag = _flag(output, "INC-005")

    assert flag.severity == Severity.NOT_EVALUATED
    assert flag.score_impact == 0
    assert flag.state in {RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT}
    assert not getattr(flag, "is_black_override", False)


def test_inc006_reference_amount_is_not_a_scored_breach(rule_engine, build_profile):
    profile = build_profile(
        has_foreign_shareholder=True,
        foreign_shareholding_pct=25,
        encashment_certificate_uploaded=True,
        remittance_amount_usd=40000,
        bida_registered=True,
    )
    output = rule_engine.evaluate(profile)
    flag = _flag(output, "INC-006")

    assert flag.severity == Severity.NOT_EVALUATED
    assert flag.score_impact == 0
    assert flag.state in {RuleState.UNKNOWN, RuleState.REQUIRES_LAWYER_JUDGMENT}
    assert not getattr(flag, "is_black_override", False)


def test_inc006_missing_remittance_amount_does_not_raise_or_create_breach(rule_engine, build_profile):
    profile = build_profile(
        has_foreign_shareholder=True,
        foreign_shareholding_pct=25,
        encashment_certificate_uploaded=True,
        remittance_amount_usd=None,
        bida_registered=True,
    )
    output = rule_engine.evaluate(profile)

    assert not any(flag.rule_id == "INC-006" for flag in output.flags)
