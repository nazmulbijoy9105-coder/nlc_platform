"""Unit tests for health, liveness, and readiness endpoint decisions."""
from fastapi import status
import pytest

from app.api import health


@pytest.mark.asyncio
async def test_liveness_reports_alive():
    response = await health.liveness()
    assert response["status"] == "alive"
    assert response["timestamp"]


@pytest.mark.asyncio
async def test_readiness_returns_200_when_database_and_redis_are_usable(monkeypatch):
    async def database():
        return health.ComponentHealth(status="ok", response_ms=2.0)

    async def redis():
        return health.ComponentHealth(status="degraded", response_ms=4.0)

    monkeypatch.setattr(health, "_check_database", database)
    monkeypatch.setattr(health, "_check_redis", redis)

    response = await health.readiness()

    assert response.status_code == status.HTTP_200_OK
    assert b'"ready":true' in response.body
    assert b'"redis":"degraded"' in response.body


@pytest.mark.asyncio
async def test_readiness_returns_503_when_database_is_unavailable(monkeypatch):
    async def database():
        return health.ComponentHealth(status="error", detail="database down")

    async def redis():
        return health.ComponentHealth(status="ok")

    monkeypatch.setattr(health, "_check_database", database)
    monkeypatch.setattr(health, "_check_redis", redis)

    response = await health.readiness()

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert b'"ready":false' in response.body


@pytest.mark.asyncio
async def test_full_health_is_healthy_when_all_components_are_healthy(monkeypatch):
    async def ok():
        return health.ComponentHealth(status="ok")

    monkeypatch.setattr(health, "_check_database", ok)
    monkeypatch.setattr(health, "_check_redis", ok)
    monkeypatch.setattr(health, "_check_s3", ok)
    monkeypatch.setattr(
        health, "_check_celery_workers",
        lambda: health.ComponentHealth(status="ok"),
    )

    response = await health.full_health_check()

    assert response.status_code == status.HTTP_200_OK
    assert b'"status":"healthy"' in response.body
    assert b'"celery_workers"' in response.body


@pytest.mark.asyncio
async def test_full_health_degrades_when_optional_component_fails(monkeypatch):
    async def ok():
        return health.ComponentHealth(status="ok")

    async def s3_error():
        return health.ComponentHealth(status="error", detail="S3 unavailable")

    monkeypatch.setattr(health, "_check_database", ok)
    monkeypatch.setattr(health, "_check_redis", ok)
    monkeypatch.setattr(health, "_check_s3", s3_error)
    monkeypatch.setattr(
        health, "_check_celery_workers",
        lambda: health.ComponentHealth(status="degraded"),
    )

    response = await health.full_health_check()

    assert response.status_code == status.HTTP_200_OK
    assert b'"status":"degraded"' in response.body


@pytest.mark.asyncio
async def test_full_health_handles_celery_probe_exception(monkeypatch):
    async def ok():
        return health.ComponentHealth(status="ok")

    def broken_celery():
        raise RuntimeError("broker probe failed")

    monkeypatch.setattr(health, "_check_database", ok)
    monkeypatch.setattr(health, "_check_redis", ok)
    monkeypatch.setattr(health, "_check_s3", ok)
    monkeypatch.setattr(health, "_check_celery_workers", broken_celery)

    response = await health.full_health_check()

    assert response.status_code == status.HTTP_200_OK
    assert b'"status":"degraded"' in response.body
    assert b"Celery check skipped" in response.body


@pytest.mark.asyncio
async def test_s3_check_reports_unconfigured_as_ok(monkeypatch):
    monkeypatch.setattr(health.settings, "aws_s3_bucket", None)

    result = await health._check_s3()

    assert result.status == "ok"
    assert "not configured" in result.detail.lower()


def test_celery_check_reports_healthy_worker(monkeypatch):
    from app.worker import celery_app

    monkeypatch.setattr(
        celery_app,
        "check_worker_health",
        lambda: {
            "status": "healthy",
            "active_workers": 1,
            "active_tasks": 2,
        },
    )

    result = health._check_celery_workers()

    assert result.status == "ok"
    assert "Responding workers: 1" in result.detail
    assert "active tasks: 2" in result.detail


def test_celery_check_degrades_when_no_workers_respond(monkeypatch):
    from app.worker import celery_app

    monkeypatch.setattr(
        celery_app,
        "check_worker_health",
        lambda: {"status": "no_workers"},
    )

    result = health._check_celery_workers()

    assert result.status == "degraded"
    assert "No responding Celery workers" in result.detail
