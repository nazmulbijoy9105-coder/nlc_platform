"""Worker task registry and beat-schedule contract tests."""


def test_celery_app_exists():
    from app.worker.celery_app import celery_app

    assert celery_app is not None


def test_evaluation_and_document_tasks_are_exported():
    from app.worker.tasks import (
        evaluate_all_companies,
        evaluate_company_compliance,
        generate_ai_document_async,
    )

    assert evaluate_all_companies is not None
    assert evaluate_company_compliance is not None
    assert generate_ai_document_async is not None


def test_maintenance_tasks_are_exported():
    from app.worker.tasks import (
        cleanup_expired_notifications,
        cleanup_old_activity_logs,
        database_health_check,
        monthly_score_snapshot_all,
    )

    assert cleanup_expired_notifications is not None
    assert cleanup_old_activity_logs is not None
    assert database_health_check is not None
    assert monthly_score_snapshot_all is not None


def test_beat_schedule_has_daily_evaluation_and_log_retention():
    from app.worker.beat_schedule import BEAT_SCHEDULE

    tasks = {entry["task"] for entry in BEAT_SCHEDULE.values()}
    assert "app.worker.tasks.evaluate_all_companies" in tasks
    assert "app.worker.tasks.cleanup_old_activity_logs" in tasks
