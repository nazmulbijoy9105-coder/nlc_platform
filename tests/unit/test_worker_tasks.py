"""Worker task tests."""

class TestWorkerTasks:
    def test_celery_app_exists(self):
        from app.worker.celery_app import celery_app
        assert celery_app is not None

    def test_evaluate_task_exists(self):
        from app.worker.tasks import evaluate_all_companies
        assert evaluate_all_companies is not None

    def test_cleanup_task_exists(self):
        from app.worker.tasks import cleanup_old_activity_logs
        assert cleanup_old_activity_logs is not None

    def test_ai_document_task_exists(self):
        from app.worker.tasks import generate_ai_document_async
        assert generate_ai_document_async is not None

    def test_beat_schedule_exists(self):
        from app.worker.beat_schedule import beat_schedule
        assert beat_schedule is not None

    def test_beat_has_daily_eval(self):
        from app.worker.beat_schedule import beat_schedule
        s = beat_schedule if isinstance(beat_schedule, dict) else beat_schedule.__dict__
        assert any("evaluate" in str(v).lower() or "compliance" in str(v).lower() for v in s.values())

    def test_beat_has_cleanup(self):
        from app.worker.beat_schedule import beat_schedule
        s = beat_schedule if isinstance(beat_schedule, dict) else beat_schedule.__dict__
        assert any("cleanup" in str(v).lower() for v in s.values())
