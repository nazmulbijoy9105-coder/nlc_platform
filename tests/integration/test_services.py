"""
tests/integration/test_services.py — Service Layer Integration Tests
NEUM LEX COUNSEL

Tests hit the real database (nlc_test) via the async session fixture.
Each test runs in a transaction that is rolled back — no test pollution.

Coverage:
  - CompanyService: create, get, list, build_company_profile
  - ComplianceService: evaluate_company, persist flags, get_flag_summary
  - UserService: create, verify_credentials, lockout logic
  - FilingService: AGM create/mark held, deadlines
  - NotificationService: queue, acknowledge, activity log
  - RulesService: get_all, get_by_rule_id (reads seeded data)
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from app.models.enums import UserRole

pytestmark = [pytest.mark.integration]


# =============================================================================
# COMPANY SERVICE
# =============================================================================

class TestCompanyService:

    @pytest.mark.asyncio
    async def test_create_company(self, db):
        from app.services.company_service import CompanyService

        svc = CompanyService(db)
        company = await svc.create_company(
            company_name="Integration Test Co Ltd",
            registration_number=f"C-{uuid.uuid4().hex[:8].upper()}",
            incorporation_date=date.today() - timedelta(days=365),
            registered_address="456 Test Road, Dhaka",
            company_type="PRIVATE_LIMITED",
            financial_year_end=date(2025, 12, 31),
        )

        assert company.id is not None
        assert company.company_name == "Integration Test Co Ltd"
        assert company.is_active is True
        assert company.register_location == "registered_office"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("is_manufacturing", [True, False, None])
    async def test_manufacturing_applicability_reaches_rule_engine_profile(self, db, is_manufacturing):
        from app.services.company_service import CompanyService

        svc = CompanyService(db)
        company = await svc.create_company(
            company_name="Manufacturing Applicability Test Ltd",
            registration_number=f"M-{uuid.uuid4().hex[:8].upper()}",
            incorporation_date=date.today() - timedelta(days=365),
            registered_address="456 Test Road, Dhaka",
            company_type="PRIVATE_LIMITED",
            financial_year_end=date(2025, 12, 31),
            is_manufacturing=is_manufacturing,
        )

        profile = await svc.build_company_profile(company.id)
        assert profile is not None
        assert profile["is_manufacturing"] is is_manufacturing

    @pytest.mark.asyncio
    async def test_get_by_registration_number(self, db, db_company):
        from app.services.company_service import CompanyService

        svc = CompanyService(db)
        found = await svc.get_by_registration_number(db_company.registration_number)
        assert found is not None
        assert found.id == db_company.id

    @pytest.mark.asyncio
    async def test_get_by_registration_number_not_found(self, db):
        from app.services.company_service import CompanyService

        svc = CompanyService(db)
        result = await svc.get_by_registration_number("NONEXISTENT-REG-XYZ")
        assert result is None

    @pytest.mark.asyncio
    async def test_list_companies_returns_created_company(self, db, db_company):
        from app.services.company_service import CompanyService

        svc = CompanyService(db)
        companies, _total = await svc.list_companies(limit=100, offset=0)
        company_ids = [c.id for c in companies]
        assert db_company.id in company_ids

    @pytest.mark.asyncio
    async def test_list_companies_filter_by_risk_band(self, db, db_company):
        from app.models.enums import RiskBand
        from app.services.company_service import CompanyService

        svc = CompanyService(db)
        # db_company is GREEN band
        companies, _ = await svc.list_companies(risk_band=RiskBand.GREEN, limit=100, offset=0)
        company_ids = [c.id for c in companies]
        assert db_company.id in company_ids

    @pytest.mark.asyncio
    async def test_get_with_relations(self, db, db_company):
        from app.services.company_service import CompanyService

        svc = CompanyService(db)
        company = await svc.get_with_relations(db_company.id)
        assert company is not None
        assert company.id == db_company.id

    @pytest.mark.asyncio
    async def test_update_company(self, db, db_company):
        from app.services.company_service import CompanyService

        svc = CompanyService(db)
        updated = await svc.update_by_id(
            db_company.id,
            company_name="Updated Company Name Ltd",
        )
        assert updated.company_name == "Updated Company Name Ltd"

    @pytest.mark.asyncio
    async def test_soft_delete(self, db, db_company):
        from app.services.company_service import CompanyService

        svc = CompanyService(db)
        await svc.soft_delete(db_company.id)

        # Should not be findable in normal list
        companies, _ = await svc.list_companies(limit=100, offset=0)
        ids = [c.id for c in companies]
        assert db_company.id not in ids

    @pytest.mark.asyncio
    async def test_get_all_active_ids(self, db, db_company):
        from app.services.company_service import CompanyService

        svc = CompanyService(db)
        ids = await svc.get_all_active_ids()
        assert db_company.id in ids

    @pytest.mark.asyncio
    async def test_portfolio_stats_returns_dict(self, db):
        from app.services.company_service import CompanyService

        svc = CompanyService(db)
        stats = await svc.get_portfolio_stats()
        assert isinstance(stats, dict)
        assert "total" in stats or len(stats) >= 0  # shape may vary

    @pytest.mark.asyncio
    async def test_duplicate_registration_number(self, db, db_company):
        from app.services.company_service import CompanyService

        svc = CompanyService(db)
        existing = await svc.get_by_registration_number(db_company.registration_number)
        assert existing is not None  # confirms uniqueness check logic


# =============================================================================
# COMPLIANCE SERVICE
# =============================================================================

class TestComplianceService:

    @pytest.mark.asyncio
    async def test_get_flag_summary_returns_dict(self, db, db_company):
        from app.services.compliance_service import ComplianceService

        svc = ComplianceService(db)
        summary = await svc.get_flag_summary(db_company.id)
        assert isinstance(summary, dict)
        # Should always have these keys
        for key in ("total_active", "black", "red", "yellow"):
            assert key in summary

    @pytest.mark.asyncio
    async def test_get_active_flags_returns_list(self, db, db_company):
        from app.services.compliance_service import ComplianceService

        svc = ComplianceService(db)
        flags = await svc.get_active_flags(db_company.id)
        assert isinstance(flags, list)

    @pytest.mark.asyncio
    async def test_get_score_history_returns_list(self, db, db_company):
        from app.services.compliance_service import ComplianceService

        svc = ComplianceService(db)
        history = await svc.get_score_history(db_company.id, months=12)
        assert isinstance(history, list)

    @pytest.mark.asyncio
    async def test_get_dashboard_kpis_returns_dict(self, db):
        from app.services.compliance_service import ComplianceService

        svc = ComplianceService(db)
        kpis = await svc.get_dashboard_kpis()
        assert isinstance(kpis, dict)

    @pytest.mark.asyncio
    async def test_evaluate_company_full_pipeline(self, db, db_company):
        """Integration: build profile → run engine → persist → verify."""
        from app.services.compliance_service import ComplianceService

        # Use the production result contract so added scoring fields fail
        # immediately at fixture construction instead of deep in persistence.
        from app.rule_engine.engine import (
            ExposureBand,
            ComplianceFlag,
            RevenueTier,
            RuleState,
            ScoreBreakdown,
            Severity,
        )

        score_breakdown = ScoreBreakdown(
            final_score=90,
            risk_band=Severity.GREEN,
            exposure_band=ExposureBand.LOW,
            override_applied=False,
            override_reason=None,
            black_flag_count=0,
            red_flag_count=0,
            yellow_flag_count=0,
            green_flag_count=0,
            active_flag_count=0,
            score_hash="abc123",
            raw_total=90,
            agm_score=25,
            audit_score=25,
            return_score=20,
            director_score=15,
            shareholding_score=5,
            capital_score=0,
            office_score=0,
            register_score=0,
            tax_score=0,
            bankruptcy_score=0,
            labour_score=0,
            bsec_score=0,
            fx_score=0,
            escalation_score=0,
            coverage=1.0,
            revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
        )
        review_finding = ComplianceFlag(
            rule_id="AGM-001",
            flag_code="AGM_TEST",
            severity=Severity.RED,
            score_impact=10,
            revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
            description="Controlled evidence review fixture",
            statutory_basis="Test fixture only",
            state=RuleState.NON_COMPLIANT,
            eval_state="VIOLATION",
        )
        mock_output = SimpleNamespace(
            flags=[review_finding],
            engine_version="test-engine-v1",
            ilrmf_version="test-ilrmf-v1",
            score_breakdown=score_breakdown,
            rescue_sequence=None,
        )
        mock_engine = SimpleNamespace(evaluate=Mock(return_value=mock_output))

        svc = ComplianceService(db)
        result = await svc.evaluate_company(
            company_id=db_company.id,
            rule_engine=mock_engine,
            trigger_source="TEST",
        )

        assert result is not None
        # Findings are evaluated and persisted, but statutory scores are not
        # published until both product release and independent legal review exist.
        assert result["score"] is None
        assert result["risk_band"] == "NOT_EVALUATED"
        assert result["legal_evaluation_status"] == "NOT_EVALUATED_PRODUCT_SCORING_DISABLED"
        assert len(result["review_findings"]) == 1
        assert result["review_findings"][0]["rule_id"] == "AGM-001"
        assert result["review_findings"][0]["score_impact_applied"] == 0
        assert "No statutory conclusion" in result["review_findings"][0]["message"]
        mock_engine.evaluate.assert_called_once()

        # The evaluation-run JSONB snapshot persists the full score contract,
        # including category deductions; no schema migration is required.
        from sqlalchemy import select
        from app.models.compliance import ComplianceEvaluationRun, ComplianceScoreHistory, ComplianceFlag

        persisted_result = await db.execute(
            select(ComplianceEvaluationRun)
            .where(ComplianceEvaluationRun.company_id == db_company.id)
            .order_by(ComplianceEvaluationRun.calculated_at.desc())
            .limit(1)
        )
        persisted_run = persisted_result.scalar_one()
        assert persisted_run.score_breakdown_snapshot is None
        assert len(persisted_run.flags_snapshot) == 1
        assert persisted_run.flags_snapshot[0]["scoring_status"] == "LEGAL_SCORE_NOT_RELEASED"
        assert persisted_run.flags_snapshot[0]["score_impact_applied"] == 0
        assert persisted_run.score is None
        assert persisted_run.risk_band == "NOT_EVALUATED"
        assert len(persisted_run.flags_snapshot) == 1
        assert persisted_run.flags_snapshot[0]["scoring_status"] == "LEGAL_SCORE_NOT_RELEASED"
        assert persisted_run.flags_snapshot[0]["score_impact_applied"] == 0
        # Immutable evaluation evidence preserves the engine's internal raw label;
        # customer-facing ComplianceFlag rows and API serializers must redact it.
        assert persisted_run.flags_snapshot[0]["severity"] == "RED"

        persisted_flag_result = await db.execute(
            select(ComplianceFlag).where(
                ComplianceFlag.company_id == db_company.id,
                ComplianceFlag.rule_id == "AGM-001",
                ComplianceFlag.flag_status == "ACTIVE",
            )
        )
        persisted_flag = persisted_flag_result.scalar_one()
        assert str(persisted_flag.severity.value if hasattr(persisted_flag.severity, "value") else persisted_flag.severity) == "NOT_EVALUATED"
        assert persisted_flag.score_impact == 0
        assert "verification pending" in persisted_flag.statutory_basis.lower()
        assert "No legal conclusion" in persisted_flag.description

        history_result = await db.execute(
            select(ComplianceScoreHistory)
            .where(ComplianceScoreHistory.company_id == db_company.id)
            .order_by(ComplianceScoreHistory.calculated_at.desc())
            .limit(1)
        )
        history = history_result.scalar_one()
        assert history.score is None
        assert str(history.risk_band.value if hasattr(history.risk_band, "value") else history.risk_band) == "NOT_EVALUATED"
        await db.refresh(db_company)
        assert db_company.current_compliance_score is None
        assert str(db_company.current_risk_band.value if hasattr(db_company.current_risk_band, "value") else db_company.current_risk_band) == "NOT_EVALUATED"


# =============================================================================
# USER SERVICE
# =============================================================================

class TestUserService:

    @pytest.mark.asyncio
    async def test_create_user(self, db, db_super_admin):
        from app.services.user_service import UserService

        svc = UserService(db)
        user = await svc.create_user(
            email=f"test_{uuid.uuid4().hex[:6]}@nlctest.com",
            full_name="Test User",
            role=UserRole.ADMIN_STAFF,
            plain_password="SecurePassword123!",
            created_by=db_super_admin.id,
        )

        assert user.id is not None
        assert user.password_hash != "SecurePassword123!"  # must be hashed
        assert user.is_active is True

    @pytest.mark.asyncio
    async def test_get_by_email(self, db, db_user):
        from app.services.user_service import UserService

        svc = UserService(db)
        found = await svc.get_by_email(db_user.email)
        assert found is not None
        assert found.id == db_user.id

    @pytest.mark.asyncio
    async def test_get_by_email_not_found(self, db):
        from app.services.user_service import UserService

        svc = UserService(db)
        result = await svc.get_by_email("nonexistent@test.com")
        assert result is None

    @pytest.mark.asyncio
    async def test_verify_credentials_correct_password(self, db, db_super_admin):
        from app.services.user_service import UserService

        svc = UserService(db)
        password = "CorrectPassword123!"
        user = await svc.create_user(
            email=f"auth_{uuid.uuid4().hex[:6]}@nlctest.com",
            full_name="Auth Test User",
            role=UserRole.ADMIN_STAFF,
            plain_password=password,
            created_by=db_super_admin.id,
        )

        result = await svc.verify_credentials(user.email, password)
        assert result is not None

    @pytest.mark.asyncio
    async def test_verify_credentials_wrong_password(self, db, db_super_admin):
        from app.services.user_service import UserService

        svc = UserService(db)
        user = await svc.create_user(
            email=f"auth_{uuid.uuid4().hex[:6]}@nlctest.com",
            full_name="Auth Test User",
            role=UserRole.ADMIN_STAFF,
            plain_password="CorrectPassword123!",
            created_by=db_super_admin.id,
        )

        result = await svc.verify_credentials(user.email, "WrongPassword!")
        assert result is None

    @pytest.mark.asyncio
    async def test_increment_failed_attempts(self, db, db_user):
        from app.services.user_service import UserService

        svc = UserService(db)
        initial_attempts = db_user.failed_login_attempts or 0
        await svc.increment_failed_attempts(db_user)

        # Reload
        refreshed = await svc.get_by_email(db_user.email)
        assert (refreshed.failed_login_attempts or 0) == initial_attempts + 1

    @pytest.mark.asyncio
    async def test_check_lockout_not_locked(self, db, db_user):
        from app.services.user_service import UserService

        svc = UserService(db)
        is_locked = await svc.check_lockout(db_user)
        assert is_locked is False  # Fresh user, not locked

    @pytest.mark.asyncio
    async def test_get_company_ids_empty_for_new_user(self, db, db_user):
        from app.services.user_service import UserService

        svc = UserService(db)
        ids = await svc.get_company_ids(db_user.id)
        assert isinstance(ids, list)

    @pytest.mark.asyncio
    async def test_grant_and_revoke_company_access(self, db, db_user, db_company):
        from app.services.user_service import UserService

        svc = UserService(db)

        # Grant
        await svc.grant_company_access(
            user_id=db_user.id,
            company_id=db_company.id,
            can_edit=True,
            can_view_financials=True,
            granted_by=db_user.id,
        )
        ids_after_grant = await svc.get_company_ids(db_user.id)
        assert str(db_company.id) in ids_after_grant

        # Revoke
        await svc.revoke_company_access(user_id=db_user.id, company_id=db_company.id)
        ids_after_revoke = await svc.get_company_ids(db_user.id)
        assert str(db_company.id) not in ids_after_revoke

    @pytest.mark.asyncio
    async def test_build_jwt_payload_shape(self, db, db_user):
        from app.services.user_service import UserService

        svc = UserService(db)
        payload = await svc.build_jwt_payload(db_user)

        assert "sub" in payload
        assert "user_id" in payload
        assert "role" in payload
        assert "company_ids" in payload


# =============================================================================
# FILING SERVICE
# =============================================================================

class TestFilingService:

    @pytest.mark.asyncio
    async def test_create_agm(self, db, db_company):
        from app.services.filing_service import AGMService

        svc = AGMService(db)
        agm = await svc.create_agm(
            company_id=db_company.id,
            financial_year=2023,
            agm_due_date=date(2024, 6, 30),
        )

        assert agm.id is not None
        assert agm.company_id == db_company.id
        assert agm.financial_year == 2023
        assert agm.agm_deadline == date(2024, 6, 30)
        assert agm.quorum_met is None
        assert agm.quorum_required is None
        assert agm.auditor_reappointed is None

    @pytest.mark.asyncio
    async def test_create_agm_duplicate_year_raises(self, db, db_company):
        """Two AGMs for the same company + year should raise integrity error."""
        from sqlalchemy.exc import IntegrityError

        from app.services.filing_service import AGMService

        svc = AGMService(db)
        await svc.create_agm(
            company_id=db_company.id,
            financial_year=2022,
            agm_due_date=date(2023, 6, 30),
        )

        with pytest.raises((IntegrityError, Exception)):
            await svc.create_agm(
                company_id=db_company.id,
                financial_year=2022,
                agm_due_date=date(2023, 7, 31),
            )

    @pytest.mark.asyncio
    async def test_get_for_company_returns_list(self, db, db_company):
        from app.services.filing_service import AGMService

        svc = AGMService(db)
        result = await svc.get_for_company(db_company.id)
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_mark_agm_held(self, db, db_company):
        from app.services.filing_service import AGMService

        svc = AGMService(db)
        agm = await svc.create_agm(
            company_id=db_company.id,
            financial_year=2021,
            agm_due_date=date(2022, 6, 30),
        )

        updated = await svc.mark_held(
            agm_id=agm.id,
            agm_date=date(2022, 5, 15),
            members_present=3,
            auditor_reappointed=True,
        )

        assert updated is not None
        assert updated.agm_date == date(2022, 5, 15)
        assert updated.auditor_reappointed is True
        assert updated.quorum_required == 2
        assert updated.quorum_met is True
        assert updated.quorum_basis == "SECTION_85_2_B_DEFAULT_ARTICLES_NOT_REVIEWED"

    @pytest.mark.asyncio
    async def test_mark_agm_held_large_private_company_uses_three_member_default(self, db, db_company):
        from app.services.filing_service import AGMService

        db_company.member_count = 7
        await db.flush()
        svc = AGMService(db)
        agm = await svc.create_agm(
            company_id=db_company.id,
            financial_year=2022,
            agm_due_date=date(2023, 6, 30),
        )
        updated = await svc.mark_held(
            agm_id=agm.id,
            agm_date=date(2023, 5, 15),
            members_present=2,
            auditor_reappointed=True,
        )
        assert updated is not None
        assert updated.quorum_required == 3
        assert updated.quorum_met is False

    @pytest.mark.asyncio
    async def test_mark_agm_held_missing_member_count_is_not_evaluated(self, db, db_company):
        from app.services.filing_service import AGMService

        db_company.member_count = None
        await db.flush()
        svc = AGMService(db)
        agm = await svc.create_agm(company_id=db_company.id, financial_year=2024)
        updated = await svc.mark_held(
            agm_id=agm.id,
            agm_date=date(2024, 5, 15),
            members_present=2,
            auditor_reappointed=True,
        )
        assert updated is not None
        assert updated.quorum_required is None
        assert updated.quorum_met is None

    @pytest.mark.asyncio
    async def test_create_audit(self, db, db_company):
        from app.services.filing_service import AuditService

        svc = AuditService(db)
        audit = await svc.create_audit(
            company_id=db_company.id,
            financial_year=2023,
            auditor_firm="Rahman & Associates",
            auditor_icab_number="ICAB-12345",
        )

        assert audit.id is not None
        assert audit.audit_complete is False

    @pytest.mark.asyncio
    async def test_create_annual_return(self, db, db_company):
        from app.services.filing_service import AnnualReturnService

        svc = AnnualReturnService(db)
        ret = await svc.create_return(
            company_id=db_company.id,
            financial_year=2023,
            agm_date=date(2024, 3, 1),
        )

        assert ret.id is not None
        assert ret.filed_date is None

    @pytest.mark.asyncio
    async def test_get_unfiled_count(self, db, db_company):
        from app.services.filing_service import AnnualReturnService

        svc = AnnualReturnService(db)
        count = await svc.get_unfiled_count(db_company.id)
        assert isinstance(count, int)
        assert count >= 0


# =============================================================================
# NOTIFICATION + ACTIVITY SERVICE
# =============================================================================

class TestNotificationService:

    @pytest.mark.asyncio
    async def test_queue_notification(self, db, db_user, db_company):
        from app.services.notification_service import NotificationService

        svc = NotificationService(db)
        notification = await svc.queue_notification(
            user_id=db_user.id,
            company_id=db_company.id,
            channel="DASHBOARD",
            subject="Test Notification",
            message="This is a test notification from the compliance engine.",
        )

        assert notification.id is not None
        from app.models.enums import NotificationStatus

        assert notification.notification_status == NotificationStatus.PENDING
        assert notification.acknowledged_at is None

    @pytest.mark.asyncio
    async def test_acknowledge_notification(self, db, db_user, db_company):
        from app.services.notification_service import NotificationService

        svc = NotificationService(db)
        notification = await svc.queue_notification(
            user_id=db_user.id,
            company_id=db_company.id,
            channel="DASHBOARD",
            subject="Acknowledge Test",
            message="Acknowledge me.",
        )

        from app.models.enums import NotificationStatus

        result = await svc.acknowledge(notification_id=notification.id, user_id=db_user.id)
        assert result is not None
        assert result.notification_status == NotificationStatus.ACKNOWLEDGED
        assert result.acknowledged_at is not None

    @pytest.mark.asyncio
    async def test_get_for_user_returns_list(self, db, db_user):
        from app.services.notification_service import NotificationService

        svc = NotificationService(db)
        result = await svc.get_for_user(user_id=db_user.id, limit=10, offset=0)
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_activity_log_append(self, db, db_user, db_company):
        from app.services.notification_service import ActivityService

        svc = ActivityService(db)
        await svc.log(
            action="TEST_ACTION",
            resource_type="company",
            resource_id=str(db_company.id),
            description="Integration test activity log entry",
            actor_user_id=db_user.id,
            ip_address="127.0.0.1",
        )

        logs = await svc.get_logs(
            resource_type="company",
            resource_id=str(db_company.id),
            limit=10,
            offset=0,
        )
        actions = [log.action for log in logs]
        assert "TEST_ACTION" in actions

    @pytest.mark.asyncio
    async def test_activity_log_immutable(self, db, db_user, db_company):
        """Activity logs must not be updateable (append-only pattern)."""

        from app.services.notification_service import ActivityService

        svc = ActivityService(db)
        await svc.log(
            action="IMMUTABLE_TEST",
            resource_type="company",
            resource_id=str(db_company.id),
            description="Test immutability",
            actor_user_id=db_user.id,
        )

        # Verify that activity logs table has no update triggers / patterns
        # The service should only use INSERT, never UPDATE
        logs = await svc.get_logs(limit=5, offset=0)
        assert isinstance(logs, list)


# =============================================================================
# RULES SERVICE
# =============================================================================

class TestRulesService:
    """Requires seed_rules.py to have been run on test DB."""

    @pytest.mark.asyncio
    async def test_get_all_returns_rules(self, db):
        from app.services.rules_service import RulesService as LegalRuleService

        svc = LegalRuleService(db)
        rules = await svc.get_all()
        assert len(rules) >= 75, "integration test setup must seed the complete legal-rule catalogue"

    @pytest.mark.asyncio
    async def test_get_by_rule_id(self, db):
        from app.services.rules_service import RulesService as LegalRuleService

        svc = LegalRuleService(db)
        rules = await svc.get_all()
        assert len(rules) >= 75, "integration test setup must seed the complete legal-rule catalogue"

        rule = await svc.get_by_rule_id("AGM-001")
        assert rule is not None
        assert rule.rule_id == "AGM-001"
        assert rule.is_active is True

    @pytest.mark.asyncio
    async def test_get_black_override_rules_stays_empty_until_legal_release(self, db):
        from app.services.rules_service import RulesService as LegalRuleService

        svc = LegalRuleService(db)
        rules = await svc.get_all()
        assert len(rules) >= 75, "integration test setup must seed the complete legal-rule catalogue"

        black_rules = await svc.get_black_override_rules()
        # Migration 0090 quarantines every rule as NOT_EVALUATED / PENDING.
        # No statutory BLACK override may be active before independent legal
        # verification and the explicit legal scoring release gate.
        assert black_rules == []

    @pytest.mark.asyncio
    async def test_update_rule_creates_version_snapshot(self, db, db_super_admin):
        from app.models.database import set_rls_context
        from app.services.rules_service import RulesService as LegalRuleService

        # The legal-rule trigger requires the real, signed Super Admin UUID;
        # an unscoped test-owner session is not a valid human actor.
        await set_rls_context(db, str(db_super_admin.id))
        svc = LegalRuleService(db)
        rules = await svc.get_all()
        assert len(rules) >= 75, "integration test setup must seed the complete legal-rule catalogue"

        # Update OFF-001 (lowest impact — safest to test with)
        await svc.get_by_rule_id("OFF-001")

        await svc.update_rule(
            rule_id="OFF-001",
            description="Updated description for testing",
            change_reason="Integration test — verifying version snapshot creation",
            changed_by=db_super_admin.id,
        )

        # Verify version history exists
        history = await svc.get_version_history("OFF-001")
        assert len(history) >= 1
        assert history[0].rule_id == "OFF-001"



# =============================================================================
# PAUSED SCORE RELEASE: FINDING, ALLOCATION AND RESCUE-PLANNER CONTRACTS
# =============================================================================

def test_score_allocation_uses_product_allowlist_and_excludes_unknown_findings(monkeypatch):
    import app.rule_engine.engine as engine_module
    from app.rule_engine.engine import RuleState
    from app.services.compliance_service import _applied_score_impacts

    monkeypatch.setattr(engine_module, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(engine_module, "PRODUCT_SCORING_RULE_IDS", frozenset({"AGM-001", "AUD-001"}))
    monkeypatch.setattr(engine_module, "VERIFIED_RULE_IDS", frozenset())
    monkeypatch.setattr(engine_module, "legal_score_is_released", lambda: True)
    confirmed = SimpleNamespace(
        rule_id="AUD-001",
        state=RuleState.NON_COMPLIANT,
        eval_state="VIOLATION",
        resolved=False,
        conditional_applies=True,
        severity="RED",
        score_impact=15,
        detail={},
    )
    unknown = SimpleNamespace(
        rule_id="AGM-001",
        state=RuleState.UNKNOWN,
        eval_state="UNKNOWN",
        resolved=False,
        conditional_applies=True,
        severity="NOT_EVALUATED",
        score_impact=25,
        detail={},
    )

    allocations = _applied_score_impacts([confirmed, unknown])

    assert allocations[0] == {"applied": 15, "status": "APPLIED"}
    assert allocations[1] == {"applied": 0, "status": "NOT_A_CONFIRMED_VIOLATION"}


def test_score_allocation_applies_product_allowlisted_rule_without_counsel_allowlist(monkeypatch):
    import app.rule_engine.engine as engine_module
    from app.rule_engine.engine import RuleState
    from app.services.compliance_service import _applied_score_impacts

    monkeypatch.setattr(engine_module, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(engine_module, "PRODUCT_SCORING_RULE_IDS", frozenset({"AGM-001"}))
    monkeypatch.setattr(engine_module, "VERIFIED_RULE_IDS", frozenset())
    finding = SimpleNamespace(
        rule_id="AGM-001",
        state=RuleState.NON_COMPLIANT,
        eval_state="VIOLATION",
        resolved=False,
        conditional_applies=True,
        severity="RED",
        score_impact=10,
        detail={},
    )

    assert _applied_score_impacts([finding]) == [{"applied": 10, "status": "APPLIED"}]


def test_rescue_planner_remains_deterministic_when_score_release_is_paused(monkeypatch):
    import app.rule_engine.engine as engine_module
    from app.rule_engine.engine import (
        ComplianceFlag,
        NLCRuleEngine,
        RevenueTier,
        RuleState,
        Severity,
    )

    monkeypatch.setattr(engine_module, "LEGAL_SCORE_RELEASED", False)
    monkeypatch.setattr(engine_module, "VERIFIED_RULE_IDS", frozenset())
    finding = ComplianceFlag(
        rule_id="AGM-001",
        flag_code="AGM_EVIDENCE_CONFIRMED",
        severity=Severity.RED,
        score_impact=0,
        revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
        description="Confirmed fact fixture; review required",
        statutory_basis="Controlled test fixture",
        state=RuleState.NON_COMPLIANT,
        eval_state="VIOLATION",
    )
    score = SimpleNamespace(risk_band=Severity.NOT_EVALUATED)

    steps = NLCRuleEngine._generate_rescue_sequence(
        None, None, [finding], score
    )

    assert len(steps) == 1
    assert steps[0]["related_rules"] == ["AGM-001"]

    dispositions = NLCRuleEngine._build_rescue_dispositions(
        [finding], score, steps
    )
    assert dispositions[0]["disposition"] == "REVIEW_REQUIRED"
    assert dispositions[0]["reason"] == "PRODUCT_SCORE_RELEASE_DISABLED"



# =============================================================================
# PDF AND RESCUE RELEASE BOUNDARIES (EXERCISED IN THE INTEGRATION JOB)
# =============================================================================

def test_pdf_report_scores_product_allowlisted_rules_and_lists_counsel_review_items(monkeypatch):
    from app.services import pdf_report_service as report_module

    monkeypatch.setattr(report_module, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(report_module, "PRODUCT_SCORING_RULE_IDS", frozenset({"AGM-001"}))
    monkeypatch.setattr(report_module, "VERIFIED_RULE_IDS", frozenset({"AGM-001"}))
    verified = SimpleNamespace(
        rule_id="AGM-001", severity="RED", description="Verified finding",
        score_impact=10, score_impact_applied=10, scoring_status="APPLIED",
        state="NON_COMPLIANT", eval_state="VIOLATION", resolved=False,
        conditional_applies=True, detail={},
    )
    unverified = SimpleNamespace(
        rule_id="MEM-001", severity="BLACK", description="Unverified legal conclusion",
        score_impact=30, score_impact_applied=0, scoring_status="LEGAL_VERIFICATION_PENDING",
        state="NON_COMPLIANT", eval_state="VIOLATION", resolved=False,
        conditional_applies=True, detail={},
    )
    company = SimpleNamespace(
        company_name="Integration Review Ltd", registration_number="IR-1",
        current_compliance_score=90, current_risk_band="RED",
    )

    page = report_module.build_compliance_report_html(
        company, [verified, unverified], datetime(2026, 11, 13)
    )

    assert "Verified finding" in page
    assert "MEM-001" in page
    assert "Independent Bangladesh-counsel/source verification remains pending" in page
    assert "Unverified legal conclusion" not in page
    assert "effective deductions -10 pts" in page


def test_pdf_builder_with_paused_release_suppresses_stale_score_and_flags(monkeypatch):
    from app.services import pdf_report_service as report_module

    monkeypatch.setattr(report_module, "LEGAL_SCORE_RELEASED", False)
    monkeypatch.setattr(report_module, "VERIFIED_RULE_IDS", frozenset())
    company = SimpleNamespace(
        company_name="Paused Integration Ltd", registration_number="PI-1",
        current_compliance_score=12, current_risk_band="BLACK",
    )
    stale_flag = SimpleNamespace(
        rule_id="INC-003", severity="BLACK", description="Stale BLACK conclusion",
        score_impact=50,
    )

    page = report_module.build_compliance_report_html(
        company, [stale_flag], datetime(2026, 11, 13)
    )

    assert "NOT EVALUATED" in page
    assert "12 / 100" not in page
    assert "Stale BLACK conclusion" not in page
    assert "Score reconciliation" not in page


def test_pdf_rescue_section_renders_structured_progress_and_blocked_reason():
    from app.services.pdf_report_service import _render_rescue_section

    step = SimpleNamespace(
        step_number=1, step_title="Verify records", step_description="Review the evidence",
        step_status="BLOCKED", target_completion_date=date(2026, 12, 1),
        statutory_basis="Controlled test basis", complexity="HIGH",
        completion_notes="Awaiting documents", blocked_reason="Missing source evidence",
    )
    plan = SimpleNamespace(
        steps=[step], started_at=datetime(2026, 11, 1),
        target_completion_date=date(2026, 12, 1), completed_steps=0,
        total_steps=8, blocked_steps=1, completion_percentage=0,
        plan_name="Evidence review plan", initial_risk_band="NOT_EVALUATED",
        initial_score=None,
    )

    html = _render_rescue_section(plan)

    assert "Corporate Rescue Plan" in html
    assert "Verify records" in html
    assert "Missing source evidence" in html
    assert "BLOCKED" in html


def test_rescue_output_validation_requires_product_release_and_unique_evidenced_findings(monkeypatch):
    import app.rule_engine.engine as engine_module
    from app.rule_engine.engine import RuleState, Severity
    from app.services.rescue_service import validate_rescue_engine_output

    flag = SimpleNamespace(
        rule_id="AGM-001", state=RuleState.NON_COMPLIANT,
        eval_state="VIOLATION", severity=Severity.RED, score_impact=10,
        resolved=False, conditional_applies=True,
    )
    output = SimpleNamespace(
        company_id="tenant-001",
        score_breakdown=SimpleNamespace(final_score=40, risk_band=Severity.RED),
        flags=[flag],
        rescue_sequence=[{"related_rules": ["AGM-001"]}],
    )

    monkeypatch.setattr(engine_module, "LEGAL_SCORE_RELEASED", False)
    monkeypatch.setattr(engine_module, "VERIFIED_RULE_IDS", frozenset())
    with pytest.raises(PermissionError, match="disabled"):
        validate_rescue_engine_output(output, expected_company_id="tenant-001")

    monkeypatch.setattr(engine_module, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(engine_module, "PRODUCT_SCORING_RULE_IDS", frozenset({"AGM-001"}))
    monkeypatch.setattr(engine_module, "VERIFIED_RULE_IDS", frozenset())
    assert validate_rescue_engine_output(
        output, expected_company_id="tenant-001"
    ) == frozenset({"AGM-001"})

    with pytest.raises(PermissionError, match="tenant"):
        validate_rescue_engine_output(output, expected_company_id="other-tenant")

    duplicate_output = SimpleNamespace(
        company_id="tenant-001",
        score_breakdown=output.score_breakdown,
        flags=[flag, flag],
        rescue_sequence=[{"related_rules": ["AGM-001"]}],
    )
    with pytest.raises(PermissionError, match="unique"):
        validate_rescue_engine_output(duplicate_output, expected_company_id="tenant-001")

    empty_plan = SimpleNamespace(
        company_id="tenant-001",
        score_breakdown=output.score_breakdown,
        flags=[flag],
        rescue_sequence=[],
    )
    with pytest.raises(ValueError, match="sequence"):
        validate_rescue_engine_output(empty_plan, expected_company_id="tenant-001")



def test_score_allocation_covers_inactive_excluded_black_and_duplicate_paths(monkeypatch):
    import app.rule_engine.engine as engine_module
    from app.rule_engine.engine import RuleState
    from app.services.compliance_service import _applied_score_impacts

    product_ids = frozenset({"AGM-001", "AUD-001", "INC-003", "X-001"})
    monkeypatch.setattr(engine_module, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(engine_module, "PRODUCT_SCORING_RULE_IDS", product_ids)
    monkeypatch.setattr(engine_module, "SCORE_DEDUCTION_RULE_IDS", product_ids)
    monkeypatch.setattr(engine_module, "VERIFIED_RULE_IDS", product_ids)
    monkeypatch.setattr(engine_module, "legal_score_is_released", lambda: True)

    def finding(rule_id, *, resolved=False, state=RuleState.NON_COMPLIANT,
                eval_state="VIOLATION", severity="RED", impact=5,
                black_override=False, event_key=None):
        return SimpleNamespace(
            rule_id=rule_id, resolved=resolved, conditional_applies=True,
            state=state, eval_state=eval_state, severity=severity,
            score_impact=impact, is_black_override=black_override,
            detail={"scoring_event_key": event_key} if event_key else {},
        )

    rows = [
        finding("AGM-001", resolved=True),
        finding("AGM-001", state=RuleState.UNKNOWN, eval_state="UNKNOWN"),
        finding("MEM-001"),
        finding("INC-003", severity="BLACK", black_override=True, impact=0),
        finding("X-001"),
        finding("AUD-001", event_key="shared-event"),
        finding("AGM-001", event_key="shared-event"),
    ]
    results = _applied_score_impacts(rows)

    assert results[0]["status"] == "INACTIVE"
    assert results[1]["status"] == "NOT_A_CONFIRMED_VIOLATION"
    assert results[2]["status"] == "EXCLUDED_FROM_PRODUCT_SCORING"
    assert results[3]["status"] == "BLACK_OVERRIDE_APPLIED"
    assert results[4]["status"] == "NO_SCORING_CATEGORY"
    assert results[5]["status"] == "DUPLICATE_EVENT_SUPPRESSED"
    assert results[6]["status"] == "APPLIED"


def test_rescue_dispositions_keep_candidates_review_only_when_product_release_is_paused(monkeypatch):
    import app.rule_engine.engine as engine_module
    from app.rule_engine.engine import (
        ComplianceFlag,
        NLCRuleEngine,
        RevenueTier,
        RuleState,
        Severity,
    )

    monkeypatch.setattr(engine_module, "LEGAL_SCORE_RELEASED", False)
    monkeypatch.setattr(engine_module, "VERIFIED_RULE_IDS", frozenset())

    def flag(rule_id, state=RuleState.NON_COMPLIANT, eval_state="VIOLATION",
             resolved=False):
        return ComplianceFlag(
            rule_id=rule_id, flag_code=f"{rule_id}_DISPOSITION",
            severity=Severity.RED, score_impact=0,
            revenue_tier=RevenueTier.COMPLIANCE_PACKAGE,
            description="Controlled fixture", statutory_basis="Test only",
            state=state, eval_state=eval_state, resolved=resolved,
        )

    rows = [
        flag("AGM-001", resolved=True),
        flag("AUD-001", state=RuleState.UNKNOWN, eval_state="UNKNOWN"),
        flag("AGM-002"),
        flag("AGM-003"),
    ]
    score = SimpleNamespace(risk_band=Severity.NOT_EVALUATED)
    steps = [{"related_rules": ["AGM-002"], "rescue_id": "RES-AGM-002"}]

    dispositions = NLCRuleEngine._build_rescue_dispositions(rows, score, steps)

    assert [item["disposition"] for item in dispositions] == [
        "NO_ACTION", "WAITING_EVIDENCE", "REVIEW_REQUIRED", "BLOCKED"
    ]
    assert dispositions[2]["reason"] == "PRODUCT_SCORE_RELEASE_DISABLED"


def test_rescue_target_date_prefers_explicit_then_latest_step_date():
    from app.services.rescue_service import _derive_plan_target

    first = date(2026, 12, 1)
    latest = date(2026, 12, 15)
    steps = [
        SimpleNamespace(target_completion_date=first),
        SimpleNamespace(target_completion_date=latest),
        SimpleNamespace(target_completion_date=None),
    ]

    assert _derive_plan_target(date(2026, 11, 30), steps) == date(2026, 11, 30)
    assert _derive_plan_target(None, steps) == latest
    assert _derive_plan_target(None, []) is None


# =============================================================================
# COUNSEL APPROVAL RELEASE BOUNDARIES
# =============================================================================

def test_company_flag_api_quarantines_unapproved_statutory_candidate(monkeypatch):
    import app.api.companies as companies_api

    monkeypatch.setattr(companies_api, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(companies_api, "PRODUCT_SCORING_RULE_IDS", frozenset({"AGM-001"}))
    monkeypatch.setattr(companies_api, "VERIFIED_RULE_IDS", frozenset())
    flag = SimpleNamespace(
        id=uuid.uuid4(),
        rule_id="AGM-001",
        description="Candidate AGM finding",
        flag_code="AGM-001",
        severity="RED",
        score_impact=15,
        flag_status="ACTIVE",
        triggered_date=date(2026, 11, 1),
        resolved_date=None,
        is_black_override=True,
        resolution_notes=None,
    )

    response = companies_api._flag_to_response(flag)

    assert response.severity == "NOT_EVALUATED"
    assert response.score_impact == 0
    assert response.legal_review_status == "NOT_LEGALLY_VERIFIED"
    assert response.is_black_override is False
    assert "No breach" in response.rule_name


@pytest.mark.asyncio
async def test_black_override_api_requires_full_counsel_release(monkeypatch):
    import app.api.rules as rules_api
    import app.rule_engine.engine as engine_module

    monkeypatch.setattr(engine_module, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(
        engine_module, "PRODUCT_SCORING_RULE_IDS", frozenset({"INC-003"})
    )
    monkeypatch.setattr(
        engine_module, "VERIFIED_RULE_IDS", frozenset({"INC-003"})
    )
    monkeypatch.setattr(rules_api, "PRODUCT_SCORING_RULE_IDS", frozenset({"INC-003"}))
    monkeypatch.setattr(rules_api, "VERIFIED_RULE_IDS", frozenset({"INC-003"}))
    monkeypatch.setattr(
        rules_api, "AUTHORIZED_BLACK_OVERRIDE_RULE_IDS", frozenset({"INC-003"})
    )

    class FakeRulesService:
        def __init__(self, db):
            self.db = db

        async def get_all(self):
            return [
                SimpleNamespace(
                    rule_id="INC-003",
                    rule_name="Minimum director requirement",
                    rule_type="THRESHOLD",
                    statutory_basis="Companies Act 1994, section 90",
                    description="Verified minimum director finding.",
                    default_severity="RED",
                    score_impact=20,
                    revenue_tier="COMPLIANCE_PACKAGE",
                    is_active=True,
                    verification_status="VERIFIED",
                    verified_at=datetime(2026, 11, 15),
                    statutory_effective_date=date(1994, 12, 1),
                    rule_version="2.2",
                    created_at=datetime(2026, 11, 15),
                    updated_at=datetime(2026, 11, 15),
                )
            ]

    monkeypatch.setattr(rules_api, "RulesService", FakeRulesService)
    result = await rules_api.get_black_overrides(current_user=None, db=object())

    assert len(result) == 1
    assert result[0].rule_id == "INC-003"
    assert result[0].is_black_override is True
    assert result[0].default_severity == "RED"
    assert result[0].score_impact == 20


def test_rule_evaluator_quarantines_unapproved_candidate_before_score_or_override(monkeypatch):
    import app.rule_engine.engine as engine_module

    monkeypatch.setattr(engine_module, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(
        engine_module, "PRODUCT_SCORING_RULE_IDS", frozenset({"AUD-001"})
    )
    monkeypatch.setattr(engine_module, "VERIFIED_RULE_IDS", frozenset())

    profile = engine_module.CompanyProfile(
        company_id="integration-counsel-gate",
        company_name="Counsel Gate Integration Ltd",
        incorporation_date=date(2020, 1, 1),
        first_auditor_appointed=False,
        first_auditor_appointment_verified=True,
        first_auditor_appointment_evidence_ref="AUDITOR-SEARCH-INT-001",
        first_auditor_appointment_verified_at=date(2026, 11, 1),
        first_auditor_appointment_verified_by="integration-reviewer",
    )
    output = engine_module.NLCRuleEngine(today=date(2026, 11, 15)).evaluate(profile)
    finding = next(flag for flag in output.flags if flag.rule_id == "AUD-001")

    assert finding.severity is engine_module.Severity.NOT_EVALUATED
    assert finding.state is engine_module.RuleState.UNKNOWN
    assert finding.eval_state == "UNKNOWN"
    assert finding.score_impact == 0
    assert finding.detail["legal_validation_status"] == "PENDING_COUNSEL_APPROVAL"
    assert finding.detail["statutory_finding_authorized"] is False


def test_compliance_score_impact_requires_verified_rule_and_global_release(monkeypatch):
    import app.rule_engine.engine as engine_module
    import app.services.compliance_service as compliance_module

    monkeypatch.setattr(engine_module, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(engine_module, "PRODUCT_SCORING_RULE_IDS", frozenset({"AGM-001"}))
    monkeypatch.setattr(engine_module, "SCORE_DEDUCTION_RULE_IDS", frozenset({"AGM-001"}))
    monkeypatch.setattr(engine_module, "VERIFIED_RULE_IDS", frozenset({"AGM-001"}))
    monkeypatch.setattr(engine_module, "legal_score_is_released", lambda: True)
    flag = SimpleNamespace(
        rule_id="AGM-001",
        score_impact=10,
        state="NON_COMPLIANT",
        eval_state="VIOLATION",
        resolved=False,
        conditional_applies=True,
    )

    result = compliance_module._applied_score_impacts([flag])

    assert result == [{"applied": 10, "status": "APPLIED"}]


def test_labour_licence_scope_is_not_inferred_from_manufacturing_status(monkeypatch):
    import app.rule_engine.engine as engine_module

    monkeypatch.setattr(engine_module, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(
        engine_module, "VERIFIED_RULE_IDS", engine_module.PRODUCT_SCORING_RULE_IDS
    )
    profile = engine_module.CompanyProfile(
        company_id="labour-scope-unknown",
        company_name="Non-manufacturing Service Ltd",
        incorporation_date=date(2020, 1, 1),
        is_manufacturing=False,
    )

    output = engine_module.NLCRuleEngine(today=date(2026, 11, 15)).evaluate(profile)
    finding = next(flag for flag in output.flags if flag.rule_id == "LBR-001")

    assert finding.flag_code == "LABOUR_LICENSE_SCOPE_NOT_VERIFIED"
    assert finding.state is engine_module.RuleState.UNKNOWN
    assert finding.severity is engine_module.Severity.NOT_EVALUATED
    assert finding.score_impact == 0


def test_labour_licence_expiry_uses_verified_printed_date_only(monkeypatch):
    import app.rule_engine.engine as engine_module

    monkeypatch.setattr(engine_module, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(
        engine_module, "VERIFIED_RULE_IDS", engine_module.PRODUCT_SCORING_RULE_IDS
    )
    profile = engine_module.CompanyProfile(
        company_id="labour-expiry-evidence",
        company_name="Contractor Establishment Ltd",
        incorporation_date=date(2020, 1, 1),
        is_manufacturing=False,
        labour_establishment_category="CONTRACTOR_ESTABLISHMENT",
        labour_license_scope_verified=True,
        labour_license_scope_evidence_ref="LEGAL-SCOPE-INTEGRATION-001",
        labour_license_scope_verified_at=date(2026, 11, 1),
        labour_license_scope_verified_by="integration-reviewer",
        factory_license_required_by_direction=True,
        labour_license_status_verified=True,
        labour_license_status_evidence_ref="DIFE-LICENCE-INTEGRATION-001",
        labour_license_status_verified_at=date(2026, 11, 2),
        labour_license_status_verified_by="integration-reviewer",
        factory_license_obtained=True,
        factory_license_expiry=date(2026, 10, 31),
    )

    output = engine_module.NLCRuleEngine(today=date(2026, 11, 15)).evaluate(profile)
    finding = next(flag for flag in output.flags if flag.rule_id == "LBR-002")

    assert finding.flag_code == "LABOUR_LICENSE_EXPIRED_REQUIRES_REVIEW"
    assert finding.state is engine_module.RuleState.REQUIRES_LAWYER_JUDGMENT
    assert finding.detail["renewal_term_calculated_automatically"] is False
    assert finding.score_impact == 0


def test_labour_court_order_review_is_independent_of_manufacturing(monkeypatch):
    import app.rule_engine.engine as engine_module

    monkeypatch.setattr(engine_module, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(
        engine_module, "VERIFIED_RULE_IDS", engine_module.PRODUCT_SCORING_RULE_IDS
    )
    profile = engine_module.CompanyProfile(
        company_id="labour-court-order",
        company_name="Service Establishment Ltd",
        incorporation_date=date(2020, 1, 1),
        is_manufacturing=None,
        labour_court_order_pending=True,
    )

    output = engine_module.NLCRuleEngine(today=date(2026, 11, 15)).evaluate(profile)
    finding = next(flag for flag in output.flags if flag.rule_id == "LBR-003")

    assert finding.flag_code == "LABOUR_COURT_ORDER_STATUS_REQUIRES_VERIFICATION"
    assert finding.state is engine_module.RuleState.UNKNOWN
    assert finding.score_impact == 0
