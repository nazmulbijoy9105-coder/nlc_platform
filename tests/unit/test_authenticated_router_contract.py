"""Structural authentication certification for every protected API router."""
from __future__ import annotations

from fastapi.routing import APIRoute

from app.core.dependencies import verify_access_token
from app.main import create_app


def _dependency_calls(dependant):
    for dependency in dependant.dependencies:
        yield dependency.call
        yield from _dependency_calls(dependency)


def test_every_route_in_each_protected_router_has_verified_jwt_dependency():
    protected_modules = (
        "companies",
        "portfolio_compliance",
        "filings",
        "rescue",
        "documents",
        "commercial",
        "finance",
        "subscriptions",
        "rjsc_forms",
        "calendar",
        "legal_provenance",
        "rules",
        "admin",
        "notifications",
        "webhooks",
    )
    import importlib

    app = create_app()
    registered = [
        route for route in app.routes if isinstance(route, APIRoute)
    ]
    mount_prefixes = {
        "companies": "/companies",
        "portfolio_compliance": "",
        "filings": "/filings",
        "rescue": "/rescue",
        "documents": "/documents",
        "commercial": "/commercial",
        "finance": "/finance",
        "subscriptions": "/subscriptions",
        "rjsc_forms": "/rjsc-forms",
        "calendar": "",
        "legal_provenance": "",
        "rules": "/rules",
        "admin": "/admin",
        "notifications": "/notifications",
        "webhooks": "/webhooks",
    }

    # Public legal-rule catalogue listing is intentionally read-only and
    # uses the dedicated CATALOG RLS principal instead of a user JWT.
    public_catalogue_endpoints = {
        ("rules", "list_rules"),
        ("admin", "cron_health"),
    }
    service_secret_endpoints = {("admin", "cron_evaluate_all")}
    checked = 0
    for module_name in protected_modules:
        module = importlib.import_module(f"app.api.{module_name}")
        assert module.router.routes, f"{module_name} router unexpectedly has no routes"
        for router_route in module.router.routes:
            if not isinstance(router_route, APIRoute):
                continue
            if (module_name, router_route.endpoint.__name__) in public_catalogue_endpoints:
                continue
            if (module_name, router_route.endpoint.__name__) in service_secret_endpoints:
                continue
            full_path = (
                f"/api/v1{mount_prefixes[module_name]}{router_route.path}"
            )
            app_route = next(
                (
                    candidate for candidate in registered
                    if candidate.path == full_path
                    and candidate.methods == router_route.methods
                    and candidate.endpoint.__name__ == router_route.endpoint.__name__
                ),
                None,
            )
            assert app_route is not None, (
                f"{module_name} route is not mounted: {full_path}"
            )
            calls = set(_dependency_calls(app_route.dependant))
            assert verify_access_token in calls, (
                f"Protected route lacks verified JWT dependency: "
                f"{module_name} {sorted(app_route.methods or [])} {full_path}"
            )
            checked += 1

    assert checked >= len(protected_modules), "No authenticated endpoints were inspected"


def test_company_live_coverage_endpoint_is_company_scoped_and_authenticated():
    app = create_app()
    route = next(
        route for route in app.routes
        if isinstance(route, APIRoute)
        and route.path == "/api/v1/companies/{company_id}/rule-coverage"
    )
    calls = set(_dependency_calls(route.dependant))
    assert verify_access_token in calls
    assert any(
        getattr(call, "__name__", "") == "_check_access"
        for call in calls
    ), "Company coverage must enforce live company membership/assignment"


def _cron_request(secret: str | None = None):
    from starlette.requests import Request

    headers = []
    if secret is not None:
        headers.append((b"x-cron-secret", secret.encode("utf-8")))
    return Request({
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "https",
        "path": "/api/v1/admin/cron/evaluate-all",
        "raw_path": b"/api/v1/admin/cron/evaluate-all",
        "query_string": b"",
        "headers": headers,
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 443),
    })


def test_portfolio_cron_route_fails_closed_without_a_long_secret(monkeypatch):
    import pytest
    from fastapi import HTTPException

    from app.api.admin import cron_evaluate_all

    monkeypatch.delenv("CRON_SECRET", raising=False)
    with pytest.raises(HTTPException) as missing:
        import asyncio
        asyncio.run(cron_evaluate_all(_cron_request(), db=None))
    assert missing.value.status_code == 403

    monkeypatch.setenv("CRON_SECRET", "short")
    with pytest.raises(HTTPException) as short:
        import asyncio
        asyncio.run(cron_evaluate_all(_cron_request("short"), db=None))
    assert short.value.status_code == 503


def test_portfolio_cron_route_rejects_invalid_secret(monkeypatch):
    import asyncio
    import pytest
    from fastapi import HTTPException

    from app.api.admin import cron_evaluate_all

    monkeypatch.setenv("CRON_SECRET", "x" * 48)
    with pytest.raises(HTTPException) as invalid:
        asyncio.run(cron_evaluate_all(_cron_request("wrong-secret"), db=None))
    assert invalid.value.status_code == 403


def test_public_cron_health_endpoint_exposes_only_liveness_metadata():
    import asyncio

    from app.api.admin import cron_health

    result = asyncio.run(cron_health())
    assert result["status"] == "ok"
    assert result["service"] == "nlc-platform"
    assert "time" in result
    assert "company" not in result
    assert "user" not in result
