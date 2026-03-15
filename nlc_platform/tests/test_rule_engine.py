import pytest

from app.rule_engine.engine import (
    ILRMF_RULES,
    calculate_risk_band,
    evaluate_company,
    evaluate_rule,
    get_rules_by_module,
    RiskBand,
    RuleModuleEnum,
)


class TestRiskBandCalculation:
    def test_green_band(self):
        assert calculate_risk_band(100) == RiskBand.GREEN
        assert calculate_risk_band(80) == RiskBand.GREEN

    def test_yellow_band(self):
        assert calculate_risk_band(79) == RiskBand.YELLOW
        assert calculate_risk_band(60) == RiskBand.YELLOW

    def test_red_band(self):
        assert calculate_risk_band(59) == RiskBand.RED
        assert calculate_risk_band(40) == RiskBand.RED

    def test_black_band(self):
        assert calculate_risk_band(39) == RiskBand.BLACK
        assert calculate_risk_band(0) == RiskBand.BLACK


class TestRuleEngine:
    def test_total_rules_count(self):
        assert len(ILRMF_RULES) == 32

    def test_rules_per_module(self):
        for module in RuleModuleEnum:
            rules = get_rules_by_module(module)
            assert len(rules) > 0, f"Module {module} has no rules"

    def test_board_composition_rules(self):
        rules = get_rules_by_module(RuleModuleEnum.BOARD_COMPOSITION)
        assert len(rules) == 4

    def test_financial_reporting_rules(self):
        rules = get_rules_by_module(RuleModuleEnum.FINANCIAL_REPORTING)
        assert len(rules) == 4

    def test_shareholder_meetings_rules(self):
        rules = get_rules_by_module(RuleModuleEnum.SHAREHOLDER_MEETINGS)
        assert len(rules) == 3


class TestCompanyEvaluation:
    def test_fully_compliant_company(self):
        company_data = {
            "id": "test-1",
            "director_count": 3,
            "directors_qualified": True,
            "independent_directors": 1,
            "board_diversity_score": 2,
            "annual_statements_filed": True,
            "fs_filing_date": True,
            "cost_audit_applicable": False,
            "rpt_disclosed": True,
            "agm_date": True,
            "egm_documentation": True,
            "minutes_maintained": True,
            "annual_return_date": True,
            "director_change_date": True,
            "registered_office_changed": True,
            "form28_filed": True,
            "paid_up_capital": 100000,
            "net_assets": 500000,
            "capital_increase_registered": True,
            "board_meetings_per_year": 6,
            "quorum_maintained": True,
            "notice_period_met": True,
            "audit_committee_exists": True,
            "auditor_appointed": True,
            "internal_audit_required": False,
            "cg_compliance_score": 80,
            "charge_registration_date": True,
            "charge_modification_filed": True,
            "charge_satisfaction_filed": True,
            "registers_maintained": True,
            "seal_usage_documented": True,
            "books_of_account": True,
            "bcp_exists": True,
        }

        result = evaluate_company(company_data)

        assert result.risk_band == RiskBand.GREEN
        assert result.total_rules == 32
        assert result.passed_rules > 25

    def test_non_compliant_company(self):
        company_data = {
            "id": "test-2",
            "director_count": 1,
            "directors_qualified": False,
            "independent_directors": 0,
            "board_diversity_score": 1,
            "annual_statements_filed": False,
            "fs_filing_date": False,
            "cost_audit_applicable": False,
            "rpt_disclosed": False,
            "agm_date": False,
            "egm_documentation": False,
            "minutes_maintained": False,
            "annual_return_date": False,
            "director_change_date": False,
            "registered_office_changed": False,
            "form28_filed": False,
            "paid_up_capital": 10000,
            "net_assets": -5000,
            "capital_increase_registered": False,
            "board_meetings_per_year": 1,
            "quorum_maintained": False,
            "notice_period_met": False,
            "audit_committee_exists": False,
            "auditor_appointed": False,
            "internal_audit_required": False,
            "cg_compliance_score": 20,
            "charge_registration_date": False,
            "charge_modification_filed": False,
            "charge_satisfaction_filed": False,
            "registers_maintained": False,
            "seal_usage_documented": False,
            "books_of_account": False,
            "bcp_exists": False,
        }

        result = evaluate_company(company_data)

        assert result.risk_band in [RiskBand.RED, RiskBand.BLACK]
        assert result.passed_rules < 10


class TestRuleEvaluation:
    def test_minimum_directors_rule(self):
        rule = next(r for r in ILRMF_RULES if r.code == "BC-001")

        company_pass = {"director_count": 3}
        result_pass = evaluate_rule(rule, company_pass)
        assert result_pass.passed is True
        assert result_pass.score == rule.max_score

        company_fail = {"director_count": 1}
        result_fail = evaluate_rule(rule, company_fail)
        assert result_fail.passed is False
        assert result_fail.score == 0

    def test_capital_requirement(self):
        rule = next(r for r in ILRMF_RULES if r.code == "CR-001")

        company_pass = {"paid_up_capital": 100000}
        result_pass = evaluate_rule(rule, company_pass)
        assert result_pass.passed is True

        company_fail = {"paid_up_capital": 50000}
        result_fail = evaluate_rule(rule, company_fail)
        assert result_fail.passed is False

    def test_agm_rule(self):
        rule = next(r for r in ILRMF_RULES if r.code == "SM-001")

        company_pass = {"agm_date": True}
        result_pass = evaluate_rule(rule, company_pass)
        assert result_pass.passed is True

        company_fail = {"agm_date": False}
        result_fail = evaluate_rule(rule, company_fail)
        assert result_fail.passed is False


class TestRuleStructure:
    def test_all_rules_have_codes(self):
        for rule in ILRMF_RULES:
            assert rule.code is not None
            assert len(rule.code) > 0

    def test_all_rules_have_max_score(self):
        for rule in ILRMF_RULES:
            assert rule.max_score > 0

    def test_all_rules_have_statutory_reference(self):
        for rule in ILRMF_RULES:
            assert rule.statutory_reference is not None
            assert len(rule.statutory_reference) > 0
