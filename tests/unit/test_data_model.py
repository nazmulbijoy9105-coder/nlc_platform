"""Data model integrity tests."""

class TestDataModel:
    def test_all_models_have_tablename(self):
        from app.models import (
            AGM,
            AIPromptTemplate,
            AnnualReturn,
            Audit,
            Company,
            ComplianceEvent,
            ComplianceFlag,
            ComplianceScoreHistory,
            Director,
            Document,
            DocumentAccessLog,
            Engagement,
            LegalRule,
            LegalRuleVersion,
            Notification,
            Shareholder,
            ShareTransfer,
            User,
            UserActivityLog,
        )
        models = [Company, Director, Shareholder, ShareTransfer, AGM, Audit, AnnualReturn, ComplianceFlag, ComplianceScoreHistory, ComplianceEvent, LegalRule, LegalRuleVersion, User, UserActivityLog, Notification, Document, AIPromptTemplate, DocumentAccessLog, Engagement]
        for m in models:
            assert hasattr(m, '__tablename__'), f"{m.__name__} missing __tablename__"

    def test_compliance_flag_has_fk_to_companies(self):
        from app.models.compliance import ComplianceFlag
        fks = list(ComplianceFlag.__table__.foreign_keys)
        company_fks = [fk for fk in fks if 'companies' in str(fk.column.table)]
        assert len(company_fks) >= 1

    def test_compliance_flag_has_rule_id(self):
        from app.models.compliance import ComplianceFlag
        cols = {c.name: c for c in ComplianceFlag.__table__.columns}
        assert 'rule_id' in cols

    def test_score_history_has_unique_constraint(self):
        from app.models.compliance import ComplianceScoreHistory
        constraints = ComplianceScoreHistory.__table__.constraints
        uq = [c for c in constraints if 'company_id' in str(c) and 'snapshot_month' in str(c)]
        assert len(uq) >= 1

    def test_legal_rule_id_is_unique(self):
        from app.models.rules import LegalRule
        cols = {c.name: c for c in LegalRule.__table__.columns}
        assert cols['rule_id'].unique

    def test_user_email_is_unique(self):
        from app.models.user import User
        cols = {c.name: c for c in User.__table__.columns}
        assert cols['email'].unique

    def test_mixin_fields_present(self):
        from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
        assert hasattr(UUIDPrimaryKeyMixin, 'id')
        assert hasattr(TimestampMixin, 'created_at')
        assert hasattr(SoftDeleteMixin, 'is_active')

    def test_company_has_compliance_score(self):
        from app.models.company import Company
        assert hasattr(Company, 'current_compliance_score')

    def test_company_has_risk_band(self):
        from app.models.company import Company
        assert hasattr(Company, 'current_risk_band')

    def test_compliance_flag_has_severity(self):
        from app.models.compliance import ComplianceFlag
        assert hasattr(ComplianceFlag, 'severity')

    def test_compliance_flag_has_score_impact(self):
        from app.models.compliance import ComplianceFlag
        assert hasattr(ComplianceFlag, 'score_impact')

    def test_rescue_plan_has_steps(self):
        from app.models.rescue import RescuePlan
        assert hasattr(RescuePlan, 'steps')
