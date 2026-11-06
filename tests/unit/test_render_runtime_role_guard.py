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
        },
        remove=("ENVIRONMENT",),
    )

    assert result.returncode == 0, result.stderr
