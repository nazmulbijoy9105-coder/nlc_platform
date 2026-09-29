"""Data model tests."""

class TestDataModel:
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

    def test_legal_rule_id_is_unique(self):
        from app.models.rules import LegalRule
        cols = {c.name: c for c in LegalRule.__table__.columns}
        assert cols['rule_id'].unique

    def test_user_email_is_unique(self):
        from app.models.user import User
        cols = {c.name: c for c in User.__table__.columns}
        assert cols['email'].unique

    def test_mixin_fields_present(self):
        from app.models.mixins import UUIDPrimaryKeyMixin
        assert hasattr(UUIDPrimaryKeyMixin, 'id')

    def test_all_models_have_tablename(self):
        from app.models import Company
        assert hasattr(Company, '__tablename__')

    def test_compliance_flag_has_fk_to_companies(self):
        from app.models.compliance import ComplianceFlag
        fks = [fk for fk in ComplianceFlag.__table__.foreign_keys]
        assert any('companies' in str(fk.column.table) for fk in fks)

    def test_score_history_has_unique_constraint(self):
        from app.models.compliance import ComplianceScoreHistory
        cs = ComplianceScoreHistory.__table__.constraints
        assert any('company_id' in str(c) and 'snapshot_month' in str(c) for c in cs)

    def test_soft_delete_mixin(self):
        from app.models.mixins import SoftDeleteMixin
        assert hasattr(SoftDeleteMixin, 'is_active')
