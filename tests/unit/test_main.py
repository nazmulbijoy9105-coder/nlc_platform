"""Unit tests for application construction and safe HTTP error envelopes."""
import asyncio

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError

from app.main import (
    AccessLogMiddleware,
    RequestIDMiddleware,
    RedactedUnhandledExceptionMiddleware,
    SecurityHeadersMiddleware,
    create_app,
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)


def _request(path="/test"):
    request = Request({
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
    })
    request.state.request_id = "request-test-123"
    return request


def test_create_app_registers_health_rjsc_and_root_routes():
    app = create_app()
    paths = {route.path for route in app.routes}

    assert "/api/v1/health" in paths
    assert "/api/v1/health/live" in paths
    assert "/api/v1/rjsc-forms/{form_id}/filed" in paths
    assert "/" in paths
    middleware = {item.cls for item in app.user_middleware}
    assert {
        RequestIDMiddleware,
        AccessLogMiddleware,
        SecurityHeadersMiddleware,
        RedactedUnhandledExceptionMiddleware,
    }.issubset(middleware)


def test_http_exception_handler_returns_safe_error_envelope():
    response = asyncio.run(
        http_exception_handler(
            _request(),
            HTTPException(status_code=403, detail="Access denied"),
        )
    )

    assert response.status_code == 403
    assert b'"request_id":"request-test-123"' in response.body
    assert b'"detail":"Access denied"' in response.body


def test_validation_exception_handler_formats_field_errors():
    exc = RequestValidationError([{
        "loc": ("query", "page"),
        "msg": "Input should be greater than 0",
        "type": "greater_than",
    }])
    response = asyncio.run(validation_exception_handler(_request(), exc))

    assert response.status_code == 422
    assert b"query \xe2\x86\x92 page" in response.body
    assert b"Request validation failed" in response.body


def test_unhandled_exception_handler_does_not_expose_exception_text():
    response = asyncio.run(
        unhandled_exception_handler(
            _request(),
            RuntimeError("secret database password must not leak"),
        )
    )

    assert response.status_code == 500
    assert b"secret database password" not in response.body
    assert b"request-test-123" in response.body



def test_redacted_exception_middleware_never_returns_request_secrets():
    async def failing_app(scope, receive, send):
        raise RuntimeError("Bearer sensitive-test-token must not escape")

    middleware = RedactedUnhandledExceptionMiddleware(failing_app)
    sent = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "method": "POST",
        "path": "/api/v1/companies/example/evaluate",
        "headers": [(b"authorization", b"Bearer sensitive-test-token")],
        "state": {"request_id": "redaction-test-request"},
    }
    asyncio.run(middleware(scope, receive, send))

    response_start = next(item for item in sent if item["type"] == "http.response.start")
    response_body = b"".join(
        item.get("body", b"") for item in sent if item["type"] == "http.response.body"
    )
    response_headers = dict(response_start["headers"])

    assert response_start["status"] == 500
    assert b"sensitive-test-token" not in response_body
    assert response_headers[b"x-request-id"] == b"redaction-test-request"
    assert response_headers[b"cache-control"].startswith(b"no-store")
