"""Render deployments must never fall back to the privileged migration URL."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]


def _import_database(overrides: dict[str, str], remove: tuple[str, ...] = ()) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    for key in remove:
        env.pop(key, None)
    env.update(overrides)
    return subprocess.run(
        [sys.executable, "-c", "import app.models.database"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_render_runtime_requires_app_database_url_even_without_environment_name():
    result = _import_database(
        {
            "RENDER": "true",
            "DATABASE_URL": "postgresql+asyncpg://migration:secret@localhost/test",
        },
        remove=("ENVIRONMENT", "APP_DATABASE_URL", "REQUIRE_RLS_APP_ROLE"),
    )

    assert result.returncode != 0
    assert "APP_DATABASE_URL is required" in result.stderr


def test_render_runtime_cannot_disable_the_rls_role_guard():
    result = _import_database(
        {
            "RENDER": "true",
            "ENVIRONMENT": "development",
            "DATABASE_URL": "postgresql+asyncpg://migration:secret@localhost/test",
            "APP_DATABASE_URL": "postgresql+asyncpg://app:secret@localhost/test",
            "REQUIRE_RLS_APP_ROLE": "false",
        }
    )

    assert result.returncode != 0
    assert "REQUIRE_RLS_APP_ROLE cannot be disabled in production" in result.stderr


def test_render_runtime_starts_with_explicit_nonprivileged_app_url():
    result = _import_database(
        {
            "RENDER": "true",
            "DATABASE_URL": "postgresql+asyncpg://migration:secret@localhost/test",
            "APP_DATABASE_URL": "postgresql+asyncpg://app:secret@localhost/test",
            "REQUIRE_RLS_APP_ROLE": "true",
            "NLC_RLS_HMAC_SECRET": "ci-only-hmac-secret-with-at-least-32-characters",
        },
        remove=("ENVIRONMENT",),
    )

    assert result.returncode == 0, result.stderr

def test_render_runtime_requires_hmac_signing_secret_at_startup():
    result = _import_database(
        {
            "RENDER": "true",
            "DATABASE_URL": "postgresql+asyncpg://migration:secret@localhost/test",
            "APP_DATABASE_URL": "postgresql+asyncpg://app:secret@localhost/test",
            "REQUIRE_RLS_APP_ROLE": "true",
        },
        remove=("ENVIRONMENT", "NLC_RLS_HMAC_SECRET"),
    )

    assert result.returncode != 0
    assert "NLC_RLS_HMAC_SECRET must contain at least 32 characters" in result.stderr


def _import_worker(overrides: dict[str, str], remove: tuple[str, ...] = ()) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    for key in ("RENDER", "ENVIRONMENT", "DATABASE_URL", "APP_DATABASE_URL",
                "REQUIRE_RLS_APP_ROLE", "NLC_RLS_HMAC_SECRET",
                "CELERY_BROKER_URL", "CELERY_BROKER", "REDIS_URL"):
        env.pop(key, None)
    for key in remove:
        env.pop(key, None)
    env.update(overrides)
    return subprocess.run(
        [sys.executable, "-c", "import app.worker.tasks.core"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_render_settings_force_rls_role_guard_even_with_development_override():
    env = os.environ.copy()
    for key in ("RENDER", "ENVIRONMENT", "REQUIRE_RLS_APP_ROLE"):
        env.pop(key, None)
    env.update({
        "RENDER": "true",
        "ENVIRONMENT": "development",
        "REQUIRE_RLS_APP_ROLE": "false",
    })
    result = subprocess.run(
        [sys.executable, "-c", "from app.core.config import settings; assert settings.REQUIRE_RLS_APP_ROLE"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_render_worker_requires_app_database_url_before_accepting_tasks():
    result = _import_worker(
        {
            "RENDER": "true",
            "ENVIRONMENT": "development",
            "DATABASE_URL": "postgresql://migration:secret@localhost/test",
            "CELERY_BROKER_URL": "redis://localhost:6379/0",
        },
        remove=("APP_DATABASE_URL", "NLC_RLS_HMAC_SECRET"),
    )
    assert result.returncode != 0
    assert "SEC-010: APP_DATABASE_URL is required" in result.stderr


def test_render_worker_requires_hmac_secret_before_accepting_tasks():
    result = _import_worker(
        {
            "RENDER": "true",
            "ENVIRONMENT": "development",
            "APP_DATABASE_URL": "postgresql://app:secret@localhost/test",
            "CELERY_BROKER_URL": "redis://localhost:6379/0",
        },
        remove=("NLC_RLS_HMAC_SECRET",),
    )
    assert result.returncode != 0
    assert "SEC-011: NLC_RLS_HMAC_SECRET" in result.stderr


def test_render_worker_requires_explicit_broker_before_accepting_tasks():
    result = _import_worker(
        {
            "RENDER": "true",
            "ENVIRONMENT": "development",
            "APP_DATABASE_URL": "postgresql://app:secret@localhost/test",
            "NLC_RLS_HMAC_SECRET": "ci-only-hmac-secret-with-at-least-32-characters",
        },
        remove=("CELERY_BROKER_URL", "CELERY_BROKER", "REDIS_URL"),
    )
    assert result.returncode != 0
    assert "SEC-012: CELERY_BROKER_URL or REDIS_URL is required" in result.stderr
