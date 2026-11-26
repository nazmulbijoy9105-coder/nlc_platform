"""The auth rate limiter must use dedicated Redis storage in production (audit F-02)."""

import pytest

import app.core.config as config_module
from app.api import auth as auth_module
from app.core.config import Settings

REDIS_URL = "redis://:secret@redis:6379/0"


def _settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


@pytest.mark.parametrize("environment", ["production", "prod", " Production "])
@pytest.mark.parametrize("redis_url", ["", "   "])
def test_production_rejects_missing_dedicated_redis_storage(environment, redis_url):
    settings = _settings(ENVIRONMENT=environment, REDIS_URL=redis_url)

    with pytest.raises(RuntimeError, match="dedicated REDIS_URL"):
        auth_module._limiter_storage_uri(settings)


@pytest.mark.parametrize("environment", ["production", "prod"])
@pytest.mark.parametrize("redis_url", ["amqp://broker.example/vhost", "https://cache.example"])
def test_production_rejects_non_redis_limiter_storage_scheme(environment, redis_url):
    settings = _settings(
        ENVIRONMENT=environment,
        REDIS_URL=redis_url,
        CELERY_BROKER_URL=redis_url,
    )

    with pytest.raises(RuntimeError, match="redis:// or rediss://"):
        auth_module._limiter_storage_uri(settings)


def test_render_runtime_rejects_missing_redis_even_when_environment_is_development(monkeypatch):
    monkeypatch.setattr(config_module, "_RENDER_RUNTIME", True)
    settings = _settings(ENVIRONMENT="development", REDIS_URL="")

    with pytest.raises(RuntimeError, match="dedicated REDIS_URL"):
        auth_module._limiter_storage_uri(settings)


def test_production_uses_configured_dedicated_redis_url():
    settings = _settings(ENVIRONMENT="production", REDIS_URL=f" {REDIS_URL} ")

    assert auth_module._limiter_storage_uri(settings) == REDIS_URL


@pytest.mark.parametrize("environment", ["development", "test"])
def test_non_production_without_redis_uses_process_local_storage(environment):
    settings = _settings(ENVIRONMENT=environment, REDIS_URL="")

    assert auth_module._limiter_storage_uri(settings) == "memory://"


def test_non_production_falls_back_to_memory_for_non_redis_celery_broker():
    settings = _settings(
        ENVIRONMENT="development",
        REDIS_URL="",
        CELERY_BROKER_URL="amqp://rabbitmq:5672/",
    )

    assert auth_module._limiter_storage_uri(settings) == "memory://"


def test_non_production_ignores_non_redis_legacy_redis_url_alias():
    settings = _settings(
        ENVIRONMENT="development",
        REDIS_URL="",
        redis_url="amqp://rabbitmq:5672/",
    )

    assert auth_module._limiter_storage_uri(settings) == "memory://"


@pytest.mark.parametrize("environment", ["development", "test"])
def test_non_production_prefers_configured_redis_url(environment):
    settings = _settings(ENVIRONMENT=environment, REDIS_URL=REDIS_URL)

    assert auth_module._limiter_storage_uri(settings) == REDIS_URL


def test_non_production_rejects_unsupported_explicit_url_by_using_memory():
    settings = _settings(
        ENVIRONMENT="development",
        REDIS_URL="amqp://rabbitmq:5672/",
    )

    assert auth_module._limiter_storage_uri(settings) == "memory://"


def test_build_limiter_refuses_to_start_in_production_without_dedicated_redis(monkeypatch):
    settings = _settings(ENVIRONMENT="production", REDIS_URL="")
    monkeypatch.setattr(auth_module, "get_settings", lambda: settings)

    with pytest.raises(RuntimeError, match="dedicated REDIS_URL"):
        auth_module._build_limiter()


def test_build_limiter_uses_memory_storage_in_development_without_redis(monkeypatch):
    settings = _settings(
        ENVIRONMENT="development",
        REDIS_URL="",
        CELERY_BROKER_URL="amqp://rabbitmq:5672/",
    )
    monkeypatch.setattr(auth_module, "get_settings", lambda: settings)

    limiter = auth_module._build_limiter()

    assert limiter._storage_uri == "memory://"


def test_build_limiter_configures_bounded_redis_timeouts(monkeypatch):
    settings = _settings(ENVIRONMENT="production", REDIS_URL=REDIS_URL)
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
    assert captured["in_memory_fallback"] == ["10/minute"]
    assert captured["in_memory_fallback_enabled"] is False


def test_production_limiter_connects_to_the_ci_redis_service(monkeypatch):
    """Exercise the actual Redis storage backend in production mode when CI provides it."""
    import os

    redis_url = os.environ.get("REDIS_URL", "").strip()
    if not redis_url:
        pytest.skip("REDIS_URL is provided by the CI Redis service")

    settings = _settings(ENVIRONMENT="production", REDIS_URL=redis_url)
    monkeypatch.setattr(auth_module, "get_settings", lambda: settings)

    limiter = auth_module._build_limiter()

    assert limiter._storage_uri == redis_url
    assert limiter._storage.check() is True
