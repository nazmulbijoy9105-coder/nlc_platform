from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class RiskBand(str, Enum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"
    BLACK = "BLACK"


class RuleModuleEnum(str, Enum):
    BOARD_COMPOSITION = "BOARD_COMPOSITION"
    FINANCIAL_REPORTING = "FINANCIAL_REPORTING"
    SHAREHOLDER_MEETINGS = "SHAREHOLDER_MEETINGS"
    STATUTORY_FILINGS = "STATUTORY_FILINGS"
    CAPITAL_REQUIREMENTS = "CAPITAL_REQUIREMENTS"
    DIRECTORS_MEETINGS = "DIRECTORS_MEETINGS"
    CORPORATE_GOVERNANCE = "CORPORATE_GOVERNANCE"
    CHARGES_MORTGAGES = "CHARGES_MORTGAGES"
    MISCELLANEOUS = "MISCELLANEOUS"


@dataclass
class Rule:
    code: str
    name: str
    module: RuleModuleEnum
    description: str
    statutory_reference: str
    max_score: int
    criteria: list[dict[str, Any]]


@dataclass
class RuleResult:
    rule_code: str
    passed: bool
    score: int
    max_score: int
    details: str
    violation_details: str | None = None


@dataclass
class EvaluationResult:
    company_id: str
    total_score: int
    risk_band: RiskBand
    total_rules: int
    passed_rules: int
    failed_rules: int
    results: list[RuleResult]
    evaluated_at: datetime


ILRMF_RULES = [
    # Module 1: Board Composition (4 rules)
    Rule(
        code="BC-001",
        name="Minimum Directors",
        module=RuleModuleEnum.BOARD_COMPOSITION,
        description="Company must have at least 2 directors",
        statutory_reference="Companies Act 1994, Section 101",
        max_score=5,
        criteria=[
            {"type": "minimum", "value": 2, "field": "director_count"}
        ],
    ),
    Rule(
        code="BC-002",
        name="Director Qualification",
        module=RuleModuleEnum.BOARD_COMPOSITION,
        description="All directors must meet qualification criteria under Companies Act",
        statutory_reference="Companies Act 1994, Section 101",
        max_score=5,
        criteria=[
            {"type": "all_qualified", "field": "directors_qualified"}
        ],
    ),
    Rule(
        code="BC-003",
        name="Independent Directors",
        module=RuleModuleEnum.BOARD_COMPOSITION,
        description="Listed companies must have independent directors",
        statutory_reference="BSEC Corporate Governance Code",
        max_score=3,
        criteria=[
            {"type": "minimum", "value": 1, "field": "independent_directors"}
        ],
    ),
    Rule(
        code="BC-004",
        name="Board Diversity",
        module=RuleModuleEnum.BOARD_COMPOSITION,
        description="Board should have diverse representation",
        statutory_reference="Corporate Governance Best Practices",
        max_score=2,
        criteria=[
            {"type": "diversity", "field": "board_diversity_score"}
        ],
    ),
    # Module 2: Financial Reporting (4 rules)
    Rule(
        code="FR-001",
        name="Annual Financial Statements",
        module=RuleModuleEnum.FINANCIAL_REPORTING,
        description="Annual financial statements must be prepared and audited",
        statutory_reference="Companies Act 1994, Section 181",
        max_score=10,
        criteria=[
            {"type": "submitted", "field": "annual_statements_filed"}
        ],
    ),
    Rule(
        code="FR-002",
        name="Financial Statement Filing",
        module=RuleModuleEnum.FINANCIAL_REPORTING,
        description="Audited financial statements must be filed with RJSC",
        statutory_reference="Companies Act 1994, Section 184",
        max_score=10,
        criteria=[
            {"type": "within_deadline", "field": "fs_filing_date", "days": 30}
        ],
    ),
    Rule(
        code="FR-003",
        name="Cost Audit",
        module=RuleModuleEnum.FINANCIAL_REPORTING,
        description="Companies meeting threshold must conduct cost audit",
        statutory_reference="Companies Act 1994, Section 191",
        max_score=5,
        criteria=[
            {"type": "conditional", "field": "cost_audit_applicable"}
        ],
    ),
    Rule(
        code="FR-004",
        name="Related Party Transactions",
        module=RuleModuleEnum.FINANCIAL_REPORTING,
        description="RPTs must be disclosed and approved",
        statutory_reference="BSEC Notification",
        max_score=5,
        criteria=[
            {"type": "disclosed", "field": "rpt_disclosed"}
        ],
    ),
    # Module 3: Shareholder Meetings (3 rules)
    Rule(
        code="SM-001",
        name="Annual General Meeting",
        module=RuleModuleEnum.SHAREHOLDER_MEETINGS,
        description="AGM must be held within 15 months from last AGM",
        statutory_reference="Companies Act 1994, Section 81",
        max_score=10,
        criteria=[
            {"type": "within_deadline", "field": "agm_date", "months": 15}
        ],
    ),
    Rule(
        code="SM-002",
        name="EGM Convenience",
        module=RuleModuleEnum.SHAREHOLDER_MEETINGS,
        description="EGM must be called for material matters",
        statutory_reference="Companies Act 1994, Section 84",
        max_score=3,
        criteria=[
            {"type": "documentation", "field": "egm_documentation"}
        ],
    ),
    Rule(
        code="SM-003",
        name="Meeting Minutes",
        module=RuleModuleEnum.SHAREHOLDER_MEETINGS,
        description="Proper minutes must be maintained for all meetings",
        statutory_reference="Companies Act 1994, Section 86",
        max_score=2,
        criteria=[
            {"type": "maintained", "field": "minutes_maintained"}
        ],
    ),
    # Module 4: Statutory Filings (4 rules)
    Rule(
        code="SF-001",
        name="Annual Return Filing",
        module=RuleModuleEnum.STATUTORY_FILINGS,
        description="Annual return must be filed within 21 days of AGM",
        statutory_reference="Companies Act 1994, Section 165",
        max_score=10,
        criteria=[
            {"type": "within_deadline", "field": "annual_return_date", "days": 21}
        ],
    ),
    Rule(
        code="SF-002",
        name="Change of Directors",
        module=RuleModuleEnum.STATUTORY_FILINGS,
        description="Changes in directors must be filed within 30 days",
        statutory_reference="Companies Act 1994, Section 95",
        max_score=5,
        criteria=[
            {"type": "within_deadline", "field": "director_change_date", "days": 30}
        ],
    ),
    Rule(
        code="SF-03",
        name="Change of Registered Office",
        module=RuleModuleEnum.STATUTORY_FILINGS,
        description="Change of registered office must be notified to RJSC",
        statutory_reference="Companies Act 1994, Section 30",
        max_score=3,
        criteria=[
            {"type": "notification", "field": "registered_office_changed"}
        ],
    ),
    Rule(
        code="SF-04",
        name="Form 28 Filing",
        module=RuleModuleEnum.STATUTORY_FILINGS,
        description="Particulars of directors must be filed",
        statutory_reference="Companies Act 1994, Section 93",
        max_score=2,
        criteria=[
            {"type": "submitted", "field": "form28_filed"}
        ],
    ),
    # Module 5: Capital Requirements (3 rules)
    Rule(
        code="CR-001",
        name="Minimum Paid-up Capital",
        module=RuleModuleEnum.CAPITAL_REQUIREMENTS,
        description="Company must maintain minimum paid-up capital",
        statutory_reference="Companies Act 1994, Section 4",
        max_score=5,
        criteria=[
            {"type": "minimum", "value": 100000, "field": "paid_up_capital"}
        ],
    ),
    Rule(
        code="CR-002",
        name="Capital Maintenance",
        module=RuleModuleEnum.CAPITAL_REQUIREMENTS,
        description="Capital must be maintained as per law",
        statutory_reference="Companies Act 1994, Section 57",
        max_score=5,
        criteria=[
            {"type": "positive", "field": "net_assets"}
        ],
    ),
    Rule(
        code="CR-003",
        name="Increase of Capital",
        module=RuleModuleEnum.CAPITAL_REQUIREMENTS,
        description="Increase of authorized capital must be registered",
        statutory_reference="Companies Act 1994, Section 58",
        max_score=3,
        criteria=[
            {"type": "conditional", "field": "capital_increase_registered"}
        ],
    ),
    # Module 6: Directors Meetings (3 rules)
    Rule(
        code="DM-001",
        name="Board Meeting Frequency",
        module=RuleModuleEnum.DIRECTORS_MEETINGS,
        description="Board must meet at least 4 times per year",
        statutory_reference="Companies Act 1994, Section 86",
        max_score=5,
        criteria=[
            {"type": "minimum", "value": 4, "field": "board_meetings_per_year"}
        ],
    ),
    Rule(
        code="DM-002",
        name="Quorum Requirements",
        module=RuleModuleEnum.DIRECTORS_MEETINGS,
        description="Board meetings must maintain proper quorum",
        statutory_reference="Companies Act 1994, Section 86",
        max_score=3,
        criteria=[
            {"type": "quorum_met", "field": "quorum_maintained"}
        ],
    ),
    Rule(
        code="DM-003",
        name="Meeting Notices",
        module=RuleModuleEnum.DIRECTORS_MEETINGS,
        description="Proper notice must be given for board meetings",
        statutory_reference="Companies Act 1994, Section 86",
        max_score=2,
        criteria=[
            {"type": "notice_given", "field": "notice_period_met"}
        ],
    ),
    # Module 7: Corporate Governance (4 rules)
    Rule(
        code="CG-001",
        name="Audit Committee",
        module=RuleModuleEnum.CORPORATE_GOVERNANCE,
        description="Listed companies must have audit committee",
        statutory_reference="BSEC Corporate Governance Code",
        max_score=5,
        criteria=[
            {"type": "exists", "field": "audit_committee_exists"}
        ],
    ),
    Rule(
        code="CG-002",
        name="Statutory Audit",
        module=RuleModuleEnum.CORPORATE_GOVERNANCE,
        description="Company must appoint statutory auditor annually",
        statutory_reference="Companies Act 1994, Section 189",
        max_score=5,
        criteria=[
            {"type": "appointed", "field": "auditor_appointed"}
        ],
    ),
    Rule(
        code="CG-003",
        name="Internal Audit",
        module=RuleModuleEnum.CORPORATE_GOVERNANCE,
        description="Companies must have internal audit function",
        statutory_reference="BSEC Corporate Governance Code",
        max_score=3,
        criteria=[
            {"type": "conditional", "field": "internal_audit_required"}
        ],
    ),
    Rule(
        code="CG-004",
        name="Corporate Governance Compliance",
        module=RuleModuleEnum.CORPORATE_GOVERNANCE,
        description="Must comply with corporate governance code",
        statutory_reference="BSEC Corporate Governance Code",
        max_score=5,
        criteria=[
            {"type": "compliance_score", "field": "cg_compliance_score"}
        ],
    ),
    # Module 8: Charges & Mortgages (3 rules)
    Rule(
        code="CM-001",
        name="Charge Registration",
        module=RuleModuleEnum.CHARGES_MORTGAGES,
        description="Charges must be registered with RJSC within 30 days",
        statutory_reference="Companies Act 1994, Section 99",
        max_score=5,
        criteria=[
            {"type": "within_deadline", "field": "charge_registration_date", "days": 30}
        ],
    ),
    Rule(
        code="CM-002",
        name="Charge Modification",
        module=RuleModuleEnum.CHARGES_MORTGAGES,
        description="Modifications to charges must be filed",
        statutory_reference="Companies Act 1994, Section 99",
        max_score=3,
        criteria=[
            {"type": "conditional", "field": "charge_modification_filed"}
        ],
    ),
    Rule(
        code="CM-003",
        name="Charge Satisfaction",
        module=RuleModuleEnum.CHARGES_MORTGAGES,
        description="Satisfaction of charges must be registered",
        statutory_reference="Companies Act 1994, Section 99",
        max_score=2,
        criteria=[
            {"type": "conditional", "field": "charge_satisfaction_filed"}
        ],
    ),
    # Module 9: Miscellaneous (4 rules)
    Rule(
        code="MX-001",
        name="Register Maintenance",
        module=RuleModuleEnum.MISCELLANEOUS,
        description="Statutory registers must be properly maintained",
        statutory_reference="Companies Act 1994",
        max_score=3,
        criteria=[
            {"type": "maintained", "field": "registers_maintained"}
        ],
    ),
    Rule(
        code="MX-002",
        name="Company Seal",
        module=RuleModuleEnum.MISCELLANEOUS,
        description="Company seal must be properly used and maintained",
        statutory_reference="Companies Act 1994, Section 17",
        max_score=1,
        criteria=[
            {"type": "documented", "field": "seal_usage_documented"}
        ],
    ),
    Rule(
        code="MX-003",
        name="Books of Account",
        module=RuleModuleEnum.MISCELLANEOUS,
        description="Proper books of account must be kept",
        statutory_reference="Companies Act 1994, Section 179",
        max_score=5,
        criteria=[
            {"type": "proper", "field": "books_of_account"}
        ],
    ),
    Rule(
        code="MX-004",
        name="Business Continuity",
        module=RuleModuleEnum.MISCELLANEOUS,
        description="Company should have business continuity plans",
        statutory_reference="Best Practices",
        max_score=2,
        criteria=[
            {"type": "exists", "field": "bcp_exists"}
        ],
    ),
]


def calculate_risk_band(score: int) -> RiskBand:
    if score >= 80:
        return RiskBand.GREEN
    elif score >= 60:
        return RiskBand.YELLOW
    elif score >= 40:
        return RiskBand.RED
    else:
        return RiskBand.BLACK


def evaluate_company(company_data: dict[str, Any]) -> EvaluationResult:
    results: list[RuleResult] = []
    total_score = 0
    max_total_score = 0

    for rule in ILRMF_RULES:
        max_total_score += rule.max_score
        result = evaluate_rule(rule, company_data)
        results.append(result)
        total_score += result.score

    passed_rules = sum(1 for r in results if r.passed)
    failed_rules = len(results) - passed_rules
    risk_band = calculate_risk_band(total_score)

    return EvaluationResult(
        company_id=company_data.get("id", ""),
        total_score=total_score,
        risk_band=risk_band,
        total_rules=len(ILRMF_RULES),
        passed_rules=passed_rules,
        failed_rules=failed_rules,
        results=results,
        evaluated_at=datetime.now(timezone.utc),
    )


def evaluate_rule(rule: Rule, company_data: dict[str, Any]) -> RuleResult:
    passed = False
    details = "Compliant"
    violation_details = None

    for criterion in rule.criteria:
        check_type = criterion.get("type")
        field = criterion.get("field")
        value = criterion.get("value")

        field_value = company_data.get(field)

        if check_type == "minimum":
            if field_value is not None and field_value >= value:
                passed = True
            else:
                passed = False
                violation_details = f"Field '{field}' must be at least {value}, found: {field_value}"
                break

        elif check_type == "within_deadline":
            if field_value is not None:
                passed = True
            else:
                passed = False
                violation_details = f"Field '{field}' must be submitted within deadline"

        elif check_type == "submitted":
            if field_value is True or field_value == "true":
                passed = True
            else:
                passed = False
                violation_details = f"Field '{field}' must be submitted"

        elif check_type == "exists":
            if field_value is True or field_value == "true":
                passed = True
            else:
                passed = False
                violation_details = f"Required entity '{field}' does not exist"

        elif check_type == "all_qualified":
            if field_value is True or field_value == "true":
                passed = True
            else:
                passed = False
                violation_details = f"Not all directors meet qualification criteria"

        elif check_type == "positive":
            if field_value is not None and field_value > 0:
                passed = True
            else:
                passed = False
                violation_details = f"Field '{field}' must be positive"

        elif check_type == "conditional":
            if field_value is True or field_value == "true":
                passed = True

        elif check_type == "diversity":
            if field_value is not None and field_value >= 2:
                passed = True
            else:
                passed = False

        elif check_type == "disclosed":
            if field_value is True or field_value == "true":
                passed = True
            else:
                passed = False
                violation_details = f"Related party transactions not disclosed"

        elif check_type == "proper":
            if field_value is True or field_value == "true":
                passed = True
            else:
                passed = False
                violation_details = f"Books of account not properly maintained"

        elif check_type == "quorum_met":
            if field_value is True or field_value == "true":
                passed = True
            else:
                passed = False
                violation_details = f"Quorum requirements not met"

        elif check_type == "maintained":
            if field_value is True or field_value == "true":
                passed = True
            else:
                passed = False

        elif check_type == "appointed":
            if field_value is True or field_value == "true":
                passed = True
            else:
                passed = False

        elif check_type == "documented":
            if field_value is True or field_value == "true":
                passed = True
            else:
                passed = False

        elif check_type == "compliance_score":
            if field_value is not None and field_value >= 70:
                passed = True
            else:
                passed = False

        elif check_type == "notification":
            if field_value is True or field_value == "true":
                passed = True
            else:
                passed = False

        elif check_type == "notice_given":
            if field_value is True or field_value == "true":
                passed = True
            else:
                passed = False

    score = rule.max_score if passed else 0

    return RuleResult(
        rule_code=rule.code,
        passed=passed,
        score=score,
        max_score=rule.max_score,
        details=details,
        violation_details=violation_details,
    )


def get_rules_by_module(module: RuleModuleEnum) -> list[Rule]:
    return [rule for rule in ILRMF_RULES if rule.module == module]


def get_all_rules() -> list[Rule]:
    return ILRMF_RULES
