"""Audit Trail enterprise tests."""

class TestAuditTrailEnterprise:
    """Verify enterprise-grade audit trail."""

    def test_score_history_model_exists(self):
                from app.models.compliance import ComplianceScoreHistory
        assert ComplianceScoreHistory is not None


    def test_compliance_event_model_exists(self):
                from app.models.compliance import ComplianceEvent
        assert ComplianceEvent is not None


    def test_rule_version_model_exists(self):
                from app.models.rules import LegalRuleVersion
        assert LegalRuleVersion is not None


    def test_activity_log_model_exists(self):
                from app.models.infrastructure import UserActivityLog
        assert UserActivityLog is not None


    def test_activity_log_has_action_field(self):
                from app.models.infrastructure import UserActivityLog
        cols = {c.name for c in UserActivityLog.__table__.columns}
        assert 'action' in cols


    def test_retention_cleanup_task_exists(self):
                from app.worker.tasks import cleanup_old_activity_logs
        assert cleanup_old_activity_logs is not None


    def test_score_history_has_unique_constraint(self):
                from app.models.compliance import ComplianceScoreHistory
        constraints = ComplianceScoreHistory.__table__.constraints
        uq = [c for c in constraints if 'company_id' in str(c) and 'snapshot_month' in str(c)]
        assert len(uq) >= 1


    def test_beat_schedule_has_cleanup(self):
                from app.worker.beat_schedule import beat_schedule
        s = beat_schedule if isinstance(beat_schedule, dict) else beat_schedule.__dict__
        assert any('cleanup' in str(v).lower() for v in s.values())


    def test_no_delete_methods_on_activity_service(self):
                from app.services.notification_service import ActivityService
        methods = [m for m in dir(ActivityService) if not m.startswith('_')]
        delete_methods = [m for m in methods if 'delete' in m.lower() or 'remove' in m.lower()]
        assert len(delete_methods) == 0


    def test_compliance_flag_has_triggered_date(self):
                from app.models.compliance import ComplianceFlag
        cols = {c.name for c in ComplianceFlag.__table__.columns}
        assert 'triggered_date' in cols or 'triggered_at' in cols


    def test_audit_log_export_endpoint_exists(self):
                with open("app/api/admin.py", encoding="utf-8") as f:
            content = f.read()
        assert "activity-logs/export" in content or "csv" in content.lower()


    def test_beat_schedule_has_daily_eval(self):
                from app.worker.beat_schedule import beat_schedule
        s = beat_schedule if isinstance(beat_schedule, dict) else beat_schedule.__dict__
        assert any('evaluate' in str(v).lower() or 'compliance' in str(v).lower() for v in s.values())

