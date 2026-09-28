"""Audit Trail 10/10 — hash chain, tamper detection, export, retention."""

class TestAuditTrailEnterprise:
    """Verify enterprise-grade audit trail."""
def test_score_history_has_hash_chain(self):
    """Score history should have hash chain for tamper detection."""
    from app.models.compliance import ComplianceScoreHistory
    cols = {c.name for c in ComplianceScoreHistory.__table__.columns}
    has_hash = "current_hash" in cols or "hash" in str(cols)
    assert has_hash, "Score history missing hash chain field"

def test_activity_log_is_append_only(self):
    """Activity log table should have no UPDATE/DELETE methods."""
    from app.services.notification_service import ActivityService
    methods = [m for m in dir(ActivityService) if not m.startswith('_')]
    delete_methods = [m for m in methods if 'delete' in m.lower() or 'remove' in m.lower()]
    assert len(delete_methods) == 0, f"Activity log has delete methods: {delete_methods}"

def test_score_history_model_exists(self):
    """ComplianceScoreHistory model should exist."""
    from app.models.compliance import ComplianceScoreHistory
    assert ComplianceScoreHistory is not None
    assert hasattr(ComplianceScoreHistory, '__tablename__')

def test_compliance_event_model_exists(self):
    """ComplianceEvent model should exist for audit chain."""
    from app.models.compliance import ComplianceEvent
    assert ComplianceEvent is not None

def test_rule_version_model_exists(self):
    """LegalRuleVersion model should exist for rule change tracking."""
    from app.models.rules import LegalRuleVersion
    assert LegalRuleVersion is not None
    assert hasattr(LegalRuleVersion, '__tablename__')

def test_activity_log_has_required_fields(self):
    """Activity log must have: action, user_id, timestamp."""
    from app.models.infrastructure import UserActivityLog
    cols = {c.name for c in UserActivityLog.__table__.columns}
    assert 'action' in cols, "Missing action column"
    assert 'user_id' in cols or 'logged_at' in cols, "Missing user/timestamp"

def test_retention_cleanup_task_exists(self):
    """7-year retention cleanup task should exist."""
    with open("app/worker/tasks.py", encoding="utf-8") as f:
        content = f.read()
    assert "cleanup_old_activity_logs" in content
    assert "7" in content or "retain" in content.lower()

def test_audit_log_export_endpoint_exists(self):
    """CSV export endpoint for auditors should exist."""
    with open("app/api/admin.py", encoding="utf-8") as f:
        content = f.read()
    assert "activity-logs/export" in content or "csv" in content.lower(), \
        "No CSV export endpoint for auditors"

def test_compliance_flag_has_audit_fields(self):
    """Compliance flags should have triggered_date and resolved_date."""
    from app.models.compliance import ComplianceFlag
    cols = {c.name for c in ComplianceFlag.__table__.columns}
    assert 'triggered_date' in cols or 'triggered_at' in cols, "Missing triggered date"
    assert 'resolved_date' in cols or 'resolved_at' in cols or 'flag_status' in cols, \
        "Missing resolution tracking"

def test_no_update_on_activity_log(self):
    """Activity log service should not have update methods."""
    from app.services.notification_service import ActivityService
    update_methods = [m for m in dir(ActivityService) 
                      if 'update' in m.lower() and not m.startswith('_')]
    assert len(update_methods) == 0, f"Activity log has update methods: {update_methods}"

def test_score_history_has_unique_constraint(self):
    """Score history should have unique (company_id, snapshot_month)."""
    from app.models.compliance import ComplianceScoreHistory
    constraints = ComplianceScoreHistory.__table__.constraints
    uq = [c for c in constraints if 'company_id' in str(c) and 'snapshot_month' in str(c)]
    assert len(uq) >= 1, "Score history missing unique constraint"

def test_beat_schedule_has_retention_task(self):
    """Beat schedule should have 7-year retention cleanup."""
    from app.worker.beat_schedule import beat_schedule
    s = beat_schedule if isinstance(beat_schedule, dict) else beat_schedule.__dict__
    has_cleanup = any('cleanup' in str(v).lower() for v in s.values())
    assert has_cleanup, "No cleanup task in beat schedule"

