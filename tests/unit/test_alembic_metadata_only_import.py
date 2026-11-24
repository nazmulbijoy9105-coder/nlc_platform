"""Alembic metadata imports must not initialise the production API database pool."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]


def _run_import(*, alembic_process: bool, metadata_only: bool = True) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    for key in (
        "APP_DATABASE_URL",
        "DATABASE_URL",
        "NLC_RLS_HMAC_SECRET",
        "REQUIRE_RLS_APP_ROLE",
        "RENDER",
        "ENVIRONMENT",
        "NLC_ALEMBIC_METADATA_ONLY",
    ):
        env.pop(key, None)
    env.update(
        {
            "ENVIRONMENT": "production",
            "RENDER": "true",
            "MIGRATION_DATABASE_URL": "postgresql://migration:secret@localhost/nlc",
        }
    )
    if metadata_only:
        env["NLC_ALEMBIC_METADATA_ONLY"] = "1"
    command = (
        "import sys; "
        + ("sys.argv[0] = 'alembic'; " if alembic_process else "")
        + "import app.models; "
        + "from app.models.database import AsyncSessionLocal, DATABASE_URL, engine; "
        + "assert len(app.models.Base.metadata.tables) > 0; "
        + (
            "assert AsyncSessionLocal is None and engine is None and DATABASE_URL == ''"
            if alembic_process
            else "assert AsyncSessionLocal is not None and engine is not None"
        )
    )
    return subprocess.run(
        [sys.executable, "-c", command],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_alembic_metadata_import_does_not_require_runtime_api_secrets_or_pool():
    result = _run_import(alembic_process=True)
    assert result.returncode == 0, result.stderr


def test_metadata_only_flag_cannot_bypass_runtime_guard_outside_alembic_cli():
    result = _run_import(alembic_process=False)
    assert result.returncode != 0
    assert "APP_DATABASE_URL is required" in result.stderr


def test_metadata_only_flag_without_migration_url_is_not_accepted():
    env = os.environ.copy()
    for key in (
        "APP_DATABASE_URL",
        "DATABASE_URL",
        "NLC_RLS_HMAC_SECRET",
        "REQUIRE_RLS_APP_ROLE",
        "RENDER",
        "ENVIRONMENT",
    ):
        env.pop(key, None)
    env.update(
        {
            "ENVIRONMENT": "production",
            "RENDER": "true",
            "NLC_ALEMBIC_METADATA_ONLY": "1",
        }
    )
    result = subprocess.run(
        [sys.executable, "-c", "import app.models.database"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "APP_DATABASE_URL is required" in result.stderr
