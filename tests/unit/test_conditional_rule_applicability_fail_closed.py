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


def test_labour_licence_scope_is_unknown_regardless_of_manufacturing_status():
    for manufacturing in (True, False, None):
        output = _evaluate(is_manufacturing=manufacturing)
        finding = _flags(output, "LBR-001")[0]
        assert finding.flag_code == "LABOUR_LICENSE_SCOPE_NOT_VERIFIED"
        assert finding.severity is Severity.NOT_EVALUATED
        assert finding.eval_state == "UNKNOWN"
        assert finding.score_impact == 0


def test_labour_licence_direction_is_unknown_after_scope_review():
    output = _evaluate(
        labour_establishment_category="COMMERCIAL_ESTABLISHMENT",
        labour_license_scope_verified=True,
        labour_license_scope_evidence_ref="LEGAL-SCOPE-001",
        labour_license_scope_verified_at=date(2026, 11, 10),
        labour_license_scope_verified_by="reviewer",
        factory_license_required_by_direction=None,
    )
    finding = _flags(output, "LBR-001")[0]
    assert finding.flag_code == "LABOUR_LICENSE_REQUIREMENT_UNKNOWN"
    assert finding.eval_state == "UNKNOWN"
    assert finding.score_impact == 0


def test_labour_licence_rule_is_not_applicable_only_after_verified_scope_review():
    output = _evaluate(
        labour_establishment_category="SERVICE_OFFICE_NOT_IN_RULE_354_CATEGORIES",
        labour_license_scope_verified=True,
        labour_license_scope_evidence_ref="LEGAL-SCOPE-002",
        labour_license_scope_verified_at=date(2026, 11, 10),
        labour_license_scope_verified_by="reviewer",
        factory_license_required_by_direction=False,
    )
    assert not _flags(output, "LBR-001")
    assert not _flags(output, "LBR-002")


def test_labour_licence_missing_printed_expiry_is_unknown():
    output = _evaluate(
        labour_establishment_category="SHOP",
        labour_license_scope_verified=True,
        labour_license_scope_evidence_ref="LEGAL-SCOPE-003",
        labour_license_scope_verified_at=date(2026, 11, 10),
        labour_license_scope_verified_by="reviewer",
        factory_license_required_by_direction=True,
        labour_license_status_verified=True,
        labour_license_status_evidence_ref="DIFE-LICENCE-003",
        labour_license_status_verified_at=date(2026, 11, 12),
        labour_license_status_verified_by="reviewer",
        factory_license_obtained=True,
        factory_license_expiry=None,
    )
    finding = _flags(output, "LBR-002")[0]
    assert finding.flag_code == "LABOUR_LICENSE_EXPIRY_NOT_VERIFIED"
    assert finding.severity is Severity.NOT_EVALUATED
    assert finding.eval_state == "UNKNOWN"
    assert finding.score_impact == 0
