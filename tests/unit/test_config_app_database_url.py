"""The application runtime must never fall back to a privileged DB URL."""

import pytest

from app.core.config import Settings


def test_production_requires_app_database_url():
    settings = Settings(
        _env_file=None,
        ENVIRONMENT="production",
        APP_DATABASE_URL="",
        DATABASE_URL="postgresql://migration_user:secret@localhost/nlc",
    )

    with pytest.raises(
        RuntimeError,
        match="APP_DATABASE_URL is required for production runtime access",
    ):
        _ = settings.ASYNC_APP_DATABASE_URL


def test_render_runtime_requires_app_database_url(monkeypatch):
    import app.core.config as config_module

    monkeypatch.setattr(config_module, "_RENDER_RUNTIME", True)

    settings = Settings(
        _env_file=None,
        ENVIRONMENT="development",
        APP_DATABASE_URL="",
        DATABASE_URL="postgresql://migration_user:secret@localhost/nlc",
    )

    with pytest.raises(
        RuntimeError,
        match="APP_DATABASE_URL is required for production runtime access",
    ):
        _ = settings.ASYNC_APP_DATABASE_URL


def test_production_uses_app_database_url():
    settings = Settings(
        _env_file=None,
        ENVIRONMENT="production",
        APP_DATABASE_URL="postgresql://nlc_app_role:secret@localhost/nlc",
        DATABASE_URL="postgresql://migration_user:secret@localhost/nlc",
    )

    assert settings.ASYNC_APP_DATABASE_URL == (
        "postgresql+asyncpg://nlc_app_role:secret@localhost/nlc"
    )


def test_development_can_use_database_url_fallback():
    settings = Settings(
        _env_file=None,
        ENVIRONMENT="development",
        APP_DATABASE_URL="",
        DATABASE_URL="postgresql://dev_user:secret@localhost/nlc",
    )

    assert settings.ASYNC_APP_DATABASE_URL == (
        "postgresql+asyncpg://dev_user:secret@localhost/nlc"
    )
