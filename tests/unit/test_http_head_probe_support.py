"""HEAD-probe support contract — root and health endpoints answer HEAD.

Platform port scanners (Render's "No open ports detected, continuing to
scan..."), load balancers and many uptime monitors send a bare HEAD request
first. FastAPI's ``@app.get`` / ``@router.get`` do NOT auto-register HEAD
(unlike plain Starlette routes), so every such probe saw ``405 Method Not
Allowed`` against ``/`` and ``/api/v1/health/live`` even though the instance
was perfectly healthy — visible in production deploy logs as
``"HEAD / HTTP/1.1" 405`` followed ~25 s later by the GET that finally
declared the port open.

These pins keep GET intact AND require HEAD on the probe-relevant routes.
Any refactor that drops HEAD from these routes must update this file in the
same PR, stating the PR that justifies the change.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture(scope="module")
def client() -> TestClient:
    # Plain (non-context-manager) TestClient: no lifespan/startup events run,
    # so no DB or Redis connection is opened for these routing-level probes.
    return TestClient(create_app())


def test_root_accepts_get(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["health"] == "/api/v1/health/live"


def test_root_accepts_head_and_returns_empty_body(client: TestClient):
    response = client.head("/")
    assert response.status_code == 200, (
        "platform port-scan probes send HEAD / first; a 405 here delays "
        "open-port detection on every deploy"
    )
    assert response.content == b""  # HEAD must never carry a body


def test_liveness_accepts_get(client: TestClient):
    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


def test_liveness_accepts_head_and_returns_empty_body(client: TestClient):
    response = client.head("/api/v1/health/live")
    assert response.status_code == 200
    assert response.content == b""


def test_readiness_still_answers_head_without_405(client: TestClient):
    # Readiness performs real DB/Redis checks: in a unit-test environment the
    # components are unreachable, so either outcome is governance-correct —
    # what must NEVER come back is 405 (method not registered).
    response = client.head("/api/v1/health/ready")
    assert response.status_code in (200, 503)


def test_full_health_still_answers_head_without_405(client: TestClient):
    response = client.head("/api/v1/health")
    assert response.status_code in (200, 503)
