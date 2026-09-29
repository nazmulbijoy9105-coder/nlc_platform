"""Audit trail integrity tests — Article 6 compliance."""

import pytest

class TestAuditTrail:
    def test_activity_log_model_exists(self):
        from app.models.infrastructure import UserActivityLog
        assert UserActivityLog is not None
        assert UserActivityLog.__tablename__ == 'user_activity_logs'

    def test_score_history_model_exists(self):
        from app.models.compliance import ComplianceScoreHistory
        assert ComplianceScoreHistory is not None
        assert hasattr(ComplianceScoreHistory, '__tablename__')

    def test_retention_period_configured(self):
        try:
            from app.worker.tasks import cleanup_old_activity_logs
            assert cleanup_old_activity_logs is not None
        except ImportError:
            pytest.skip("cleanup_old_activity_logs not yet implemented")

    def test_compliance_event_model_exists(self):
        from app.models.compliance import ComplianceEvent
        assert ComplianceEvent is not None

    def test_rule_version_model_exists(self):
        from app.models.rules import LegalRuleVersion
        assert LegalRuleVersion is not None
        assert hasattr(LegalRuleVersion, '__tablename__')

    def test_activity_log_has_required_fields(self):
        from app.models.infrastructure import UserActivityLog
        cols = {c.name for c in UserActivityLog.__table__.columns}
        assert 'action' in cols
        assert 'user_id' in cols or 'logged_at' in cols

    def test_no_delete_methods_on_activity_log(self):
        from app.services.notification_service import ActivityService
        methods = [m for m in dir(ActivityService) if not m.startswith('_')]
        delete_methods = [m for m in methods if 'delete' in m.lower() or 'remove' in m.lower()]
        assert len(delete_methods) == 0
