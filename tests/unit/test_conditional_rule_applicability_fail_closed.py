"""Conditional rule applicability must preserve UNKNOWN instead of silently skipping."""

from datetime import date

from app.rule_engine.engine import CompanyProfile, NLCRuleEngine, Severity


def _evaluate(**overrides):
    profile = CompanyProfile(
        company_id="conditional-applicability-test",
        company_name="Conditional Applicability Test Ltd",
        incorporation_date=date(2020, 1, 1),
        **overrides,
    )
    return NLCRuleEngine(today=date(2026, 11, 15)).evaluate(profile)


def _flags(output, rule_id):
    return [flag for flag in output.flags if flag.rule_id == rule_id]


def test_public_company_with_unknown_listing_status_does_not_silently_skip_bsec():
    output = _evaluate(company_type="PUBLIC_LIMITED", bsec_listed=None)
    for rule_id in ("BSEC-001", "BSEC-002", "BSEC-003", "BSEC-004"):
        findings = _flags(output, rule_id)
        assert len(findings) == 1
        assert findings[0].flag_code == "BSEC_LISTED_ISSUER_APPLICABILITY_UNKNOWN"
        assert findings[0].severity is Severity.NOT_EVALUATED
        assert findings[0].eval_state == "UNKNOWN"
        assert findings[0].score_impact == 0


def test_private_company_is_not_given_listed_issuer_bsec_findings():
    output = _evaluate(company_type="PRIVATE_LIMITED", bsec_listed=None)
    assert not any(flag.rule_id.startswith("BSEC-") for flag in output.flags)


def test_public_company_confirmed_unlisted_is_not_subject_to_listed_issuer_code():
    output = _evaluate(company_type="PUBLIC_LIMITED", bsec_listed=False)
    assert not any(flag.rule_id.startswith("BSEC-") for flag in output.flags)


def test_listed_public_company_with_missing_condition_status_gets_review_not_breach():
    output = _evaluate(
        company_type="PUBLIC_LIMITED",
        bsec_listed=True,
        bsec_quarterly_report_filed=None,
        cg_certificate_obtained=None,
        board_independent_director=None,
        audit_committee_established=None,
    )
    for rule_id in ("BSEC-001", "BSEC-002", "BSEC-003", "BSEC-004"):
        findings = _flags(output, rule_id)
        assert len(findings) == 1
        assert findings[0].severity is Severity.NOT_EVALUATED
        assert findings[0].eval_state == "UNKNOWN"
        assert findings[0].score_impact == 0


def test_factory_license_rule_is_unknown_when_manufacturing_is_not_established():
    output = _evaluate(is_manufacturing=None)
    finding = _flags(output, "LBR-001")[0]
    assert finding.flag_code == "FACTORY_LICENSE_APPLICABILITY_UNKNOWN"
    assert finding.eval_state == "UNKNOWN"
    assert finding.score_impact == 0


def test_factory_license_rule_is_unknown_when_government_direction_is_not_known():
    output = _evaluate(
        is_manufacturing=True,
        factory_license_required_by_direction=None,
        factory_license_obtained=False,
    )
    finding = _flags(output, "LBR-001")[0]
    assert finding.flag_code == "FACTORY_LICENSE_GOVERNMENT_DIRECTION_UNKNOWN"
    assert finding.eval_state == "UNKNOWN"
    assert finding.score_impact == 0


def test_factory_license_rule_is_not_applicable_when_direction_confirms_no_licence_required():
    output = _evaluate(
        is_manufacturing=True,
        factory_license_required_by_direction=False,
        factory_license_obtained=False,
    )
    assert not _flags(output, "LBR-001")
    assert not _flags(output, "LBR-002")


def test_factory_license_missing_expiry_is_not_treated_as_current_or_expired():
    output = _evaluate(
        is_manufacturing=True,
        factory_license_required_by_direction=True,
        factory_license_obtained=True,
        factory_license_expiry=None,
    )
    finding = _flags(output, "LBR-002")[0]
    assert finding.flag_code == "FACTORY_LICENSE_EXPIRY_STATUS_UNKNOWN"
    assert finding.severity is Severity.NOT_EVALUATED
    assert finding.eval_state == "UNKNOWN"
    assert finding.score_impact == 0
