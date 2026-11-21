from __future__ import annotations

import pytest

from app.core.config import Settings


def test_production_runtime_url_requires_dedicated_app_database_url():
    settings = Settings(
        ENVIRONMENT="production",
        REQUIRE_RLS_APP_ROLE=True,
        DATABASE_URL="postgresql://migration_owner:secret@db.example.test/nlc",
        APP_DATABASE_URL="",
    )

    with pytest.raises(RuntimeError, match="APP_DATABASE_URL is required"):
        _ = settings.ASYNC_APP_DATABASE_URL


def test_production_runtime_url_uses_only_app_database_url():
    settings = Settings(
        ENVIRONMENT="production",
        REQUIRE_RLS_APP_ROLE=True,
        DATABASE_URL="postgresql://migration_owner:secret@db.example.test/nlc",
        APP_DATABASE_URL="postgresql://nlc_app_role:runtime@db.example.test/nlc",
    )

    assert settings.ASYNC_APP_DATABASE_URL.startswith(
        "postgresql+asyncpg://nlc_app_role:runtime@"
    )
    assert "migration_owner" not in settings.ASYNC_APP_DATABASE_URL


def test_legacy_async_database_url_alias_is_runtime_scoped():
    settings = Settings(
        ENVIRONMENT="production",
        REQUIRE_RLS_APP_ROLE=True,
        DATABASE_URL="postgresql://migration_owner:secret@db.example.test/nlc",
        APP_DATABASE_URL="postgresql://nlc_app_role:runtime@db.example.test/nlc",
    )

    assert settings.ASYNC_DATABASE_URL == settings.ASYNC_APP_DATABASE_URL
    assert "migration_owner" not in settings.ASYNC_DATABASE_URL


def test_development_may_use_database_url_when_app_role_is_not_required():
    settings = Settings(
        ENVIRONMENT="development",
        REQUIRE_RLS_APP_ROLE=False,
        DATABASE_URL="postgresql://dev_user:dev@localhost/nlc",
        APP_DATABASE_URL="",
    )

    assert settings.ASYNC_APP_DATABASE_URL.startswith(
        "postgresql+asyncpg://dev_user:dev@"
    )


def test_production_sync_url_is_also_runtime_scoped():
    settings = Settings(
        ENVIRONMENT="production",
        REQUIRE_RLS_APP_ROLE=True,
        DATABASE_URL="postgresql://migration_owner:secret@db.example.test/nlc",
        APP_DATABASE_URL="postgresql://nlc_app_role:runtime@db.example.test/nlc",
    )

    assert settings.SYNC_DATABASE_URL.startswith(
        "postgresql://nlc_app_role:runtime@"
    )
    assert "migration_owner" not in settings.SYNC_DATABASE_URL
