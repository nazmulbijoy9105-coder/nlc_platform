"""Service layer tests — handles missing DATABASE_URL."""

class TestCompanyService:
    def test_exists(self):
        from app.services.company_service import CompanyService
        assert CompanyService is not None

    def test_has_build_profile(self):
        from app.services.company_service import CompanyService
        assert hasattr(CompanyService, "build_company_profile")


class TestComplianceService:
    def test_exists(self):
        from app.services.compliance_service import ComplianceService
        assert ComplianceService is not None

    def test_has_evaluate(self):
        from app.services.compliance_service import ComplianceService
        assert hasattr(ComplianceService, "evaluate_company")

    def test_has_get_flags(self):
        from app.services.compliance_service import ComplianceService
        assert hasattr(ComplianceService, "get_active_flags")


class TestUserService:
    def test_exists(self):
        from app.services.user_service import UserService
        assert UserService is not None

    def test_has_verify_credentials(self):
        from app.services.user_service import UserService
        assert hasattr(UserService, "verify_credentials")

    def test_has_lockout(self):
        from app.services.user_service import UserService
        assert hasattr(UserService, "check_lockout")

    def test_has_2fa(self):
        from app.services.user_service import UserService
        assert hasattr(UserService, "setup_totp")


class TestRJSCFormService:
    def test_exists(self):
        from app.services.rjsc_form_service import RJSCFormService
        assert RJSCFormService is not None

    def test_has_methods(self):
        from app.services.rjsc_form_service import RJSCFormService
        assert hasattr(RJSCFormService, "get_forms_for_company")


class TestRescueService:
    def test_exists(self):
        from app.services.rescue_service import RescueService
        assert RescueService is not None

    def test_has_get_active_plan(self):
        from app.services.rescue_service import RescueService
        assert hasattr(RescueService, "get_active_plan")


class TestRulesService:
    def test_exists(self):
        from app.services.rules_service import RulesService
        assert RulesService is not None

    def test_has_get_by_rule_id(self):
        from app.services.rules_service import RulesService
        assert hasattr(RulesService, "get_by_rule_id")
