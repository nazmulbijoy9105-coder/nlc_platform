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
