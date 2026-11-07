"""Worker startup and event-loop lifecycle must enforce DB safety."""

import pytest

from app.worker.celery_app import verify_worker_runtime_security
from app.worker.tasks.core import run_async


def test_worker_process_verifies_runtime_database_role(monkeypatch):
    import app.models.database as database

    calls = []

    async def verify():
        calls.append("verified")

    async def dispose():
        calls.append("disposed")

    monkeypatch.setattr(database, "verify_runtime_database_role", verify)
    monkeypatch.setattr(database, "dispose_engine", dispose)

    verify_worker_runtime_security()

    assert calls == ["verified", "disposed"]


def test_worker_process_fails_closed_when_runtime_role_is_unsafe(monkeypatch):
    import app.models.database as database

    async def reject():
        raise RuntimeError("unsafe runtime role")

    async def dispose():
        return None

    monkeypatch.setattr(database, "verify_runtime_database_role", reject)
    monkeypatch.setattr(database, "dispose_engine", dispose)

    with pytest.raises(RuntimeError, match="unsafe runtime role"):
        verify_worker_runtime_security()


def test_worker_task_disposes_async_engine_before_closing_event_loop(monkeypatch):
    import app.models.database as database

    calls = []

    async def dispose():
        calls.append("disposed")

    async def task_body():
        return "task-result"

    monkeypatch.setattr(database, "dispose_engine", dispose)

    assert run_async(task_body()) == "task-result"
    assert calls == ["disposed"]


def test_first_task_gates_non_prefork_worker_pools(monkeypatch):
    import types

    import app.worker.celery_app as celery_app

    calls = []
    monkeypatch.setattr(celery_app, "_worker_runtime_verified", False)
    monkeypatch.setattr(
        celery_app,
        "verify_worker_runtime_security",
        lambda: calls.append("verified"),
    )

    celery_app.on_task_prerun(
        task_id="task-1",
        task=types.SimpleNamespace(name="unit-test-task"),
        args=(),
        kwargs={},
    )

    assert calls == ["verified"]

def test_eager_tasks_default_off_in_production(monkeypatch):
    import app.worker.celery_app as celery_app

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.delenv("CELERY_TASK_ALWAYS_EAGER", raising=False)

    assert celery_app._resolve_task_always_eager() is False


def test_eager_tasks_rejected_in_production(monkeypatch):
    import app.worker.celery_app as celery_app

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("CELERY_TASK_ALWAYS_EAGER", "true")

    with pytest.raises(RuntimeError, match="forbidden in production"):
        celery_app._resolve_task_always_eager()


def test_eager_tasks_remain_available_for_development(monkeypatch):
    import app.worker.celery_app as celery_app

    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.delenv("CELERY_TASK_ALWAYS_EAGER", raising=False)

    assert celery_app._resolve_task_always_eager() is True
