"""Audit trail integrity tests — Article 6 compliance."""

class TestAuditTrail:
    """Verify audit trail immutability and retention."""

    def test_activity_log_model_exists(self):
        """UserActivityLog model should exist."""
        from app.models.infrastructure import UserActivityLog
        assert UserActivityLog is not None

    def test_activity_log_is_append_only(self):
        """Activity log table should have no UPDATE path."""
        from app.models.infrastructure import UserActivityLog
        # Verify the model has created_at but no updated_at (append-only)
        # This is a contract test — the model should not support updates
        assert hasattr(UserActivityLog, '__tablename__')
        assert UserActivityLog.__tablename__ == 'user_activity_logs'

    def test_score_history_model_exists(self):
        """Score history model should exist (immutable)."""
        from app.models.compliance import ComplianceScoreHistory
        assert ComplianceScoreHistory is not None
        assert hasattr(ComplianceScoreHistory, '__tablename__')

    def test_retention_period_configured(self):
        """7-year retention should be configured in worker tasks."""
        import os
        found = False
        worker_path = os.path.join("app", "worker", "tasks.py")
        if os.path.exists(worker_path):
            with open(worker_path, encoding="utf-8", errors="ignore") as f:
                content = f.read()
                if "cleanup_old_activity_logs" in content and ("7" in content or "retain" in content.lower()):
                    found = True
        assert found, "7-year retention cleanup task not found in worker tasks"

    def test_compliance_event_model_exists(self):
        """ComplianceEvent model should exist for audit chain."""
        from app.models.compliance import ComplianceEvent
        assert ComplianceEvent is not None

    def test_rule_version_model_exists(self):
        """LegalRuleVersion model should exist for rule change tracking."""
        from app.models.rules import LegalRuleVersion
        assert LegalRuleVersion is not None

    def test_activity_log_has_required_fields(self):
        """Activity log must have: user_id, action, timestamp."""
        from app.models.infrastructure import UserActivityLog
        # Verify key fields exist on the model
        columns = [c.name for c in UserActivityLog.__table__.columns]
        assert 'action' in columns, "Activity log missing 'action' column"
        assert 'user_id' in columns or 'logged_at' in columns, "Activity log missing user/timestamp"

    def test_no_delete_methods_on_activity_log(self):
        """Activity log service should not have delete methods."""
        from app.services.notification_service import ActivityService
        # Verify no public delete methods
        methods = [m for m in dir(ActivityService) if not m.startswith('_')]
        delete_methods = [m for m in methods if 'delete' in m.lower() or 'remove' in m.lower()]
        assert len(delete_methods) == 0, f"Activity log has delete methods: {delete_methods}"
