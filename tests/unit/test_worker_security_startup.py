"""Worker startup must enforce the same PostgreSQL identity gate as the API."""

import pytest

from app.worker.celery_app import configure_worker


def test_worker_startup_verifies_runtime_database_role(monkeypatch):
    import app.models.database as database

    calls = []

    async def verify():
        calls.append("verified")

    monkeypatch.setattr(database, "verify_runtime_database_role", verify)

    configure_worker(sender="unit-test-worker")

    assert calls == ["verified"]


def test_worker_startup_fails_closed_when_runtime_role_is_unsafe(monkeypatch):
    import app.models.database as database

    async def reject():
        raise RuntimeError("unsafe runtime role")

    monkeypatch.setattr(database, "verify_runtime_database_role", reject)

    with pytest.raises(RuntimeError, match="unsafe runtime role"):
        configure_worker(sender="unit-test-worker")
