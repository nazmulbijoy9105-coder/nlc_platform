"""The auth rate limiter must use shared Redis storage in production (audit F-02)."""

import pytest

import app.core.config as config_module
from app.api import auth as auth_module
from app.core.config import Settings

REDIS_URL = "redis://:secret@redis:6379/0"


def _settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


@pytest.mark.parametrize("environment", ["production", "prod", " Production "])
@pytest.mark.parametrize("redis_url", ["", "   ", "memory://", "MEMORY://"])
def test_production_rejects_missing_or_process_local_storage(environment, redis_url):
    settings = _settings(ENVIRONMENT=environment, redis_url=redis_url)

    with pytest.raises(RuntimeError, match="shared Redis URL"):
        auth_module._limiter_storage_uri(settings)


def test_render_runtime_rejects_missing_redis_even_when_environment_is_development(monkeypatch):
    monkeypatch.setattr(config_module, "_RENDER_RUNTIME", True)
    settings = _settings(ENVIRONMENT="development", redis_url="")

    with pytest.raises(RuntimeError, match="shared Redis URL"):
        auth_module._limiter_storage_uri(settings)


def test_production_uses_configured_redis_url():
    settings = _settings(ENVIRONMENT="production", redis_url=f" {REDIS_URL} ")

    assert auth_module._limiter_storage_uri(settings) == REDIS_URL


@pytest.mark.parametrize("environment", ["development", "test"])
def test_non_production_without_redis_uses_process_local_storage(environment):
    settings = _settings(ENVIRONMENT=environment, redis_url="")

    assert auth_module._limiter_storage_uri(settings) == "memory://"


def test_non_production_prefers_configured_redis_url():
    settings = _settings(ENVIRONMENT="development", redis_url=REDIS_URL)

    assert auth_module._limiter_storage_uri(settings) == REDIS_URL


def test_build_limiter_refuses_to_start_in_production_without_redis(monkeypatch):
    settings = _settings(ENVIRONMENT="production", redis_url="")
    monkeypatch.setattr(auth_module, "get_settings", lambda: settings)

    with pytest.raises(RuntimeError, match="shared Redis URL"):
        auth_module._build_limiter()


def test_build_limiter_uses_memory_storage_in_development_without_redis(monkeypatch):
    settings = _settings(ENVIRONMENT="development", redis_url="")
    monkeypatch.setattr(auth_module, "get_settings", lambda: settings)

    limiter = auth_module._build_limiter()

    assert limiter._storage_uri == "memory://"


def test_build_limiter_configures_bounded_redis_timeouts(monkeypatch):
    settings = _settings(ENVIRONMENT="production", redis_url=REDIS_URL)
    captured = {}

    class LimiterStub:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(auth_module, "get_settings", lambda: settings)
    monkeypatch.setattr(auth_module, "Limiter", LimiterStub)

    auth_module._build_limiter()

    assert captured["storage_uri"] == REDIS_URL
    assert captured["storage_options"] == {
        "socket_connect_timeout": 1.0,
        "socket_timeout": 1.0,
    }
