"""Auth rate-limit breaches must return 429 with Retry-After (audit F-02)."""

import inspect

import pytest
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api import auth as auth_module
from app.core.config import Settings


@pytest.fixture
def development_limiter(monkeypatch):
    settings = Settings(_env_file=None, ENVIRONMENT="development", redis_url="")
    monkeypatch.setattr(auth_module, "get_settings", lambda: settings)
    return auth_module._build_limiter()


def test_shared_limiter_emits_rate_limit_headers():
    assert auth_module.limiter._headers_enabled is True


def test_every_limited_auth_endpoint_accepts_the_response_parameter():
    limited = {name.rsplit(".", 1)[-1] for name in auth_module.limiter._route_limits}
    endpoints = {
        route.endpoint.__name__: route.endpoint
        for route in auth_module.router.routes
        if route.endpoint.__name__ in limited
    }

    assert limited == {"login", "confirm_2fa_setup", "verify_2fa"}
    assert set(endpoints) == limited
    for name, endpoint in endpoints.items():
        assert "response" in inspect.signature(endpoint).parameters, name


def test_breach_returns_429_with_retry_after_and_success_carries_limit_headers(
    development_limiter,
):
    app = FastAPI()
    app.state.limiter = development_limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    @app.post("/limited")
    @development_limiter.limit("2/minute")
    async def limited(request: Request, response: Response):
        return {"ok": True}

    client = TestClient(app)
    first = client.post("/limited")
    assert first.status_code == 200
    assert first.headers["X-RateLimit-Limit"] == "2"
    assert client.post("/limited").status_code == 200

    breached = client.post("/limited")

    assert breached.status_code == 429
    assert 0 < int(breached.headers["Retry-After"]) <= 60
