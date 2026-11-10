"""Company-law coverage map for the NLC company workspace.

This is a product coverage taxonomy, not a statutory rule registry. Rule IDs
remain in the statutory catalogue; this module organizes company records,
events and conditional activation for continuous monitoring.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping


class CoverageLayer(str, Enum):
    CORE = "CORE"
    CONDITIONAL = "CONDITIONAL"


class Applicability(str, Enum):
    ACTIVE = "ACTIVE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class LegalCoverageDomain:
    domain_id: str
    title: str
    layer: CoverageLayer
    record_types: tuple[str, ...]
    event_types: tuple[str, ...]
    rule_prefixes: tuple[str, ...] = ()
    activation_facts: tuple[str, ...] = ()


CORE_DOMAINS: tuple[LegalCoverageDomain, ...] = (
    LegalCoverageDomain("INCORPORATION", "Incorporation and constitution", CoverageLayer.CORE,
        ("COMPANY_PROFILE", "INCORPORATION_CERTIFICATE", "MOA", "AOA", "CONSTITUTIONAL_AMENDMENT"),
        ("COMPANY_INCORPORATED", "CONSTITUTION_AMENDED"), ("INC-",)),
    LegalCoverageDomain("MEMBERSHIP", "Membership and ownership", CoverageLayer.CORE,
        ("MEMBER", "MEMBERS_REGISTER", "BENEFICIAL_OWNERSHIP_RECORD"),
        ("MEMBER_ADMITTED", "MEMBER_CEASED", "OWNERSHIP_CHANGED"), ("MEM-", "REG-")),
    LegalCoverageDomain("SHARE_CAPITAL", "Share capital and allotments", CoverageLayer.CORE,
        ("SHARE_CLASS", "CAPITAL_STRUCTURE", "ALLOTMENT", "SHARE_CERTIFICATE"),
        ("SHARES_ALLOTTED", "CAPITAL_INCREASED", "CAPITAL_ALTERED"), ("SH-", "CAP-")),
    LegalCoverageDomain("SHARE_TRANSFERS", "Share transfers", CoverageLayer.CORE,
        ("TRANSFER_INSTRUMENT", "STAMP_EVIDENCE", "TRANSFER_APPROVAL", "SHARE_REGISTER_ENTRY"),
        ("TRANSFER_EXECUTED", "TRANSFER_LODGED", "TRANSFER_REGISTERED", "TRANSFER_REFUSED"), ("TR-",)),
    LegalCoverageDomain("DIRECTORS", "Directors and officers", CoverageLayer.CORE,
        ("DIRECTOR", "DIRECTOR_CONSENT", "DIRECTOR_APPOINTMENT", "DIRECTOR_CESSATION", "FORM_IX", "FORM_XII"),
        ("DIRECTOR_APPOINTED", "DIRECTOR_CONSENTED", "DIRECTOR_CEASED", "DIRECTOR_DETAILS_CHANGED"), ("DIR-", "DEF-")),
    LegalCoverageDomain("AGM", "Annual general meetings", CoverageLayer.CORE,
        ("AGM", "AGM_NOTICE", "AGM_CONSENT", "AGM_ATTENDANCE", "AGM_MINUTES"),
        ("AGM_SCHEDULED", "AGM_NOTICE_SENT", "AGM_HELD", "AGM_ADJOURNED"), ("AGM-",)),
    LegalCoverageDomain("BOARD", "Board meetings and decisions", CoverageLayer.CORE,
        ("BOARD_MEETING", "BOARD_NOTICE", "BOARD_ATTENDANCE", "BOARD_RESOLUTION", "BOARD_MINUTES"),
        ("BOARD_MEETING_SCHEDULED", "BOARD_NOTICE_SENT", "BOARD_MEETING_HELD", "BOARD_RESOLUTION_PASSED"), ("BOD-",)),
    LegalCoverageDomain("AUDIT", "Auditor and audit", CoverageLayer.CORE,
        ("AUDITOR", "AUDITOR_APPOINTMENT", "AUDIT_REPORT", "AUDIT_COMPLETION"),
        ("AUDITOR_APPOINTED", "AUDITOR_REAPPOINTED", "AUDITOR_RESIGNED", "AUDIT_COMPLETED"), ("AUD-",)),
    LegalCoverageDomain("ACCOUNTS", "Books and financial statements", CoverageLayer.CORE,
        ("ACCOUNTING_PERIOD", "BOOKS_OF_ACCOUNT", "FINANCIAL_STATEMENT", "BOARD_APPROVAL"),
        ("FINANCIAL_YEAR_CLOSED", "ACCOUNTS_PREPARED", "ACCOUNTS_APPROVED", "STATEMENTS_PRESENTED"), ("ACC-",)),
    LegalCoverageDomain("ANNUAL_RETURNS", "Annual returns and RJSC filings", CoverageLayer.CORE,
        ("SCHEDULE_X", "ANNUAL_RETURN", "RJSC_FILING", "RJSC_ACKNOWLEDGEMENT"),
        ("ANNUAL_RETURN_DUE", "ANNUAL_RETURN_SUBMITTED", "ANNUAL_RETURN_ACCEPTED", "ANNUAL_RETURN_REJECTED"), ("AR-",)),
    LegalCoverageDomain("STATUTORY_REGISTERS", "Statutory registers and minutes", CoverageLayer.CORE,
        ("MEMBERS_REGISTER", "DIRECTOR_RECORDS", "CHARGES_REGISTER", "MEETING_MINUTES"),
        ("REGISTER_ENTRY_ADDED", "REGISTER_CORRECTED", "REGISTER_LOCATION_CHANGED"), ("REG-",)),
    LegalCoverageDomain("CHARGES", "Company charges", CoverageLayer.CORE,
        ("CHARGE_INSTRUMENT", "CHARGE_RECORD", "CHARGE_MODIFICATION", "CHARGE_SATISFACTION"),
        ("CHARGE_CREATED", "CHARGE_MODIFIED", "CHARGE_SATISFIED"), ("CHG-", "CAP-")),
    LegalCoverageDomain("REGISTERED_OFFICE", "Registered office", CoverageLayer.CORE,
        ("REGISTERED_OFFICE", "OFFICE_CHANGE_RESOLUTION", "OFFICE_FILING_RECEIPT"),
        ("REGISTERED_OFFICE_CHANGED",), ("OFF-",)),
    LegalCoverageDomain("WINDING_UP", "Corporate winding-up and liquidation", CoverageLayer.CORE,
        ("WINDING_UP_PETITION", "COURT_ORDER", "LIQUIDATOR_APPOINTMENT", "LIQUIDATION_NOTICE"),
        ("WINDING_UP_PETITION_FILED", "WINDING_UP_ORDER_MADE", "LIQUIDATOR_APPOINTED", "COMPANY_RESTORED"),
        ("BNK-", "STR-")),
)


CONDITIONAL_DOMAINS: tuple[LegalCoverageDomain, ...] = (
    LegalCoverageDomain("INCOME_TAX", "Income tax and NBR", CoverageLayer.CONDITIONAL,
        ("TIN", "TAX_RETURN", "TAX_PAYMENT", "TAX_ASSESSMENT"),
        ("TAX_PERIOD_CLOSED", "TAX_RETURN_DUE", "TAX_RETURN_FILED"),
        ("TAX-",), ("taxpayer_status_verified", "income_tax_return_duty_verified")),
    LegalCoverageDomain("VAT", "VAT and supplementary duty", CoverageLayer.CONDITIONAL,
        ("BIN", "VAT_REGISTRATION", "VAT_RETURN", "VAT_INVOICE", "VAT_PAYMENT"),
        ("VAT_TAX_PERIOD_CLOSED", "VAT_RETURN_DUE", "VAT_RETURN_FILED"),
        ("VAT-",), ("taxable_supply_verified", "mandatory_vat_registration_verified")),
    LegalCoverageDomain("LABOUR", "Labour law", CoverageLayer.CONDITIONAL,
        ("EMPLOYEE_ROSTER", "ESTABLISHMENT_CLASS", "LABOUR_LICENCE", "LABOUR_REGISTER"),
        ("EMPLOYEE_COUNT_CHANGED", "ESTABLISHMENT_CLASS_CHANGED", "LABOUR_LICENCE_EXPIRED"),
        ("LBR-",), ("covered_employer_status_verified", "labour_direction_applicability_verified")),
    LegalCoverageDomain("TRADE_LICENCE", "Trade licence", CoverageLayer.CONDITIONAL,
        ("BUSINESS_PREMISES", "TRADE_LICENCE", "TRADE_LICENCE_RECEIPT"),
        ("BUSINESS_STARTED", "TRADE_LICENCE_ISSUED", "TRADE_LICENCE_EXPIRED"),
        ("TL-",), ("trade_licence_required_verified",)),
    LegalCoverageDomain("FIRE_SAFETY", "Fire safety and fire licence", CoverageLayer.CONDITIONAL,
        ("PREMISES", "FIRE_LICENCE", "FIRE_INSPECTION", "FIRE_NOC"),
        ("PREMISES_OPENED", "FIRE_LICENCE_ISSUED", "FIRE_LICENCE_EXPIRED"),
        (), ("fire_licence_required_verified",)),
    LegalCoverageDomain("ENVIRONMENT", "Environmental clearance", CoverageLayer.CONDITIONAL,
        ("ENVIRONMENTAL_CLASSIFICATION", "ENVIRONMENT_CLEARANCE", "ENVIRONMENTAL_CONDITIONS"),
        ("ACTIVITY_CHANGED", "ENVIRONMENT_CLEARANCE_ISSUED", "ENVIRONMENT_CLEARANCE_EXPIRED"),
        (), ("environmental_clearance_required_verified",)),
    LegalCoverageDomain("SECTOR_LICENCES", "Sector-specific licences", CoverageLayer.CONDITIONAL,
        ("SECTOR_CLASSIFICATION", "SECTOR_LICENCE", "SECTOR_REGULATOR_APPROVAL"),
        ("REGULATED_ACTIVITY_STARTED", "SECTOR_LICENCE_ISSUED", "SECTOR_LICENCE_EXPIRED"),
        (), ("regulated_sector_activity_verified",)),
    LegalCoverageDomain("FOREIGN_INVESTMENT_FX", "Foreign investment and foreign exchange", CoverageLayer.CONDITIONAL,
        ("FOREIGN_SHAREHOLDER", "INVESTMENT_APPROVAL", "REMITTANCE_RECORD", "BANK_CERTIFICATE"),
        ("FOREIGN_INVESTMENT_RECEIVED", "CAPITAL_REMITTANCE_MADE", "FOREIGN_SHARE_TRANSFERRED"),
        ("FX-", "INC-"), ("foreign_investor_or_transaction_verified",)),
    LegalCoverageDomain("BANGLADESH_BANK", "Bangladesh Bank requirements", CoverageLayer.CONDITIONAL,
        ("REGULATED_ENTITY_STATUS", "BB_APPROVAL", "BB_RETURN", "BANK_DIRECTION"),
        ("REGULATED_STATUS_CHANGED", "BB_DIRECTION_RECEIVED", "BB_RETURN_DUE"),
        (), ("bangladesh_bank_regulated_activity_verified",)),
    LegalCoverageDomain("BSEC", "BSEC and securities-market requirements", CoverageLayer.CONDITIONAL,
        ("LISTED_ISSUER_STATUS", "SECURITIES_ISSUE", "BSEC_APPROVAL", "BSEC_DISCLOSURE"),
        ("SECURITIES_ISSUED", "LISTING_GRANTED", "LISTING_SUSPENDED", "BSEC_DIRECTION_RECEIVED"),
        ("BSEC-",), ("bsec_scope_or_issuer_status_verified",)),
    LegalCoverageDomain("COURT_REGULATOR_ORDERS", "Court and regulator directions", CoverageLayer.CONDITIONAL,
        ("COURT_ORDER", "REGULATOR_DIRECTION", "SERVICE_EVIDENCE", "COMPLIANCE_RESPONSE"),
        ("ORDER_RECEIVED", "ORDER_SERVED", "ORDER_DEADLINE_CHANGED", "ORDER_DISCHARGED"),
        (), ("operative_order_or_direction_verified",)),
)


ALL_DOMAINS = {domain.domain_id: domain for domain in (*CORE_DOMAINS, *CONDITIONAL_DOMAINS)}
if len(ALL_DOMAINS) != len(CORE_DOMAINS) + len(CONDITIONAL_DOMAINS):
    raise RuntimeError("Duplicate legal coverage domain ID")


def evaluate_domain_applicability(
    domain: LegalCoverageDomain,
    company_facts: Mapping[str, bool | None],
    *,
    company_type: str | None,
) -> Applicability:
    """Resolve domain activation without converting missing facts into True."""
    if domain.layer is CoverageLayer.CORE:
        if company_type is None:
            return Applicability.UNKNOWN
        return (
            Applicability.ACTIVE
            if company_type.upper() in {"PRIVATE_LIMITED", "PRIVATE_COMPANY"}
            else Applicability.NOT_APPLICABLE
        )
    if not domain.activation_facts:
        return Applicability.UNKNOWN
    values = [company_facts.get(key) for key in domain.activation_facts]
    if any(value is True for value in values):
        return Applicability.ACTIVE
    if all(value is False for value in values):
        return Applicability.NOT_APPLICABLE
    return Applicability.UNKNOWN
