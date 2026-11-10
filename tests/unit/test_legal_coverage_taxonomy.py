"""Coverage taxonomy tests: core company-law domains vs conditional regimes."""

from canonical_architecture.legal_coverage import (
    ALL_DOMAINS,
    CORE_DOMAINS,
    CONDITIONAL_DOMAINS,
    Applicability,
    CoverageLayer,
    evaluate_domain_applicability,
)


def test_coverage_taxonomy_contains_core_company_law_domains():
    required = {
        "INCORPORATION", "MEMBERSHIP", "SHARE_CAPITAL", "SHARE_TRANSFERS",
        "DIRECTORS", "AGM", "BOARD", "AUDIT", "ACCOUNTS", "ANNUAL_RETURNS",
        "STATUTORY_REGISTERS", "CHARGES", "REGISTERED_OFFICE", "WINDING_UP",
    }
    assert required <= set(ALL_DOMAINS)
    assert all(domain.layer is CoverageLayer.CORE for domain in CORE_DOMAINS)


def test_conditional_regimes_are_not_activated_by_missing_facts():
    bsec = ALL_DOMAINS["BSEC"]
    assert bsec.layer is CoverageLayer.CONDITIONAL
    assert evaluate_domain_applicability(
        bsec, {"bsec_scope_or_issuer_status_verified": None},
        company_type="PRIVATE_LIMITED",
    ) is Applicability.UNKNOWN
    assert evaluate_domain_applicability(
        bsec, {"bsec_scope_or_issuer_status_verified": False},
        company_type="PRIVATE_LIMITED",
    ) is Applicability.NOT_APPLICABLE
    assert evaluate_domain_applicability(
        bsec, {"bsec_scope_or_issuer_status_verified": True},
        company_type="PRIVATE_LIMITED",
    ) is Applicability.ACTIVE


def test_conditional_domain_uses_any_verified_activation_fact():
    vat = ALL_DOMAINS["VAT"]
    assert evaluate_domain_applicability(
        vat,
        {
            "taxable_supply_verified": True,
            "mandatory_vat_registration_verified": None,
        },
        company_type="PRIVATE_LIMITED",
    ) is Applicability.ACTIVE


def test_core_domain_requires_known_private_company_type():
    agm = ALL_DOMAINS["AGM"]
    assert evaluate_domain_applicability(
        agm, {}, company_type=None
    ) is Applicability.UNKNOWN
    assert evaluate_domain_applicability(
        agm, {}, company_type="PRIVATE_LIMITED"
    ) is Applicability.ACTIVE
    assert evaluate_domain_applicability(
        agm, {}, company_type="PUBLIC_LIMITED"
    ) is Applicability.NOT_APPLICABLE
