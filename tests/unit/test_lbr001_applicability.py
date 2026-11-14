"""Labour licensing applies by establishment category and verified evidence, not manufacturing alone."""

from datetime import date

import pytest

from app.rule_engine.engine import RuleState, Severity


@pytest.mark.parametrize("manufacturing", [True, False, None])
def test_lbr001_scope_unknown_for_every_manufacturing_state(
    rule_engine, build_profile, manufacturing
):
    output = rule_engine.evaluate(build_profile(is_manufacturing=manufacturing))
    finding = next(flag for flag in output.flags if flag.rule_id == "LBR-001")

    assert finding.flag_code == "LABOUR_LICENSE_SCOPE_NOT_VERIFIED"
    assert finding.state is RuleState.UNKNOWN
    assert finding.eval_state == "UNKNOWN"
    assert finding.severity is Severity.NOT_EVALUATED
    assert finding.score_impact == 0
    assert finding.detail["is_manufacturing_is_not_the_licensing_test"] is True


def test_lbr001_verified_non_applicable_category_does_not_trigger(
    rule_engine, build_profile
):
    output = rule_engine.evaluate(build_profile(
        is_manufacturing=False,
        labour_establishment_category="SERVICE_OFFICE_NOT_IN_RULE_354_CATEGORIES",
        labour_license_scope_verified=True,
        labour_license_scope_evidence_ref="LEGAL-SCOPE-001",
        labour_license_scope_verified_at=date(2026, 11, 10),
        labour_license_scope_verified_by="counsel-reviewer",
        factory_license_required_by_direction=False,
    ))

    assert not any(flag.rule_id == "LBR-001" for flag in output.flags)
    assert not any(flag.rule_id == "LBR-002" for flag in output.flags)


def test_lbr001_verified_applicable_category_with_verified_missing_licence_requires_review(
    rule_engine, build_profile
):
    output = rule_engine.evaluate(build_profile(
        is_manufacturing=False,
        labour_establishment_category="COMMERCIAL_ESTABLISHMENT",
        labour_license_scope_verified=True,
        labour_license_scope_evidence_ref="LEGAL-SCOPE-002",
        labour_license_scope_verified_at=date(2026, 11, 10),
        labour_license_scope_verified_by="counsel-reviewer",
        factory_license_required_by_direction=True,
        labour_license_status_verified=True,
        labour_license_status_evidence_ref="DIFE-SEARCH-002",
        labour_license_status_verified_at=date(2026, 11, 12),
        labour_license_status_verified_by="compliance-reviewer",
        factory_license_obtained=False,
    ))
    finding = next(flag for flag in output.flags if flag.rule_id == "LBR-001")

    assert finding.flag_code == "LABOUR_LICENSE_NOT_OBTAINED_REQUIRES_REVIEW"
    assert finding.state is RuleState.REQUIRES_LAWYER_JUDGMENT
    assert finding.severity is Severity.NOT_EVALUATED
    assert finding.score_impact == 0


def test_lbr001_does_not_infer_missing_licence_from_unverified_status(
    rule_engine, build_profile
):
    output = rule_engine.evaluate(build_profile(
        labour_establishment_category="INDUSTRIAL_ESTABLISHMENT",
        labour_license_scope_verified=True,
        labour_license_scope_evidence_ref="LEGAL-SCOPE-003",
        labour_license_scope_verified_at=date(2026, 11, 10),
        labour_license_scope_verified_by="counsel-reviewer",
        factory_license_required_by_direction=True,
        factory_license_obtained=False,
    ))
    finding = next(flag for flag in output.flags if flag.rule_id == "LBR-001")

    assert finding.flag_code == "LABOUR_LICENSE_STATUS_NOT_VERIFIED"
    assert finding.state is RuleState.UNKNOWN
    assert finding.score_impact == 0


def test_lbr002_uses_printed_expiry_and_does_not_calculate_renewal_term(
    rule_engine, build_profile
):
    output = rule_engine.evaluate(build_profile(
        labour_establishment_category="CONTRACTOR_ESTABLISHMENT",
        labour_license_scope_verified=True,
        labour_license_scope_evidence_ref="LEGAL-SCOPE-004",
        labour_license_scope_verified_at=date(2026, 11, 10),
        labour_license_scope_verified_by="counsel-reviewer",
        factory_license_required_by_direction=True,
        labour_license_status_verified=True,
        labour_license_status_evidence_ref="DIFE-LICENCE-004",
        labour_license_status_verified_at=date(2026, 11, 12),
        labour_license_status_verified_by="compliance-reviewer",
        factory_license_obtained=True,
        factory_license_expiry=date(2026, 10, 31),
    ))
    finding = next(flag for flag in output.flags if flag.rule_id == "LBR-002")

    assert finding.flag_code == "LABOUR_LICENSE_EXPIRED_REQUIRES_REVIEW"
    assert finding.state is RuleState.REQUIRES_LAWYER_JUDGMENT
    assert finding.severity is Severity.NOT_EVALUATED
    assert finding.score_impact == 0
    assert finding.detail["renewal_term_calculated_automatically"] is False


def test_lbr002_missing_printed_expiry_is_unknown(rule_engine, build_profile):
    output = rule_engine.evaluate(build_profile(
        labour_establishment_category="SHOP",
        labour_license_scope_verified=True,
        labour_license_scope_evidence_ref="LEGAL-SCOPE-005",
        labour_license_scope_verified_at=date(2026, 11, 10),
        labour_license_scope_verified_by="counsel-reviewer",
        factory_license_required_by_direction=True,
        labour_license_status_verified=True,
        labour_license_status_evidence_ref="DIFE-LICENCE-005",
        labour_license_status_verified_at=date(2026, 11, 12),
        labour_license_status_verified_by="compliance-reviewer",
        factory_license_obtained=True,
        factory_license_expiry=None,
    ))
    finding = next(flag for flag in output.flags if flag.rule_id == "LBR-002")

    assert finding.flag_code == "LABOUR_LICENSE_EXPIRY_NOT_VERIFIED"
    assert finding.state is RuleState.UNKNOWN
    assert finding.score_impact == 0
